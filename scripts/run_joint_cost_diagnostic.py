"""Once-only actual timing of the frozen family1policy on consumed calibration inputs."""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='4'
for k in ('HF_HUB_OFFLINE','TRANSFORMERS_OFFLINE'):os.environ[k]='1'
os.environ['TOKENIZERS_PARALLELISM']='false';os.environ['PYTHONDONTWRITEBYTECODE']='1'
import argparse,json,signal,subprocess,sys,time,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from run_signal_discrimination import git,cpu,rss,now,hashes_ok
from anytime_ncm.evidence_preflight import sha,write_new
from anytime_ncm.quality_controller import Meter
from anytime_ncm.controller_study import schedule,sum_work,work,timing_analysis
from anytime_ncm.latency_diagnostic import value_hash
from anytime_ncm.quality_campaign import campaign_root,verify_campaign,record_phase,usage_zero
from anytime_ncm.wmt_data import StringRows,identity
BASE=ROOT/'docs/studies/quality-tolerant';CAMPAIGN=campaign_root(ROOT);SELECT=CAMPAIGN/'joint_controller_selection';PREV=CAMPAIGN/'signal_discrimination';OUT=CAMPAIGN/'joint_cost_diagnostic'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def size():return sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file())
def alarm(seconds):
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('Cost diagnostic wall cap')));signal.setitimer(signal.ITIMER_REAL,seconds)
def stop_alarm():signal.setitimer(signal.ITIMER_REAL,0)
def load():
    lock=read(BASE/'joint-cost-diagnostic-lock.json');source=read(BASE/'joint-cost-diagnostic-source-lock.json');hashes_ok(source['source_sha256']);hashes_ok(source['protected_sha256'])
    if git('-C','third_party/ncm','rev-parse','HEAD')!=source['upstream_commit'] or git('-C','third_party/ncm','status','--porcelain'):raise ValueError('Upstream changed')
    if sha(SELECT/'policy.json')!=lock['policy_sha256']:raise ValueError('Selected policy changed')
    return lock,source

