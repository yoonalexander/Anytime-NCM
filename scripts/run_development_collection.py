"""Once-only fit/calibration official-corpus collection under frozen campaign access."""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='4'
for k in ('HF_HUB_OFFLINE','TRANSFORMERS_OFFLINE'):os.environ[k]='1'
os.environ['TOKENIZERS_PARALLELISM']='false';os.environ['PYTHONDONTWRITEBYTECODE']='1'
import argparse,gzip,hashlib,io,json,signal,subprocess,sys,tarfile,time,zipfile,importlib.metadata
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from run_signal_discrimination import git,cpu,rss,now,hashes_ok
from anytime_ncm.evidence_preflight import sha,write_new
from anytime_ncm.quality_controller import Meter,sentence_targets
from anytime_ncm.controller_study import cache_row
from anytime_ncm.development_data import selected_segments
from anytime_ncm.quality_campaign import campaign_root,verify_campaign,record_phase,usage_zero
from anytime_ncm.wmt_data import identity
BASE=ROOT/'docs/studies/quality-tolerant';CAMPAIGN=campaign_root(ROOT);OUT=CAMPAIGN/'development_collection';PRIVATE=ROOT/'data/quality_tolerant_campaign_20261029/development_collection';ALLOC=CAMPAIGN/'development_eligibility/source-only-allocation.json'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def key(e):return str(e['year'])+':'+str(e['index'])
def size():return sum(p.stat().st_size for d in (OUT,PRIVATE) for p in d.rglob('*') if p.is_file())
def alarm(seconds):
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('Development collection wall cap')));signal.setitimer(signal.ITIMER_REAL,seconds)
def stop_alarm():signal.setitimer(signal.ITIMER_REAL,0)
def load():
    lock=read(BASE/'development-collection-lock.json');source=read(BASE/'development-collection-source-lock.json');hashes_ok(source['source_sha256']);hashes_ok(source['protected_sha256'])
    if git('-C','third_party/ncm','rev-parse','HEAD')!=source['upstream_commit'] or git('-C','third_party/ncm','status','--porcelain'):raise ValueError('Upstream changed')
    return lock,source

def extract(entries,lock,meter):
    sources={};references={};year_report=[]
    for item in lock['archives']:
        path=ROOT/item['path']
        if not path.is_file() or path.stat().st_size!=item['bytes'] or sha(path)!=item['sha256']:raise ValueError('Cached official archive changed; no network fallback')
        remaining=lock['decompressed_bytes_cap']-meter.counts['decompressed_bytes']
        with gzip.open(path,'rb') as f:payload=f.read(remaining)
        if len(payload)>=remaining:raise RuntimeError('Decompression ceiling boundary')
        meter.take('decompressed_bytes',len(payload));members={}
        with tarfile.open(fileobj=io.BytesIO(payload),mode='r:') as tar:
            for kind in ('source','reference'):
                name=item[kind+'_member'];matches=[m for m in tar.getmembers() if m.name==name]
                if len(matches)!=1 or not matches[0].isfile() or matches[0].size>16<<20:raise ValueError('Invalid pinned member')
                with tar.extractfile(matches[0]) as stream:members[kind]=stream.read()
                if hashlib.sha256(members[kind]).hexdigest()!=item[kind+'_sha256']:raise ValueError('Pinned SGML member changed')
        active={e['index'] for e in entries if e['year']==item['year']}
        source,headers=selected_segments(members['source'],'source',item['source_member'],active,item['rows'],meter)
        reference,_=selected_segments(members['reference'],'reference',item['reference_member'],active,item['rows'],meter,headers)
        for i in active:sources[str(item['year'])+':'+str(i)]=source[i];references[str(item['year'])+':'+str(i)]=reference[i]
        year_report.append(dict(year=item['year'],source_headers=item['rows'],reference_headers=item['rows'],selected_bodies_each=len(active),all_unselected_utf8_payloads_skipped=True,source_reference_headers_aligned=True))
        del payload,members,source,reference,headers
    if set(sources)!=set(references) or set(sources)!={key(e) for e in entries}:raise ValueError('Incomplete selected extraction')
    with (PRIVATE/'sources.jsonl').open('x',encoding='utf-8',newline='\n') as f:
        for e in entries:f.write(json.dumps(dict(e,source=sources[key(e)]),ensure_ascii=False)+'\n')
    with (PRIVATE/'references.jsonl').open('x',encoding='utf-8',newline='\n') as f:
        for e in entries:f.write(json.dumps(dict(year=e['year'],index=e['index'],role=e['role'],reference=references[key(e)]),ensure_ascii=False)+'\n')
    write_new(OUT/'corpus-access.json',dict(years=year_report,source_body_decodes=len(sources),reference_body_decodes=len(references),source_convention='exact prior audited SGML segment payload; no unescape/whitespace rewrite',evaluation_bodies_decoded=0,confirmation_bodies_decoded=0,historical_bodies_decoded=0,downloads=0))
    return references

