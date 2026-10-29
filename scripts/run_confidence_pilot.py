"""Once-only richer-confidence engineering pilot under campaign ceilings."""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='4'
for k in ('HF_HUB_OFFLINE','TRANSFORMERS_OFFLINE'):os.environ[k]='1'
os.environ['TOKENIZERS_PARALLELISM']='false';os.environ['PYTHONDONTWRITEBYTECODE']='1'
import argparse
from datetime import datetime,timezone
import json,resource,signal,subprocess,sys,time,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from anytime_ncm.evidence_preflight import sha,write_new
from anytime_ncm.quality_controller import Meter
from anytime_ncm.controller_study import selected_rows,cache_row
from anytime_ncm.latency_diagnostic import check_parity
from anytime_ncm.confidence_pilot import schedule,analyze
from anytime_ncm.quality_campaign import verify_campaign,record_phase,usage_zero,campaign_root
from anytime_ncm.wmt_data import StringRows,identity
BASE=ROOT/'docs/studies/quality-tolerant';CAMPAIGN=campaign_root(ROOT);OUT=CAMPAIGN/'signal_pilot'

def read(p):return json.loads(p.read_text(encoding='utf-8'))
def git(*a):return subprocess.check_output(['git.exe',*a],cwd=ROOT,text=True,timeout=60).strip()
def now():return datetime.now(timezone.utc).isoformat()
def rss():return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
def cpu():
    a=resource.getrusage(resource.RUSAGE_SELF);b=resource.getrusage(resource.RUSAGE_CHILDREN)
    return a.ru_utime+a.ru_stime+b.ru_utime+b.ru_stime

def hashes_ok(values):
    for p,h in values.items():
        if sha(ROOT/p)!=h:raise ValueError('Frozen bytes changed: '+p)

def load():
    lock=read(BASE/'confidence-pilot-lock.json');sources=read(BASE/'confidence-pilot-source-lock.json')
    hashes_ok(sources['source_sha256']);hashes_ok(sources['protected_sha256'])
    if git('-C','third_party/ncm','rev-parse','HEAD')!=sources['upstream_commit'] or git('-C','third_party/ncm','status','--porcelain'):raise ValueError('Upstream changed')
    return lock,sources

def alarm(seconds):
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('Pilot wall allocation exhausted')));signal.setitimer(signal.ITIMER_REAL,seconds)
def stop_alarm():signal.setitimer(signal.ITIMER_REAL,0)
def size():return sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file())

