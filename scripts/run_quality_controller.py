"""Two-stage prospective controller development and once-only online evaluation."""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='4'
for k in ('HF_HUB_OFFLINE','TRANSFORMERS_OFFLINE'):os.environ[k]='1'
os.environ['TOKENIZERS_PARALLELISM']='false';os.environ['PYTHONDONTWRITEBYTECODE']='1'
import argparse
from datetime import datetime,timezone
import hashlib,json,resource,signal,subprocess,sys,time,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from anytime_ncm.evidence_preflight import sha,write_new
from anytime_ncm.quality_controller import Controller,Meter,fit_models,candidates,replay,point_losses,point_pass
from anytime_ncm.controller_study import METHODS,selected_rows,cache_row,schedule,work,sum_work,timing_analysis
from anytime_ncm.latency_diagnostic import check_parity
from anytime_ncm.wmt_data import StringRows,identity
from anytime_ncm.wmt_metrics import scores
BASE=ROOT/'docs/studies/quality-tolerant';OUT=ROOT/'results/quality_tolerant/controller';DEV=OUT/'development';EVAL=OUT/'evaluation'

def read(p):return json.loads(p.read_text(encoding='utf-8'))
def git(*a):return subprocess.check_output(['git.exe',*a],cwd=ROOT,text=True,timeout=60).strip()
def now():return datetime.now(timezone.utc).isoformat()
def rss():return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
def size():return sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file())
def hashes_ok(values,base=ROOT):
    for p,h in values.items():
        if sha(base/p)!=h:raise ValueError('Frozen bytes changed: '+p)
def load_lock():
    lock=read(BASE/'controller-lock.json');sources=read(BASE/'controller-source-lock.json');split=read(BASE/'controller-split.json')
    hashes_ok(sources['source_sha256']);hashes_ok(sources['protected_sha256'])
    if git('-C','third_party/ncm','rev-parse','HEAD')!=sources['upstream_commit'] or git('-C','third_party/ncm','status','--porcelain'):raise ValueError('Upstream differs')
    return lock,sources,split

def clean_main(commit):
    if git('rev-parse','HEAD')!=commit or git('branch','--show-current')!='main' or git('status','--porcelain') or git('ls-remote','origin','refs/heads/main').split()[0]!=commit:
        raise ValueError('Need clean main at verified pushed commit')
def alarm(seconds):
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('Controller wall allocation exhausted')))
    signal.setitimer(signal.ITIMER_REAL,seconds)
def stop_alarm():signal.setitimer(signal.ITIMER_REAL,0)
def artifacts(path):return {str(p.relative_to(path)):sha(p) for p in path.rglob('*') if p.is_file()}

def check_resources(lock,started,wall):
    if time.monotonic()-started>wall or rss()>lock['parent_rss_bytes'] or size()>lock['artifact_bytes']:raise RuntimeError('Controller resource cap')
def read_data(entries,split,meter,reference=True):
    indices={e['index'] for e in entries}
    meter.take('source_materializations',len(indices));sources=StringRows((ROOT/'data/wmt14/sources.pickle').read_bytes()).select(indices)
    refs={}
    if reference:
        meter.take('reference_materializations',len(indices));refs=StringRows((ROOT/'data/wmt14/reference_translations.pickle').read_bytes()).select(indices)
    all_entries=[e for es in split['parts'].values() for e in es];rows=[]
    for origins,path in [(('exploration','development'),'results/phase4/wmt14/trajectories.jsonl'),(('E2_audit',),'results/evidence_gaps/e2/trajectories.jsonl')]:
        allowed=[e for e in all_entries if e['origin'] in origins];active=[e for e in entries if e['origin'] in origins]
        rows.extend(selected_rows(ROOT/path,active,allowed,meter))
    rows.sort(key=lambda r:r['index'])
    if [r['index'] for r in rows]!=sorted(indices):raise ValueError('Incomplete selected rows')
    return rows,sources,refs

def coverage(entries,refs):
    from anytime_ncm.wmt_policy import cues
    return dict(inputs=len(entries),components=len({e['component'] for e in entries}),numeric_covered=sum(bool(cues(refs[e['index']])[0]) for e in entries))
