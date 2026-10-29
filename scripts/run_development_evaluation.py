"""Once-only1188input development evaluation of the already pushed selected policy."""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='4'
for k in ('HF_HUB_OFFLINE','TRANSFORMERS_OFFLINE'):os.environ[k]='1'
os.environ['TOKENIZERS_PARALLELISM']='false';os.environ['PYTHONDONTWRITEBYTECODE']='1'
import argparse,hashlib,importlib.metadata,json,math,signal,subprocess,sys,time,zipfile,resource
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from run_signal_discrimination import git,cpu,rss,now,hashes_ok
from anytime_ncm.evidence_preflight import sha,write_new
from anytime_ncm.development_reporting import plain
from anytime_ncm.development_evaluation_adapter import runtime_spec
from anytime_ncm.development_evaluation_data import extract_corpus,key
from anytime_ncm.development_models import decide
from anytime_ncm.quality_controller import Meter,point_losses,point_pass
from anytime_ncm.controller_study import METHODS,schedule,sum_work,work,timing_analysis,cache_row
from anytime_ncm.latency_diagnostic import value_hash
from anytime_ncm.quality_campaign import campaign_root,verify_campaign,record_phase,usage_zero
from anytime_ncm.wmt_data import identity
from anytime_ncm.wmt_metrics import scores
BASE=ROOT/'docs/studies/quality-tolerant';CAMPAIGN=campaign_root(ROOT);OUT=CAMPAIGN/'development_evaluation';PRIVATE=ROOT/'data/quality_tolerant_campaign_20261029/development_evaluation';POLICY=CAMPAIGN/'development_controller/policy.json'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,v):write_new(p,plain(v))
def size():return sum(p.stat().st_size for d in (OUT,PRIVATE) for p in d.rglob('*') if p.is_file())
def own_cpu():
    r=resource.getrusage(resource.RUSAGE_SELF);return r.ru_utime+r.ru_stime
def alarm(seconds):
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('One-shot evaluation wall cap')));signal.setitimer(signal.ITIMER_REAL,seconds)
def stop_alarm():signal.setitimer(signal.ITIMER_REAL,0)
def load():
    lock=read(BASE/'development-evaluation-lock.json');source=read(BASE/'development-evaluation-source-lock.json');hashes_ok(source['source_sha256']);hashes_ok(source['protected_sha256'])
    if git('-C','third_party/ncm','rev-parse','HEAD')!=source['upstream_commit'] or git('-C','third_party/ncm','status','--porcelain'):raise ValueError('Upstream changed')
    relative=POLICY.relative_to(ROOT).as_posix();committed=subprocess.check_output(['git.exe','show',lock['policy_commit']+':'+relative],cwd=ROOT,timeout=60)
    if sha(POLICY)!=lock['policy_sha256'] or hashlib.sha256(committed).hexdigest()!=lock['policy_sha256']:raise ValueError('Policy not exactly frozen before evaluation release')
    runtime_spec(read(POLICY)['policy'])
    return lock,source

def model_context(entries,prefix_limit):
    import torch,transformers
    from anytime_ncm.wmt_model import WmtModel
    from anytime_ncm.target_encoding import model_fingerprint
    if (sys.version_info[:3]!=(3,12,3) or torch.__version__!='2.10.0+cu128' or torch.version.cuda!='12.8' or transformers.__version__!='4.57.6' or not torch.cuda.is_available() or torch.cuda.get_device_name()!='NVIDIA GeForce RTX 5060'):raise RuntimeError('Material inference environment drift')
    torch.set_num_threads(4);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=True;sources={}
    for line in (PRIVATE/'sources.jsonl').read_text(encoding='utf-8').splitlines():
        e=json.loads(line);sources[key(e)]=e['source']
    if len(sources)!=1188 or set(sources)!={key(e) for e in entries}:raise ValueError('Evaluation source cache mismatch')
    model=WmtModel(ROOT);receipt=dict(pid=os.getpid(),prefix_calls=0,worker_source_materializations=1188,reference_cache_opened=False,environment=dict(python=sys.version,torch=torch.__version__,cuda=torch.version.cuda,transformers=transformers.__version__,gpu=torch.cuda.get_device_name(),physical_gpu_bytes=torch.cuda.get_device_properties(0).total_memory,precision='float32/eval',cpu_threads=4,tf32_matmul=False,tf32_cudnn=True))
    receipt['nvidia_smi']=subprocess.check_output(['/usr/lib/wsl/lib/nvidia-smi','--query-gpu=driver_version,name,memory.total','--format=csv,noheader'],text=True,timeout=15).strip();original=model.official['prefix']
    def prefix(text):
        if receipt['prefix_calls']>=prefix_limit:raise RuntimeError('Prefix call cap')
        receipt['prefix_calls']+=1;return original(text)
    model.official['prefix']=prefix
    for e in entries:
        if identity(prefix(sources[key(e)]))!=e['identity']:raise ValueError('Audited evaluation-prefix mismatch')
    fingerprint=lambda:dict(generator=model_fingerprint(model.net),tokenizer=model_fingerprint(model.tokenizer.vqvae));receipt['state_before']=fingerprint()
    return model,sources,receipt,fingerprint

