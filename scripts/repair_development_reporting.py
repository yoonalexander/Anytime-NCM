"""Reporting-only repair: verify preserved phase07traces; no inference/reference scoring."""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='1'
os.environ['PYTHONDONTWRITEBYTECODE']='1'
import argparse,json,math,signal,subprocess,sys,time,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from run_signal_discrimination import git,cpu,rss,now,hashes_ok
from run_development_collection import support,key
from anytime_ncm.evidence_preflight import sha,write_new
from anytime_ncm.development_reporting import plain
from anytime_ncm.controller_study import cache_row
from anytime_ncm.quality_campaign import campaign_root,verify_campaign,record_phase,usage_zero
BASE=ROOT/'docs/studies/quality-tolerant';CAMPAIGN=campaign_root(ROOT);ORIGINAL=CAMPAIGN/'development_collection';OUT=CAMPAIGN/'development_collection_reporting';PRIVATE=ROOT/'data/quality_tolerant_campaign_20261029/development_collection'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def size():return sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file())
def load():
    lock=read(BASE/'development-reporting-lock.json');source=read(BASE/'development-reporting-source-lock.json');hashes_ok(source['source_sha256']);hashes_ok(source['protected_sha256']);hashes_ok(source['preserved_private_sha256'])
    if git('-C','third_party/ncm','rev-parse','HEAD')!=source['upstream_commit'] or git('-C','third_party/ncm','status','--porcelain'):raise ValueError('Upstream changed')
    return lock,source

