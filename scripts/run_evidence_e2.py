"""One frozen E2 exact-text audit, followed by two paired timing processes."""
from datetime import datetime, timezone
import argparse
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time
import zipfile

for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'): os.environ[name]='4'
for name in ('HF_HUB_OFFLINE','TRANSFORMERS_OFFLINE'): os.environ[name]='1'
os.environ['TOKENIZERS_PARALLELISM']='false'
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from anytime_ncm.evidence_preflight import sha, write_new, minimum_coverage, mc_precision
from anytime_ncm.evidence_exact import make_schedule, analyze, FAMILY, TAIL
from anytime_ncm.wmt_data import StringRows, identity
from run_evidence_e1 import git, cached_inputs, parity, read

OUT=ROOT/'results/evidence_gaps/e2'
LOCK=ROOT/'docs/studies/evidence-gaps/e2-lock.json'
SOURCES=['scripts/run_evidence_e2.py','scripts/verify_evidence_e2.py','src/anytime_ncm/evidence_exact.py','tests/test_evidence_exact.py',
         'docs/studies/evidence-gaps/e2-protocol.md','docs/studies/evidence-gaps/e2-lock.json',
         'scripts/run_evidence_e1.py','src/anytime_ncm/evidence_timing.py','src/anytime_ncm/forced_wmt.py',
         'src/anytime_ncm/wmt_model.py','src/anytime_ncm/online.py','src/anytime_ncm/upstream_adapter.py',
         'src/anytime_ncm/target_encoding.py','src/anytime_ncm/evidence_preflight.py','src/anytime_ncm/stronger_s1.py',
         'src/anytime_ncm/wmt_data.py','src/anytime_ncm/wmt_metrics.py','src/anytime_ncm/wmt_policy.py',
         'configs/phase4_wmt_sources.json','third_party/ncm/models/next_concept.py','third_party/ncm/models/quant.py',
         'third_party/ncm/models/vqvae.py','third_party/ncm/scripts/eval_shard.py']


def prepare():
    protocol='docs/studies/evidence-gaps/e2-protocol.md'
    write_new(LOCK,dict(stage='E2-exact',base_commit='b78d666446707e43c31d54021c8519cb2678d89a',protocol=protocol,protocol_sha256=sha(ROOT/protocol),
        E0_manifest_sha256=sha(ROOT/'results/evidence_gaps/e0/input-manifest.json'),config_sha256=sha(ROOT/'configs/phase4_wmt_sources.json'),
        parent_manifest_sha256=sha(ROOT/'docs/partitions/wmt14-phase4.json'),E1_execution_sha256=sha(ROOT/'results/evidence_gaps/e1/execution.json'),
        collection_limits=dict(inputs=256,generator_levels=2816,decoder=2816,encoder=0),
        per_timing_process_limits=dict(inputs=6204,generator_levels=39809,decoder=11374,encoder=0),
        total_limits=dict(inputs=12664,generator_levels=82434,decoder=25564,encoder=0),
        model_wall_seconds=14400,analysis_wall_seconds=3600,conservative_setup_reporting_charge_seconds=10800,
        artifact_bytes=1073741824,analysis_rss_bytes=8589934592,paid_compute_dollars=0,
        bootstrap_draws=100000,seed=20261026,family_intervals=FAMILY,tail_alpha=TAIL,
        cue_zero_event_minimum_coverage=minimum_coverage(TAIL),mc_precision=mc_precision(100000,TAIL,FAMILY),
        forbidden_work=dict(target_encodings=0,fits=0,E3_inputs=0,E4_inputs=0,new_nonidentical_rules=0)))
    print('E2 exact protocol locked; zero new outcomes accessed.',flush=True)


def load_plan():
    lock=read(LOCK)
    for path,key in [(lock['protocol'],'protocol_sha256'),('results/evidence_gaps/e0/input-manifest.json','E0_manifest_sha256'),
                     ('configs/phase4_wmt_sources.json','config_sha256'),('docs/partitions/wmt14-phase4.json','parent_manifest_sha256'),
                     ('results/evidence_gaps/e1/execution.json','E1_execution_sha256')]:
        if sha(ROOT/path)!=lock[key]: raise ValueError('Frozen dependency differs: '+path)
    if read(ROOT/'results/evidence_gaps/e1/execution.json')['decision']!='cheaper_forced_path_observed_not_adaptive_speedup':
        raise ValueError('E1 cost entry gate not met')
    manifest=read(ROOT/'results/evidence_gaps/e0/input-manifest.json')
    entries=manifest['roles']['E2_audit'] if 'roles' in manifest else manifest['E2_audit']
    warm=manifest['E1_existing_exploration']
    if len(entries)!=256 or len(warm)!=16 or any(e['outcome_access_released'] for e in entries):
        raise ValueError('Sealed E0 roles differ')
    return lock,entries,warm


