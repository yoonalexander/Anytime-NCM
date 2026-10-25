"""One capped Q0 multiplicity-extension run; no empirical data/model access."""
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
OUT=ROOT/'results/quality_tolerant/q0_multiplicity'
LOCK=ROOT/'docs/studies/quality-tolerant/q0-multiplicity-lock.json'
SOURCES=ROOT/'docs/studies/quality-tolerant/q0-multiplicity-source-lock.json'


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1<<20),b''):h.update(chunk)
    return h.hexdigest()


def write_new(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(value,stream,indent=2,sort_keys=True,allow_nan=False);stream.write('\n')


def git(*args):
    return subprocess.check_output(['git.exe',*args],cwd=ROOT,text=True,timeout=30).strip()


def now():return datetime.now(timezone.utc).isoformat()


def verify():
    start=time.monotonic(); lock=json.loads(LOCK.read_text()); receipt=json.loads((OUT/'execution.json').read_text())
    checks=[]
    for group,base in [('source_sha256',ROOT),('protected_sha256',ROOT),('artifact_sha256',OUT)]:
        for rel,digest in receipt[group].items():
            if sha(base/rel)!=digest:raise RuntimeError('Frozen hash changed: '+rel)
            checks.append(group+':'+rel)
    if receipt['counts']!={k:lock['limits'][k] for k in ['trials','bootstrap_draws','datasets']}:
        raise AssertionError('Frozen allocation incomplete')
    gates=json.loads((OUT/'gate-trials.json').read_text()); cues=json.loads((OUT/'cue-trials.json').read_text())
    if [x['case'] for x in gates]!=lock['gate_cases']:raise AssertionError('Gate cases incomplete')
    if [(x['n'],x['case']) for x in cues]!=[(n,c) for n in lock['cue_ns'] for c in lock['cue_cases']]:raise AssertionError('Cue cases incomplete')
    if not all(v['passed'] for x in gates for v in x['checks'].values()):raise AssertionError('MC sanity failure')
    for key in ['wall_seconds','max_rss_bytes']:
        limit=lock['limits']['wall_seconds' if key=='wall_seconds' else 'memory_bytes']
        if receipt[key]>limit:raise AssertionError('Resource cap')
    if receipt['status']!='synthetic_validation_complete' or receipt['forbidden_work']!=lock['forbidden_work']:
        raise AssertionError('Incomplete/forbidden work')
    if sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file())>lock['limits']['storage_bytes']:raise AssertionError('Storage cap')
    print(json.dumps({'verified':True,'hash_checks':len(checks),'frozen_gate_cases':len(gates),'frozen_cue_cases':len(cues),
                      'counts':receipt['counts'],'new_random_draws':0,'verify_wall_seconds':time.monotonic()-start}))


