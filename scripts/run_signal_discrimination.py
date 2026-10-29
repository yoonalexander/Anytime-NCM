"""Once-only collection and four fixed development probes under campaign ceilings."""
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
from anytime_ncm.quality_controller import Meter,sentence_targets
from anytime_ncm.controller_study import selected_rows,cache_row
from anytime_ncm.latency_diagnostic import check_parity,value_hash
from anytime_ncm.signal_discrimination import analyze
from anytime_ncm.quality_campaign import verify_campaign,record_phase,usage_zero,campaign_root
from anytime_ncm.wmt_data import StringRows,identity
BASE=ROOT/'docs/studies/quality-tolerant';CAMPAIGN=campaign_root(ROOT);OUT=CAMPAIGN/'signal_discrimination'

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
    lock=read(BASE/'signal-discrimination-lock.json');sources=read(BASE/'signal-discrimination-source-lock.json')
    hashes_ok(sources['source_sha256']);hashes_ok(sources['protected_sha256'])
    if git('-C','third_party/ncm','rev-parse','HEAD')!=sources['upstream_commit'] or git('-C','third_party/ncm','status','--porcelain'):raise ValueError('Upstream changed')
    return lock,sources

def alarm(seconds):
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('Discrimination wall allocation exhausted')));signal.setitimer(signal.ITIMER_REAL,seconds)
def stop_alarm():signal.setitimer(signal.ITIMER_REAL,0)
def size():return sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file())