def collected(entries):
    rows=[json.loads(s) for s in (OUT/'trajectories.jsonl').read_text(encoding='utf-8').splitlines()]
    if [(r['identity'],r['index']) for r in rows]!=[(e['identity'],e['index']) for e in entries]: raise ValueError('Collected identities/order differ')
    return {r['index']:r for r in rows}


def worker(stage,seconds):
    import torch
    import transformers
    from anytime_ncm.wmt_model import WmtModel
    from anytime_ncm.forced_wmt import forced_request,ForwardCounter
    from anytime_ncm.target_encoding import model_fingerprint
    start=time.monotonic()
    lock,entries,warm=load_plan()
    started=read(OUT/'started.json')
    if any(sha(ROOT/p)!=digest for p,digest in started['source_sha256'].items()): raise ValueError('Execution source changed')
    if (sys.version_info[:3]!=(3,12,3) or torch.__version__!='2.10.0+cu128' or torch.version.cuda!='12.8'
            or transformers.__version__!='4.57.6' or not torch.cuda.is_available() or torch.cuda.get_device_name()!='NVIDIA GeForce RTX 5060'):
        raise RuntimeError('Material environment drift')
    torch.set_num_threads(4)
    allowed=entries if stage=='collection' else entries+warm
    sources=StringRows((ROOT/'data/wmt14/sources.pickle').read_bytes()).select({e['index'] for e in allowed})
    for e in entries:
        import hashlib
        if hashlib.sha256(sources[e['index']].encode()).hexdigest()!=e['source_text_sha256']: raise ValueError('Source text hash differs')
    cache=None
    if stage!='collection':
        cache=collected(entries)
        existing,_,_=cached_inputs(warm)
        cache.update(existing)
        expected_plan=make_schedule(entries,warm,cache)
        if read(OUT/'timing-schedule.json')!=expected_plan: raise ValueError('Timing schedule differs from frozen algorithm')
        plan=[r for r in expected_plan if r['block']==int(stage)]
        limits=lock['per_timing_process_limits']
    else:
        plan=[dict(request_id=i,index=e['index'],identity=e['identity'],depth=11,schedule='every_level') for i,e in enumerate(entries)]
        limits=lock['collection_limits']
    receipt=dict(stage=stage,pid=os.getpid(),started_utc=datetime.now(timezone.utc).isoformat(),completed_requests=0)
    write_new(OUT/f'{stage}-started.json',receipt)
    counter=None
    result=None
    try:
        loading=time.monotonic()
        model=WmtModel(ROOT)
        receipt['model_load_seconds']=time.monotonic()-loading
        receipt['environment']=dict(python=sys.version,torch=torch.__version__,cuda=torch.version.cuda,transformers=transformers.__version__,
            gpu=torch.cuda.get_device_name(),cpu_threads=torch.get_num_threads(),precision='float32/eval',
            tf32_matmul=torch.backends.cuda.matmul.allow_tf32,tf32_cudnn=torch.backends.cudnn.allow_tf32,
            free_total_device_bytes_before=list(torch.cuda.mem_get_info()))
        receipt['nvidia_smi']=subprocess.check_output(['nvidia-smi','--query-gpu=driver_version,name,memory.total','--format=csv,noheader'],text=True).strip()
        fingerprint=lambda:dict(generator=model_fingerprint(model.net),tokenizer=model_fingerprint(model.tokenizer.vqvae))
        receipt['state_before']=fingerprint()
        counter=ForwardCounter(model,limits)
        begin_event,end_event=torch.cuda.Event(enable_timing=True),torch.cuda.Event(enable_timing=True)
        with (OUT/f'{stage}-starts.jsonl').open('x',encoding='utf-8',newline='\n') as ledger,(OUT/f'{stage}-requests.jsonl').open('x',encoding='utf-8',newline='\n') as stream:
            trajectory_stream=(OUT/'trajectories.jsonl').open('x',encoding='utf-8',newline='\n') if stage=='collection' else None
            try:
                for number,request in enumerate(plan):
                    if time.monotonic()-start>seconds: raise RuntimeError('E2 model wall cap')
                    prefix=model.official['prefix'](sources[request['index']])
                    if identity(prefix)!=request['identity']: raise ValueError('Source effective-prefix identity differs before forward')
                    before=dict(counter.counts)
                    counter.take('inputs')
                    ledger.write(json.dumps(dict(request,work_before=before,request_count=counter.counts['inputs']))+'\n');ledger.flush()
                    torch.cuda.synchronize();torch.cuda.reset_peak_memory_stats();torch.manual_seed(20261023)
                    result=None
                    wall_start=time.perf_counter_ns();begin_event.record()
                    result=forced_request(model,sources[request['index']],request['depth'],request['schedule'])
                    end_event.record();torch.cuda.synchronize()
                    wall_ms=(time.perf_counter_ns()-wall_start)/1e6
                    work={k:counter.counts[k]-before[k] for k in before}
                    expected=dict(inputs=1,generator_levels=request['depth'],decoder=request['depth'] if request['schedule']=='every_level' else 1,encoder=0)
                    if work!=expected: raise ValueError('Actual work differs')
                    if stage=='collection':
                        trajectory=dict(identity=request['identity'],index=request['index'],partition='E2_audit',prefix_ids=result['prefix_ids'],codes=result['codes'][0].cpu().tolist(),levels=result['observations'])
                        # Collection is the once-only source of new outcomes; later native full/forced calls validate it.
                        hashes=parity(result,trajectory,request)
                        trajectory_stream.write(json.dumps(trajectory,ensure_ascii=True)+'\n');trajectory_stream.flush()
                    else: hashes=parity(result,cache[request['index']],request)
                    stream.write(json.dumps(dict(request,wall_ms=wall_ms,cuda_stream_span_ms=begin_event.elapsed_time(end_event),
                        peak_allocated_bytes=torch.cuda.max_memory_allocated(),peak_reserved_bytes=torch.cuda.max_memory_reserved(),work=work,parity=True,**hashes),allow_nan=False)+'\n');stream.flush()
                    receipt['completed_requests']+=1
                    if number%128==0 or number+1==len(plan):
                        if sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file())>lock['artifact_bytes']: raise RuntimeError('E2 artifact cap')
                        print(f'E2 {stage}: {number+1}/{len(plan)} requests; work/parity accepted',flush=True)
            finally:
                if trajectory_stream: trajectory_stream.close()
        receipt['state_after']=fingerprint()
        if receipt['state_before']!=receipt['state_after'] or counter.counts['inputs']!=limits['inputs']: raise RuntimeError('State/request completion failure')
        receipt.update(status='complete',counts=dict(counter.counts),actual_forward_calls=dict(counter.calls),wall_seconds=time.monotonic()-start,
            max_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,finished_utc=datetime.now(timezone.utc).isoformat())
        write_new(OUT/f'{stage}-execution.json',receipt)
    except Exception as error:
        receipt.update(status='failed',error=type(error).__name__+': '+str(error),counts=dict(counter.counts) if counter else {},wall_seconds=time.monotonic()-start)
        if result is not None: write_new(OUT/f'{stage}-failure-output.json',dict(request=request,prefix_ids=result['prefix_ids'],codes=result['codes'][0].cpu().tolist(),observations=result['observations']))
        write_new(OUT/f'{stage}-failure.json',receipt)
        raise
    finally:
        if counter: counter.close()


