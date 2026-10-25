"""One locked Q0 execution: only synthetic statistics and named source/metadata hashes."""
from __future__ import annotations
import os
for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[name]='1'
os.environ['PYTHONDONTWRITEBYTECODE']='1'
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time
import zipfile

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/quality_tolerant/q0'
LOCK_PATH=ROOT/'docs/studies/quality-tolerant/q0-lock.json'
SOURCE_LOCK=ROOT/'docs/studies/quality-tolerant/q0-source-lock.json'


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1<<20),b''):h.update(chunk)
    return h.hexdigest()


def write_new(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(value,stream,indent=2,sort_keys=True,allow_nan=False); stream.write('\n')


def git(*args):
    return subprocess.check_output(['git.exe',*args],cwd=ROOT,text=True,timeout=30).strip()


def now(): return datetime.now(timezone.utc).isoformat()


def verify():
    receipt=json.loads((OUT/'execution.json').read_text())
    for rel,sha in receipt['source_sha256'].items():
        if digest(ROOT/rel)!=sha:raise RuntimeError('Executed source changed: '+rel)
    for rel,sha in receipt['protected_sha256'].items():
        if digest(ROOT/rel)!=sha:raise RuntimeError('Historical metadata changed: '+rel)
    for rel,sha in receipt['artifact_sha256'].items():
        if digest(OUT/rel)!=sha:raise RuntimeError('Artifact changed: '+rel)
    lock=json.loads(LOCK_PATH.read_text())
    assert receipt['counts']=={k:lock['limits'][k] for k in ['trials','bootstrap_draws','datasets']}
    assert receipt['status']=='synthetic_validation_complete'
    assert receipt['forbidden_work']==lock['forbidden_work_caps']
    assert receipt['model_libraries_imported'] is False
    assert receipt['wall_seconds']<=lock['limits']['wall_seconds']
    assert receipt['max_rss_bytes']<=lock['limits']['memory_bytes']
    assert sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file())<=lock['limits']['storage_bytes']
    print(json.dumps({'verified':True,'counts':receipt['counts'],'lock_commit':receipt['source_commit'],
                      'historical_sources_unchanged':True,'no_simulation_reexecution':True}))


