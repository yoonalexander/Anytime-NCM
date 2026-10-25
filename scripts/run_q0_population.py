"""One prospective aggregate reference-coverage/source-document audit."""
from __future__ import annotations
import os
for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[name]='1'
os.environ['PYTHONDONTWRITEBYTECODE']='1'
import argparse
from datetime import datetime,timezone
import gzip
import hashlib
import io
import json
from pathlib import Path
import resource
import signal
import subprocess
import sys
import tarfile
import time
import urllib.request
import zipfile

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/quality_tolerant/q0_population'
LOCK=ROOT/'docs/studies/quality-tolerant/q0-population-lock.json'
SOURCES=ROOT/'docs/studies/quality-tolerant/q0-population-source-lock.json'


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1<<20),b''):h.update(chunk)
    return h.hexdigest()


def write_new(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8',newline='\n') as f:json.dump(value,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')


def git(*args):return subprocess.check_output(['git.exe',*args],cwd=ROOT,text=True,timeout=30).strip()
def now():return datetime.now(timezone.utc).isoformat()


class Ledger:
    def __init__(self,limits,stream):
        self.limits=limits;self.stream=stream
        self.counts={k:0 for k in ['reference_materializations','pinned_source_materializations','official_source_materializations','download_requests','download_bytes']}
    def charge(self,key,n,label):
        if key not in self.counts or type(n) is not int or n<=0:raise ValueError('Invalid charge')
        if self.counts[key]+n>self.limits[key]:raise RuntimeError('Allocation exhausted: '+key)
        self.counts[key]+=n
        self.stream.write(json.dumps({'kind':key,'amount':n,'label':label,'counts':dict(self.counts)})+'\n');self.stream.flush()


def download_source_member(lock,ledger,check,total_start):
    path=ROOT/lock['archive_path'];path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():raise RuntimeError('Refuse archive overwrite or retry')
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self,*args,**kwargs):return None
    opener=urllib.request.build_opener(NoRedirect)
    ledger.charge('download_requests',1,'official source-document archive GET')
    signal.setitimer(signal.ITIMER_REAL,min(lock['download_seconds'],max(1,lock['limits']['wall_seconds']-(time.monotonic()-total_start))))
    try:
        request=urllib.request.Request(lock['document_url'],headers={'User-Agent':'Anytime-NCM-Q0-population-audit','Accept-Encoding':'identity'})
        with opener.open(request,timeout=lock['read_timeout_seconds']) as response,path.open('xb') as output:
            content_length=response.headers.get('Content-Length')
            if content_length is not None and int(content_length)>lock['limits']['download_bytes']:raise RuntimeError('Download Content-Length cap')
            while True:
                check();remaining=lock['limits']['download_bytes']-ledger.counts['download_bytes']
                if remaining<=0:raise RuntimeError('Download byte cap reached')
                chunk=response.read(min(65536,remaining))
                if not chunk:break
                ledger.charge('download_bytes',len(chunk),'archive transport bytes');output.write(chunk)
        raw=path.read_bytes()
        if hashlib.md5(raw,usedforsecurity=False).hexdigest()!=lock['archive_md5']:raise RuntimeError('Official archive MD5 differs')
        with gzip.GzipFile(fileobj=io.BytesIO(raw)) as f:unpacked=f.read(lock['decompression_bytes'])
        if len(unpacked)>=lock['decompression_bytes']:raise RuntimeError('Decompression cap reached')
        with tarfile.open(fileobj=io.BytesIO(unpacked),mode='r:') as archive:
            members=[x for x in archive.getmembers() if x.name==lock['source_member']]
            if len(members)!=1 or not members[0].isfile() or members[0].size>lock['member_bytes']:raise RuntimeError('Source member invalid')
            f=archive.extractfile(members[0]);source=f.read();f.close()
        return source,{'url':lock['document_url'],'archive_bytes':len(raw),'archive_sha256':hashlib.sha256(raw).hexdigest(),
            'archive_md5':lock['archive_md5'],'decompressed_bytes':len(unpacked),'opened_member':lock['source_member'],
            'member_bytes':len(source),'member_sha256':hashlib.sha256(source).hexdigest(),'other_member_body_decodes':0}
    finally:
        signal.setitimer(signal.ITIMER_REAL,max(1,lock['limits']['wall_seconds']-(time.monotonic()-total_start)))