def worker(session,seconds):
    started=time.monotonic();lock,_=load();alarm(seconds)
    import numpy as np
    import torch,transformers
    from anytime_ncm.wmt_model import WmtModel
    from anytime_ncm.forced_wmt import ForwardCounter,forced_request
    from anytime_ncm.joint_risk_wmt import joint_request
    from anytime_ncm.target_encoding import model_fingerprint
    entries=read(OUT/'access-release.json')['entries'];plan=read(OUT/'timing-schedule.json')[str(session)];cache=read(OUT/'parity-hashes.json');vectors=read(OUT/'current8-features.json');policy=read(SELECT/'policy.json')['policy']
    receipt=dict(session=session,pid=os.getpid(),started_utc=now(),completed_requests=0,prefix_calls=0);write_new(OUT/f'{session}-started.json',receipt)
    counter=None;result=None;request=None;meter=Meter(lock['per_session_feature_caps']);limits=sum_work(plan)
    try:
        if (sys.version_info[:3]!=(3,12,3) or torch.__version__!='2.10.0+cu128' or torch.version.cuda!='12.8' or transformers.__version__!='4.57.6'
            or not torch.cuda.is_available() or torch.cuda.get_device_name()!='NVIDIA GeForce RTX 5060'):raise RuntimeError('Material environment drift')
        torch.set_num_threads(4);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=True
        sources=StringRows((ROOT/'data/wmt14/sources.pickle').read_bytes()).select({e['index'] for e in entries});model=WmtModel(ROOT)
        receipt['environment']=dict(python=sys.version,torch=torch.__version__,cuda=torch.version.cuda,transformers=transformers.__version__,gpu=torch.cuda.get_device_name(),physical_gpu_bytes=torch.cuda.get_device_properties(0).total_memory,precision='float32/eval',cpu_threads=4,tf32_matmul=False,tf32_cudnn=True)
        receipt['nvidia_smi']=subprocess.check_output(['/usr/lib/wsl/lib/nvidia-smi','--query-gpu=driver_version,name,memory.total','--format=csv,noheader'],text=True,timeout=15).strip()
        original=model.official['prefix']
        def prefix(text):
            if receipt['prefix_calls']>=2585:raise RuntimeError('Prefix cap')
            receipt['prefix_calls']+=1;return original(text)
        model.official['prefix']=prefix
        for e in entries:
            if identity(prefix(sources[e['index']]))!=e['identity']:raise ValueError('Effective-prefix identity mismatch')
        fingerprint=lambda:dict(generator=model_fingerprint(model.net),tokenizer=model_fingerprint(model.tokenizer.vqvae))
        receipt['state_before']=fingerprint();counter=ForwardCounter(model,limits);begin,end=torch.cuda.Event(enable_timing=True),torch.cuda.Event(enable_timing=True)
        with (OUT/f'{session}-starts.jsonl').open('x',encoding='utf-8',newline='\n') as ledger,(OUT/f'{session}-requests.jsonl').open('x',encoding='utf-8',newline='\n') as stream:
            for number,request in enumerate(plan):
                if time.monotonic()-started>seconds or rss()>lock['worker_rss_bytes']:raise RuntimeError('Worker time/RSS cap')
                before=dict(counter.counts);fbefore=dict(meter.counts);counter.take('inputs');ledger.write(json.dumps(dict(request,work_before=before,feature_work_before=fbefore))+'\n');ledger.flush()
                torch.cuda.synchronize();torch.cuda.reset_peak_memory_stats();torch.manual_seed(20261023);result=None;wall=time.perf_counter_ns();begin.record()
                if request['method']=='controller':result=joint_request(model,sources[request['index']],policy,meter)
                else:result=forced_request(model,sources[request['index']],request['depth'],'terminal')
                end.record();torch.cuda.synchronize();wall_ms=(time.perf_counter_ns()-wall)/1e6
                counts={k:counter.counts[k]-before[k] for k in before};fwork={k:meter.counts[k]-fbefore[k] for k in fbefore}
                expected_features=dict.fromkeys(lock['per_session_feature_caps'],1 if request['method']=='controller' else 0)
                if counts!=work(request) or fwork!=expected_features or result['exit_level']!=request['depth'] or [o['level'] for o in result['observations']]!=request['visits']:raise ValueError('Online/replay work or exit mismatch')
                hashes=dict(prefix=value_hash(result['prefix_ids']),codes=value_hash(result['codes'][0].cpu().tolist()),outputs={str(o['level']):dict(ids=value_hash(o['ids']),text=value_hash(o['text'])) for o in result['observations']})
                c=cache[str(request['index'])]
                if hashes['prefix']!=c['prefix'] or hashes['codes']!=c['codes'][str(request['depth'])] or any(hashes['outputs'][str(d)]!=c['outputs'][str(d)] for d in request['visits']):raise ValueError('Output/final-prefix parity failed')
                current_hashes={str(v['level']):value_hash(v['codes']) for v in result.get('prefix_codes',[])}
                if request['method']=='controller':
                    if current_hashes!={'8':c['codes']['8']} or [v['level'] for v in result['features']]!=[8]:raise ValueError('Actual current generated prefix differs')
                    if not np.allclose(result['features'][0]['values'],vectors[str(request['index'])],rtol=1e-5,atol=1e-6):raise ValueError('Actual causal feature parity failed')
                reserved=torch.cuda.max_memory_reserved()
                if reserved>min(lock['gpu_reserved_bytes'],receipt['environment']['physical_gpu_bytes']):raise RuntimeError('GPU memory cap')
                stream.write(json.dumps(dict(request,wall_ms=wall_ms,cuda_stream_span_ms=begin.elapsed_time(end),work=counts,feature_work=fwork,peak_allocated_bytes=torch.cuda.max_memory_allocated(),peak_reserved_bytes=reserved,parity=True,hashes=hashes,current_code_hashes=current_hashes,features=result.get('features',[])),allow_nan=False)+'\n');stream.flush();receipt['completed_requests']+=1
                if number%256==0 or number+1==len(plan):
                    if size()>lock['artifact_bytes']:raise RuntimeError('Artifact cap')
                    print(f'Joint cost session {session}: {number+1}/{len(plan)}; actual skipped work/current-feature/output parity passed',flush=True)
        receipt['state_after']=fingerprint()
        if receipt['state_before']!=receipt['state_after'] or counter.counts!=limits or meter.counts!=lock['per_session_feature_caps'] or receipt['prefix_calls']!=2585:raise ValueError('Completion/state/work mismatch')
        receipt.update(status='complete',counts=dict(counter.counts),forward_calls=dict(counter.calls),feature_counts=meter.counts,wall_seconds=time.monotonic()-started,cpu_seconds=cpu(),max_rss_bytes=rss(),finished_utc=now());write_new(OUT/f'{session}-execution.json',receipt)
    except BaseException as error:
        write_new(OUT/f'{session}-failure.json',dict(receipt,error=repr(error),request=request,counts=dict(counter.counts) if counter else {},feature_counts=meter.counts,automatic_retry=False));raise
    finally:
        if counter:counter.close()
        stop_alarm()