def run():
    start=time.monotonic(); started=now(); lock=json.loads(LOCK_PATH.read_text())
    # Import heavy statistical libraries only after applying the locked limits.
    limits=lock['limits']; resource.setrlimit(resource.RLIMIT_AS,(limits['memory_bytes'],limits['memory_bytes']))
    resource.setrlimit(resource.RLIMIT_CPU,(limits['cpu_seconds'],limits['cpu_seconds']))
    def expired(*_): raise TimeoutError('Q0 wall cap exhausted')
    signal.signal(signal.SIGALRM,expired); signal.alarm(limits['wall_seconds'])
    def check():
        if time.monotonic()-start>limits['wall_seconds']: raise TimeoutError('Q0 wall cap exhausted')
        if sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file())>limits['storage_bytes']:
            raise RuntimeError('Q0 durable storage cap exhausted')
    if (OUT/'started.json').exists(): raise RuntimeError('One execution only: existing start receipt')
    head=git('rev-parse','HEAD'); remote=git('ls-remote','origin','refs/heads/main').split()[0]
    if head!=remote:raise RuntimeError('Local/live main mismatch')
    if git('branch','--show-current')!='main':raise RuntimeError('Require main')
    if git('status','--porcelain=v1','--untracked-files=all'):raise RuntimeError('Require clean checkout before execution')
    frozen=json.loads(SOURCE_LOCK.read_text())
    for rel,sha in frozen['source_sha256'].items():
        if digest(ROOT/rel)!=sha: raise RuntimeError('Lock/source mismatch: '+rel)
    protected={rel:digest(ROOT/rel) for rel in frozen['protected_paths']}
    hashes=dict(frozen['source_sha256']); hashes[str(SOURCE_LOCK.relative_to(ROOT))]=digest(SOURCE_LOCK)
    OUT.mkdir(parents=True,exist_ok=True)
    write_new(OUT/'started.json',{'stage':'Q0','started_utc':started,'source_commit':head,
        'verified_live_remote':remote,'source_sha256':hashes,'protected_sha256':protected})
    counts={}; status='failed'; phase='tests'
    try:
        with zipfile.ZipFile(OUT/'execution-sources.zip','x',compression=zipfile.ZIP_DEFLATED) as archive:
            for rel in hashes: archive.write(ROOT/rel,rel)
        check()
        remaining=max(1,limits['wall_seconds']-int(time.monotonic()-start))
        completed=subprocess.run([sys.executable,'-m','pytest','tests/test_q0_statistics.py','-q','-p','no:cacheprovider',
            '--junitxml=results/quality_tolerant/q0/focused-tests.xml'],cwd=ROOT,
            text=True,capture_output=True,timeout=remaining)
        (OUT/'test-output.txt').write_text(completed.stdout+completed.stderr,encoding='utf-8')
        if completed.returncode: raise RuntimeError('Focused synthetic tests failed; do not simulate')
        sys.path.insert(0,str(ROOT/'src'))
        import numpy, scipy, sacrebleu
        from anytime_ncm.q0_statistics import Budget, analytical, trials, text_bootstrap, timing_bootstrap
        phase='analytic'
        write_new(OUT/'statistical-feasibility.json',analytical(lock))
        with (OUT/'ledger.jsonl').open('x',encoding='utf-8') as ledger:
            budget=Budget(limits,ledger); counts=budget.counts
            phase='trials'; write_new(OUT/'synthetic-trials.json',trials(lock,budget,check))
            phase='corpus'; write_new(OUT/'synthetic-corpus.json',text_bootstrap(lock,budget,check))
            phase='timing'; write_new(OUT/'synthetic-timing.json',timing_bootstrap(lock,budget,check))
        for k in counts:
            if counts[k]!=limits[k]:raise AssertionError('Frozen counts incomplete')
        for rel,sha in protected.items():
            if digest(ROOT/rel)!=sha: raise RuntimeError('Historical/reservation hash changed')
        model_imported=any(x.split('.')[0] in {'torch','transformers','anytime_ncm.wmt_model'} for x in sys.modules)
        if model_imported:raise RuntimeError('Forbidden model library import')
        check(); status='synthetic_validation_complete'
        artifact_sha={p.name:digest(p) for p in OUT.iterdir() if p.is_file()}
        rss=max(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)*1024
        write_new(OUT/'execution.json',{'stage':'Q0','status':status,'source_commit':head,
            'verified_live_remote_before_tests':remote,'started_utc':started,'finished_utc':now(),
            'wall_seconds':time.monotonic()-start,'preparation_reporting_charge_seconds':7200,
            'charged_wall_seconds':7200+time.monotonic()-start,'cpu_seconds_self':resource.getrusage(resource.RUSAGE_SELF).ru_utime+resource.getrusage(resource.RUSAGE_SELF).ru_stime,
            'max_rss_bytes':rss,'counts':dict(counts),'source_sha256':hashes,
            'protected_sha256':protected,'artifact_sha256':artifact_sha,
            'python':sys.version,'numpy':numpy.__version__,'scipy':scipy.__version__,'sacrebleu':sacrebleu.__version__,
            'model_libraries_imported':False,'forbidden_work':lock['forbidden_work_caps'],
            'cost_dollars':0,'note':'Synthetic validation is not empirical feasibility or bootstrap coverage certification.'})
        phase='verify'; verify()
    except BaseException as error:
        write_new(OUT/'failure.json',{'stage':'Q0','phase':phase,'error':repr(error),'counts':dict(counts),
            'wall_seconds':time.monotonic()-start,'finished_utc':now(),'retry_allowed':False})
        raise
    finally:
        signal.alarm(0)


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('action',choices=['run','verify'])
    args=parser.parse_args()
    if args.action=='run':run()
    else:verify()
