"""Once-only consumed-input real latency diagnostic, after pushed protocol lock."""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'): os.environ[k]='4'
for k in ('HF_HUB_OFFLINE','TRANSFORMERS_OFFLINE'): os.environ[k]='1'
os.environ['TOKENIZERS_PARALLELISM']='false'
os.environ['PYTHONDONTWRITEBYTECODE']='1'
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import resource
import signal
import subprocess
import sys
import time
import zipfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from anytime_ncm.evidence_preflight import sha, write_new
from anytime_ncm.latency_diagnostic import METHODS, make_schedule, work, parity_cache, check_parity, analyze, document_components
from anytime_ncm.wmt_data import StringRows, identity
OUT=ROOT/'results/quality_tolerant/latency_diagnostic'
BASE=ROOT/'docs/studies/quality-tolerant'

def read(p): return json.loads(p.read_text(encoding='utf-8'))
def git(*a): return subprocess.check_output(['git.exe',*a],cwd=ROOT,text=True,timeout=60).strip()
def now(): return datetime.now(timezone.utc).isoformat()
def total_size(): return sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file())
def hashes_ok(values):
    for p,h in values.items():
        if sha(ROOT/p)!=h: raise ValueError('Frozen file differs: '+p)

def load_lock():
    lock=read(BASE/'latency-diagnostic-lock.json')
    sources=read(BASE/'latency-diagnostic-source-lock.json')
    hashes_ok(sources['source_sha256']); hashes_ok(sources['protected_sha256'])
    if git('-C','third_party/ncm','rev-parse','HEAD') != sources['upstream_commit'] or git('-C','third_party/ncm','status','--porcelain'):
        raise ValueError('Frozen upstream differs')
    return lock,sources

def sum_work(plan):
    return {k:sum(work(r)[k] for r in plan) for k in ('inputs','generator_levels','decoder','encoder')}