def worker(seconds):
    started=time.monotonic();lock,_=load();alarm(seconds)
    import torch,transformers
    from anytime_ncm.wmt_model import WmtModel
    from anytime_ncm.development_trace import trace_request
    from anytime_ncm.forced_wmt import ForwardCounter
    from anytime_ncm.target_encoding import model_fingerprint
    entries=read(OUT/'access-release.json')['entries'];plan=read(OUT/'collection-plan.json');sources={}
    for line in (PRIVATE/'sources.jsonl').read_text(encoding='utf-8').splitlines():
        r=json.loads(line);sources[key(r)]=r['source']
    if len(sources)!=4299 or set(sources)!={key(e) for e in entries}:raise ValueError('Worker source allocation mismatch')
    receipt=dict(pid=os.getpid(),started_utc=now(),completed_requests=0,prefix_calls=0,worker_source_materializations=4299,reference_cache_opened=False);write_new(OUT/'worker-started.json',receipt);counter=None;request=None;meter=Meter(lock['feature_caps'])
    try:
        if (sys.version_info[:3]!=(3,12,3) or torch.__version__!='2.10.0+cu128' or torch.version.cuda!='12.8' or transformers.__version__!='4.57.6' or not torch.cuda.is_available() or torch.cuda.get_device_name()!='NVIDIA GeForce RTX 5060'):raise RuntimeError('Material environment drift')
        torch.set_num_threads(4);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=True;model=WmtModel(ROOT)
        receipt['environment']=dict(python=sys.version,torch=torch.__version__,cuda=torch.version.cuda,transformers=transformers.__version__,gpu=torch.cuda.get_device_name(),physical_gpu_bytes=torch.cuda.get_device_properties(0).total_memory,precision='float32/eval',cpu_threads=4,tf32_matmul=False,tf32_cudnn=True)
        receipt['nvidia_smi']=subprocess.check_output(['/usr/lib/wsl/lib/nvidia-smi','--query-gpu=driver_version,name,memory.total','--format=csv,noheader'],text=True,timeout=15).strip();original=model.official['prefix']
        def prefix(text):
            if receipt['prefix_calls']>=8603:raise RuntimeError('Source-prefix cap')
            receipt['prefix_calls']+=1;return original(text)
        model.official['prefix']=prefix
        for e in entries:
            if identity(prefix(sources[key(e)]))!=e['identity']:raise ValueError('Audited effective-prefix identity mismatch')
        fingerprint=lambda:dict(generator=model_fingerprint(model.net),tokenizer=model_fingerprint(model.tokenizer.vqvae));receipt['state_before']=fingerprint();counter=ForwardCounter(model,lock['forward_caps'])
        with (OUT/'request-starts.jsonl').open('x',encoding='utf-8',newline='\n') as ledger,(OUT/'requests.jsonl').open('x',encoding='utf-8',newline='\n') as public,(PRIVATE/'trajectories.jsonl').open('x',encoding='utf-8',newline='\n') as private:
            for number,request in enumerate(plan):
                if time.monotonic()-started>seconds or rss()>lock['worker_rss_bytes'] or size()>lock['artifact_bytes']:raise RuntimeError('Worker resources')
                before=dict(counter.counts);fbefore=dict(meter.counts);counter.take('inputs');ledger.write(json.dumps(dict(request,work_before=before,feature_work_before=fbefore))+'\n');ledger.flush()
                torch.cuda.synchronize();torch.cuda.reset_peak_memory_stats();torch.manual_seed(20261023);result=trace_request(model,sources[key(request)],meter);torch.cuda.synchronize()
                counts={k:counter.counts[k]-before[k] for k in before};fwork={k:meter.counts[k]-fbefore[k] for k in fbefore}
                if counts!=dict(inputs=1,generator_levels=11,decoder=12,encoder=0) or fwork!=dict(cheap_features=2,selected_logit_features=2,cue_features=2) or not result['native_final_parity'] or identity(result['prefix_ids'])!=request['identity']:raise ValueError('Native trace identity/work/parity mismatch')
                cache=cache_row(dict(identity=request['identity'],**result));reserved=torch.cuda.max_memory_reserved()
                if reserved>min(lock['gpu_reserved_bytes'],receipt['environment']['physical_gpu_bytes']):raise RuntimeError('GPU memory cap')
                private.write(json.dumps(dict(request,**result),ensure_ascii=False,allow_nan=False)+'\n');private.flush()
                public.write(json.dumps(dict(request,work=counts,feature_work=fwork,peak_allocated_bytes=torch.cuda.max_memory_allocated(),peak_reserved_bytes=reserved,native_final_parity=True,hashes=cache,features=result['features']),allow_nan=False)+'\n');public.flush();receipt['completed_requests']+=1
                if number%256==0 or number+1==len(plan):print(f'Development collection: {number+1}/{len(plan)}; native final/current-prefix features and exact work passed',flush=True)
        receipt['state_after']=fingerprint()
        if receipt['state_before']!=receipt['state_after'] or counter.counts!=lock['forward_caps'] or meter.counts!=lock['feature_caps'] or receipt['prefix_calls']!=8603:raise ValueError('Incomplete collection or state mutation')
        receipt.update(status='complete',counts=dict(counter.counts),feature_counts=meter.counts,forward_calls=dict(counter.calls),wall_seconds=time.monotonic()-started,cpu_seconds=cpu(),max_rss_bytes=rss(),finished_utc=now());write_new(OUT/'worker-execution.json',receipt)
    except BaseException as error:
        write_new(OUT/'worker-failure.json',dict(receipt,error=repr(error),request=request,counts=dict(counter.counts) if counter else {},feature_counts=meter.counts,automatic_retry=False));raise
    finally:
        if counter:counter.close()
        stop_alarm()