def worker(seconds):
    started=time.monotonic();lock,_=load();alarm(seconds)
    import torch,transformers
    from anytime_ncm.wmt_model import WmtModel
    from anytime_ncm.causal_light import instrumented_request,FEATURE_NAMES
    from anytime_ncm.forced_wmt import ForwardCounter
    from anytime_ncm.target_encoding import model_fingerprint
    entries=read(OUT/'access-release.json')['entries'];plan=read(OUT/'collection-plan.json');cache=read(OUT/'parity-hashes.json')
    receipt=dict(pid=os.getpid(),started_utc=now(),completed_requests=0,prefix_calls=0,source_materializations=361)
    write_new(OUT/'worker-started.json',receipt);counter=None;result=None;request=None;meter=Meter(lock['feature_caps'])
    try:
        if (sys.version_info[:3]!=(3,12,3) or torch.__version__!='2.10.0+cu128' or torch.version.cuda!='12.8' or transformers.__version__!='4.57.6'
            or not torch.cuda.is_available() or torch.cuda.get_device_name()!='NVIDIA GeForce RTX 5060'):raise RuntimeError('Material environment drift')
        if list(FEATURE_NAMES['selected_logit'])!=lock['feature_names']:raise ValueError('Feature schema differs')
        torch.set_num_threads(4);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=True
        sources=StringRows((ROOT/'data/wmt14/sources.pickle').read_bytes()).select({e['index'] for e in entries})
        loading=time.monotonic();model=WmtModel(ROOT);receipt['model_load_seconds']=time.monotonic()-loading
        receipt['environment']=dict(python=sys.version,torch=torch.__version__,cuda=torch.version.cuda,transformers=transformers.__version__,gpu=torch.cuda.get_device_name(),
            precision='float32/eval',cpu_threads=4,tf32_matmul=False,tf32_cudnn=True,physical_gpu_bytes=torch.cuda.get_device_properties(0).total_memory)
        receipt['nvidia_smi']=subprocess.check_output(['/usr/lib/wsl/lib/nvidia-smi','--query-gpu=driver_version,name,memory.total','--format=csv,noheader'],text=True,timeout=15).strip()
        original=model.official['prefix']
        def prefix(text):
            if receipt['prefix_calls']>=727:raise RuntimeError('Prefix cap')
            receipt['prefix_calls']+=1;return original(text)
        model.official['prefix']=prefix
        for e in entries:
            if identity(prefix(sources[e['index']]))!=e['identity']:raise ValueError('Effective-prefix identity mismatch')
        fingerprint=lambda:dict(generator=model_fingerprint(model.net),tokenizer=model_fingerprint(model.tokenizer.vqvae))
        receipt['state_before']=fingerprint();counter=ForwardCounter(model,lock['forward_caps'])
        with (OUT/'request-starts.jsonl').open('x',encoding='utf-8',newline='\n') as ledger,(OUT/'requests.jsonl').open('x',encoding='utf-8',newline='\n') as stream:
            for number,request in enumerate(plan):
                if time.monotonic()-started>seconds or rss()>lock['worker_rss_bytes']:raise RuntimeError('Worker wall/RSS cap')
                before=dict(counter.counts);fbefore=dict(meter.counts);counter.take('inputs')
                ledger.write(json.dumps(dict(request,work_before=before,feature_work_before=fbefore))+'\n');ledger.flush()
                torch.cuda.synchronize();torch.cuda.reset_peak_memory_stats();torch.manual_seed(20261023)
                result=None;wall=time.perf_counter_ns();result=instrumented_request(model,sources[request['index']],'selected_logit',meter)
                torch.cuda.synchronize();wall_ms=(time.perf_counter_ns()-wall)/1e6
                work={k:counter.counts[k]-before[k] for k in before};fwork={k:meter.counts[k]-fbefore[k] for k in fbefore}
                if work!=dict(inputs=1,generator_levels=11,decoder=3,encoder=0) or fwork!=dict(cheap_features=2,selected_logit_features=2,cue_features=2):raise ValueError('Actual collection work differs')
                hashes=check_parity(result,cache[str(request['index'])],dict(depth=11,method='assigned_sparse'))
                code_hashes={str(v['level']):value_hash(v['codes']) for v in result['prefix_codes']}
                if any(code_hashes[str(d)]!=cache[str(request['index'])]['codes'][str(d)] for d in (8,10,11)):raise ValueError('Current generated prefix mismatch')
                reserved=torch.cuda.max_memory_reserved()
                if reserved>min(lock['gpu_reserved_bytes'],receipt['environment']['physical_gpu_bytes']):raise RuntimeError('GPU memory cap')
                stream.write(json.dumps(dict(request,wall_ms=wall_ms,work=work,feature_work=fwork,peak_allocated_bytes=torch.cuda.max_memory_allocated(),
                    peak_reserved_bytes=reserved,parity=True,hashes=hashes,features=result['features'],component_ms=result['component_ms'],code_hashes=code_hashes),allow_nan=False)+'\n');stream.flush()
                receipt['completed_requests']+=1
                if number%64==0 or number+1==len(plan):
                    if size()>lock['artifact_bytes']:raise RuntimeError('Artifact cap')
                    print(f'Signal collection: {number+1}/{len(plan)}; current/final parity passed',flush=True)
        receipt['state_after']=fingerprint()
        if receipt['state_before']!=receipt['state_after'] or counter.counts!=lock['forward_caps'] or meter.counts!=lock['feature_caps'] or receipt['prefix_calls']!=727:raise ValueError('Completion/state/work mismatch')
        receipt.update(status='complete',counts=dict(counter.counts),forward_calls=dict(counter.calls),feature_counts=meter.counts,wall_seconds=time.monotonic()-started,cpu_seconds=cpu(),max_rss_bytes=rss(),finished_utc=now())
        if rss()>lock['worker_rss_bytes']:raise RuntimeError('Worker RSS cap')
        write_new(OUT/'worker-execution.json',receipt)
    except BaseException as error:
        write_new(OUT/'worker-failure.json',dict(receipt,error=repr(error),request=request,counts=dict(counter.counts) if counter else {},feature_counts=meter.counts,automatic_retry=False));raise
    finally:
        if counter:counter.close()
        stop_alarm()