def worker(session,seconds):
    import torch
    import transformers
    from anytime_ncm.wmt_model import WmtModel
    from anytime_ncm.forced_wmt import ForwardCounter, forced_request
    from anytime_ncm.sparse_wmt import sparse_request
    from anytime_ncm.target_encoding import model_fingerprint
    start=time.monotonic(); lock,_=load_lock()
    signal.signal(signal.SIGALRM,lambda *_: (_ for _ in ()).throw(TimeoutError('Model wall allocation exhausted')))
    signal.setitimer(signal.ITIMER_REAL,seconds)
    plan=read(OUT/'timing-schedule.json')[str(session)]
    entries=read(OUT/'access-release.json')['entries']
    expected=read(OUT/'parity-hashes.json')
    limits=sum_work(plan)
    if any(limits[k]>v for k,v in lock['per_session_forward_caps'].items()): raise ValueError('Schedule exceeds cap')
    receipt=dict(session=session,pid=os.getpid(),started_utc=now(),completed_requests=0,prefix_calls=0)
    write_new(OUT/f'{session}-started.json',receipt)
    counter=None; result=None; request=None
    try:
        if (sys.version_info[:3]!=(3,12,3) or torch.__version__!='2.10.0+cu128' or torch.version.cuda!='12.8'
            or transformers.__version__!='4.57.6' or not torch.cuda.is_available()
            or torch.cuda.get_device_name()!='NVIDIA GeForce RTX 5060'):
            raise RuntimeError('Material environment drift')
        torch.set_num_threads(4)
        torch.backends.cuda.matmul.allow_tf32=False; torch.backends.cudnn.allow_tf32=True
        source_path=ROOT/'data/wmt14/sources.pickle'
        sources=StringRows(source_path.read_bytes()).select({e['index'] for e in entries})
        for e in entries:
            if hashlib.sha256(sources[e['index']].encode()).hexdigest()!=e['source_text_sha256']: raise ValueError('Source differs')
        loading=time.monotonic(); model=WmtModel(ROOT); receipt['model_load_seconds']=time.monotonic()-loading
        receipt['environment']=dict(python=sys.version,torch=torch.__version__,transformers=transformers.__version__,
            cuda=torch.version.cuda,gpu=torch.cuda.get_device_name(),precision='float32/eval',cpu_threads=torch.get_num_threads(),
            tf32_matmul=torch.backends.cuda.matmul.allow_tf32,tf32_cudnn=torch.backends.cudnn.allow_tf32,
            free_total_device_bytes_before=list(torch.cuda.mem_get_info()))
        receipt['nvidia_smi']=subprocess.check_output(['/usr/lib/wsl/lib/nvidia-smi','--query-gpu=driver_version,name,memory.total','--format=csv,noheader'],text=True,timeout=15).strip()
        prefix_fn=model.official['prefix']
        def prefix(text):
            if receipt['prefix_calls']>=lock['per_session_prefix_calls']: raise RuntimeError('Prefix call cap')
            receipt['prefix_calls']+=1
            return prefix_fn(text)
        model.official['prefix']=prefix
        for e in entries:
            if identity(prefix(sources[e['index']]))!=e['identity']: raise ValueError('Effective-prefix identity differs')
        fingerprint=lambda:dict(generator=model_fingerprint(model.net),tokenizer=model_fingerprint(model.tokenizer.vqvae))
        receipt['state_before']=fingerprint(); counter=ForwardCounter(model,limits)
        begin,end=torch.cuda.Event(enable_timing=True),torch.cuda.Event(enable_timing=True)
        with (OUT/f'{session}-starts.jsonl').open('x',encoding='utf-8',newline='\n') as ledger,(OUT/f'{session}-requests.jsonl').open('x',encoding='utf-8',newline='\n') as stream:
            for number,request in enumerate(plan):
                if time.monotonic()-start>seconds: raise RuntimeError('Model wall allocation exhausted')
                if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>lock['worker_rss_bytes']: raise RuntimeError('Worker RSS cap')
                before=dict(counter.counts);counter.take('inputs')
                ledger.write(json.dumps(dict(request,work_before=before))+'\n');ledger.flush()
                torch.cuda.synchronize();torch.cuda.reset_peak_memory_stats();torch.manual_seed(20261023)
                result=None; wall=time.perf_counter_ns();begin.record()
                if request['method']=='assigned_sparse': result=sparse_request(model,sources[request['index']],request['depth'])
                else: result=forced_request(model,sources[request['index']],request['depth'],'terminal')
                end.record();torch.cuda.synchronize();wall_ms=(time.perf_counter_ns()-wall)/1e6
                actual={k:counter.counts[k]-before[k] for k in before}
                if actual!=work(request): raise ValueError('Actual work differs')
                hashes=check_parity(result,expected[str(request['index'])],request)
                reserved=torch.cuda.max_memory_reserved()
                if reserved>lock['gpu_reserved_bytes']: raise RuntimeError('GPU memory cap')
                stream.write(json.dumps(dict(request,wall_ms=wall_ms,cuda_stream_span_ms=begin.elapsed_time(end),
                    peak_allocated_bytes=torch.cuda.max_memory_allocated(),peak_reserved_bytes=reserved,work=actual,parity=True,hashes=hashes),allow_nan=False)+'\n');stream.flush()
                receipt['completed_requests']+=1
                if number%256==0 or number+1==len(plan):
                    if total_size()>lock['artifact_bytes']: raise RuntimeError('Artifact cap')
                    print(f'Latency session {session}: {number+1}/{len(plan)}; work and output parity passed',flush=True)
        receipt['state_after']=fingerprint()
        if receipt['state_before']!=receipt['state_after'] or counter.counts!=limits or receipt['prefix_calls']!=len(plan)+len(entries):
            raise ValueError('Incomplete work or mutated state')
        receipt.update(status='complete',counts=dict(counter.counts),forward_calls=dict(counter.calls),wall_seconds=time.monotonic()-start,
            max_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,finished_utc=now())
        if receipt['max_rss_bytes']>lock['worker_rss_bytes']: raise RuntimeError('Worker RSS cap')
        write_new(OUT/f'{session}-execution.json',receipt)
    except BaseException as error:
        receipt.update(status='failed',error=repr(error),request=request,counts=dict(counter.counts) if counter else {},wall_seconds=time.monotonic()-start)
        write_new(OUT/f'{session}-failure.json',receipt)
        raise
    finally:
        if counter: counter.close()
        signal.setitimer(signal.ITIMER_REAL,0)