def support(targets,entries):
    report={};ready=True;cue_ready=True
    for role,floor in [('development_fit',20),('development_calibration',10)]:
        active=[key(e) for e in entries if e['role']==role];levels={}
        for d in (8,10):
            values=[targets[k][str(d)] for k in active];adverse=sum(max([0.]+[v for v in row if v is not None])>4 for row in values);endpoint={}
            for t,name in enumerate(('bleu','chrf','numeric_reference_f1','negation_cue_mismatch_rate')):
                defined=[v[t] for v in values if v[t] is not None];pos=sum(x>0 for x in defined);nonpos=sum(x<=0 for x in defined)
                endpoint[name]=dict(defined=len(defined),missing=len(values)-len(defined),adverse=pos,nonadverse=nonpos,nonzero=sum(x!=0 for x in defined),minimum=float(min(defined)) if defined else None,maximum=float(max(defined)) if defined else None)
                if t in (2,3) and role=='development_fit':cue_ready=cue_ready and pos>=5 and nonpos>=5
            ready=ready and min(adverse,len(values)-adverse)>=floor and endpoint['numeric_reference_f1']['defined']>=(100 if role=='development_fit' else 40)
            levels[str(d)]=dict(joint_proxy_threshold=4.,adverse=adverse,nonadverse=len(values)-adverse,endpoints=endpoint)
        report[role]=dict(inputs=len(active),components=len({e['component'] for e in entries if e['role']==role}),levels=levels)
    return dict(roles=report,joint_controller_development_supported=ready,fit_cue_endpoint_heads_meet_5each_sanity_floor=cue_ready,quality_power_or_guarantee_established=False,independent_confirmation=False,Q0_passed=False)