def worker(session,seconds):
    started=time.monotonic();lock,_=load();alarm(seconds)
    import torch,transformers
    from anytime_ncm.wmt_model import WmtModel
    from anytime_ncm.causal_confidence import instrumented_request,RICH_NAMES
    from anytime_ncm.forced_wmt import ForwardCounter
    from anytime_ncm.target_encoding import model_fingerprint
    entries=lock['entries'];plan=read(OUT/'timing-schedule.json')[str(session)];cache=read(OUT/'parity-hashes.json')
    receipt=dict(session=session,pid=os.getpid(),started_utc=now(),completed_requests=0,prefix_calls=0)
    write_new(OUT/f'{session}-started.json',receipt);counter=None;result=None;request=None;meter=Meter(lock['per_session_feature_caps'])
    try:
        if (sys.version_info[:3]!=(3,12,3) or torch.__version__!='2.10.0+cu128' or torch.version.cuda!='12.8' or transformers.__version__!='4.57.6'
            or not torch.cuda.is_available() or torch.cuda.get_device_name()!='NVIDIA GeForce RTX 5060'):raise RuntimeError('Material environment drift')
        if list(RICH_NAMES)!=lock['rich_feature_names']:raise ValueError('Feature schema differs')
        torch.set_num_threads(4);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=True
        sources=StringRows((ROOT/'data/wmt14/sources.pickle').read_bytes()).select({e['index'] for e in entries})
        loading=time.monotonic();model=WmtModel(ROOT);receipt['model_load_seconds']=time.monotonic()-loading
        receipt['environment']=dict(python=sys.version,torch=torch.__version__,cuda=torch.version.cuda,transformers=transformers.__version__,gpu=torch.cuda.get_device_name(),
            precision='float32/eval',cpu_threads=4,tf32_matmul=False,tf32_cudnn=True,physical_gpu_bytes=torch.cuda.get_device_properties(0).total_memory)
        receipt['nvidia_smi']=subprocess.check_output(['/usr/lib/wsl/lib/nvidia-smi','--query-gpu=driver_version,name,memory.total','--format=csv,noheader'],text=True,timeout=15).strip()
        original=model.official['prefix']
        def prefix(text):
            if receipt['prefix_calls']>=90:raise RuntimeError('Prefix cap')
            receipt['prefix_calls']+=1;return original(text)
        model.official['prefix']=prefix
        for e in entries:
            if identity(prefix(sources[e['index']]))!=e['identity']:raise ValueError('Effective-prefix identity mismatch')
        fingerprint=lambda:dict(generator=model_fingerprint(model.net),tokenizer=model_fingerprint(model.tokenizer.vqvae))
        receipt['state_before']=fingerprint();counter=ForwardCounter(model,lock['per_session_forward_caps'])
        begin,end=torch.cuda.Event(enable_timing=True),torch.cuda.Event(enable_timing=True)
        with (OUT/f'{session}-starts.jsonl').open('x',encoding='utf-8',newline='\n') as ledger,(OUT/f'{session}-requests.jsonl').open('x',encoding='utf-8',newline='\n') as stream:
            for number,request in enumerate(plan):
                if time.monotonic()-started>seconds or rss()>lock['worker_rss_bytes']:raise RuntimeError('Worker wall/RSS cap')
                before=dict(counter.counts);fbefore=dict(meter.counts);counter.take('inputs')
                ledger.write(json.dumps(dict(request,work_before=before,feature_work_before=fbefore))+'\n');ledger.flush()
                torch.cuda.synchronize();torch.cuda.reset_peak_memory_stats();torch.manual_seed(20261023)
                result=None;wall=time.perf_counter_ns();begin.record()
                result=instrumented_request(model,sources[request['index']],request['kind'],meter)
                end.record();torch.cuda.synchronize();wall_ms=(time.perf_counter_ns()-wall)/1e6
                work={k:counter.counts[k]-before[k] for k in before};fwork={k:meter.counts[k]-fbefore[k] for k in fbefore}
                expected=dict(cheap_features=2,confidence_features=2 if request['kind']=='rich' else 0,cue_features=2 if request['kind']=='rich' else 0)
                if work!=dict(inputs=1,generator_levels=11,decoder=3,encoder=0) or fwork!=expected:raise ValueError('Actual instrumentation work differs')
                hashes=check_parity(result,cache[str(request['index'])],dict(depth=11,method='assigned_sparse'))
                reserved=torch.cuda.max_memory_reserved()
                if reserved>min(lock['gpu_reserved_bytes'],receipt['environment']['physical_gpu_bytes']):raise RuntimeError('GPU memory cap')
                stream.write(json.dumps(dict(request,wall_ms=wall_ms,cuda_stream_span_ms=begin.elapsed_time(end),work=work,feature_work=fwork,
                    peak_allocated_bytes=torch.cuda.max_memory_allocated(),peak_reserved_bytes=reserved,parity=True,hashes=hashes,features=result['features'],component_ms=result['component_ms']),allow_nan=False)+'\n');stream.flush()
                receipt['completed_requests']+=1
                if number%16==0 or number+1==len(plan):
                    if size()>lock['artifact_bytes']:raise RuntimeError('Pilot artifact cap')
                    print(f'Confidence pilot session {session}: {number+1}/{len(plan)}; work/output parity passed',flush=True)
        receipt['state_after']=fingerprint()
        if receipt['state_before']!=receipt['state_after'] or counter.counts!=lock['per_session_forward_caps'] or meter.counts!=lock['per_session_feature_caps'] or receipt['prefix_calls']!=90:
            raise ValueError('Pilot completion/state/work mismatch')
        receipt.update(status='complete',counts=dict(counter.counts),forward_calls=dict(counter.calls),feature_counts=meter.counts,
            wall_seconds=time.monotonic()-started,cpu_seconds=cpu(),max_rss_bytes=rss(),finished_utc=now())
        if rss()>lock['worker_rss_bytes']:raise RuntimeError('Worker RSS cap')
        write_new(OUT/f'{session}-execution.json',receipt)
    except BaseException as error:
        write_new(OUT/f'{session}-failure.json',dict(receipt,error=repr(error),request=request,counts=dict(counter.counts) if counter else {},feature_counts=meter.counts,automatic_retry=False))
        if result is not None:write_new(OUT/f'{session}-failure-output.json',dict(prefix_ids=result['prefix_ids'],codes=result['codes'][0].cpu().tolist(),observations=result['observations'],features=result['features']))
        raise
    finally:
        if counter:counter.close()
        stop_alarm()