def corpus_score(hyps,refs,meter):meter.take('corpus_scores');return scores(hyps,refs)

def verify_dev():
    receipt=read(DEV/'execution.json');hashes_ok(receipt['artifact_sha256'],DEV)
    if receipt['status']!='complete' or sha(DEV/'policy.json')!=receipt['selected_policy_sha256'] or receipt['counts']['fits']!=8:raise ValueError('Invalid development lock')
    return receipt

def develop(commit):
    started=time.monotonic();lock,sources,split=load_lock();clean_main(commit)
    DEV.mkdir(parents=True,exist_ok=False);write_new(DEV/'started.json',dict(protocol_commit=commit,started_utc=now(),test_outcomes_released=False))
    meter=None;alarm(lock['development_wall_seconds'])
    try:
        with zipfile.ZipFile(DEV/'execution-sources.zip','x',compression=zipfile.ZIP_DEFLATED) as z:
            for p in sources['source_sha256']:z.writestr(p,(ROOT/p).read_bytes())
            z.writestr('source-lock.json',json.dumps(sources,indent=2))
        with (DEV/'synthetic-tests.log').open('x',encoding='utf-8',newline='\n') as f:
            test=subprocess.run([sys.executable,'-m','pytest','tests/test_quality_controller.py','-q','-s','-p','no:cacheprovider','--basetemp=results/quality_tolerant/controller/development/pytest-tmp',
                '--junitxml=results/quality_tolerant/controller/development/synthetic-tests.xml'],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,timeout=lock['synthetic_test_wall_seconds'])
        if test.returncode:raise RuntimeError('Synthetic validation failed before outcome access')
        print('Controller synthetic validation passed; fit/calibration only released',flush=True)
        config=read(ROOT/'configs/phase4_wmt_sources.json')
        for p,v in config['files'].items():
            if sha(ROOT/p)!=v['sha256'] or (ROOT/p).stat().st_size!=v['size']:raise ValueError('Pinned asset differs: '+p)
        write_new(DEV/'asset-preflight.json',dict(asset_sha256={p:v['sha256'] for p,v in config['files'].items()},checkpoint_loads=0))
        fit=split['parts']['fit'];cal=split['parts']['calibration'];entries=sorted(fit+cal,key=lambda e:e['index'])
        write_new(DEV/'access-release.json',dict(entries=entries,roles=['fit','calibration'],test_outcome_bodies=False,E3_E4_outputs=False,source_commit=commit))
        with (DEV/'ledger.jsonl').open('x',encoding='utf-8',newline='\n') as stream:
            meter=Meter(lock['development_caps'],stream);rows,source,reference=read_data(entries,split,meter)
            fit_ids={e['index'] for e in fit};cal_ids={e['index'] for e in cal};train_rows=[r for r in rows if r['index'] in fit_ids];cal_rows=[r for r in rows if r['index'] in cal_ids]
            counts={p:coverage(split['parts'][p],reference) for p in ('fit','calibration')}
            if counts['fit']['numeric_covered']<12 or counts['calibration']['numeric_covered']<8:raise ValueError('Insufficient fit/calibration cue coverage')
            write_new(DEV/'coverage.json',counts)
            models=fit_models(train_rows,source,reference,meter);write_new(DEV/'models.json',models)
            refs=[reference[r['index']] for r in cal_rows];full=corpus_score([r['levels'][-1]['text'] for r in cal_rows],refs,meter)
            prior=read(ROOT/'results/quality_tolerant/latency_diagnostic/analysis.json')['methods']
            h=read(ROOT/'results/quality_tolerant/q1/cost-calibration.json')['observation_step_proxy_ms']
            reports=[];specs=candidates(models)
            for spec in specs:
                ctrl=Controller(spec,meter);pred=[]
                for r in cal_rows:
                    meter.take('replay_inputs');pred.append(replay(ctrl,source[r['index']],r))
                metric=full if spec['kind']=='full' else corpus_score([r['levels'][d-1]['text'] for r,(d,v) in zip(cal_rows,pred)],refs,meter)
                estimated=sum(prior['fixed:'+str(d)]['mean_ms']+max(0,len(v)-1)*h for d,v in pred)/len(pred)
                reports.append(dict(name=spec['name'],metrics=metric,losses=point_losses(metric,full),point_pass=point_pass(metric,full),
                    estimated_mean_ms=estimated,early_inputs=sum(d<11 for d,v in pred),exits={str(d):sum(p[0]==d for p in pred) for d in (8,10,11)}))
            feasible=[r for r in reports if r['point_pass']]
            selected=min(feasible,key=lambda r:(r['estimated_mean_ms'],r['name']))
            fixed=[]
            for d in range(1,12):
                metric=full if d==11 else corpus_score([r['levels'][d-1]['text'] for r in cal_rows],refs,meter)
                fixed.append(dict(method='fixed:'+str(d),metrics=metric,losses=point_losses(metric,full),point_pass=point_pass(metric,full),profile_mean_ms=prior['fixed:'+str(d)]['mean_ms']))
            comparator=min((r for r in fixed if r['point_pass']),key=lambda r:(r['profile_mean_ms'],r['method']))['method']
            policy=next(s for s in specs if s['name']==selected['name'])
            write_new(DEV/'candidate-results.json',dict(candidates=reports,fixed=fixed,selected=selected['name'],locked_fixed_comparator=comparator,selection_uses_test=False,
                observation_step_proxy_ms=h,controller_cost_in_proxy=0,proxy_interpretation='selection estimate only; all true online work must be timed'))
            write_new(DEV/'policy.json',dict(policy=policy,locked_fixed_comparator=comparator,protocol_commit=commit,features=list(__import__('anytime_ncm.quality_controller',fromlist=['FEATURES']).FEATURES),
                fit_inputs=260,calibration_inputs=101,test_inputs_seen_for_selection=0,Q0_passed=False,independent_confirmation=False))
        hashes_ok(sources['protected_sha256']);check_resources(lock,started,lock['development_wall_seconds'])
        write_new(DEV/'execution.json',dict(status='complete',protocol_commit=commit,counts=meter.counts,selected_policy_sha256=sha(DEV/'policy.json'),selected=selected['name'],
            wall_seconds=time.monotonic()-started,max_rss_bytes=rss(),model_loads=0,paid_compute_dollars=0,finished_utc=now(),artifact_sha256=artifacts(DEV)))
        print('DEVELOPMENT COMPLETE; selected '+selected['name']+'; PUSH POLICY BEFORE EVALUATION',flush=True)
    except BaseException as error:
        write_new(DEV/'failure.json',dict(error=repr(error),counts=meter.counts if meter else {},wall_seconds=time.monotonic()-started,automatic_retry=False));raise
    finally:stop_alarm()