def run(commit):
    started=time.monotonic();lock,source=load();verify_campaign(ROOT,lock['campaign_reservation'])
    if git('rev-parse','HEAD')!=commit or git('branch','--show-current')!='main' or git('status','--porcelain') or git('ls-remote','origin','refs/heads/main').split()[0]!=commit:raise ValueError('Need clean main at pushed cost lock')
    OUT.mkdir(parents=True,exist_ok=False);write_new(OUT/'started.json',dict(source_commit=commit,policy_sha256=lock['policy_sha256'],started_utc=now()));alarm(lock['wall_seconds'])
    try:
        with zipfile.ZipFile(OUT/'execution-sources.zip','x',compression=zipfile.ZIP_DEFLATED) as z:
            for p in source['source_sha256']:z.writestr(p,(ROOT/p).read_bytes())
            z.writestr('source-lock.json',json.dumps(source,indent=2))
        synthetic_start=time.monotonic()
        with (OUT/'synthetic-tests.log').open('x',encoding='utf-8',newline='\n') as log:
            test=subprocess.run([sys.executable,'-m','pytest','tests/test_joint_cost_diagnostic.py','-q','-s','-p','no:cacheprovider','--junitxml=results/quality_tolerant/campaign_20261029/joint_cost_diagnostic/synthetic-tests.xml'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=lock['test_wall_seconds'])
        synthetic_wall_seconds=time.monotonic()-synthetic_start
        if test.returncode:raise RuntimeError('Synthetic validation failed before source/model access')
        if 'SYNTHETIC_JOINT_REQUESTS 4' not in (OUT/'synthetic-tests.log').read_text(encoding='utf-8'):raise ValueError('Missing synthetic work receipt')
        config=read(ROOT/'configs/phase4_wmt_sources.json');assets={p:v for p,v in config['files'].items() if p!='data/wmt14/reference_translations.pickle'}
        for p,v in assets.items():
            if sha(ROOT/p)!=v['sha256'] or (ROOT/p).stat().st_size!=v['size']:raise ValueError('Pinned asset differs: '+p)
        write_new(OUT/'asset-preflight.json',dict(asset_sha256={p:v['sha256'] for p,v in assets.items()},reference_bodies=0))
        entries=sorted(read(BASE/'controller-split.json')['parts']['calibration'],key=lambda e:e['index']);prior=read(SELECT/'candidate-results.json');policy=read(SELECT/'policy.json');chosen=next(v for v in prior['candidates'] if v['name']==policy['policy']['name'])
        if len(entries)!=101 or chosen['early_inputs']!=23 or policy['policy']['name']!='selected_logit:8:guard1:0.6':raise ValueError('Frozen cost diagnostic target differs')
        write_new(OUT/'access-release.json',dict(entries=entries,roles=['consumed_calibration_only'],new_reference_or_trajectory_bodies=0,worker_source_materializations=202,old_test87_released=False,E3_E4_unallocated_released=False,policy_unchanged=True))
        cache=read(PREV/'parity-hashes.json');write_new(OUT/'parity-hashes.json',{str(e['index']):cache[str(e['index'])] for e in entries})
        vectors={}
        for line in (PREV/'requests.jsonl').read_text(encoding='utf-8').splitlines():
            record=json.loads(line)
            if not record['warmup'] and any(e['index']==record['index'] for e in entries):vectors[str(record['index'])]=record['features'][0]['values']
        if len(vectors)!=101:raise ValueError('Missing old current features')
        write_new(OUT/'current8-features.json',vectors)
        assignments={v['index']:(v['depth'],v['visits']) for v in chosen['assignments']};predictions=[assignments[e['index']] for e in entries];plans={str(s):schedule(entries,predictions,s) for s in (0,1)}
        for plan in plans.values():
            if any(sum_work(plan)[k]>v for k,v in lock['per_session_forward_caps'].items()):raise ValueError('Plan exceeds work cap')
        write_new(OUT/'timing-schedule.json',plans)
        print('Four synthetic checks passed; fixed policy calibration cost measurement released',flush=True);model_start=time.monotonic()
        for s in (0,1):
            remaining=min(lock['model_wall_seconds']-(time.monotonic()-model_start),lock['wall_seconds']-(time.monotonic()-started))
            if remaining<=0:raise RuntimeError('Model time cap')
            subprocess.run([sys.executable,str(Path(__file__).resolve()),'worker','--session',str(s),'--seconds',str(remaining)],cwd=ROOT,check=True,timeout=remaining)
        model_seconds=time.monotonic()-model_start;processes=[read(OUT/f'{s}-execution.json') for s in (0,1)]
        if len({p['pid'] for p in processes})!=2:raise ValueError('Need two independent model processes')
        records=[json.loads(line) for s in (0,1) for line in (OUT/f'{s}-requests.jsonl').read_text(encoding='utf-8').splitlines()]
        quality={'controller':{k:chosen[k] for k in ('metrics','losses','point_pass')},**{r['method']:r for r in prior['fixed']}}
        report=timing_analysis(records,entries,quality,policy['locked_fixed_comparator'],23);report.update(population='consumed_calibration101',policy_selected_on_same_quality_data=True,new_quality_evidence=False,original_phase04_spend_gate_still_failed=True)
        write_new(OUT/'analysis.json',report);counts={k:sum(p['counts'][k] for p in processes) for k in lock['per_session_forward_caps']}
        hashes_ok(source['protected_sha256']);hashes_ok(source['source_sha256'])
        if time.monotonic()-started>lock['wall_seconds'] or cpu()>lock['execution_cpu_cap_seconds'] or rss()>lock['parent_rss_bytes'] or size()>lock['artifact_bytes']:raise RuntimeError('Diagnostic resource cap')
        usage=usage_zero();usage.update(model_requests=counts['inputs']+4,model_orchestration_seconds=model_seconds+synthetic_wall_seconds+lock['prior_synthetic_model_wall_allowance_seconds'],cpu_seconds=cpu()+lock['reporting_cpu_charge_seconds'],artifact_bytes=lock['artifact_bytes']);verify_campaign(ROOT,usage)
        write_new(OUT/'decision.json',dict(status=report['decision'],next_branch='prospectively_lock_allocated_evaluation' if report['decision']=='exploratory_controller_screen_passed' else 'bounded_family2_or_data_eligibility_review',Q0_passed=False,independent_confirmation=False,old_test87_released=False,reserved_outputs_released=False,phase04_failed_spend_gate_preserved=True))
        write_new(OUT/'execution.json',dict(status='complete',source_commit=commit,policy_sha256=lock['policy_sha256'],counts=counts,feature_counts={k:sum(p['feature_counts'][k] for p in processes) for k in lock['per_session_feature_caps']},synthetic_model_requests=4,synthetic_wall_seconds_charged=synthetic_wall_seconds,prior_synthetic_model_wall_allowance_seconds=lock['prior_synthetic_model_wall_allowance_seconds'],model_wall_charge_interpretation='real process wall plus entire current synthetic test process and conservative phase01/02 synthetic ceilings; allowances are not claims of actual execution',synthetic_generator_levels=30,synthetic_decoder_calls=4,real_checkpoint_loads=2,new_fits=0,new_controller_families=0,target_encodings=0,reference_bodies=0,old_trajectory_bodies=0,source_materializations=202,prior_saved_feature_records=366,bootstrap_draws=20000,model_orchestration_wall_seconds=model_seconds,total_wall_seconds=time.monotonic()-started,cpu_seconds_before_reporting_charge=cpu(),max_parent_rss_bytes=rss(),campaign_usage=usage,automatic_retries=0,paid_compute_dollars=0,model_states_unchanged=True,all_output_work_and_feature_parity=True,finished_utc=now(),artifact_sha256={p.relative_to(OUT).as_posix():sha(p) for p in OUT.rglob('*') if p.is_file()}))
        print(json.dumps(record_phase(ROOT,'05-joint-cost-diagnostic','joint_cost_diagnostic/execution.json')),flush=True);print('JOINT COST DIAGNOSTIC COMPLETE: '+report['decision'],flush=True)
    except BaseException as error:
        failure=OUT/'failure.json'
        if not failure.exists():write_new(failure,dict(error=repr(error),wall_seconds=time.monotonic()-started,campaign_usage=lock['campaign_reservation'],conservative_reservation_charge=True,automatic_retry=False))
        if not (CAMPAIGN/'accounting/phase-05-joint-cost-diagnostic.json').exists():record_phase(ROOT,'05-joint-cost-diagnostic','joint_cost_diagnostic/failure.json')
        raise
    finally:stop_alarm()

def verify():
    lock,source=load();e=read(OUT/'execution.json');hashes_ok({('results/quality_tolerant/campaign_20261029/joint_cost_diagnostic/'+p):h for p,h in e['artifact_sha256'].items()});plans=read(OUT/'timing-schedule.json');cache=read(OUT/'parity-hashes.json')
    total=dict.fromkeys(lock['per_session_forward_caps'],0)
    for s in (0,1):
        p=read(OUT/f'{s}-execution.json');rows=[json.loads(line) for line in (OUT/f'{s}-requests.jsonl').read_text(encoding='utf-8').splitlines()]
        if len(rows)!=2484 or p['counts']!=sum_work(plans[str(s)]) or p['state_before']!=p['state_after'] or p['prefix_calls']!=2585 or p['feature_counts']!=lock['per_session_feature_caps']:raise ValueError('Session incomplete')
        for expected,r in zip(plans[str(s)],rows):
            if any(r[k]!=v for k,v in expected.items()) or not r['parity'] or r['work']!=work(r):raise ValueError('Request mismatch')
            c=cache[str(r['index'])];h=r['hashes']
            if h['prefix']!=c['prefix'] or h['codes']!=c['codes'][str(r['depth'])] or any(h['outputs'][str(d)]!=c['outputs'][str(d)] for d in r['visits']):raise ValueError('Parity hash mismatch')
            if r['method']=='controller' and r['current_code_hashes']!={'8':c['codes']['8']}:raise ValueError('Actual current-prefix mismatch')
        for k in total:total[k]+=p['counts'][k]
    if e['status']!='complete' or e['counts']!=total or total['inputs']!=4968 or e['new_fits'] or e['reference_bodies']:raise ValueError('Invalid diagnostic execution')
    print(json.dumps(dict(verified=True,protected_files=len(source['protected_sha256']),real_requests=total['inputs'],campaign=verify_campaign(ROOT),new_inference_or_fitting_or_resampling=0)))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=('run','worker','verify'));p.add_argument('--commit');p.add_argument('--session',type=int);p.add_argument('--seconds',type=float);a=p.parse_args()
    if a.mode=='run':run(a.commit)
    elif a.mode=='worker':worker(a.session,a.seconds)
    else:verify()
