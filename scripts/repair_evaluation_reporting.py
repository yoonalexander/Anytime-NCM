"""One-shot zero-inference repair of phase09 cache reporting and corpus points."""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='1'
os.environ['PYTHONDONTWRITEBYTECODE']='1'
import argparse,json,resource,signal,subprocess,sys,time,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from run_signal_discrimination import git,cpu,rss,now,hashes_ok
from anytime_ncm.evidence_preflight import sha,write_new
from anytime_ncm.development_reporting import plain
from anytime_ncm.evaluation_reporting import validated_cache
from anytime_ncm.development_evaluation_data import key
from anytime_ncm.development_models import decide
from anytime_ncm.controller_study import METHODS,cache_row
from anytime_ncm.quality_controller import Meter,point_losses,point_pass
from anytime_ncm.wmt_metrics import scores
from anytime_ncm.quality_campaign import campaign_root,verify_campaign,record_phase,usage_zero
BASE=ROOT/'docs/studies/quality-tolerant';C=campaign_root(ROOT);OLD=C/'development_evaluation';OUT=C/'development_evaluation_reporting';PRIVATE=ROOT/'data/quality_tolerant_campaign_20261029/development_evaluation';POLICY=C/'development_controller/policy.json'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,v):write_new(p,plain(v))
def load():
    lock=read(BASE/'evaluation-reporting-lock.json');s=read(BASE/'evaluation-reporting-source-lock.json')
    for k in ('source_sha256','protected_sha256','private_sha256'):hashes_ok(s[k])
    if git('-C','third_party/ncm','rev-parse','HEAD')!=s['upstream_commit'] or git('-C','third_party/ncm','status','--porcelain'):raise ValueError('Upstream changed')
    return lock,s