def worker(session,seconds):
    import torch,transformers
    from anytime_ncm.wmt_model import WmtModel
    from anytime_ncm.forced_wmt import ForwardCounter,forced_request
    from anytime_ncm.controller_wmt import controller_request
    from anytime_ncm.target_encoding import model_fingerprint
    started=time.monotonic();lock,_,split=load_lock();verify_dev();alarm(seconds)
    entries=split['parts']['test'];plan=read(EVAL/'timing-schedule.json')[str(session)];cache=read(EVAL/'parity-hashes.json');policy=read(DEV/'policy.json')['policy']
    limits=sum_work(plan)
    if any(limits[k]>v for k,v in lock['per_session_forward_caps'].items()):raise ValueError('Plan exceeds cap')
    meter=Meter(dict(decisions=358,features=358));counter=None;result=None;request=None
    receipt=dict(session=session,pid=os.getpid(),started_utc=now(),completed_requests=0,prefix_calls=0,policy_sha256=sha(DEV/'policy.json'))
    write_new(EVAL/f'{session}-started.json',receipt)
    try:
        if (sys.version_info[:3]!=(3,12,3) or torch.__version__!='2.10.0+cu128' or torch.version.cuda!='12.8' or transformers.__version__!='4.57.6'
            or not torch.cuda.is_available() or torch.cuda.get_device_name()!='NVIDIA GeForce RTX 5060'):raise RuntimeError('Material environment drift')
        torch.set_num_threads(4);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=True
        sources=StringRows((ROOT/'data/wmt14/sources.pickle').read_bytes()).select({e['index'] for e in entries})
        loading=time.monotonic();model=WmtModel(ROOT);receipt['model_load_seconds']=time.monotonic()-loading
        receipt['environment']=dict(python=sys.version,torch=torch.__version__,cuda=torch.version.cuda,transformers=transformers.__version__,gpu=torch.cuda.get_device_name(),
            precision='float32/eval',cpu_threads=4,tf32_matmul=False,tf32_cudnn=True,free_total_device_bytes_before=list(torch.cuda.mem_get_info()))
        receipt['nvidia_smi']=subprocess.check_output(['/usr/lib/wsl/lib/nvidia-smi','--query-gpu=driver_version,name,memory.total','--format=csv,noheader'],text=True,timeout=15).strip()
        original=model.official['prefix']
        def prefix(text):
            if receipt['prefix_calls']>=2235:raise RuntimeError('Prefix call cap')
            receipt['prefix_calls']+=1;return original(text)
        model.official['prefix']=prefix
        for e in entries:
            if identity(prefix(sources[e['index']]))!=e['identity']:raise ValueError('Effective-prefix identity differs')
        fingerprint=lambda:dict(generator=model_fingerprint(model.net),tokenizer=model_fingerprint(model.tokenizer.vqvae))
        receipt['state_before']=fingerprint();counter=ForwardCounter(model,limits);controller=Controller(policy,meter)
        begin,end=torch.cuda.Event(enable_timing=True),torch.cuda.Event(enable_timing=True)
        with (EVAL/f'{session}-starts.jsonl').open('x',encoding='utf-8',newline='\n') as ledger,(EVAL/f'{session}-requests.jsonl').open('x',encoding='utf-8',newline='\n') as stream:
            for number,request in enumerate(plan):
                if time.monotonic()-started>seconds or rss()>lock['worker_rss_bytes']:raise RuntimeError('Worker time/RSS cap')
                before=dict(counter.counts);budget_before=dict(meter.counts);counter.take('inputs')
                ledger.write(json.dumps(dict(request,work_before=before,controller_work_before=budget_before))+'\n');ledger.flush()
                torch.cuda.synchronize();torch.cuda.reset_peak_memory_stats();torch.manual_seed(20261023)
                result=None;wall=time.perf_counter_ns();begin.record()
                if request['method']=='controller':result=controller_request(model,sources[request['index']],controller)
                else:result=forced_request(model,sources[request['index']],request['depth'],'terminal')
                end.record();torch.cuda.synchronize();wall_ms=(time.perf_counter_ns()-wall)/1e6
                actual={k:counter.counts[k]-before[k] for k in before}
                if actual!=work(request) or result['exit_level']!=request['depth'] or [o['level'] for o in result['observations']]!=request['visits']:raise ValueError('Online/replay work or exit mismatch')
                parity_method=('fixed:11' if policy['kind']=='full' else 'assigned_sparse') if request['method']=='controller' else request['method']
                hashes=check_parity(result,cache[str(request['index'])],dict(depth=request['depth'],method=parity_method))
                reserved=torch.cuda.max_memory_reserved()
                if reserved>min(lock['gpu_reserved_bytes'],torch.cuda.get_device_properties(0).total_memory):raise RuntimeError('GPU memory cap')
                stream.write(json.dumps(dict(request,wall_ms=wall_ms,cuda_stream_span_ms=begin.elapsed_time(end),work=actual,
                    controller_work={k:meter.counts[k]-budget_before[k] for k in budget_before},peak_allocated_bytes=torch.cuda.max_memory_allocated(),peak_reserved_bytes=reserved,parity=True,hashes=hashes),allow_nan=False)+'\n');stream.flush()
                receipt['completed_requests']+=1
                if number%256==0 or number+1==len(plan):
                    if size()>lock['artifact_bytes']:raise RuntimeError('Artifact cap')
                    print(f'Controller session {session}: {number+1}/{len(plan)}; online exits/work/output parity passed',flush=True)
        receipt['state_after']=fingerprint()
        if receipt['state_before']!=receipt['state_after'] or counter.counts!=limits or receipt['prefix_calls']!=2235:raise ValueError('Incomplete work or model mutation')
        receipt.update(status='complete',counts=dict(counter.counts),controller_work=meter.counts,forward_calls=dict(counter.calls),wall_seconds=time.monotonic()-started,max_rss_bytes=rss(),finished_utc=now())
        if rss()>lock['worker_rss_bytes']:raise RuntimeError('Worker RSS cap')
        write_new(EVAL/f'{session}-execution.json',receipt)
    except BaseException as error:
        write_new(EVAL/f'{session}-failure.json',dict(receipt,error=repr(error),request=request,counts=dict(counter.counts) if counter else {},controller_work=meter.counts,automatic_retry=False))
        if result is not None:write_new(EVAL/f'{session}-failure-output.json',dict(prefix_ids=result['prefix_ids'],codes=result['codes'][0].cpu().tolist(),observations=result['observations']))
        raise
    finally:
        if counter:counter.close()
        stop_alarm()