def cache_worker(seconds):
    started=time.monotonic();lock,_=load();alarm(seconds)
    import torch
    from anytime_ncm.development_trace import trace_request
    from anytime_ncm.forced_wmt import ForwardCounter
    entries=read(OUT/'access-release.json')['entries'];plan=read(OUT/'cache-plan.json');counter=None;meter=Meter(lock['cache_feature_caps']);receipt=dict(started_utc=now(),completed_requests=0);save(OUT/'cache-started.json',receipt);request=None
    try:
        model,sources,info,fingerprint=model_context(entries,2381);info.update(receipt);receipt=info;counter=ForwardCounter(model,lock['cache_forward_caps'])
        with (OUT/'cache-starts.jsonl').open('x',encoding='utf-8',newline='\n') as ledger,(OUT/'cache-requests.jsonl').open('x',encoding='utf-8',newline='\n') as public,(PRIVATE/'native-traces.jsonl').open('x',encoding='utf-8',newline='\n') as private:
            for number,request in enumerate(plan):
                if time.monotonic()-started>seconds or cpu()>lock['cache_cpu_seconds'] or rss()>lock['worker_rss_bytes'] or size()>lock['artifact_bytes']:raise RuntimeError('Cache worker resources')
                before=dict(counter.counts);fbefore=dict(meter.counts);counter.take('inputs');ledger.write(json.dumps(dict(request,work_before=before,feature_work_before=fbefore))+'\n');ledger.flush();torch.cuda.synchronize();torch.cuda.reset_peak_memory_stats();torch.manual_seed(20261023)
                result=trace_request(model,sources[key(request)],meter);torch.cuda.synchronize();counts={k:counter.counts[k]-before[k] for k in before};fwork={k:meter.counts[k]-fbefore[k] for k in fbefore}
                if counts!=dict(inputs=1,generator_levels=11,decoder=12,encoder=0) or fwork!=dict(cheap_features=2,selected_logit_features=2,cue_features=2) or not result['native_final_parity'] or identity(result['prefix_ids'])!=request['identity']:raise ValueError('Native evaluation-cache work/parity mismatch')
                reserved=torch.cuda.max_memory_reserved()
                if reserved>min(lock['gpu_reserved_bytes'],receipt['environment']['physical_gpu_bytes']):raise RuntimeError('Cache GPU memory cap')
                private.write(json.dumps(dict(request,**result),ensure_ascii=False,allow_nan=False)+'\n');private.flush();public.write(json.dumps(dict(request,work=counts,feature_work=fwork,native_final_parity=True,hashes=cache_row(dict(identity=request['identity'],**result)),features=result['features'],peak_reserved_bytes=reserved),allow_nan=False)+'\n');public.flush();receipt['completed_requests']+=1
                if number%256==0 or number+1==len(plan):print(f'Evaluation native cache: {number+1}/{len(plan)}; identity/native-final/work passed',flush=True)
        receipt['state_after']=fingerprint()
        if cpu()>lock['cache_cpu_seconds'] or receipt['state_before']!=receipt['state_after'] or counter.counts!=lock['cache_forward_caps'] or meter.counts!=lock['cache_feature_caps'] or receipt['prefix_calls']!=2381:raise ValueError('Incomplete native cache/state mutation')
        receipt.update(status='complete',counts=dict(counter.counts),feature_counts=meter.counts,wall_seconds=time.monotonic()-started,cpu_seconds=cpu(),max_rss_bytes=rss(),finished_utc=now());save(OUT/'cache-execution.json',receipt)
    except BaseException as error:
        save(OUT/'cache-failure.json',dict(receipt,error=repr(error),request=request,counts=dict(counter.counts) if counter else {},feature_counts=meter.counts,automatic_retry=False));raise
    finally:
        if counter:counter.close()
        stop_alarm()