def run(remote):
    start=time.monotonic()
    if git('rev-parse','HEAD')!=remote or git('branch','--show-current')!='main' or git('status','--porcelain'): raise ValueError('Need clean source lock main/remote equality')
    if git('ls-remote','origin','refs/heads/main').split()[0]!=remote: raise ValueError('Live remote differs')
    if git('rev-parse','HEAD',directory=ROOT/'third_party/ncm')!='c70274273f489abc73832b2b98584a8483b6b203': raise ValueError('Upstream differs')
    lock,entries,warm=load_plan()
    OUT.mkdir(parents=True,exist_ok=False)
    started=dict(stage='E2-exact',source_commit=remote,started_utc=datetime.now(timezone.utc).isoformat(),source_sha256={p:sha(ROOT/p) for p in SOURCES})
    write_new(OUT/'started.json',started)
    try:
        config=read(ROOT/'configs/phase4_wmt_sources.json')
        for path,info in config['files'].items():
            if sha(ROOT/path)!=info['sha256'] or (ROOT/path).stat().st_size!=info['size']: raise ValueError('Pinned asset differs: '+path)
        write_new(OUT/'preflight.json',dict(config_sha256=sha(ROOT/'configs/phase4_wmt_sources.json'),assets_sha256={p:i['sha256'] for p,i in config['files'].items()},E0_manifest_sha256=lock['E0_manifest_sha256']))
        with zipfile.ZipFile(OUT/'execution-sources.zip','x',compression=zipfile.ZIP_DEFLATED) as z:
            for p in SOURCES: z.writestr(p,(ROOT/p).read_bytes())
            z.writestr('manifest.json',json.dumps(started,indent=2))
        write_new(OUT/'access-release.json',dict(stage='E2-exact',released_utc=datetime.now(timezone.utc).isoformat(),source_commit=remote,
            E0_manifest_sha256=lock['E0_manifest_sha256'],role='E2_audit',entries=entries,source_access=True,new_trajectory_access=True,
            references_access=True,E3_released=False,E4_released=False,prior_exposure='official aggregate baseline and E0 source-only hashes; unknown training/document overlap'))
        for stage in ('collection','0','1'):
            remaining=lock['model_wall_seconds']-(time.monotonic()-start)
            if remaining<=0: raise RuntimeError('E2 model execution cap')
            subprocess.run([sys.executable,str(Path(__file__).resolve()),'--worker',stage,'--worker-seconds',str(remaining)],cwd=ROOT,check=True,timeout=remaining)
            if stage=='collection':
                cache=collected(entries);existing,_,_=cached_inputs(warm);cache.update(existing)
                write_new(OUT/'timing-schedule.json',make_schedule(entries,warm,cache))
        model_seconds=time.monotonic()-start
        processes=[read(OUT/f'{stage}-execution.json') for stage in ('collection','0','1')]
        if len({p['pid'] for p in processes})!=3: raise RuntimeError('Distinct process sessions required')
        counts={k:sum(p['counts'][k] for p in processes) for k in lock['total_limits']}
        if counts['inputs']!=12664 or any(counts[k]>v for k,v in lock['total_limits'].items()): raise RuntimeError('Total work failure')
        rows=collected(entries)
        references=StringRows((ROOT/'data/wmt14/reference_translations.pickle').read_bytes()).select({e['index'] for e in entries})
        write_new(OUT/'reference-access.json',dict(role='E2_audit',indices=sorted(references),materializations_per_reference=1,other_roles_accessed=0))
        records=[json.loads(s) for b in range(2) for s in (OUT/f'{b}-requests.jsonl').read_text().splitlines()]
        report=analyze(rows,entries,[references[e['index']] for e in entries],records,read(OUT/'timing-schedule.json'),lock['analysis_wall_seconds'],lock['bootstrap_draws'])
        write_new(OUT/'analysis.json',report)
        rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        size=sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file())
        if rss>lock['analysis_rss_bytes'] or size>lock['artifact_bytes']: raise RuntimeError('Analysis resource cap')
        write_new(OUT/'execution.json',dict(status='complete',source_commit=remote,counts=counts,model_orchestration_wall_seconds=model_seconds,
            analysis_wall_seconds=report['analysis_wall_seconds'],conservative_setup_reporting_charge_seconds=10800,analysis_max_rss_bytes=rss,artifact_bytes=size,
            process_ids=[p['pid'] for p in processes],new_audit_input_outcomes=256,new_audit_references=256,E3_inputs=0,E4_inputs=0,fits=0,target_encodings=0,
            paid_compute_dollars=0,all_parity_passed=True,model_states_unchanged=True,decision=report['decision'],
            artifact_sha256={p.name:sha(p) for p in OUT.iterdir() if p.is_file()}))
        print('E2 COMPLETE:',report['decision'],counts,flush=True)
    except Exception as error:
        write_new(OUT/'failure.json',dict(error=type(error).__name__+': '+str(error),wall_seconds=time.monotonic()-start,automatic_retry=False))
        raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare',action='store_true');parser.add_argument('--remote-head')
    parser.add_argument('--worker',choices=('collection','0','1'));parser.add_argument('--worker-seconds',type=float)
    args=parser.parse_args()
    if args.prepare: prepare()
    elif args.worker is not None:
        if not args.worker_seconds or args.worker_seconds<=0: raise ValueError('Positive remaining wall allocation required')
        worker(args.worker,args.worker_seconds)
    elif args.remote_head: run(args.remote_head)
    else: parser.error('Supply --remote-head only after the source lock push')