def evaluate(commit):
    started=time.monotonic();lock,sources,split=load_lock();clean_main(commit);dev=verify_dev()
    if git('cat-file','-e',commit+':results/quality_tolerant/controller/development/policy.json')!='':raise ValueError('Policy not committed')
    EVAL.mkdir(parents=True,exist_ok=False);meter=None
    write_new(EVAL/'started.json',dict(policy_commit=commit,protocol_commit=dev['protocol_commit'],policy_sha256=sha(DEV/'policy.json'),started_utc=now()))
    alarm(lock['evaluation_wall_seconds'])
    try:
        entries=split['parts']['test'];policy=read(DEV/'policy.json')
        write_new(EVAL/'access-release.json',dict(entries=entries,roles=['test'],consumed_only=True,selection_complete=True,policy_commit=commit,policy_sha256=sha(DEV/'policy.json'),E3_E4_outputs=False))
        with (EVAL/'ledger.jsonl').open('x',encoding='utf-8',newline='\n') as stream:
            meter=Meter(lock['evaluation_caps'],stream);rows,source,reference=read_data(entries,split,meter)
            counts=coverage(entries,reference);write_new(EVAL/'coverage.json',counts)
            if counts['numeric_covered']<8:raise ValueError('Insufficient test numeric coverage')
            controller=Controller(policy['policy'],meter);pred=[]
            for row in rows:meter.take('replay_inputs');pred.append(replay(controller,source[row['index']],row))
            write_new(EVAL/'parity-hashes.json',{str(r['index']):cache_row(r) for r in rows})
            write_new(EVAL/'predictions.json',[dict(index=r['index'],depth=d,visits=v) for r,(d,v) in zip(rows,pred)])
            plans={str(s):schedule(entries,pred,s) for s in (0,1)};write_new(EVAL/'timing-schedule.json',plans)
            for plan in plans.values():
                if any(sum_work(plan)[k]>v for k,v in lock['per_session_forward_caps'].items()):raise ValueError('Forward plan cap')
            model_start=time.monotonic()
            for session in (0,1):
                remaining=lock['model_wall_seconds']-(time.monotonic()-model_start)
                if remaining<=0:raise RuntimeError('Model orchestration cap')
                subprocess.run([sys.executable,str(Path(__file__).resolve()),'worker','--session',str(session),'--seconds',str(remaining)],cwd=ROOT,check=True,timeout=remaining)
            model_seconds=time.monotonic()-model_start
            quality={};refs=[reference[r['index']] for r in rows]
            full=corpus_score([r['levels'][-1]['text'] for r in rows],refs,meter)
            for method in METHODS:
                depths=[d for d,v in pred] if method=='controller' else [int(method.split(':')[1])]*len(rows)
                score=full if method=='fixed:11' else corpus_score([r['levels'][d-1]['text'] for r,d in zip(rows,depths)],refs,meter)
                quality[method]=dict(metrics=score,losses=point_losses(score,full),point_pass=point_pass(score,full))
            records=[json.loads(line) for s in (0,1) for line in (EVAL/f'{s}-requests.jsonl').read_text(encoding='utf-8').splitlines()]
            analysis_start=time.monotonic();alarm(lock['analysis_wall_seconds'])
            analysis=timing_analysis(records,entries,quality,policy['locked_fixed_comparator'],sum(d<11 for d,v in pred))
            analysis['analysis_wall_seconds']=time.monotonic()-analysis_start;stop_alarm()
            write_new(EVAL/'analysis.json',analysis)
        processes=[read(EVAL/f'{s}-execution.json') for s in (0,1)]
        if len({r['pid'] for r in processes})!=2:raise ValueError('Need distinct processes')
        total={k:sum(p['counts'][k] for p in processes) for k in lock['total_forward_caps']}
        if any(total[k]>v for k,v in lock['total_forward_caps'].items()) or total['inputs']!=4296:raise ValueError('Total work cap')
        hashes_ok(sources['protected_sha256']);verify_dev();check_resources(lock,started,lock['evaluation_wall_seconds'])
        write_new(EVAL/'decision.json',dict(status=analysis['decision'],selected_policy=dev['selected'],Q0_passed=False,Q4_authorized=False,independent_quality_confirmation=False,
            reserved_outputs_released=False,automatic_refit=False,next_step='Report this bounded controller experiment and stop before confirmation or another fit.'))
        write_new(EVAL/'execution.json',dict(status='complete',policy_commit=commit,protocol_commit=dev['protocol_commit'],counts=meter.counts,forward_counts=total,
            controller_work={k:sum(p['controller_work'][k] for p in processes) for k in ('decisions','features')},process_ids=[p['pid'] for p in processes],
            model_orchestration_wall_seconds=model_seconds,total_wall_seconds=time.monotonic()-started,max_parent_rss_bytes=rss(),artifact_bytes=size(),paid_compute_dollars=0,
            new_inputs=0,new_trajectories=0,encoder_calls=0,target_encodings=0,model_states_unchanged=True,all_output_exit_work_parity_passed=True,
            bootstrap_draws=20000,automatic_retries=0,finished_utc=now(),artifact_sha256=artifacts(EVAL)))
        print('CONTROLLER EVALUATION COMPLETE: '+analysis['decision'],flush=True)
    except BaseException as error:
        write_new(EVAL/'failure.json',dict(error=repr(error),counts=meter.counts if meter else {},wall_seconds=time.monotonic()-started,automatic_retry=False));raise
    finally:stop_alarm()