def verify():
    started=time.monotonic();lock=json.loads(LOCK.read_text());r=json.loads((OUT/'execution.json').read_text())
    checked=0
    for key,base in [('source_sha256',ROOT),('protected_sha256',ROOT),('artifact_sha256',OUT)]:
        for rel,digest in r[key].items():
            if sha(base/rel)!=digest:raise RuntimeError('Frozen hash changed: '+rel)
            checked+=1
    if r['status']!='coverage_audit_complete':raise AssertionError('Audit incomplete')
    if r['counts']['reference_materializations']!=2171:raise AssertionError('Coverage allowlist incomplete')
    for k,v in r['counts'].items():
        if v>lock['limits'][k]:raise AssertionError('Counter cap')
    for key,cap in [('wall_seconds','wall_seconds'),('max_rss_bytes','memory_bytes')]:
        if r[key]>lock['limits'][cap]:raise AssertionError('Resource cap')
    if r['forbidden_work']!=lock['forbidden_work']:raise AssertionError('Forbidden work')
    if not r['model_outputs_still_sealed']:raise AssertionError('Outcome release')
    print(json.dumps({'verified':True,'hash_checks':checked,'reference_materializations':2171,'new_reference_reads':0,'verify_wall_seconds':time.monotonic()-started}))


def run():
    start=time.monotonic();started=now();lock=json.loads(LOCK.read_text());limits=lock['limits']
    resource.setrlimit(resource.RLIMIT_AS,(limits['memory_bytes'],limits['memory_bytes']))
    resource.setrlimit(resource.RLIMIT_CPU,(limits['cpu_seconds'],limits['cpu_seconds']))
    def expired(*_):raise TimeoutError('Audit deadline exhausted')
    signal.signal(signal.SIGALRM,expired);signal.alarm(limits['wall_seconds'])
    def check():
        if time.monotonic()-start>limits['wall_seconds']:raise TimeoutError('Wall cap')
        paths=[OUT,ROOT/'data/wmt14/q0_population']
        if sum(p.stat().st_size for base in paths for p in base.rglob('*') if p.is_file())>limits['storage_bytes']:raise RuntimeError('Storage cap')
    if (OUT/'started.json').exists():raise RuntimeError('One audit only; no silent rerun')
    head=git('rev-parse','HEAD');remote=git('ls-remote','origin','refs/heads/main').split()[0]
    if head!=remote or git('branch','--show-current')!='main' or git('status','--porcelain=v1','--untracked-files=all'):
        raise RuntimeError('Require clean matching local/live main')
    frozen=json.loads(SOURCES.read_text())
    for rel,digest in frozen['source_sha256'].items():
        if sha(ROOT/rel)!=digest:raise RuntimeError('Locked source differs: '+rel)
    hashes=dict(frozen['source_sha256']);hashes[str(SOURCES.relative_to(ROOT))]=sha(SOURCES)
    protected={rel:sha(ROOT/rel) for rel in frozen['protected_paths']}
    write_new(OUT/'started.json',{'stage':lock['stage'],'started_utc':started,'source_commit':head,'verified_live_main':remote,
        'source_sha256':hashes,'protected_sha256':protected})
    counts={};phase='synthetic_tests'
    try:
        with zipfile.ZipFile(OUT/'execution-sources.zip','x',compression=zipfile.ZIP_DEFLATED) as z:
            for rel in hashes:z.write(ROOT/rel,rel)
        test=subprocess.run([sys.executable,'-m','pytest','tests/test_q0_population.py','tests/test_q0_multiplicity.py','tests/test_q0_statistics.py','-q','-p','no:cacheprovider','--junitxml=results/quality_tolerant/q0_population/focused-tests.xml'],cwd=ROOT,text=True,capture_output=True,timeout=max(1,limits['wall_seconds']-int(time.monotonic()-start)))
        (OUT/'test-output.txt').write_text(test.stdout+test.stderr,encoding='utf-8')
        if test.returncode:raise RuntimeError('Synthetic tests failed before real-data access')
        phase='input_preflight';check();sys.path.insert(0,str(ROOT/'src'))
        import numpy,scipy
        from anytime_ncm.wmt_data import StringRows
        from anytime_ncm.q0_population import populations,parse_source_sgml,align_sources,aggregate_references
        parent=json.loads((ROOT/'docs/partitions/wmt14-phase4.json').read_text())
        reserved=json.loads((ROOT/'results/evidence_gaps/e0/input-manifest.json').read_text())
        roles,consumed,original_final=populations(parent,reserved)
        if {k:len(v) for k,v in roles.items()}!=lock['role_counts']:raise RuntimeError('Role counts differ')
        for kind in ['reference','source']:
            p=ROOT/lock[kind+'_path']
            if p.stat().st_size!=lock[kind+'_bytes'] or sha(p)!=lock[kind+'_sha256']:raise RuntimeError('Pinned '+kind+' asset differs')
        selected=set().union(*(set(v) for v in roles.values()))
        allowed_sha=hashlib.sha256(json.dumps(sorted(selected),separators=(',',':')).encode()).hexdigest()
        write_new(OUT/'coverage-access-release.json',{'stage':lock['stage'],'authorization':'User accepted narrow coverage/population audit; protocol committed before access','source_commit':head,
            'permitted_role_counts':lock['role_counts'],'unique_reference_indices':len(selected),'allowed_index_list_sha256':allowed_sha,
            'reference_access':'machine-only, once per allowed index, cue-presence aggregate only','reference_text_or_flags_export':False,
            'new_reference_derived_aggregate_exposure':True,'E3_E4_model_output_release':False,'new_model_outputs_read':0,'original_manifests_unchanged':True})
        with (OUT/'ledger.jsonl').open('x',encoding='utf-8') as stream:
            ledger=Ledger(limits,stream);counts=ledger.counts;documents=None;metadata={'status':'unavailable'}
            phase='document_metadata'
            try:
                source_member,provenance=download_source_member(lock,ledger,check,start)
                ledger.charge('official_source_materializations',3003,'official German source rows for document metadata')
                official=parse_source_sgml(source_member)
                ledger.charge('pinned_source_materializations',3003,'pinned source rows for exact document alignment')
                pinned=StringRows((ROOT/lock['source_path']).read_bytes()).select(set(range(3003)))
                docroles=dict(roles,original_consumed_final=original_final)
                documents,alignment=align_sources(pinned,official,docroles)
                del pinned,official,source_member
                metadata={'status':'aligned','provenance':provenance,'alignment':alignment}
                write_new(OUT/'document-map.json',documents)
            except Exception as error:
                metadata={'status':'unavailable','reason':repr(error),'retry_permitted':False,'model_output_access':False}
                write_new(OUT/'metadata-unavailable.json',metadata)
            write_new(OUT/'document-provenance.json',metadata)
            phase='reference_coverage';check()
            ledger.charge('reference_materializations',2171,'single permitted reference coverage materialization')
            aggregate=aggregate_references((ROOT/lock['reference_path']).read_bytes(),roles,consumed,original_final,documents)
            if aggregate['roles']['E2_audit']['numeric_covered_groups']!=48:raise RuntimeError('Prior E2 aggregate coverage parity differs')
            aggregate['document_metadata_status']=metadata['status'];aggregate['model_outputs_inspected']=0
            aggregate['reference_derived_aggregate_exposure_disclosed']=True
            write_new(OUT/'population-coverage.json',aggregate)
        phase='preservation_and_receipt'
        for rel,digest in protected.items():
            if sha(ROOT/rel)!=digest:raise RuntimeError('Historical evidence changed: '+rel)
        if any(m=='torch' or m.startswith('torch.') or m=='transformers' or m.startswith('transformers.') for m in sys.modules):raise RuntimeError('Forbidden model import')
        check();rss=max(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)*1024
        if rss>limits['memory_bytes']:raise RuntimeError('RSS cap')
        write_new(OUT/'execution.json',{'stage':lock['stage'],'status':'coverage_audit_complete','source_commit':head,'verified_live_remote_before_access':remote,
            'started_utc':started,'finished_utc':now(),'wall_seconds':time.monotonic()-start,'max_rss_bytes':rss,'counts':dict(counts),
            'preparation_reporting_charge_seconds':7200,'charged_wall_seconds':7200+time.monotonic()-start,'source_sha256':hashes,'protected_sha256':protected,
            'artifact_sha256':{p.name:sha(p) for p in OUT.iterdir() if p.is_file()},'reference_file_sha256':lock['reference_sha256'],'pinned_source_file_sha256':lock['source_sha256'],
            'document_metadata_status':metadata['status'],'model_outputs_still_sealed':True,'reference_coverage_aggregate_access_only':True,
            'forbidden_work':lock['forbidden_work'],'python':sys.version,'numpy':numpy.__version__,'scipy':scipy.__version__,'cost_dollars':0})
        phase='verification';verify()
    except BaseException as error:
        write_new(OUT/'failure.json',{'stage':lock['stage'],'phase':phase,'error':repr(error),'counts':dict(counts),'wall_seconds':time.monotonic()-start,'retry_allowed':False})
        raise
    finally:signal.setitimer(signal.ITIMER_REAL,0)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['run','verify']);args=p.parse_args()
    run() if args.action=='run' else verify()