def run(commit):
    start=time.monotonic();lock,s=load();verify_campaign(ROOT,lock['campaign_reservation'])
    if git('rev-parse','HEAD')!=commit or git('branch','--show-current')!='main' or git('status','--porcelain') or git('ls-remote','origin','refs/heads/main').split()[0]!=commit:raise ValueError('Need clean pushed reporting lock')
    OUT.mkdir(parents=True,exist_ok=False);save(OUT/'started.json',dict(source_commit=commit,started_utc=now(),new_model_work=False));meter=Meter(lock['analysis_caps'])
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('Reporting wall cap')));signal.setitimer(signal.ITIMER_REAL,lock['wall_seconds'])
    try:
        with zipfile.ZipFile(OUT/'execution-sources.zip','x',compression=zipfile.ZIP_DEFLATED) as z:
            for p in s['source_sha256']:z.writestr(p,(ROOT/p).read_bytes())
            z.writestr('source-lock.json',json.dumps(s,indent=2))
        with (OUT/'synthetic-tests.log').open('x',encoding='utf-8') as log:
            testcode='import resource,runpy;resource.setrlimit(resource.RLIMIT_CPU,(20,20));runpy.run_module("pytest",run_name="__main__")'
            result=subprocess.run([sys.executable,'-c',testcode,'tests/test_evaluation_reporting.py','-q','-p','no:cacheprovider','--basetemp=results/quality_tolerant/campaign_20261029/development_evaluation_reporting/pytest-tmp','--junitxml=results/quality_tolerant/campaign_20261029/development_evaluation_reporting/synthetic-tests.xml'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=lock['test_wall_seconds'])
        if result.returncode:raise RuntimeError('Reporting synthetic validation failed')
        failure=read(OLD/'failure.json');preserved=read(OLD/'failure-preservation.json')
        if not failure['conservative_reservation_charge'] or failure['counts']['native_trace_bodies'] or failure['counts']['corpus_scores'] or preserved['error']!='Unsupported report value: TorchVersion' or (OLD/'cache-execution.json').exists():raise ValueError('Different original failure')
        entries=read(OLD/'access-release.json')['entries'];plan=read(OLD/'cache-plan.json');public=[json.loads(x) for x in (OLD/'cache-requests.jsonl').read_text().splitlines()]
        with (PRIVATE/'native-traces.jsonl').open(encoding='utf-8') as lines:rows,counts=validated_cache(entries,plan,public,lines,meter)
        allowed={key(e):e for e in entries};refs={}
        for line in (PRIVATE/'references.jsonl').read_text(encoding='utf-8').splitlines():
            meter.take('reference_cache_bodies');r=json.loads(line);k=key(r)
            if k not in allowed or k in refs or any(r[f]!=allowed[k][f] for f in ('role','component','identity')):raise ValueError('Reference cache allocation mismatch')
            refs[k]=r['reference']
        if set(refs)!=set(allowed):raise ValueError('Incomplete reference cache')
        policy=read(POLICY);pred=[]
        for e in entries:
            meter.take('predictions');k=key(e);pred.append((8,[8]) if decide(policy['policy'],8,rows[k]['features'][0]['values']) else (11,[8,11]))
        save(OUT/'parity-hashes.json',{k:cache_row(r) for k,r in rows.items()});save(OUT/'current8-features.json',{k:r['features'][0]['values'] for k,r in rows.items()});save(OUT/'predictions.json',[dict(year=e['year'],index=e['index'],depth=d,visits=v) for e,(d,v) in zip(entries,pred)])
        ordered=[key(e) for e in entries];references=[refs[k] for k in ordered]
        def metric(hyps):meter.take('corpus_scores');return scores(hyps,references)
        full=metric([rows[k]['levels'][-1]['text'] for k in ordered]);quality={}
        for method in METHODS:
            depths=[d for d,v in pred] if method=='controller' else [int(method.split(':')[1])]*1188;m=full if method=='fixed:11' else metric([rows[k]['levels'][d-1]['text'] for k,d in zip(ordered,depths)]);quality[method]=dict(metrics=m,losses=point_losses(m,full),point_pass=point_pass(m,full))
        save(OUT/'quality-points.json',quality);save(OUT/'decision.json',dict(status='saved_evaluation_quality_point_screen_passed' if quality['controller']['point_pass'] and full['numeric_reference_coverage']>=100 else 'saved_evaluation_quality_point_screen_failed_or_inadequate_coverage',early_inputs=sum(d<11 for d,v in pred),numeric_reference_coverage=full['numeric_reference_coverage'],timing_requests=0,Q0_passed=False,independent_quality_guarantee=False,original_success_contract_established=False,post_evaluation_retuning_allowed=False,next_branch='prospectively_bounded_first_timing_diagnostic_if_feasible_then_closeout',original_full_matrix_incomplete=True))
        if any(k=='torch' or k.startswith('torch.') or k=='transformers' or k.startswith('transformers.') for k in sys.modules):raise ValueError('Parent model framework import')
        for k in ('source_sha256','protected_sha256','private_sha256'):hashes_ok(s[k])
        if cpu()>lock['execution_cpu_cap_seconds'] or rss()>lock['parent_rss_bytes'] or sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file())>lock['artifact_bytes']:raise RuntimeError('Reporting resource cap')
        usage=usage_zero();usage.update(cpu_seconds=cpu()+lock['reporting_cpu_charge_seconds'],artifact_bytes=lock['artifact_bytes']);verify_campaign(ROOT,usage)
        save(OUT/'execution.json',dict(status='complete',source_commit=commit,original_failure_sha256=sha(OLD/'failure.json'),original_preservation_sha256=sha(OLD/'failure-preservation.json'),original_full_reservation_preserved=True,original_cache_terminal_receipt_available=False,original_cache_final_state_hashes_available=False,original_final_resource_values_available=False,saved_native_counts_verified=counts,private_public_hash_bindings=1193,analysis_counts=meter.counts,new_model_requests=0,new_checkpoint_loads=0,new_corpus_payload_decodes=0,new_reference_cache_body_reads=1188,new_corpus_scores=12,new_fits=0,new_families=0,target_encodings=0,bootstrap_draws=0,synthetic_nn_requests=0,cpu_seconds_before_reporting_charge=cpu(),total_wall_seconds=time.monotonic()-start,max_rss_bytes=rss(),campaign_usage=usage,paid_dollars=0,finished_utc=now(),artifact_sha256={p.relative_to(OUT).as_posix():sha(p) for p in OUT.rglob('*') if p.is_file()}))
        print(json.dumps(record_phase(ROOT,'09r-evaluation-reporting','development_evaluation_reporting/execution.json')),flush=True);print(json.dumps(read(OUT/'decision.json')),flush=True)
    except BaseException as error:
        save(OUT/'failure.json',dict(error=repr(error),campaign_usage=lock['campaign_reservation'],conservative_reservation_charge=True,automatic_retry=False));record_phase(ROOT,'09r-evaluation-reporting','development_evaluation_reporting/failure.json');raise
    finally:signal.setitimer(signal.ITIMER_REAL,0)
def verify():
    lock,s=load();e=read(OUT/'execution.json');hashes_ok({('results/quality_tolerant/campaign_20261029/development_evaluation_reporting/'+p):h for p,h in e['artifact_sha256'].items()})
    if e['status']!='complete' or e['new_model_requests'] or e['new_fits'] or e['original_cache_terminal_receipt_available'] or e['private_public_hash_bindings']!=1193:raise ValueError('Invalid reporting receipt')
    print(json.dumps(dict(verified=True,no_new_model_or_reference_scoring_or_resampling=True,original_failure_preserved=True,campaign=verify_campaign(ROOT))))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=('run','verify'));p.add_argument('--commit');a=p.parse_args();run(a.commit) if a.mode=='run' else verify()