def run(commit):
    started=time.monotonic();lock,source=load();verify_campaign(ROOT,lock['campaign_reservation'])
    if git('rev-parse','HEAD')!=commit or git('branch','--show-current')!='main' or git('status','--porcelain') or git('ls-remote','origin','refs/heads/main').split()[0]!=commit:raise ValueError('Need clean main at pushed study lock')
    OUT.mkdir(parents=True,exist_ok=False);write_new(OUT/'started.json',dict(source_commit=commit,started_utc=now()))
    alarm(lock['wall_seconds']);meter=None
    try:
        with zipfile.ZipFile(OUT/'execution-sources.zip','x',compression=zipfile.ZIP_DEFLATED) as z:
            for p in source['source_sha256']:z.writestr(p,(ROOT/p).read_bytes())
            z.writestr('source-lock.json',json.dumps(source,indent=2))
        with (OUT/'synthetic-tests.log').open('x',encoding='utf-8',newline='\n') as log:
            test=subprocess.run([sys.executable,'-m','pytest','tests/test_signal_discrimination.py','-q','-s','-p','no:cacheprovider','--junitxml=results/quality_tolerant/campaign_20261029/signal_discrimination/synthetic-tests.xml'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=lock['test_wall_seconds'])
        if test.returncode:raise RuntimeError('Synthetic validation failed before released outcome/model access')
        if 'SYNTHETIC_PROBE_FITS 3' not in (OUT/'synthetic-tests.log').read_text(encoding='utf-8'):raise ValueError('Missing synthetic fit accounting')
        print('Synthetic validation passed; consumed fit/calibration access released',flush=True)
        config=read(ROOT/'configs/phase4_wmt_sources.json')
        for p,v in config['files'].items():
            if sha(ROOT/p)!=v['sha256'] or (ROOT/p).stat().st_size!=v['size']:raise ValueError('Pinned asset differs: '+p)
        write_new(OUT/'asset-preflight.json',dict(asset_sha256={p:v['sha256'] for p,v in config['files'].items()}))
        split=read(BASE/'controller-split.json');entries=sorted(split['parts']['fit']+split['parts']['calibration'],key=lambda e:e['index'])
        if len(entries)!=361 or len(split['parts']['fit'])!=260 or len(split['parts']['calibration'])!=101:raise ValueError('Allocation differs')
        write_new(OUT/'access-release.json',dict(entries=entries,roles=['fit','calibration'],source_commit=commit,old_test87_released=False,E3_E4_unallocated_released=False,previously_consumed_development=True))
        with (OUT/'access-and-fit-ledger.jsonl').open('x',encoding='utf-8',newline='\n') as stream:
            meter=Meter(lock['analysis_caps'],stream);all_entries=[e for es in split['parts'].values() for e in es];rows=[]
            for origins,path in [(('exploration','development'),'results/phase4/wmt14/trajectories.jsonl'),(('E2_audit',),'results/evidence_gaps/e2/trajectories.jsonl')]:
                rows.extend(selected_rows(ROOT/path,[e for e in entries if e['origin'] in origins],[e for e in all_entries if e['origin'] in origins],meter))
            rows.sort(key=lambda r:r['index'])
            meter.take('reference_materializations',361);refs=StringRows((ROOT/'data/wmt14/reference_translations.pickle').read_bytes()).select({e['index'] for e in entries})
            targets={str(r['index']):{str(d):v for d,v in sentence_targets(r,refs[r['index']],meter).items()} for r in rows}
            write_new(OUT/'proxy-labels.json',targets);write_new(OUT/'parity-hashes.json',{str(r['index']):cache_row(r) for r in rows})
            plan=[]
            for e in sorted(split['parts']['fit'],key=lambda e:e['index'])[:5]:plan.append(dict(request_id=len(plan),index=e['index'],identity=e['identity'],warmup=True))
            for e in entries:plan.append(dict(request_id=len(plan),index=e['index'],identity=e['identity'],warmup=False))
            write_new(OUT/'collection-plan.json',plan)
            model_start=time.monotonic();remaining=min(lock['model_wall_seconds'],lock['wall_seconds']-(model_start-started))
            subprocess.run([sys.executable,str(Path(__file__).resolve()),'worker','--seconds',str(remaining)],cwd=ROOT,check=True,timeout=remaining);model_seconds=time.monotonic()-model_start
            records=[json.loads(line) for line in (OUT/'requests.jsonl').read_text(encoding='utf-8').splitlines()]
            fit_ids=sorted(e['index'] for e in split['parts']['fit']);cal_ids=sorted(e['index'] for e in split['parts']['calibration']);components={e['index']:e['component'] for e in entries}
            analysis=analyze(records,targets,fit_ids,cal_ids,components,meter)
            write_new(OUT/'analysis.json',analysis);write_new(OUT/'models.json',analysis['models'])
        process=read(OUT/'worker-execution.json');hashes_ok(source['protected_sha256']);hashes_ok(source['source_sha256'])
        usage=usage_zero();usage.update(model_requests=process['counts']['inputs'],model_orchestration_seconds=model_seconds,cpu_seconds=cpu()+lock['reporting_cpu_charge_seconds'],real_fits=meter.counts['fits'],controller_families=1 if meter.counts['fits'] else 0,artifact_bytes=lock['artifact_bytes'])
        if time.monotonic()-started>lock['wall_seconds'] or cpu()>lock['execution_cpu_cap_seconds'] or rss()>lock['parent_rss_bytes'] or size()>lock['artifact_bytes']:raise RuntimeError('Resource cap')
        verify_campaign(ROOT,usage)
        write_new(OUT/'decision.json',dict(analysis['decision'],Q0_passed=False,independent_confirmation=False,reserved_outputs_released=False,whole_controller_speedup_established=False,quality_guarantee=False))
        write_new(OUT/'execution.json',dict(status='complete',source_commit=commit,counts=process['counts'],feature_counts=process['feature_counts'],analysis_counts=meter.counts,
            synthetic_model_requests=0,synthetic_real_checkpoint_loads=0,synthetic_probe_fits=3,source_materializations=361,old_trajectory_bodies=361,reference_bodies=361,new_fits=meter.counts['fits'],new_controller_families=usage['controller_families'],target_encodings=0,bootstrap_draws=0,
            model_orchestration_wall_seconds=model_seconds,total_wall_seconds=time.monotonic()-started,cpu_seconds_before_reporting_charge=cpu(),reporting_cpu_charge_seconds=lock['reporting_cpu_charge_seconds'],max_parent_rss_bytes=rss(),artifact_bytes_before_reporting=size(),
            model_states_unchanged=True,all_output_and_work_parity=True,paid_compute_dollars=0,automatic_retries=0,campaign_usage=usage,finished_utc=now(),artifact_sha256={p.relative_to(OUT).as_posix():sha(p) for p in OUT.rglob('*') if p.is_file()}))
        print(json.dumps(record_phase(ROOT,'03-signal-discrimination','signal_discrimination/execution.json')),flush=True)
        print('SIGNAL DISCRIMINATION COMPLETE: '+analysis['decision']['status'],flush=True)
    except BaseException as error:
        failure=OUT/'failure.json'
        if not failure.exists():write_new(failure,dict(error=repr(error),partial_parent_counts=meter.counts if meter else {},wall_seconds=time.monotonic()-started,campaign_usage=lock['campaign_reservation'],budget_charge_interpretation='conservative entire reservation after failed phase; not a claim all reserved work executed',automatic_retry=False))
        if not (CAMPAIGN/'accounting/phase-03-signal-discrimination.json').exists():record_phase(ROOT,'03-signal-discrimination','signal_discrimination/failure.json')
        raise
    finally:stop_alarm()

def verify():
    lock,source=load();e=read(OUT/'execution.json');hashes_ok({('results/quality_tolerant/campaign_20261029/signal_discrimination/'+p):h for p,h in e['artifact_sha256'].items()})
    process=read(OUT/'worker-execution.json');records=[json.loads(line) for line in (OUT/'requests.jsonl').read_text(encoding='utf-8').splitlines()];plan=read(OUT/'collection-plan.json');cache=read(OUT/'parity-hashes.json')
    if len(records)!=366 or len(plan)!=366 or process['counts']!=lock['forward_caps'] or process['state_before']!=process['state_after'] or process['prefix_calls']!=727 or process['feature_counts']!=lock['feature_caps']:raise ValueError('Collection incomplete')
    if e['status']!='complete' or e['counts']!=lock['forward_caps'] or e['new_fits']>4 or e['target_encodings'] or e['reference_bodies']!=361:raise ValueError('Invalid study receipt')
    for expected,r in zip(plan,records):
        if any(r[k]!=v for k,v in expected.items()) or not r['parity'] or r['work']!=dict(inputs=1,generator_levels=11,decoder=3,encoder=0):raise ValueError('Collection request differs')
        c=cache[str(r['index'])];h=r['hashes']
        if any(r['code_hashes'][str(d)]!=c['codes'][str(d)] for d in (8,10,11)) or h['prefix']!=c['prefix'] or h['codes']!=c['codes']['11'] or any(h['outputs'][str(d)]!=c['outputs'][str(d)] for d in (8,10,11)):raise ValueError('Collection hash mismatch')
        if [f['level'] for f in r['features']]!=[8,10] or any(len(f['values'])!=27 for f in r['features']):raise ValueError('Feature shape/order mismatch')
    analysis=read(OUT/'analysis.json')
    from anytime_ncm.signal_discrimination import decide
    if decide(analysis['levels'])!=analysis['decision'] or read(OUT/'models.json')!=analysis['models']:raise ValueError('Analysis/decision mismatch')
    print(json.dumps(dict(verified=True,protected_files=len(source['protected_sha256']),model_requests=e['counts']['inputs'],campaign=verify_campaign(ROOT),new_inference_or_fitting=0)))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=('run','worker','verify'));p.add_argument('--commit');p.add_argument('--seconds',type=float);a=p.parse_args()
    if a.mode=='run':run(a.commit)
    elif a.mode=='worker':worker(a.seconds)
    else:verify()