def timing_worker(session,seconds):
    started=time.monotonic();lock,_=load();alarm(seconds)
    import torch
    from anytime_ncm.forced_wmt import ForwardCounter,forced_request
    from anytime_ncm.joint_risk_wmt import joint_request
    entries=read(OUT/'access-release.json')['entries'];plan=read(OUT/'timing-schedule.json')[str(session)];cache=read(OUT/'parity-hashes.json');vectors=read(OUT/'current8-features.json');controller=runtime_spec(read(POLICY)['policy']);limits=sum_work(plan)
    if any(limits[k]>v for k,v in lock['per_session_forward_caps'].items()):raise ValueError('Session work cap')
    counter=None;meter=Meter(lock['per_session_feature_caps']);receipt=dict(session=session,started_utc=now(),completed_requests=0);save(OUT/f'{session}-started.json',receipt);request=None
    try:
        model,sources,info,fingerprint=model_context(entries,29760);info.update(receipt);receipt=info;counter=ForwardCounter(model,limits);begin,end=torch.cuda.Event(enable_timing=True),torch.cuda.Event(enable_timing=True)
        with (OUT/f'{session}-starts.jsonl').open('x',encoding='utf-8',newline='\n') as ledger,(OUT/f'{session}-requests.jsonl').open('x',encoding='utf-8',newline='\n') as stream:
            for number,request in enumerate(plan):
                if time.monotonic()-started>seconds or cpu()>lock['timing_worker_cpu_seconds'] or rss()>lock['worker_rss_bytes'] or size()>lock['artifact_bytes']:raise RuntimeError('Timing worker resources')
                before=dict(counter.counts);fbefore=dict(meter.counts);counter.take('inputs');ledger.write(json.dumps(dict(request,work_before=before,feature_work_before=fbefore))+'\n');ledger.flush();torch.cuda.synchronize();torch.cuda.reset_peak_memory_stats();torch.manual_seed(20261023);wall=time.perf_counter_ns();begin.record()
                if request['method']=='controller':result=joint_request(model,sources[key(request)],controller,meter)
                else:result=forced_request(model,sources[key(request)],request['depth'],'terminal')
                end.record();torch.cuda.synchronize();wall_ms=(time.perf_counter_ns()-wall)/1e6;actual={k:counter.counts[k]-before[k] for k in before};fwork={k:meter.counts[k]-fbefore[k] for k in fbefore};ctrl=request['method']=='controller';expected=dict(cheap_features=int(ctrl),selected_logit_features=0,cue_features=0,decisions=int(ctrl))
                if actual!=work(request) or fwork!=expected or result['exit_level']!=request['depth'] or [o['level'] for o in result['observations']]!=request['visits']:raise ValueError('Actual selected policy/replay work mismatch')
                hashes=dict(prefix=value_hash(result['prefix_ids']),codes=value_hash(result['codes'][0].cpu().tolist()),outputs={str(o['level']):dict(ids=value_hash(o['ids']),text=value_hash(o['text'])) for o in result['observations']});c=cache[key(request)]
                if hashes['prefix']!=c['prefix'] or hashes['codes']!=c['codes'][str(request['depth'])] or any(hashes['outputs'][str(d)]!=c['outputs'][str(d)] for d in request['visits']):raise ValueError('Actual output/prefix parity failed')
                current={str(v['level']):value_hash(v['codes']) for v in result.get('prefix_codes',[])}
                if ctrl:
                    if current!={'8':c['codes']['8']} or [v['level'] for v in result['features']]!=[8] or not np.allclose(result['features'][0]['values'][:19],vectors[key(request)][:19],rtol=1e-5,atol=1e-6) or result['features'][0]['values'][19:]!=[0.]*8:raise ValueError('Actual cheap current feature/prefix mismatch')
                reserved=torch.cuda.max_memory_reserved()
                if reserved>min(lock['gpu_reserved_bytes'],receipt['environment']['physical_gpu_bytes']):raise RuntimeError('Timing GPU memory cap')
                stream.write(json.dumps(dict(request,wall_ms=wall_ms,cuda_stream_span_ms=begin.elapsed_time(end),work=actual,feature_work=fwork,peak_allocated_bytes=torch.cuda.max_memory_allocated(),peak_reserved_bytes=reserved,parity=True,hashes=hashes,current_code_hashes=current,features=result.get('features',[])),allow_nan=False)+'\n');stream.flush();receipt['completed_requests']+=1
                if number%512==0 or number+1==len(plan):print(f'One-shot evaluation session {session}: {number+1}/{len(plan)}; causal exits/skipped work/current-output parity passed',flush=True)
        receipt['state_after']=fingerprint()
        if cpu()>lock['timing_worker_cpu_seconds'] or receipt['state_before']!=receipt['state_after'] or counter.counts!=limits or meter.counts!=lock['per_session_feature_caps'] or receipt['prefix_calls']!=29760:raise ValueError('Timing completion/state/work mismatch')
        receipt.update(status='complete',counts=dict(counter.counts),feature_counts=meter.counts,wall_seconds=time.monotonic()-started,cpu_seconds=cpu(),max_rss_bytes=rss(),finished_utc=now());save(OUT/f'{session}-execution.json',receipt)
    except BaseException as error:
        save(OUT/f'{session}-failure.json',dict(receipt,error=repr(error),request=request,counts=dict(counter.counts) if counter else {},feature_counts=meter.counts,automatic_retry=False));raise
    finally:
        if counter:counter.close()
        stop_alarm()