def run():
    start=time.monotonic(); lock=json.loads(LOCK.read_text()); limits=lock['limits']; started=now()
    resource.setrlimit(resource.RLIMIT_AS,(limits['memory_bytes'],limits['memory_bytes']))
    resource.setrlimit(resource.RLIMIT_CPU,(limits['cpu_seconds'],limits['cpu_seconds']))
    def alarm(*_):raise TimeoutError('Q0 multiplicity wall cap exhausted')
    signal.signal(signal.SIGALRM,alarm);signal.alarm(limits['wall_seconds'])
    def check():
        if time.monotonic()-start>limits['wall_seconds']:raise TimeoutError('Wall cap')
        if sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file())>limits['storage_bytes']:raise RuntimeError('Storage cap')
    if (OUT/'started.json').exists():raise RuntimeError('One execution only; existing start is immutable')
    head=git('rev-parse','HEAD'); remote=git('ls-remote','origin','refs/heads/main').split()[0]
    if head!=remote or git('branch','--show-current')!='main':raise RuntimeError('Require matching main and live remote')
    if git('status','--porcelain=v1','--untracked-files=all'):raise RuntimeError('Require clean checkout')
    frozen=json.loads(SOURCES.read_text())
    for rel,digest in frozen['source_sha256'].items():
        if sha(ROOT/rel)!=digest:raise RuntimeError('Source lock mismatch: '+rel)
    protected={rel:sha(ROOT/rel) for rel in frozen['protected_paths']}
    hashes=dict(frozen['source_sha256']);hashes[str(SOURCES.relative_to(ROOT))]=sha(SOURCES)
    write_new(OUT/'started.json',{'stage':lock['stage'],'started_utc':started,'source_commit':head,
        'verified_live_main':remote,'source_sha256':hashes,'protected_sha256':protected})
    counts=dict(trials=0,bootstrap_draws=0,datasets=0);phase='tests'
    try:
        with zipfile.ZipFile(OUT/'execution-sources.zip','x',compression=zipfile.ZIP_DEFLATED) as archive:
            for rel in hashes:archive.write(ROOT/rel,rel)
        completed=subprocess.run([sys.executable,'-m','pytest','tests/test_q0_multiplicity.py','tests/test_q0_statistics.py',
            '-q','-p','no:cacheprovider','--junitxml=results/quality_tolerant/q0_multiplicity/focused-tests.xml'],
            cwd=ROOT,text=True,capture_output=True,timeout=max(1,limits['wall_seconds']-int(time.monotonic()-start)))
        (OUT/'test-output.txt').write_text(completed.stdout+completed.stderr,encoding='utf-8')
        if completed.returncode:raise RuntimeError('Focused synthetic tests failed; no simulations authorized')
        sys.path.insert(0,str(ROOT/'src'))
        import numpy,scipy
        from anytime_ncm.q0_statistics import Budget
        from anytime_ncm.q0_multiplicity import analytical,gate_trials,cue_trials
        phase='analytical';check();write_new(OUT/'statistical-feasibility.json',analytical(lock))
        with (OUT/'ledger.jsonl').open('x',encoding='utf-8') as ledger:
            budget=Budget(limits,ledger);counts=budget.counts
            phase='gate_trials';write_new(OUT/'gate-trials.json',gate_trials(lock,budget,check))
            phase='cue_trials';write_new(OUT/'cue-trials.json',cue_trials(lock,budget,check))
        if counts!={k:limits[k] for k in counts}:raise AssertionError('Incomplete frozen work')
        for rel,digest in protected.items():
            if sha(ROOT/rel)!=digest:raise RuntimeError('Protected prior source/result changed: '+rel)
        model_imported=any(m=='torch' or m.startswith('torch.') or m=='transformers' or m.startswith('transformers.') or m=='anytime_ncm.wmt_model' for m in sys.modules)
        if model_imported:raise RuntimeError('Forbidden model import')
        check();rss=max(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)*1024
        if rss>limits['memory_bytes']:raise RuntimeError('RSS cap')
        write_new(OUT/'execution.json',{'stage':lock['stage'],'status':'synthetic_validation_complete','source_commit':head,
            'verified_live_remote_before_tests':remote,'started_utc':started,'finished_utc':now(),'counts':dict(counts),
            'wall_seconds':time.monotonic()-start,'max_rss_bytes':rss,'preparation_reporting_charge_seconds':7200,
            'charged_wall_seconds':7200+time.monotonic()-start,'source_sha256':hashes,'protected_sha256':protected,
            'artifact_sha256':{p.name:sha(p) for p in OUT.iterdir() if p.is_file()},
            'python':sys.version,'numpy':numpy.__version__,'scipy':scipy.__version__,
            'model_libraries_imported':False,'forbidden_work':lock['forbidden_work'],'cost_dollars':0})
        phase='verification';verify()
    except BaseException as error:
        write_new(OUT/'failure.json',{'stage':lock['stage'],'phase':phase,'error':repr(error),'counts':dict(counts),
            'wall_seconds':time.monotonic()-start,'finished_utc':now(),'retry_allowed':False})
        raise
    finally:signal.alarm(0)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['run','verify']);args=p.parse_args()
    run() if args.action=='run' else verify()
