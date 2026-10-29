"""Bounded first timing diagnostic; never retry original cache/evaluation matrix."""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='4'
for k in ('HF_HUB_OFFLINE','TRANSFORMERS_OFFLINE'):os.environ[k]='1'
os.environ['TOKENIZERS_PARALLELISM']='false';os.environ['PYTHONDONTWRITEBYTECODE']='1'
import argparse,json,resource,signal,subprocess,sys,time,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from run_signal_discrimination import git,cpu,rss,now,hashes_ok
from run_development_evaluation import model_context
from anytime_ncm.evidence_preflight import sha,write_new
from anytime_ncm.development_reporting import plain
from anytime_ncm.evaluation_reporting import native_environment
from anytime_ncm.development_evaluation_adapter import runtime_spec
from anytime_ncm.development_evaluation_data import key
from anytime_ncm.first_timing_diagnostic import plans,analyze
from anytime_ncm.controller_study import work,sum_work
from anytime_ncm.quality_controller import Meter
from anytime_ncm.latency_diagnostic import value_hash
from anytime_ncm.quality_campaign import campaign_root,verify_campaign,record_phase,usage_zero
B=ROOT/'docs/studies/quality-tolerant';C=campaign_root(ROOT);OUT=C/'first_timing_diagnostic';SAVED=C/'development_evaluation_reporting';POLICY=C/'development_controller/policy.json'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,v):write_new(p,plain(v))
def own_cpu():
    r=resource.getrusage(resource.RUSAGE_SELF);return r.ru_utime+r.ru_stime

def size():return sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file())
def alarm(seconds):
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('First timing diagnostic wall cap')));signal.setitimer(signal.ITIMER_REAL,seconds)
def load():
    lock=read(B/'first-timing-diagnostic-lock.json');s=read(B/'first-timing-diagnostic-source-lock.json')
    for k in ('source_sha256','protected_sha256','private_sha256'):hashes_ok(s[k])
    if git('-C','third_party/ncm','rev-parse','HEAD')!=s['upstream_commit'] or git('-C','third_party/ncm','status','--porcelain'):raise ValueError('Upstream changed')
    if sha(POLICY)!=lock['policy_sha256']:raise ValueError('Selected policy changed')
    return lock,s

def worker(session,seconds):
    started=time.monotonic();lock,s=load();alarm(seconds);resource.setrlimit(resource.RLIMIT_CPU,(450,450))
    import torch
    from anytime_ncm.forced_wmt import ForwardCounter,forced_request
    from anytime_ncm.joint_risk_wmt import joint_request
    entries=read(C/'development_evaluation/access-release.json')['entries'];plan=read(OUT/'timing-schedule.json')[str(session)];cache=read(SAVED/'parity-hashes.json');vectors=read(SAVED/'current8-features.json');controller=runtime_spec(read(POLICY)['policy']);limits=sum_work(plan);meter=Meter(lock['feature_caps']);counter=None;receipt=dict(session=session,started_utc=now(),completed_requests=0);save(OUT/f'{session}-started.json',receipt);request=None
    try:
        if any(limits[k]>v for k,v in lock['forward_caps'].items()):raise ValueError('Session work cap')
        model,sources,info,fingerprint=model_context(entries,3574);info['environment']=native_environment(info['environment']);info.update(receipt);receipt=info
        save(OUT/f'{session}-environment-start.json',receipt)
        counter=ForwardCounter(model,limits);begin,end=torch.cuda.Event(enable_timing=True),torch.cuda.Event(enable_timing=True)
        with (OUT/f'{session}-starts.jsonl').open('x',encoding='utf-8',newline='\n') as ledger,(OUT/f'{session}-requests.jsonl').open('x',encoding='utf-8',newline='\n') as stream:
            for number,request in enumerate(plan):
                if cpu()>lock['worker_cpu_seconds'] or rss()>lock['worker_rss_bytes'] or size()>lock['artifact_bytes']:raise RuntimeError('Worker resource cap')
                before=dict(counter.counts);f0=dict(meter.counts);counter.take('inputs');ledger.write(json.dumps(dict(request,work_before=before,feature_work_before=f0))+'\n');ledger.flush();torch.cuda.synchronize();torch.cuda.reset_peak_memory_stats();torch.manual_seed(20261023);wall=time.perf_counter_ns();begin.record()
                if request['method']=='controller':result=joint_request(model,sources[key(request)],controller,meter)
                else:result=forced_request(model,sources[key(request)],11,'terminal')
                end.record();torch.cuda.synchronize();wall_ms=(time.perf_counter_ns()-wall)/1e6;actual={k:counter.counts[k]-before[k] for k in before};fwork={k:meter.counts[k]-f0[k] for k in f0};ctrl=request['method']=='controller'
                if actual!=work(request) or fwork!=dict(cheap_features=int(ctrl),selected_logit_features=0,cue_features=0,decisions=int(ctrl)) or result['exit_level']!=request['depth'] or [o['level'] for o in result['observations']]!=request['visits']:raise ValueError('Actual policy exit/work mismatch')
                c=cache[key(request)];h=dict(prefix=value_hash(result['prefix_ids']),codes=value_hash(result['codes'][0].cpu().tolist()),outputs={str(o['level']):dict(ids=value_hash(o['ids']),text=value_hash(o['text'])) for o in result['observations']});current={str(v['level']):value_hash(v['codes']) for v in result.get('prefix_codes',[])}
                if h['prefix']!=c['prefix'] or h['codes']!=c['codes'][str(request['depth'])] or any(h['outputs'][str(d)]!=c['outputs'][str(d)] for d in request['visits']):raise ValueError('Actual output/current-prefix parity failed')
                if ctrl:
                    values=result['features'][0]['values']
                    if current!={'8':c['codes']['8']} or [f['level'] for f in result['features']]!=[8] or len(values)!=27 or any(abs(a-b)>1e-6+1e-5*abs(b) for a,b in zip(values[:19],vectors[key(request)][:19])) or values[19:]!=[0.]*8:raise ValueError('Actual causal cheap features mismatch')
                reserved=torch.cuda.max_memory_reserved()
                if reserved>min(lock['gpu_reserved_bytes'],receipt['environment']['physical_gpu_bytes']):raise RuntimeError('GPU cap')
                stream.write(json.dumps(dict(request,wall_ms=wall_ms,cuda_stream_span_ms=begin.elapsed_time(end),work=actual,feature_work=fwork,hashes=h,current_code_hashes=current,features=result.get('features',[]),parity=True,peak_reserved_bytes=reserved),allow_nan=False)+'\n');stream.flush();receipt['completed_requests']+=1
                if number%512==0 or number+1==len(plan):print(f'First timing diagnostic session {session}: {number+1}/{len(plan)}; causal exit/current-feature/output/work passed',flush=True)
        receipt['state_after']=fingerprint()
        if receipt['state_before']!=receipt['state_after'] or counter.counts!=limits or meter.counts!=lock['feature_caps'] or receipt['prefix_calls']!=3574 or cpu()>lock['worker_cpu_seconds']:raise ValueError('Incomplete timing/state/work')
        receipt.update(status='complete',counts=dict(counter.counts),feature_counts=meter.counts,wall_seconds=time.monotonic()-started,cpu_seconds=cpu(),max_rss_bytes=rss(),finished_utc=now());save(OUT/f'{session}-execution.json',receipt)
    except BaseException as error:
        save(OUT/f'{session}-failure.json',dict(receipt,error=repr(error),request=request,counts=dict(counter.counts) if counter else {},feature_counts=meter.counts,automatic_retry=False));raise
    finally:
        if counter:counter.close()
        signal.setitimer(signal.ITIMER_REAL,0)