def verify():
    lock,source,split=load_lock();dev=verify_dev();e=read(EVAL/'execution.json');hashes_ok(e['artifact_sha256'],EVAL)
    for s in (0,1):
        plan=read(EVAL/'timing-schedule.json')[str(s)];rows=[json.loads(line) for line in (EVAL/f'{s}-requests.jsonl').read_text(encoding='utf-8').splitlines()]
        receipt=read(EVAL/f'{s}-execution.json')
        if len(plan)!=len(rows) or receipt['counts']!=sum_work(plan) or receipt['state_before']!=receipt['state_after']:raise ValueError('Incomplete worker')
        for expected,r in zip(plan,rows):
            if any(r[k]!=v for k,v in expected.items()) or r['work']!=work(r) or not r['parity']:raise ValueError('Request differs')
    if e['status']!='complete' or e['forward_counts']['inputs']!=4296 or e['encoder_calls']!=0:raise ValueError('Incomplete execution')
    print(json.dumps(dict(verified=True,selected=dev['selected'],fits=dev['counts']['fits'],requests=e['forward_counts']['inputs'],protected_files=len(source['protected_sha256']),new_model_calls=0,new_bootstrap_draws=0)))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=('develop','evaluate','worker','verify'));p.add_argument('--commit');p.add_argument('--session',type=int);p.add_argument('--seconds',type=float);a=p.parse_args()
    if a.mode=='develop':develop(a.commit)
    elif a.mode=='evaluate':evaluate(a.commit)
    elif a.mode=='worker':worker(a.session,a.seconds)
    else:verify()
