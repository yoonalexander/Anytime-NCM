"""Once-only source-metadata eligibility/capacity audit; no corpus decoding or models."""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='1'
os.environ['PYTHONDONTWRITEBYTECODE']='1'
import argparse,json,signal,subprocess,sys,time,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from run_signal_discrimination import git,cpu,rss,now,hashes_ok
from anytime_ncm.evidence_preflight import sha,write_new
from anytime_ncm.quality_controller import Meter
from anytime_ncm.development_eligibility import allocate,summarize,feasible,ROLES
from anytime_ncm.quality_campaign import campaign_root,verify_campaign,record_phase,usage_zero
BASE=ROOT/'docs/studies/quality-tolerant';CAMPAIGN=campaign_root(ROOT);OUT=CAMPAIGN/'development_eligibility'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def size():return sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file())
def load():
    lock=read(BASE/'development-eligibility-lock.json');source=read(BASE/'development-eligibility-source-lock.json');hashes_ok(source['source_sha256']);hashes_ok(source['protected_sha256'])
    if git('-C','third_party/ncm','rev-parse','HEAD')!=source['upstream_commit'] or git('-C','third_party/ncm','status','--porcelain'):raise ValueError('Upstream changed')
    return lock,source

def run(commit):
    started=time.monotonic();lock,source=load();verify_campaign(ROOT,lock['campaign_reservation'])
    if git('rev-parse','HEAD')!=commit or git('branch','--show-current')!='main' or git('status','--porcelain') or git('ls-remote','origin','refs/heads/main').split()[0]!=commit:raise ValueError('Need clean main at pushed audit lock')
    OUT.mkdir(parents=True,exist_ok=False);write_new(OUT/'started.json',dict(source_commit=commit,started_utc=now()))
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('Metadata audit wall cap')));signal.setitimer(signal.ITIMER_REAL,lock['wall_seconds']);meter=Meter(lock['analysis_caps'])
    try:
        with zipfile.ZipFile(OUT/'execution-sources.zip','x',compression=zipfile.ZIP_DEFLATED) as z:
            for p in source['source_sha256']:z.writestr(p,(ROOT/p).read_bytes())
            z.writestr('source-lock.json',json.dumps(source,indent=2))
        with (OUT/'synthetic-tests.log').open('x',encoding='utf-8',newline='\n') as log:
            test=subprocess.run([sys.executable,'-m','pytest','tests/test_development_eligibility.py','-q','-p','no:cacheprovider','--junitxml=results/quality_tolerant/campaign_20261029/development_eligibility/synthetic-tests.xml'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=lock['test_wall_seconds'])
        if test.returncode:raise RuntimeError('Synthetic metadata tests failed before public-manifest audit')
        before=verify_campaign(ROOT);write_new(OUT/'campaign-before.json',before)
        records=read(ROOT/lock['manifest_path']);meter.take('metadata_records',len(records));allocation=allocate(records);summary=summarize(allocation)
        if sum(len(v) for v in allocation['parts'].values())!=5487 or sum(v['components'] for v in summary.values())!=297 or sum(r['role']=='confirmation' for r in records)!=7700:raise ValueError('Prior allocation differs')
        year_rows=lock['official_rows_by_year']
        if any(r['index']>=year_rows[str(r['year'])] for r in records):raise ValueError('Year/index outside official frame')
        write_new(OUT/'source-only-allocation.json',allocation);write_new(OUT/'role-summary.json',summary)
        archives=[]
        for item in lock['cached_archives']:
            p=ROOT/item['path']
            if not p.is_file():raise ValueError('Required cached archive missing; no implicit network fallback')
            meter.take('archive_hash_bytes',p.stat().st_size)
            if p.stat().st_size!=item['bytes'] or sha(p)!=item['sha256']:raise ValueError('Pinned archive changed')
            archives.append(dict(item,verified=True,decoded_source_reference_bodies=0))
        write_new(OUT/'archive-availability.json',archives)
        staged=verify_campaign(ROOT,lock['campaign_reservation']);ceilings=read(BASE/'campaign-20261029-lock.json')['ceilings'];decision=feasible(summary,staged['charged_usage'],ceilings)
        decision.update(existing_development_numeric_covered=1229,role_numeric_coverage_not_inspected=True,unknown_checkpoint_training_overlap=True,story_independence_proven=False,confirmation_inputs_retained=7700,confirmation_components_retained=447,model_outcomes_read=0,source_or_reference_text_decodes=0,downloads=0)
        write_new(OUT/'decision.json',decision);write_new(OUT/'access-receipt.json',dict(source_only_manifest_records=len(records),new_development_allocation_inputs=5487,roles=list(ROLES),confirmation_reallocated=False,private_metadata_json_opened=False,source_reference_bodies_decoded=0,model_requests=0,reference_quality_evidence_added=False))
        if any(k=='torch' or k.startswith('torch.') or k=='transformers' or k.startswith('transformers.') or k=='tokenizers' for k in sys.modules):raise ValueError('Forbidden model/tokenizer framework imported')
        hashes_ok(source['source_sha256']);hashes_ok(source['protected_sha256'])
        if time.monotonic()-started>lock['wall_seconds'] or cpu()>lock['execution_cpu_cap_seconds'] or rss()>lock['parent_rss_bytes'] or size()>lock['artifact_bytes']:raise RuntimeError('Audit resource cap')
        usage=usage_zero();usage.update(cpu_seconds=cpu()+lock['reporting_cpu_charge_seconds'],artifact_bytes=lock['artifact_bytes']);verify_campaign(ROOT,usage)
        write_new(OUT/'execution.json',dict(status='complete',source_commit=commit,analysis_counts=meter.counts,model_requests=0,model_framework_imports=0,source_tokenizations=0,source_or_reference_body_decodes=0,private_cue_metadata_reads=0,new_fits=0,new_controller_families=0,target_encodings=0,synthetic_model_requests=0,synthetic_fits=0,bootstrap_draws=0,simulations=0,downloads=0,paid_dollars=0,automatic_retries=0,total_wall_seconds=time.monotonic()-started,cpu_seconds_before_reporting_charge=cpu(),max_parent_rss_bytes=rss(),campaign_usage=usage,finished_utc=now(),artifact_sha256={p.relative_to(OUT).as_posix():sha(p) for p in OUT.rglob('*') if p.is_file()}))
        print(json.dumps(record_phase(ROOT,'06-development-eligibility','development_eligibility/execution.json')),flush=True);print('DEVELOPMENT ELIGIBILITY COMPLETE: '+decision['status'],flush=True)
    except BaseException as error:
        failure=OUT/'failure.json'
        if not failure.exists():write_new(failure,dict(error=repr(error),counts=meter.counts,campaign_usage=lock['campaign_reservation'],conservative_reservation_charge=True,automatic_retry=False))
        if not (CAMPAIGN/'accounting/phase-06-development-eligibility.json').exists():record_phase(ROOT,'06-development-eligibility','development_eligibility/failure.json')
        raise
    finally:signal.setitimer(signal.ITIMER_REAL,0)

def verify():
    lock,source=load();e=read(OUT/'execution.json');hashes_ok({('results/quality_tolerant/campaign_20261029/development_eligibility/'+p):h for p,h in e['artifact_sha256'].items()})
    allocation=read(OUT/'source-only-allocation.json');summary=summarize(allocation);saved=read(OUT/'role-summary.json')
    if summary!=saved or e['status']!='complete' or e['model_requests'] or e['source_or_reference_body_decodes'] or e['new_fits']:raise ValueError('Invalid metadata audit receipt')
    if sum(v['inputs'] for v in summary.values())!=5487 or sum(v['components'] for v in summary.values())!=297:raise ValueError('Allocation changed')
    before=read(OUT/'campaign-before.json')['charged_usage'];staged={k:before[k]+lock['campaign_reservation'][k] for k in before};expected=feasible(summary,staged,read(BASE/'campaign-20261029-lock.json')['ceilings']);decision=read(OUT/'decision.json')
    if any(decision[k]!=v for k,v in expected.items()):raise ValueError('Decision differs')
    print(json.dumps(dict(verified=True,protected_files=len(source['protected_sha256']),allocation_summary=summary,campaign=verify_campaign(ROOT),new_corpus_decodes_or_models=0)))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=('run','verify'));p.add_argument('--commit');a=p.parse_args();run(a.commit) if a.mode=='run' else verify()