def run(commit):
    started=time.monotonic();lock,source=load();verify_campaign(ROOT,lock['campaign_reservation'])
    if git('rev-parse','HEAD')!=commit or git('branch','--show-current')!='main' or git('status','--porcelain') or git('ls-remote','origin','refs/heads/main').split()[0]!=commit:raise ValueError('Need clean main at pushed one-shot evaluation lock')
    if PRIVATE.exists():raise ValueError('Evaluation already exists; no implicit reuse/retry')
    OUT.mkdir(parents=True,exist_ok=False);PRIVATE.mkdir(parents=True,exist_ok=False);save(OUT/'started.json',dict(source_commit=commit,policy_commit=lock['policy_commit'],policy_sha256=lock['policy_sha256'],started_utc=now()));alarm(lock['wall_seconds']);meter=Meter(lock['analysis_caps'])
    try:
        with zipfile.ZipFile(OUT/'execution-sources.zip','x',compression=zipfile.ZIP_DEFLATED) as z:
            for p in source['source_sha256']:z.writestr(p,(ROOT/p).read_bytes())
            z.writestr('source-lock.json',json.dumps(source,indent=2))
        if sys.version_info[:3]!=(3,12,3) or any(importlib.metadata.version(k)!=v for k,v in lock['versions'].items()):raise RuntimeError('Pinned analysis environment drift')
        test_start=time.monotonic()
        with (OUT/'synthetic-tests.log').open('x',encoding='utf-8',newline='\n') as log:
            test_code='import resource,runpy; resource.setrlimit(resource.RLIMIT_CPU,(50,50)); runpy.run_module("pytest",run_name="__main__")'
            test=subprocess.run([sys.executable,'-c',test_code,'tests/test_development_evaluation.py','-q','-s','-p','no:cacheprovider','--basetemp=results/quality_tolerant/campaign_20261029/development_evaluation/pytest-tmp','--junitxml=results/quality_tolerant/campaign_20261029/development_evaluation/synthetic-tests.xml'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=lock['test_wall_seconds'])
        synthetic_seconds=time.monotonic()-test_start
        if test.returncode:raise RuntimeError('Synthetic validation failed before evaluation release')
        if 'SYNTHETIC_DEVELOPMENT_EVALUATION_REQUESTS 4' not in (OUT/'synthetic-tests.log').read_text(encoding='utf-8'):raise ValueError('Missing synthetic API ledger')
        policy=read(POLICY);entries=sorted(read(CAMPAIGN/'development_eligibility/source-only-allocation.json')['parts']['development_evaluation'],key=lambda e:(e['year'],e['index']))
        if len(entries)!=1188 or len({e['component'] for e in entries})!=60 or not policy['ready_for_development_evaluation'] or policy['locked_fixed_comparator']!='fixed:11':raise ValueError('Fixed evaluation gate/allocation changed')
        save(OUT/'access-release.json',dict(entries=entries,roles=['development_evaluation'],policy_commit=lock['policy_commit'],policy_sha256=lock['policy_sha256'],selection_already_pushed=True,proposed_confirmation7700_released=False,historical87_E3_E4_unallocated_released=False,independent_confirmation=False))
        sources,references,receipt=extract_corpus(ROOT,entries,lock['archives'],meter,lock['decompressed_bytes_cap']);save(OUT/'corpus-access.json',dict(years=receipt,selected_source_payloads=1188,selected_reference_payloads=1188,all_other_payloads_skipped_before_utf8=True,source_convention='exact audited raw segment payload'))
        for name,field,values in [('sources.jsonl','source',sources),('references.jsonl','reference',references)]:
            with (PRIVATE/name).open('x',encoding='utf-8',newline='\n') as f:
                for e in entries:f.write(json.dumps(dict(e,**{field:values[key(e)]}),ensure_ascii=False)+'\n')
        config=read(ROOT/'configs/phase4_wmt_sources.json');assets={p:v for p,v in config['files'].items() if p.startswith('artifacts/wmt14/')}
        for p,v in assets.items():
            if sha(ROOT/p)!=v['sha256'] or (ROOT/p).stat().st_size!=v['size']:raise ValueError('Pinned local asset drift')
        save(OUT/'asset-preflight.json',dict(asset_sha256={p:v['sha256'] for p,v in assets.items()},historical_corpus_bodies_read=0));plan=[]
        for i,e in enumerate(entries[:5]):plan.append(dict(e,request_id=len(plan),position=i,warmup=True))
        for i,e in enumerate(entries):plan.append(dict(e,request_id=len(plan),position=i,warmup=False))
        save(OUT/'cache-plan.json',plan);print('Five synthetic cases passed; committed-policy development evaluation released once',flush=True);model_start=time.monotonic();remaining=min(lock['model_wall_seconds'],lock['wall_seconds']-(model_start-started));subprocess.run([sys.executable,str(Path(__file__).resolve()),'cache-worker','--seconds',str(remaining)],cwd=ROOT,check=True,timeout=remaining)
        rows={};cache={};vectors={};predictions=[];ordered_keys=[key(e) for e in entries]
        for line in (PRIVATE/'native-traces.jsonl').read_text(encoding='utf-8').splitlines():
            meter.take('native_trace_bodies');r=json.loads(line)
            if r['warmup']:continue
            k=key(r)
            if k not in references or k in rows:raise ValueError('Duplicate/unallocated native evaluation row')
            rows[k]=r;cache[k]=cache_row(r);vectors[k]=r['features'][0]['values']
        if len(rows)!=1188:raise ValueError('Missing native evaluation cache')
        for k in ordered_keys:predictions.append((8,[8]) if decide(policy['policy'],8,vectors[k]) else (11,[8,11]))
        save(OUT/'parity-hashes.json',cache);save(OUT/'current8-features.json',vectors);save(OUT/'predictions.json',[dict(year=e['year'],index=e['index'],depth=d,visits=v) for e,(d,v) in zip(entries,predictions)])
        plans={str(s):schedule(entries,predictions,s) for s in (0,1)}
        for plan in plans.values():
            for r in plan:r['year']=entries[r['position']]['year']
            if any(sum_work(plan)[k]>v for k,v in lock['per_session_forward_caps'].items()):raise ValueError('Predicted timing plan exceeds frozen cap')
        save(OUT/'timing-schedule.json',plans);refs=[references[k] for k in ordered_keys]
        def metric(hyps):meter.take('corpus_scores');return scores(hyps,refs)
        full=metric([rows[k]['levels'][-1]['text'] for k in ordered_keys])
        if full['numeric_reference_coverage']<100:raise ValueError('Inadequate numeric point coverage; no inference certificate implied')
        quality={}
        for method in METHODS:
            depths=[d for d,v in predictions] if method=='controller' else [int(method.split(':')[1])]*1188;m=full if method=='fixed:11' else metric([rows[k]['levels'][d-1]['text'] for k,d in zip(ordered_keys,depths)]);quality[method]=dict(metrics=m,losses=point_losses(m,full),point_pass=point_pass(m,full))
        save(OUT/'quality-points.json',quality);save(OUT/'evaluation-shape.json',dict(inputs=1188,components=60,numeric_reference_coverage=full['numeric_reference_coverage'],early_inputs=sum(d<11 for d,v in predictions),policy_unchanged=True,quality_points_do_not_control_timing_collection=True))
        for s in (0,1):
            remaining=min(lock['model_wall_seconds']-(time.monotonic()-model_start),lock['wall_seconds']-(time.monotonic()-started))
            if remaining<=0:raise RuntimeError('Evaluation model deadline')
            subprocess.run([sys.executable,str(Path(__file__).resolve()),'timing-worker','--session',str(s),'--seconds',str(remaining)],cwd=ROOT,check=True,timeout=remaining)
        model_seconds=time.monotonic()-model_start;processes=[read(OUT/'cache-execution.json')]+[read(OUT/f'{s}-execution.json') for s in (0,1)]
        if len({p['pid'] for p in processes})!=3 or any(p['state_before']!=processes[0]['state_before'] for p in processes):raise ValueError('Expected three separate identical-checkpoint processes')
        records=[json.loads(line) for s in (0,1) for line in (OUT/f'{s}-requests.jsonl').read_text(encoding='utf-8').splitlines()];analysis=timing_analysis(records,entries,quality,policy['locked_fixed_comparator'],sum(d<11 for d,v in predictions));analysis.update(population='development_evaluation1188',policy_commit=lock['policy_commit'],policy_selected_before_outcome_release=True,independent_quality_guarantee=False,original_success_contract_established=False,post_evaluation_retuning=False)
        save(OUT/'analysis.json',analysis);counts={k:sum(p['counts'][k] for p in processes) for k in lock['cache_forward_caps']}
        hashes_ok(source['protected_sha256']);hashes_ok(source['source_sha256'])
        if time.monotonic()-started>lock['wall_seconds'] or own_cpu()>lock['parent_own_cpu_seconds'] or cpu()>lock['execution_cpu_cap_seconds'] or rss()>lock['parent_rss_bytes'] or size()>lock['artifact_bytes']:raise RuntimeError('Evaluation completion resource cap')
        usage=usage_zero();usage.update(model_requests=counts['inputs']+4,model_orchestration_seconds=model_seconds+synthetic_seconds,cpu_seconds=cpu()+lock['reporting_cpu_charge_seconds'],artifact_bytes=lock['artifact_bytes']);verify_campaign(ROOT,usage)
        save(OUT/'decision.json',dict(status=analysis['decision'],next_branch='confirmation_readiness_audit_and_campaign_closeout',Q0_passed=False,independent_confirmation=False,proposed_confirmation_released=False,original_success_contract_established=False,post_evaluation_refits_or_reselection_allowed=False))
        save(OUT/'execution.json',dict(status='complete',source_commit=commit,policy_commit=lock['policy_commit'],policy_sha256=lock['policy_sha256'],counts=counts,cache_counts=processes[0]['counts'],timing_counts={k:sum(p['counts'][k] for p in processes[1:]) for k in counts},feature_counts={k:sum(p['feature_counts'].get(k,0) for p in processes) for k in ('cheap_features','selected_logit_features','cue_features','decisions')},analysis_counts=meter.counts,synthetic_model_requests=4,synthetic_generator_levels=30,synthetic_decoder_calls=5,synthetic_wall_seconds_charged=synthetic_seconds,real_checkpoint_loads=3,new_fits=0,new_controller_families=0,target_encodings=0,encoder_calls=0,source_payload_decodes=1188,reference_payload_decodes=1188,worker_source_materializations=3564,worker_reference_cache_opened=False,bootstrap_draws=20000,model_states_unchanged=True,all_actual_exit_work_current_features_and_outputs_verified=True,model_orchestration_wall_seconds=model_seconds,total_wall_seconds=time.monotonic()-started,cpu_seconds_before_reporting_charge=cpu(),max_parent_rss_bytes=rss(),private_artifact_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in PRIVATE.rglob('*') if p.is_file()},campaign_usage=usage,automatic_retries=0,paid_dollars=0,finished_utc=now(),artifact_sha256={p.relative_to(OUT).as_posix():sha(p) for p in OUT.rglob('*') if p.is_file()}))
        print(json.dumps(record_phase(ROOT,'09-development-evaluation','development_evaluation/execution.json')),flush=True);print('ONE-SHOT DEVELOPMENT EVALUATION COMPLETE: '+analysis['decision'],flush=True)
    except BaseException as error:
        failure=OUT/'failure.json'
        if not failure.exists():save(failure,dict(error=repr(error),counts=meter.counts,campaign_usage=lock['campaign_reservation'],conservative_reservation_charge=True,automatic_retry=False))
        if not (CAMPAIGN/'accounting/phase-09-development-evaluation.json').exists():record_phase(ROOT,'09-development-evaluation','development_evaluation/failure.json')
        raise
    finally:stop_alarm()