def run(commit):
    start=time.monotonic();lock,source_lock=load_lock()
    if git('rev-parse','HEAD')!=commit or git('branch','--show-current')!='main' or git('status','--porcelain'):
        raise ValueError('Require clean main at the pushed source lock')
    if git('ls-remote','origin','refs/heads/main').split()[0]!=commit: raise ValueError('Live remote differs')
    OUT.mkdir(parents=True,exist_ok=False)
    write_new(OUT/'started.json',dict(source_commit=commit,started_utc=now(),source_lock_sha256=sha(BASE/'latency-diagnostic-source-lock.json')))
    try:
        with zipfile.ZipFile(OUT/'execution-sources.zip','x',compression=zipfile.ZIP_DEFLATED) as z:
            for p in source_lock['source_sha256']: z.writestr(p,(ROOT/p).read_bytes())
            z.writestr('source-lock.json',json.dumps(source_lock,indent=2))
        with (OUT/'synthetic-tests.log').open('x',encoding='utf-8') as f:
            check=subprocess.run([sys.executable,'-m','pytest','tests/test_latency_diagnostic.py','-q','-s','-p','no:cacheprovider',
                '--basetemp=results/quality_tolerant/latency_diagnostic/pytest-tmp','--junitxml=results/quality_tolerant/latency_diagnostic/synthetic-tests.xml'],
                cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,timeout=lock['synthetic_test_wall_seconds'])
        if check.returncode: raise RuntimeError('Synthetic validation failed; no released model loaded')
        print('Focused synthetic validation passed; preparing fixed consumed-input schedule',flush=True)
        config=read(ROOT/'configs/phase4_wmt_sources.json')
        assets={p:v for p,v in config['files'].items() if p!='data/wmt14/reference_translations.pickle'}
        for p,v in assets.items():
            if sha(ROOT/p)!=v['sha256'] or (ROOT/p).stat().st_size!=v['size']: raise ValueError('Pinned asset differs: '+p)
        write_new(OUT/'asset-preflight.json',dict(assets_sha256={p:v['sha256'] for p,v in assets.items()},reference_bodies_read=0))
        entries=sorted(read(ROOT/'results/evidence_gaps/e0/input-manifest.json')['roles']['E2_audit'],key=lambda e:e['index'])
        quality=read(ROOT/'results/quality_tolerant/q1/results.json')['E2_audit']
        exits=quality['searches']['sparse_8_10_11']['exits']
        from anytime_ncm.q1_exploratory import digest
        if len(entries)!=256 or len(exits)!=256 or digest(exits)!=quality['searches']['sparse_8_10_11']['assignment_sha256']:
            raise ValueError('Frozen Q1 assignment differs')
        trajectory=ROOT/'results/evidence_gaps/e2/trajectories.jsonl'
        if sha(trajectory)!=lock['E2_trajectory_sha256']: raise ValueError('E2 trajectory digest differs')
        allowed={(e['index'],e['identity']) for e in entries};seen=set();cache={}
        header=re.compile(rb'^\{"identity":\s*"([a-f0-9]{64})",\s*"index":\s*(\d+),\s*"partition":\s*"E2_audit"')
        with trajectory.open('rb') as stream:
            for raw in stream:
                m=header.match(raw)
                if m is None or (int(m[2]),m[1].decode()) not in allowed or int(m[2]) in seen or len(seen)>=256:
                    raise ValueError('Forbidden/duplicate trajectory before body decode')
                row=json.loads(raw);i=int(m[2]);seen.add(i)
                if (row['index'],row['identity'])!=(i,m[1].decode()) or identity(row['prefix_ids'])!=row['identity']: raise ValueError('Header/identity differs')
                from anytime_ncm.stronger_s1 import validate_rows
                validate_rows([row]);cache[str(i)]=parity_cache(row)
        if len(seen)!=256: raise ValueError('Missing E2 trajectories')
        write_new(OUT/'parity-hashes.json',cache)
        write_new(OUT/'access-release.json',dict(source_commit=commit,entries=entries,E2_trajectory_bodies=256,
            source_materializations_cap=512,reference_bodies=0,new_trajectories=0,E3_model_outputs=False,E4_model_outputs=False,
            saved_Q1_assignment_sha256=quality['searches']['sparse_8_10_11']['assignment_sha256'],entry_exception='exploratory actual assigned-exit latency only'))
        plans={str(s):make_schedule(entries,exits,s) for s in (0,1)}
        for plan in plans.values():
            if any(sum_work(plan)[k]>v for k,v in lock['per_session_forward_caps'].items()): raise ValueError('Plan exceeds work caps')
        write_new(OUT/'timing-schedule.json',plans)
        documents=document_components(read(ROOT/'results/quality_tolerant/q0_population/document-map.json'),read(ROOT/'docs/partitions/wmt14-phase4.json'))
        write_new(OUT/'document-components.json',documents)
        write_new(OUT/'saved-quality-summary.json',dict(assigned={k:v for k,v in quality['searches']['sparse_8_10_11'].items() if k in ('metrics','losses','point_quality_pass','assignment_sha256','exit_histogram')},
            baselines={k:{a:b for a,b in v.items() if a in ('metrics','losses','point_quality_pass')} for k,v in quality['baselines'].items() if k.startswith('fixed:')},
            interpretation='Reused consumed-data exploratory point scores conditional on exact new output parity; no fresh quality inference.'))
        model_start=time.monotonic()
        for session in (0,1):
            remaining=lock['model_wall_seconds']-(time.monotonic()-model_start)
            if remaining<=0: raise RuntimeError('Model orchestration cap')
            subprocess.run([sys.executable,str(Path(__file__).resolve()),'worker','--session',str(session),'--seconds',str(remaining)],cwd=ROOT,check=True,timeout=remaining)
        model_seconds=time.monotonic()-model_start
        processes=[read(OUT/f'{s}-execution.json') for s in (0,1)]
        if len({p['pid'] for p in processes})!=2: raise ValueError('Need two distinct sessions')
        counts={k:sum(p['counts'][k] for p in processes) for k in lock['total_forward_caps']}
        if counts['inputs']!=12408 or any(counts[k]>v for k,v in lock['total_forward_caps'].items()): raise ValueError('Total work cap')
        records=[json.loads(line) for s in (0,1) for line in (OUT/f'{s}-requests.jsonl').read_text(encoding='utf-8').splitlines()]
        analysis_start=time.monotonic()
        signal.signal(signal.SIGALRM,lambda *_: (_ for _ in ()).throw(TimeoutError('Analysis wall cap')))
        signal.setitimer(signal.ITIMER_REAL,lock['analysis_wall_seconds'])
        report=analyze(records,entries,documents,quality,lock['bootstrap_draws'])
        report['analysis_wall_seconds']=time.monotonic()-analysis_start
        signal.setitimer(signal.ITIMER_REAL,0)
        write_new(OUT/'analysis.json',report)
        hashes_ok(source_lock['protected_sha256']);hashes_ok(source_lock['source_sha256'])
        rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        if rss>lock['parent_rss_bytes'] or total_size()>lock['artifact_bytes'] or time.monotonic()-start>lock['total_execution_wall_seconds']: raise RuntimeError('Execution resource cap')
        write_new(OUT/'decision.json',dict(status=report['decision'],Q0_passed=False,Q3_authorized=False,reserved_outputs_released=False,
            integrated_online_policy_speedup_demonstrated=False,new_quality_guarantee=False,controller_fits=0,
            next_step='Report this diagnostic and stop; controller and confirmation require separate authorization and protocols.'))
        write_new(OUT/'execution.json',dict(status='complete',source_commit=commit,counts=counts,process_ids=[p['pid'] for p in processes],
            source_materializations=512,consumed_trajectory_bodies=256,reference_bodies=0,new_inputs=0,new_trajectories=0,
            target_encodings=0,encoder_calls=counts['encoder'],fits=0,bootstrap_draws=lock['bootstrap_draws'],
            model_orchestration_wall_seconds=model_seconds,total_wall_seconds=time.monotonic()-start,max_parent_rss_bytes=rss,
            artifact_bytes=total_size(),paid_compute_dollars=0,all_output_parity_passed=True,model_states_unchanged=True,
            automatic_retries=0,finished_utc=now(),artifact_sha256={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file()}))
        print('LATENCY DIAGNOSTIC COMPLETE: '+report['decision'],flush=True)
    except BaseException as error:
        write_new(OUT/'failure.json',dict(error=repr(error),wall_seconds=time.monotonic()-start,automatic_retry=False,finished_utc=now()))
        raise