def run(commit):
    started=time.monotonic();lock,source=load();verify_campaign(ROOT,lock['campaign_reservation'])
    if git('rev-parse','HEAD')!=commit or git('branch','--show-current')!='main' or git('status','--porcelain') or git('ls-remote','origin','refs/heads/main').split()[0]!=commit:raise ValueError('Need clean main at pushed collection lock')
    if PRIVATE.exists():raise ValueError('Private collection already exists; no silent reuse/retry')
    OUT.mkdir(parents=True,exist_ok=False);PRIVATE.mkdir(parents=True,exist_ok=False);write_new(OUT/'started.json',dict(source_commit=commit,started_utc=now()));alarm(lock['wall_seconds']);meter=Meter(lock['analysis_caps'])
    try:
        with zipfile.ZipFile(OUT/'execution-sources.zip','x',compression=zipfile.ZIP_DEFLATED) as z:
            for p in source['source_sha256']:z.writestr(p,(ROOT/p).read_bytes())
            z.writestr('source-lock.json',json.dumps(source,indent=2))
        if any(importlib.metadata.version(k)!=v for k,v in lock['versions'].items()):raise RuntimeError('Pinned analysis/tokenizer package drift')
        synthetic_start=time.monotonic()
        with (OUT/'synthetic-tests.log').open('x',encoding='utf-8',newline='\n') as log:
            test=subprocess.run([sys.executable,'-m','pytest','tests/test_development_collection.py','-q','-s','-p','no:cacheprovider','--junitxml=results/quality_tolerant/campaign_20261029/development_collection/synthetic-tests.xml'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=lock['test_wall_seconds'])
        synthetic_seconds=time.monotonic()-synthetic_start
        if test.returncode:raise RuntimeError('Synthetic validation failed before corpus/model access')
        if 'SYNTHETIC_DEVELOPMENT_REQUESTS 3' not in (OUT/'synthetic-tests.log').read_text(encoding='utf-8'):raise ValueError('Missing synthetic model-work ledger')
        allocation=read(ALLOC);entries=sorted(allocation['parts']['development_fit']+allocation['parts']['development_calibration'],key=lambda e:(e['year'],e['index']))
        if len(entries)!=4299 or len({e['identity'] for e in entries})!=4299 or any(e['role'] not in ('development_fit','development_calibration') for e in entries):raise ValueError('Fit/calibration access mismatch')
        write_new(OUT/'access-release.json',dict(entries=entries,source_commit=commit,source_payloads=4299,reference_payloads=4299,development_evaluation1188_released=False,proposed_confirmation7700_released=False,old_test87_E3_E4_unallocated_released=False))
        references=extract(entries,lock,meter);config=read(ROOT/'configs/phase4_wmt_sources.json');assets={p:v for p,v in config['files'].items() if p.startswith('artifacts/wmt14/')}
        for p,v in assets.items():
            if sha(ROOT/p)!=v['sha256'] or (ROOT/p).stat().st_size!=v['size']:raise ValueError('Pinned local model asset changed')
        write_new(OUT/'asset-preflight.json',dict(asset_sha256={p:v['sha256'] for p,v in assets.items()},historical_corpus_bodies_read=0))
        plan=[]
        for e in sorted(allocation['parts']['development_fit'],key=lambda e:(e['year'],e['index']))[:5]:plan.append(dict(e,request_id=len(plan),warmup=True))
        for e in entries:plan.append(dict(e,request_id=len(plan),warmup=False))
        write_new(OUT/'collection-plan.json',plan);print('Seven synthetic checks passed; new fit/calibration-only corpus/model collection released',flush=True)
        model_start=time.monotonic();remaining=min(lock['model_wall_seconds'],lock['wall_seconds']-(model_start-started))
        subprocess.run([sys.executable,str(Path(__file__).resolve()),'worker','--seconds',str(remaining)],cwd=ROOT,check=True,timeout=remaining);model_seconds=time.monotonic()-model_start
        targets={};cache={}
        for line in (PRIVATE/'trajectories.jsonl').read_text(encoding='utf-8').splitlines():
            meter.take('new_trace_bodies');row=json.loads(line)
            if row['warmup']:continue
            k=key(row)
            if k not in references or k in targets:raise ValueError('Unexpected/duplicate new development trajectory')
            targets[k]={str(d):v for d,v in sentence_targets(row,references[k],meter).items()};cache[k]=cache_row(row)
        if len(targets)!=4299:raise ValueError('Missing development outcomes')
        write_new(OUT/'proxy-labels.json',targets);write_new(OUT/'parity-hashes.json',cache);labels=support(targets,entries);write_new(OUT/'label-support.json',labels)
        process=read(OUT/'worker-execution.json');hashes_ok(source['protected_sha256']);hashes_ok(source['source_sha256'])
        if time.monotonic()-started>lock['wall_seconds'] or cpu()>lock['execution_cpu_cap_seconds'] or rss()>lock['parent_rss_bytes'] or size()>lock['artifact_bytes']:raise RuntimeError('Collection resource cap')
        usage=usage_zero();usage.update(model_requests=process['counts']['inputs']+3,model_orchestration_seconds=model_seconds+synthetic_seconds,cpu_seconds=cpu()+lock['reporting_cpu_charge_seconds'],artifact_bytes=lock['artifact_bytes']);verify_campaign(ROOT,usage)
        write_new(OUT/'decision.json',dict(status='joint_development_collection_supported' if labels['joint_controller_development_supported'] else 'development_labels_inadequate',next_branch='prospectively_lock_bounded_fitting_and_selection' if labels['joint_controller_development_supported'] else 'bounded_existing_data_family2_or_closeout',cue_endpoint_head_sanity_floor_passed=labels['fit_cue_endpoint_heads_meet_5each_sanity_floor'],Q0_passed=False,independent_confirmation=False,evaluation_outcomes_released=False,quality_guarantee=False))
        write_new(OUT/'execution.json',dict(status='complete',source_commit=commit,analysis_counts=meter.counts,counts=process['counts'],feature_counts=process['feature_counts'],synthetic_model_requests=3,synthetic_generator_levels=22,synthetic_decoder_calls=15,synthetic_initializations=1,real_checkpoint_loads=1,new_fits=0,new_controller_families=0,target_encodings=0,encoder_calls=0,bootstrap_draws=0,source_payload_decodes=4299,reference_payload_decodes=4299,worker_source_materializations=4299,worker_reference_cache_opened=False,model_states_unchanged=True,native_final_parity_all_requests=True,model_orchestration_wall_seconds=model_seconds,synthetic_wall_seconds_charged=synthetic_seconds,total_wall_seconds=time.monotonic()-started,cpu_seconds_before_reporting_charge=cpu(),max_parent_rss_bytes=rss(),private_artifact_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in PRIVATE.rglob('*') if p.is_file()},campaign_usage=usage,automatic_retries=0,paid_compute_dollars=0,finished_utc=now(),artifact_sha256={p.relative_to(OUT).as_posix():sha(p) for p in OUT.rglob('*') if p.is_file()}))
        print(json.dumps(record_phase(ROOT,'07-development-collection','development_collection/execution.json')),flush=True);print('DEVELOPMENT COLLECTION COMPLETE; joint support='+str(labels['joint_controller_development_supported'])+'; cue floor='+str(labels['fit_cue_endpoint_heads_meet_5each_sanity_floor']),flush=True)
    except BaseException as error:
        failure=OUT/'failure.json'
        if not failure.exists():write_new(failure,dict(error=repr(error),counts=meter.counts,campaign_usage=lock['campaign_reservation'],conservative_reservation_charge=True,automatic_retry=False))
        if not (CAMPAIGN/'accounting/phase-07-development-collection.json').exists():record_phase(ROOT,'07-development-collection','development_collection/failure.json')
        raise
    finally:stop_alarm()