def verify():
    lock,source=load();e=read(OUT/'execution.json');hashes_ok({('results/quality_tolerant/campaign_20261029/development_evaluation/'+p):h for p,h in e['artifact_sha256'].items()});hashes_ok(e['private_artifact_sha256']);plans=read(OUT/'timing-schedule.json');cache=read(OUT/'parity-hashes.json');cache_records=[json.loads(line) for line in (OUT/'cache-requests.jsonl').read_text(encoding='utf-8').splitlines()]
    cp=read(OUT/'cache-execution.json')
    if len(cache_records)!=1193 or cp['counts']!=lock['cache_forward_caps'] or cp['state_before']!=cp['state_after'] or cp['prefix_calls']!=2381:raise ValueError('Incomplete native cache receipt')
    for r in cache_records:
        if not r['native_final_parity'] or r['work']!=dict(inputs=1,generator_levels=11,decoder=12,encoder=0) or (not r['warmup'] and r['hashes']!=cache[key(r)]):raise ValueError('Native cache parity/work mismatch')
    total=dict(cp['counts'])
    for s in (0,1):
        p=read(OUT/f'{s}-execution.json');records=[json.loads(line) for line in (OUT/f'{s}-requests.jsonl').read_text(encoding='utf-8').splitlines()]
        if len(records)!=28572 or p['counts']!=sum_work(plans[str(s)]) or p['state_before']!=p['state_after'] or p['state_before']!=cp['state_before'] or p['feature_counts']!=lock['per_session_feature_caps'] or p['prefix_calls']!=29760:raise ValueError('Incomplete timing process')
        for expected,r in zip(plans[str(s)],records):
            if any(r[k]!=v for k,v in expected.items()) or r['work']!=work(r) or not r['parity']:raise ValueError('Timing plan/work mismatch')
            c=cache[key(r)];h=r['hashes']
            if h['prefix']!=c['prefix'] or h['codes']!=c['codes'][str(r['depth'])] or any(h['outputs'][str(d)]!=c['outputs'][str(d)] for d in r['visits']):raise ValueError('Actual output-prefix receipt mismatch')
            if r['method']=='controller' and r['current_code_hashes']!={'8':c['codes']['8']}:raise ValueError('Actual current generated prefix mismatch')
        for k in total:total[k]+=p['counts'][k]
    if e['status']!='complete' or total!=e['counts'] or total['inputs']!=58337 or e['new_fits'] or e['target_encodings']:raise ValueError('Invalid one-shot evaluation receipt')
    print(json.dumps(dict(verified=True,protected_files=len(source['protected_sha256']),real_requests=total['inputs'],no_new_inference_fitting_resampling_or_reference_scores=True,campaign=verify_campaign(ROOT))))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=('run','cache-worker','timing-worker','verify'));p.add_argument('--commit');p.add_argument('--session',type=int);p.add_argument('--seconds',type=float);a=p.parse_args()
    if a.mode=='run':run(a.commit)
    elif a.mode=='cache-worker':cache_worker(a.seconds)
    elif a.mode=='timing-worker':timing_worker(a.session,a.seconds)
    else:verify()