def verify():
    lock,sources=load_lock();execution=read(OUT/'execution.json')
    for p,h in execution['artifact_sha256'].items():
        if sha(OUT/p)!=h: raise ValueError('Artifact differs: '+p)
    for s in (0,1):
        plan=read(OUT/'timing-schedule.json')[str(s)]
        records=[json.loads(line) for line in (OUT/f'{s}-requests.jsonl').read_text(encoding='utf-8').splitlines()]
        process=read(OUT/f'{s}-execution.json')
        if len(records)!=len(plan) or process['counts']!=sum_work(plan) or process['state_before']!=process['state_after']: raise ValueError('Incomplete session')
        for expected,row in zip(plan,records):
            if any(row[k]!=v for k,v in expected.items()) or not row['parity'] or row['work']!=work(row): raise ValueError('Request receipt differs')
    if execution['status']!='complete' or execution['counts']['inputs']!=12408 or execution['counts']['encoder']!=0: raise ValueError('Execution incomplete')
    if any(execution['counts'][k]>v for k,v in lock['total_forward_caps'].items()): raise ValueError('Forward cap')
    print(json.dumps(dict(verified=True,counts=execution['counts'],artifact_hash_checks=len(execution['artifact_sha256']),
        protected_hash_checks=len(sources['protected_sha256']),outcome_replays=0,new_model_calls=0)))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=('run','worker','verify'))
    parser.add_argument('--commit');parser.add_argument('--session',type=int);parser.add_argument('--seconds',type=float)
    a=parser.parse_args()
    if a.mode=='run':run(a.commit)
    elif a.mode=='worker':worker(a.session,a.seconds)
    else:verify()