def run(commit):
    started=time.monotonic();lock,source=load();verify_campaign(ROOT,lock['campaign_reservation'])
    if git('rev-parse','HEAD')!=commit or git('branch','--show-current')!='main' or git('status','--porcelain') or git('ls-remote','origin','refs/heads/main').split()[0]!=commit:
        raise ValueError('Need clean main at pushed pilot lock')
    OUT.mkdir(parents=True,exist_ok=False);write_new(OUT/'started.json',dict(source_commit=commit,started_utc=now(),campaign_goal='campaign-20261029-objective.md'))
    alarm(lock['wall_seconds']);meter=None
    try:
        with zipfile.ZipFile(OUT/'execution-sources.zip','x',compression=zipfile.ZIP_DEFLATED) as z:
            for p in source['source_sha256']:z.writestr(p,(ROOT/p).read_bytes())
            z.writestr('source-lock.json',json.dumps(source,indent=2))
        with (OUT/'synthetic-tests.log').open('x',encoding='utf-8',newline='\n') as log:
            test=subprocess.run([sys.executable,'-m','pytest','tests/test_confidence_pilot.py','-q','-s','-p','no:cacheprovider',
                '--junitxml=results/quality_tolerant/campaign_20261029/signal_pilot/synthetic-tests.xml'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=lock['test_wall_seconds'])
        if test.returncode:raise RuntimeError('Pilot synthetic validation failed before released data/model work')
        import re
        text=(OUT/'synthetic-tests.log').read_text(encoding='utf-8');match=re.search(r'SYNTHETIC_PILOT_REQUESTS (\d+)',text)
        if not match or int(match[1])!=5:raise ValueError('Missing exact synthetic model-request ledger')
        synthetic_requests=int(match[1]);print('Pilot synthetic validation passed; sixteen consumed fit inputs released',flush=True)
        config=read(ROOT/'configs/phase4_wmt_sources.json');assets={p:v for p,v in config['files'].items() if p!='data/wmt14/reference_translations.pickle'}
        for p,v in assets.items():
            if sha(ROOT/p)!=v['sha256'] or (ROOT/p).stat().st_size!=v['size']:raise ValueError('Pinned asset differs: '+p)
        write_new(OUT/'asset-preflight.json',dict(asset_sha256={p:v['sha256'] for p,v in assets.items()},reference_bodies=0))
        split=read(BASE/'controller-split.json');entries=lock['entries']
        if entries!=sorted(split['parts']['fit'],key=lambda e:e['index'])[:16]:raise ValueError('Pilot allocation differs')
        write_new(OUT/'access-release.json',dict(entries=entries,source_commit=commit,old_trajectory_bodies=16,worker_source_materializations=32,reference_bodies=0,
            old_test87_released=False,E3_E4_unallocated_released=False,new_inputs=0))
        meter=Meter(dict(trajectory_bodies=16));all_entries=[e for es in split['parts'].values() for e in es];rows=[]
        for origins,path in [(('exploration','development'),'results/phase4/wmt14/trajectories.jsonl'),(('E2_audit',),'results/evidence_gaps/e2/trajectories.jsonl')]:
            rows.extend(selected_rows(ROOT/path,[e for e in entries if e['origin'] in origins],[e for e in all_entries if e['origin'] in origins],meter))
        if meter.counts['trajectory_bodies']!=16:raise ValueError('Wrong pilot cache count')
        write_new(OUT/'parity-hashes.json',{str(r['index']):cache_row(r) for r in rows})
        write_new(OUT/'timing-schedule.json',{str(s):schedule(entries,s) for s in (0,1)})
        model_start=time.monotonic()
        for s in (0,1):
            remaining=min(lock['model_wall_seconds']-(time.monotonic()-model_start),lock['wall_seconds']-(time.monotonic()-started))
            if remaining<=0:raise RuntimeError('Pilot model/time allocation')
            subprocess.run([sys.executable,str(Path(__file__).resolve()),'worker','--session',str(s),'--seconds',str(remaining)],cwd=ROOT,check=True,timeout=remaining)
        model_seconds=time.monotonic()-model_start
        processes=[read(OUT/f'{s}-execution.json') for s in (0,1)]
        if len({p['pid'] for p in processes})!=2:raise ValueError('Need separate model processes')
        records=[json.loads(line) for s in (0,1) for line in (OUT/f'{s}-requests.jsonl').read_text(encoding='utf-8').splitlines()]
        report=analyze(records);write_new(OUT/'analysis.json',report)
        counts={k:sum(p['counts'][k] for p in processes) for k in lock['total_forward_caps']}
        if counts!=lock['total_forward_caps']:raise ValueError('Pilot global work differs')
        hashes_ok(source['protected_sha256']);hashes_ok(source['source_sha256'])
        usage=usage_zero();usage.update(model_requests=counts['inputs']+synthetic_requests,model_orchestration_seconds=model_seconds,
            cpu_seconds=cpu()+lock['reporting_cpu_charge_seconds'],artifact_bytes=lock['artifact_bytes'])
        if (time.monotonic()-started>lock['wall_seconds'] or cpu()>lock['execution_cpu_cap_seconds'] or rss()>lock['parent_rss_bytes'] or size()>lock['artifact_bytes']):raise RuntimeError('Pilot resource cap')
        verify_campaign(ROOT,usage)
        write_new(OUT/'decision.json',dict(status=report['decision'],next_branch='signal_discrimination' if report['decision']=='pilot_passed' else 'prospectively_bounded_instrumentation_alternative_or_closeout',
            predictive_usefulness_established=False,quality_confirmation=False,Q0_passed=False,reserved_outputs_released=False))
        write_new(OUT/'execution.json',dict(status='complete',source_commit=commit,counts=counts,feature_counts={k:sum(p['feature_counts'][k] for p in processes) for k in lock['per_session_feature_caps']},
            synthetic_model_requests=synthetic_requests,synthetic_real_checkpoint_loads=0,source_materializations=32,old_trajectory_bodies=16,reference_bodies=0,
            new_fits=0,new_controller_families=0,target_encodings=0,bootstrap_draws=0,model_orchestration_wall_seconds=model_seconds,total_wall_seconds=time.monotonic()-started,
            cpu_seconds_before_reporting_charge=cpu(),reporting_cpu_charge_seconds=lock['reporting_cpu_charge_seconds'],max_parent_rss_bytes=rss(),artifact_bytes_before_reporting=size(),
            model_states_unchanged=True,all_output_and_work_parity=True,paid_compute_dollars=0,automatic_retries=0,process_ids=[p['pid'] for p in processes],
            campaign_usage=usage,finished_utc=now(),artifact_sha256={p.relative_to(OUT).as_posix():sha(p) for p in OUT.rglob('*') if p.is_file()}))
        print(json.dumps(record_phase(ROOT,'01-signal-pilot','signal_pilot/execution.json')),flush=True)
        print('CONFIDENCE PILOT COMPLETE: '+report['decision'],flush=True)
    except BaseException as error:
        # Charge the full frozen reservation if exact terminal work is not yet reconstructible.
        failure=OUT/'failure.json'
        if not failure.exists():write_new(failure,dict(error=repr(error),partial_parent_counts=meter.counts if meter else {},wall_seconds=time.monotonic()-started,
            campaign_usage=lock['campaign_reservation'],budget_charge_interpretation='conservative entire reservation after failed phase; not a claim all reserved work executed',automatic_retry=False))
        account=CAMPAIGN/'accounting/phase-01-signal-pilot.json'
        if not account.exists():record_phase(ROOT,'01-signal-pilot','signal_pilot/failure.json')
        raise
    finally:stop_alarm()

def verify():
    lock,source=load();e=read(OUT/'execution.json');hashes_ok({('results/quality_tolerant/campaign_20261029/signal_pilot/'+p):h for p,h in e['artifact_sha256'].items()})
    if e['status']!='complete' or e['counts']!=lock['total_forward_caps'] or e['synthetic_model_requests']!=5 or e['new_fits'] or e['reference_bodies']:raise ValueError('Invalid pilot receipt')
    plans=read(OUT/'timing-schedule.json');cache=read(OUT/'parity-hashes.json')
    for s in (0,1):
        rows=[json.loads(line) for line in (OUT/f'{s}-requests.jsonl').read_text(encoding='utf-8').splitlines()];p=read(OUT/f'{s}-execution.json')
        if len(rows)!=74 or p['counts']!=lock['per_session_forward_caps'] or p['state_before']!=p['state_after'] or p['prefix_calls']!=90:raise ValueError('Pilot session incomplete')
        for expected,r in zip(plans[str(s)],rows):
            if any(r[k]!=v for k,v in expected.items()) or not r['parity']:raise ValueError('Pilot request differs')
            c=cache[str(r['index'])];h=r['hashes']
            if h['prefix']!=c['prefix'] or h['codes']!=c['codes']['11'] or any(h['outputs'][str(d)]!=c['outputs'][str(d)] for d in (8,10,11)):raise ValueError('Pilot hash mismatch')
    print(json.dumps(dict(verified=True,protected_files=len(source['protected_sha256']),model_requests=e['counts']['inputs'],campaign=verify_campaign(ROOT),new_inference_or_analysis=0)))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=('run','worker','verify'));p.add_argument('--commit');p.add_argument('--session',type=int);p.add_argument('--seconds',type=float);a=p.parse_args()
    if a.mode=='run':run(a.commit)
    elif a.mode=='worker':worker(a.session,a.seconds)
    else:verify()