def run(commit):
    started=time.monotonic();lock,source=load();verify_campaign(ROOT,lock['campaign_reservation'])
    if git('rev-parse','HEAD')!=commit or git('branch','--show-current')!='main' or git('status','--porcelain') or git('ls-remote','origin','refs/heads/main').split()[0]!=commit:raise ValueError('Need clean main at pushed reporting lock')
    OUT.mkdir(parents=True,exist_ok=False);write_new(OUT/'started.json',dict(source_commit=commit,started_utc=now(),new_model_work=False))
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('Reporting repair wall cap')));signal.setitimer(signal.ITIMER_REAL,lock['wall_seconds'])
    try:
        with zipfile.ZipFile(OUT/'execution-sources.zip','x',compression=zipfile.ZIP_DEFLATED) as z:
            for p in source['source_sha256']:z.writestr(p,(ROOT/p).read_bytes())
            z.writestr('source-lock.json',json.dumps(source,indent=2))
        with (OUT/'synthetic-tests.log').open('x',encoding='utf-8',newline='\n') as log:
            test=subprocess.run([sys.executable,'-m','pytest','tests/test_development_reporting.py','-q','-p','no:cacheprovider','--junitxml=results/quality_tolerant/campaign_20261029/development_collection_reporting/synthetic-tests.xml'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=lock['test_wall_seconds'])
        if test.returncode:raise RuntimeError('Synthetic reporting repair failed before saved outcome replay')
        worker=read(ORIGINAL/'worker-execution.json');failure=read(ORIGINAL/'failure.json');old_lock=read(BASE/'development-collection-lock.json');allocation=read(CAMPAIGN/'development_eligibility/source-only-allocation.json');entries=sorted(allocation['parts']['development_fit']+allocation['parts']['development_calibration'],key=lambda e:(e['year'],e['index']));allowed={key(e):e for e in entries}
        if len(entries)!=4299 or worker['status']!='complete' or worker['counts']!=old_lock['forward_caps'] or worker['feature_counts']!=old_lock['feature_caps'] or worker['state_before']!=worker['state_after'] or worker['prefix_calls']!=8603 or worker['reference_cache_opened']:raise ValueError('Original worker incomplete or invalid')
        if failure['error']!="TypeError('Object of type bool is not JSON serializable')" or not failure['conservative_reservation_charge']:raise ValueError('Different original failure')
        if worker['max_rss_bytes']>old_lock['worker_rss_bytes'] or worker['wall_seconds']>old_lock['model_wall_seconds'] or sum(p.stat().st_size for d in (ORIGINAL,PRIVATE) for p in d.rglob('*') if p.is_file())>old_lock['artifact_bytes']:raise ValueError('Recorded worker/storage cap exceeded')
        expected_counts=dict(source_segment_headers=13955,reference_segment_headers=13955,source_body_decodes=4299,reference_body_decodes=4299,new_trace_bodies=4304,sentence_label_pairs=12897)
        if any(failure['counts'][k]!=v for k,v in expected_counts.items()):raise ValueError('Original parent data/label work incomplete')
        plan=read(ORIGINAL/'collection-plan.json');public=[json.loads(line) for line in (ORIGINAL/'requests.jsonl').read_text(encoding='utf-8').splitlines()];cache=read(ORIGINAL/'parity-hashes.json')
        if len(plan)!=4304 or len(public)!=4304 or len(cache)!=4299:raise ValueError('Incomplete saved public records')
        private_count=0;nonwarm=set();sums=dict(inputs=0,generator_levels=0,decoder=0,encoder=0)
        with (PRIVATE/'trajectories.jsonl').open(encoding='utf-8') as stream:
            for number,line in enumerate(stream):
                if number>=4304:raise ValueError('Extra private trace')
                private=json.loads(line);r=public[number];p=plan[number];private_count+=1
                if any(r[k]!=v or private[k]!=v for k,v in p.items()) or key(r) not in allowed or any(r[k]!=allowed[key(r)][k] for k in ('identity','component','role')):raise ValueError('Saved trace allocation mismatch')
                if r['work']!=dict(inputs=1,generator_levels=11,decoder=12,encoder=0) or r['feature_work']!=dict(cheap_features=2,selected_logit_features=2,cue_features=2) or not r['native_final_parity'] or not private['native_final_parity']:raise ValueError('Saved work/native parity failed')
                if len(private['prefix_ids'])!=96 or len(private['codes'])!=313 or [o['level'] for o in private['levels']]!=list(range(1,12)) or any(len(o['ids'])!=64 for o in private['levels']):raise ValueError('Invalid saved prefix/output shape')
                if cache_row(private)!=r['hashes'] or private['features']!=r['features'] or [v['level'] for v in r['features']]!=[8,10] or any(len(v['values'])!=27 or not all(math.isfinite(x) for x in v['values']) for v in r['features']):raise ValueError('Private/public prefix-feature binding failed')
                if r['peak_reserved_bytes']>min(old_lock['gpu_reserved_bytes'],worker['environment']['physical_gpu_bytes']):raise ValueError('Recorded GPU cap exceeded')
                if not r['warmup']:
                    k=key(r)
                    if k in nonwarm or r['hashes']!=cache[k]:raise ValueError('Duplicate/nonmatching saved nonwarm trace')
                    nonwarm.add(k)
                for k,v in r['work'].items():sums[k]+=v
        if private_count!=4304 or nonwarm!=set(allowed) or sums!=worker['counts'] or sum(r['warmup'] for r in public)!=5:raise ValueError('Saved population/work incomplete')
        targets=read(ORIGINAL/'proxy-labels.json')
        if set(targets)!=set(allowed):raise ValueError('Saved label allocation differs')
        for values in targets.values():
            if set(values)!={'8','10'}:raise ValueError('Wrong saved label levels')
            for row in values.values():
                if len(row)!=4 or any((v is None and t!=2) or (v is not None and (type(v)not in (int,float) or not math.isfinite(v))) for t,v in enumerate(row)):raise ValueError('Invalid/missing saved endpoint')
        labels=plain(support(targets,entries));write_new(OUT/'label-support.json',labels)
        decision=dict(status='joint_development_collection_supported' if labels['joint_controller_development_supported'] else 'development_labels_inadequate',next_branch='prospectively_lock_bounded_fitting_and_selection' if labels['joint_controller_development_supported'] else 'bounded_existing_data_family2_or_closeout',cue_endpoint_head_sanity_floor_passed=labels['fit_cue_endpoint_heads_meet_5each_sanity_floor'],Q0_passed=False,independent_confirmation=False,evaluation_outcomes_released=False,quality_guarantee=False,original_attempt_reporting_failure_preserved=True)
        write_new(OUT/'decision.json',decision)
        if any(k=='torch' or k.startswith('torch.') or k=='transformers' or k.startswith('transformers.') for k in sys.modules):raise ValueError('Unexpected model framework import')
        hashes_ok(source['protected_sha256']);hashes_ok(source['preserved_private_sha256'])
        if time.monotonic()-started>lock['wall_seconds'] or cpu()>lock['execution_cpu_cap_seconds'] or rss()>lock['parent_rss_bytes'] or size()>lock['artifact_bytes']:raise RuntimeError('Reporting resource cap')
        usage=usage_zero();usage.update(cpu_seconds=cpu()+lock['reporting_cpu_charge_seconds'],artifact_bytes=lock['artifact_bytes']);verify_campaign(ROOT,usage)
        write_new(OUT/'completion.json',dict(status='saved_collection_verified_reporting_repaired',original_source_commit='e26967e7bc8e457fd48f22aec84e886f724bd81c',reporting_source_commit=commit,original_failure_sha256=sha(ORIGINAL/'failure.json'),partial_original_label_support_sha256=sha(ORIGINAL/'label-support.json'),actual_known_original_model_attempts=4307,original_charged_model_attempts=4312,original_real_forward_counts=sums,private_public_trace_hash_bindings=4304,nonwarm_label_rows=4299,reference_rescoring=0,new_model_work=0,original_parent_final_resource_gate_reached=False,original_parent_actual_final_cpu_receipt_available=False,original_full_reservation_charge_preserved=True,new_label_support_sha256=sha(OUT/'label-support.json')))
        write_new(OUT/'execution.json',dict(status='complete',source_commit=commit,new_model_requests=0,new_checkpoint_loads=0,new_reference_or_source_payload_decodes=0,new_reference_scores=0,new_fits=0,new_controller_families=0,target_encodings=0,bootstrap_draws=0,simulations=0,saved_private_trace_body_reads=4304,saved_public_trace_records=4304,saved_label_rows=4299,original_worker_cpu_seconds=worker['cpu_seconds'],original_worker_wall_seconds=worker['wall_seconds'],original_worker_max_rss_bytes=worker['max_rss_bytes'],original_combined_public_private_bytes=sum(p.stat().st_size for d in (ORIGINAL,PRIVATE) for p in d.rglob('*') if p.is_file()),total_wall_seconds=time.monotonic()-started,cpu_seconds_before_reporting_charge=cpu(),max_parent_rss_bytes=rss(),campaign_usage=usage,automatic_retries=0,paid_dollars=0,finished_utc=now(),artifact_sha256={p.relative_to(OUT).as_posix():sha(p) for p in OUT.rglob('*') if p.is_file()}))
        print(json.dumps(record_phase(ROOT,'07r-development-reporting','development_collection_reporting/execution.json')),flush=True);print('DEVELOPMENT REPORTING REPAIR COMPLETE: '+decision['status'],flush=True)
    except BaseException as error:
        failure=OUT/'failure.json'
        if not failure.exists():write_new(failure,dict(error=repr(error),campaign_usage=lock['campaign_reservation'],conservative_reservation_charge=True,automatic_retry=False))
        if not (CAMPAIGN/'accounting/phase-07r-development-reporting.json').exists():record_phase(ROOT,'07r-development-reporting','development_collection_reporting/failure.json')
        raise
    finally:signal.setitimer(signal.ITIMER_REAL,0)

def verify():
    lock,source=load();e=read(OUT/'execution.json');hashes_ok({('results/quality_tolerant/campaign_20261029/development_collection_reporting/'+p):h for p,h in e['artifact_sha256'].items()});c=read(OUT/'completion.json')
    if e['status']!='complete' or e['new_model_requests'] or e['new_reference_scores'] or e['new_fits'] or c['original_failure_sha256']!=sha(ORIGINAL/'failure.json') or c['new_label_support_sha256']!=sha(OUT/'label-support.json') or c['private_public_trace_hash_bindings']!=4304:raise ValueError('Invalid reporting repair receipt')
    print(json.dumps(dict(verified=True,protected_files=len(source['protected_sha256']),original_failure_preserved=True,new_inference_or_fitting_or_reference_scoring=0,campaign=verify_campaign(ROOT))))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=('run','verify'));p.add_argument('--commit');a=p.parse_args();run(a.commit) if a.mode=='run' else verify()