def run(commit):
    started=time.monotonic();lock,s=load();verify_campaign(ROOT,lock['campaign_reservation'])
    if git('rev-parse','HEAD')!=commit or git('branch','--show-current')!='main' or git('status','--porcelain') or git('ls-remote','origin','refs/heads/main').split()[0]!=commit:raise ValueError('Need clean pushed diagnostic lock')
    OUT.mkdir(parents=True,exist_ok=False);save(OUT/'started.json',dict(source_commit=commit,started_utc=now()));alarm(lock['wall_seconds'])
    try:
        with zipfile.ZipFile(OUT/'execution-sources.zip','x',compression=zipfile.ZIP_DEFLATED) as z:
            for p in s['source_sha256']:z.writestr(p,(ROOT/p).read_bytes())
            z.writestr('source-lock.json',json.dumps(s,indent=2))
        with (OUT/'synthetic-tests.log').open('x',encoding='utf-8') as log:
            code='import resource,runpy;resource.setrlimit(resource.RLIMIT_CPU,(20,20));runpy.run_module("pytest",run_name="__main__")';t=subprocess.run([sys.executable,'-c',code,'tests/test_first_timing_diagnostic.py','-q','-p','no:cacheprovider','--junitxml=results/quality_tolerant/campaign_20261029/first_timing_diagnostic/synthetic-tests.xml'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=lock['test_wall_seconds'])
        if t.returncode:raise RuntimeError('Pure diagnostic synthetic checks failed')
        entries=read(C/'development_evaluation/access-release.json')['entries'];pred=read(SAVED/'predictions.json');expected=[(p['depth'],p['visits']) for p in pred]
        if len(entries)!=1188 or len(pred)!=1188 or any((e['year'],e['index'])!=(p['year'],p['index']) for e,p in zip(entries,pred)):raise ValueError('Fixed evaluation predictions/allocation changed')
        save(OUT/'timing-schedule.json',{str(session):plans(entries,expected,session) for session in (0,1)})
        model_start=time.monotonic()
        for session in (0,1):
            remaining=min(lock['model_wall_seconds']-(time.monotonic()-model_start),lock['wall_seconds']-(time.monotonic()-started))
            if remaining<=0:raise RuntimeError('Diagnostic deadline')
            subprocess.run([sys.executable,str(Path(__file__).resolve()),'worker','--session',str(session),'--seconds',str(remaining)],cwd=ROOT,check=True,timeout=remaining)
        model_seconds=time.monotonic()-model_start;workers=[read(OUT/f'{i}-execution.json') for i in (0,1)]
        if workers[0]['pid']==workers[1]['pid'] or workers[0]['state_before']!=workers[1]['state_before']:raise ValueError('Expected two separate identical-state processes')
        records=[json.loads(line) for i in (0,1) for line in (OUT/f'{i}-requests.jsonl').read_text().splitlines()];a=analyze(records,entries,read(SAVED/'quality-points.json'));save(OUT/'analysis.json',a)
        for k in ('source_sha256','protected_sha256','private_sha256'):hashes_ok(s[k])
        if own_cpu()>lock['parent_own_cpu_seconds'] or cpu()>lock['execution_cpu_cap_seconds'] or rss()>lock['parent_rss_bytes'] or size()>lock['artifact_bytes']:raise RuntimeError('Parent completion resource cap')
        usage=usage_zero();usage.update(model_requests=4772,model_orchestration_seconds=model_seconds,cpu_seconds=cpu()+lock['reporting_cpu_charge_seconds'],artifact_bytes=lock['artifact_bytes']);verify_campaign(ROOT,usage)
        save(OUT/'decision.json',dict(status=a['status'],timing_screen_passed=a['timing_screen_passed'],quality_point_pass=a['quality_point_pass'],next_branch='confirmation_readiness_audit_and_final_closeout',original_success_contract_established=False,original_phase09_matrix_complete=False,no_more_models_fits_or_data_extensions=True,confirmation_released=False))
        save(OUT/'execution.json',dict(status='complete',source_commit=commit,counts={k:sum(w['counts'][k] for w in workers) for k in workers[0]['counts']},feature_counts={k:sum(w['feature_counts'][k] for w in workers) for k in workers[0]['feature_counts']},real_checkpoint_loads=2,synthetic_nn_requests=0,new_fits=0,new_corpus_scores=0,reference_cache_opened=False,target_encodings=0,source_prefix_calls=7148,worker_source_materializations=2376,model_states_unchanged=True,all_actual_current_features_exits_outputs_and_skipped_work_verified=True,bootstrap_draws=20000,model_orchestration_seconds=model_seconds,cpu_seconds_before_reporting_charge=cpu(),total_wall_seconds=time.monotonic()-started,max_parent_rss_bytes=rss(),campaign_usage=usage,paid_dollars=0,finished_utc=now(),artifact_sha256={p.relative_to(OUT).as_posix():sha(p) for p in OUT.rglob('*') if p.is_file()}))
        print(json.dumps(record_phase(ROOT,'09t-first-timing-diagnostic','first_timing_diagnostic/execution.json')),flush=True);print(json.dumps(a),flush=True)
    except BaseException as error:
        save(OUT/'failure.json',dict(error=repr(error),campaign_usage=lock['campaign_reservation'],conservative_reservation_charge=True,automatic_retry=False));record_phase(ROOT,'09t-first-timing-diagnostic','first_timing_diagnostic/failure.json');raise
    finally:signal.setitimer(signal.ITIMER_REAL,0)

def verify():
    lock,s=load();e=read(OUT/'execution.json');hashes_ok({('results/quality_tolerant/campaign_20261029/first_timing_diagnostic/'+p):h for p,h in e['artifact_sha256'].items()});schedule=read(OUT/'timing-schedule.json');cache=read(SAVED/'parity-hashes.json');counts=dict(inputs=0,generator_levels=0,decoder=0,encoder=0)
    for session in (0,1):
        w=read(OUT/f'{session}-execution.json');records=[json.loads(x) for x in (OUT/f'{session}-requests.jsonl').read_text().splitlines()]
        if len(records)!=2386 or w['counts']!=sum_work(schedule[str(session)]) or w['state_before']!=w['state_after'] or w['prefix_calls']!=3574 or w['feature_counts']!=lock['feature_caps']:raise ValueError('Incomplete diagnostic worker')
        for p,r in zip(schedule[str(session)],records):
            if any(r[k]!=v for k,v in p.items()) or r['work']!=work(r) or not r['parity']:raise ValueError('Diagnostic replay mismatch')
            c=cache[key(r)];h=r['hashes']
            if h['prefix']!=c['prefix'] or h['codes']!=c['codes'][str(r['depth'])] or any(h['outputs'][str(d)]!=c['outputs'][str(d)] for d in r['visits']):raise ValueError('Diagnostic parity binding failed')
            if r['method']=='controller' and r['current_code_hashes']!={'8':c['codes']['8']}:raise ValueError('Current8codes mismatch')
        for k,v in w['counts'].items():counts[k]+=v
    if counts!=e['counts'] or counts['inputs']!=4772 or e['new_fits'] or e['new_corpus_scores'] or e['reference_cache_opened']:raise ValueError('Invalid diagnostic receipt')
    print(json.dumps(dict(verified=True,new_models_or_fits_or_scores_or_resampling=0,campaign=verify_campaign(ROOT))))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=('run','worker','verify'));p.add_argument('--commit');p.add_argument('--session',type=int);p.add_argument('--seconds',type=float);a=p.parse_args()
    if a.mode=='run':run(a.commit)
    elif a.mode=='worker':worker(a.session,a.seconds)
    else:verify()