def verify():
    lock,source=load();e=read(OUT/'execution.json');hashes_ok({('results/quality_tolerant/campaign_20261029/development_collection/'+p):h for p,h in e['artifact_sha256'].items()});hashes_ok(e['private_artifact_sha256'])
    process=read(OUT/'worker-execution.json');records=[json.loads(line) for line in (OUT/'requests.jsonl').read_text(encoding='utf-8').splitlines()];plan=read(OUT/'collection-plan.json');cache=read(OUT/'parity-hashes.json')
    if e['status']!='complete' or len(records)!=4304 or process['counts']!=lock['forward_caps'] or process['feature_counts']!=lock['feature_caps'] or process['state_before']!=process['state_after'] or process['prefix_calls']!=8603 or e['new_fits'] or e['target_encodings']:raise ValueError('Invalid collection execution')
    for expected,r in zip(plan,records):
        if any(r[k]!=v for k,v in expected.items()) or r['work']!=dict(inputs=1,generator_levels=11,decoder=12,encoder=0) or not r['native_final_parity']:raise ValueError('Development request mismatch')
        if not r['warmup'] and r['hashes']!=cache[key(r)]:raise ValueError('Saved new prefix-cache mismatch')
        if [v['level'] for v in r['features']]!=[8,10] or any(len(v['values'])!=27 for v in r['features']):raise ValueError('Wrong current/past feature schema')
    if e['analysis_counts']['source_body_decodes']!=4299 or e['analysis_counts']['reference_body_decodes']!=4299 or e['analysis_counts']['new_trace_bodies']!=4304 or e['analysis_counts']['sentence_label_pairs']!=12897:raise ValueError('Access/label counts mismatch')
    print(json.dumps(dict(verified=True,protected_files=len(source['protected_sha256']),real_requests=4304,new_reference_utf8_decodes=0,new_model_calls_or_fits=0,campaign=verify_campaign(ROOT))))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=('run','worker','verify'));p.add_argument('--commit');p.add_argument('--seconds',type=float);a=p.parse_args()
    if a.mode=='run':run(a.commit)
    elif a.mode=='worker':worker(a.seconds)
    else:verify()
