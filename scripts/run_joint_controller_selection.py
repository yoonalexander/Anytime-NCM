"""Once-only selection among fixed family1 stopping candidates; no real model calls."""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='4'
os.environ['PYTHONDONTWRITEBYTECODE']='1'
import argparse,json,resource,signal,subprocess,sys,time,zipfile
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from anytime_ncm.evidence_preflight import sha,write_new
from anytime_ncm.quality_controller import Meter,point_losses,point_pass
from anytime_ncm.controller_study import selected_rows
from anytime_ncm.joint_risk_controller import candidates,replay,estimated_cost,select
from anytime_ncm.quality_campaign import campaign_root,verify_campaign,record_phase,usage_zero
from anytime_ncm.wmt_data import StringRows
from anytime_ncm.wmt_metrics import scores
BASE=ROOT/'docs/studies/quality-tolerant';CAMPAIGN=campaign_root(ROOT);PREV=CAMPAIGN/'signal_discrimination';OUT=CAMPAIGN/'joint_controller_selection'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def git(*a):return subprocess.check_output(['git.exe',*a],cwd=ROOT,text=True,timeout=60).strip()
def now():return datetime.now(timezone.utc).isoformat()
def cpu():
    a=resource.getrusage(resource.RUSAGE_SELF);b=resource.getrusage(resource.RUSAGE_CHILDREN);return a.ru_utime+a.ru_stime+b.ru_utime+b.ru_stime
def rss():return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
def size():return sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file())
def hashes_ok(values):
    for p,h in values.items():
        if sha(ROOT/p)!=h:raise ValueError('Frozen bytes changed: '+p)
def load():
    lock=read(BASE/'joint-controller-selection-lock.json');source=read(BASE/'joint-controller-selection-source-lock.json');hashes_ok(source['source_sha256']);hashes_ok(source['protected_sha256'])
    if git('-C','third_party/ncm','rev-parse','HEAD')!=source['upstream_commit'] or git('-C','third_party/ncm','status','--porcelain'):raise ValueError('Upstream changed')
    return lock,source

def run(commit):
    started=time.monotonic();lock,source=load();verify_campaign(ROOT,lock['campaign_reservation'])
    if git('rev-parse','HEAD')!=commit or git('branch','--show-current')!='main' or git('status','--porcelain') or git('ls-remote','origin','refs/heads/main').split()[0]!=commit:raise ValueError('Need clean pushed main at source lock')
    OUT.mkdir(parents=True,exist_ok=False);write_new(OUT/'started.json',dict(source_commit=commit,started_utc=now()))
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('Selection wall cap')));signal.setitimer(signal.ITIMER_REAL,lock['wall_seconds']);meter=None
    try:
        with zipfile.ZipFile(OUT/'execution-sources.zip','x',compression=zipfile.ZIP_DEFLATED) as z:
            for p in source['source_sha256']:z.writestr(p,(ROOT/p).read_bytes())
            z.writestr('source-lock.json',json.dumps(source,indent=2))
        with (OUT/'synthetic-tests.log').open('x',encoding='utf-8',newline='\n') as log:
            test=subprocess.run([sys.executable,'-m','pytest','tests/test_joint_risk_controller.py','-q','-s','-p','no:cacheprovider','--junitxml=results/quality_tolerant/campaign_20261029/joint_controller_selection/synthetic-tests.xml'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=lock['test_wall_seconds'])
        if test.returncode:raise RuntimeError('Synthetic validation failed before calibration access')
        split=read(BASE/'controller-split.json');entries=sorted(split['parts']['calibration'],key=lambda e:e['index']);all_entries=[e for es in split['parts'].values() for e in es]
        write_new(OUT/'access-release.json',dict(entries=entries,old_trajectory_bodies=101,reference_bodies=101,prior_feature_records=366,old_test87_released=False,reserved_outputs_released=False,selection_is_consumed_development=True))
        with (OUT/'access-ledger.jsonl').open('x',encoding='utf-8',newline='\n') as stream:
            meter=Meter(lock['analysis_caps'],stream);rows=[]
            for origins,path in [(('exploration','development'),'results/phase4/wmt14/trajectories.jsonl'),(('E2_audit',),'results/evidence_gaps/e2/trajectories.jsonl')]:rows.extend(selected_rows(ROOT/path,[e for e in entries if e['origin'] in origins],[e for e in all_entries if e['origin'] in origins],meter))
            rows.sort(key=lambda r:r['index']);indices=[e['index'] for e in entries]
            if [r['index'] for r in rows]!=indices:raise ValueError('Incomplete calibration population')
            meter.take('reference_materializations',101);reference=StringRows((ROOT/'data/wmt14/reference_translations.pickle').read_bytes()).select(set(indices));refs=[reference[i] for i in indices]
            records=[]
            for line in (PREV/'requests.jsonl').read_text(encoding='utf-8').splitlines():meter.take('saved_feature_records');records.append(json.loads(line))
            by={r['index']:r for r in records if not r['warmup']}
            if len(records)!=366 or len(by)!=361 or not set(indices)<=set(by):raise ValueError('Missing saved features')
            models=read(PREV/'models.json');specs=candidates(models)
            if len(specs)>81:raise ValueError('Candidate cap')
            profile=lock['fixed_profile_ms'];profile={int(k):v for k,v in profile.items()};reports=[]
            def score(hyps):meter.take('corpus_scores');return scores(hyps,refs)
            full=score([r['levels'][-1]['text'] for r in rows])
            for spec in specs:
                assignments=[replay(spec,by[r['index']],meter) for r in rows]
                metric=full if spec['kind']=='full' else score([r['levels'][d-1]['text'] for r,(d,visits) in zip(rows,assignments)])
                estimate=estimated_cost(spec,assignments,profile,lock['observation_proxy_ms'],lock['extra_per_decision_ms'])
                reports.append(dict(name=spec['name'],metrics=metric,losses=point_losses(metric,full),point_pass=point_pass(metric,full),estimated_mean_ms=estimate,estimated_saving=(profile[11]-estimate)/profile[11],
                    optimistic_no_observation_mean_ms=sum(profile[d] for d,v in assignments)/101,early_inputs=sum(d<11 for d,v in assignments),exits={str(d):sum(x[0]==d for x in assignments) for d in (8,10,11)},assignments=[dict(index=i,depth=d,visits=v) for i,(d,v) in zip(indices,assignments)]))
            fixed=[]
            for d in range(1,12):
                metric=full if d==11 else score([r['levels'][d-1]['text'] for r in rows])
                fixed.append(dict(method='fixed:'+str(d),metrics=metric,losses=point_losses(metric,full),point_pass=point_pass(metric,full),profile_mean_ms=profile[d],adjusted_quality_exclusion=False))
            selected=select(reports,profile[11]);comparator=min((r for r in fixed if r['point_pass']),key=lambda r:(r['profile_mean_ms'],r['method']))['method']
            spec=next(s for s in specs if s['name']==selected['selected'])
            write_new(OUT/'candidate-specs.json',specs);write_new(OUT/'candidate-results.json',dict(candidates=reports,fixed=fixed,full=full,selection=selected,locked_fixed_comparator=comparator,all_fixed_controls_remain_potentially_feasible_for_inference=True))
            write_new(OUT/'policy.json',dict(policy=spec,locked_fixed_comparator=comparator,source_commit=commit,models_source_sha256=sha(PREV/'models.json'),calibration_inputs=101,evaluation_outcomes_seen_for_selection=0,
                independent_confirmation=False,Q0_passed=False,ready_for_allocated_evaluation=selected['ready_for_allocated_evaluation'],all_fixed_controls_required=True))
        hashes_ok(source['protected_sha256']);hashes_ok(source['source_sha256'])
        if time.monotonic()-started>lock['wall_seconds'] or cpu()>lock['execution_cpu_cap_seconds'] or rss()>lock['parent_rss_bytes'] or size()>lock['artifact_bytes']:raise RuntimeError('Selection resource cap')
        usage=usage_zero();usage.update(cpu_seconds=cpu()+lock['reporting_cpu_charge_seconds'],artifact_bytes=lock['artifact_bytes']);verify_campaign(ROOT,usage)
        write_new(OUT/'decision.json',dict(selected,locked_fixed_comparator=comparator,actual_speedup_established=False,old_test87_released=False,reserved_outputs_released=False))
        write_new(OUT/'execution.json',dict(status='complete',source_commit=commit,analysis_counts=meter.counts,candidate_count=len(specs),selected_policy_sha256=sha(OUT/'policy.json'),new_fits=0,new_controller_families=0,model_requests=0,checkpoint_loads=0,target_encodings=0,synthetic_model_requests=0,synthetic_fits=0,
            total_wall_seconds=time.monotonic()-started,cpu_seconds_before_reporting_charge=cpu(),max_parent_rss_bytes=rss(),artifact_bytes_before_reporting=size(),campaign_usage=usage,automatic_retries=0,paid_compute_dollars=0,finished_utc=now(),artifact_sha256={p.relative_to(OUT).as_posix():sha(p) for p in OUT.rglob('*') if p.is_file()}))
        print(json.dumps(record_phase(ROOT,'04-joint-controller-selection','joint_controller_selection/execution.json')),flush=True);print('JOINT SELECTION COMPLETE: '+selected['selected']+'; '+selected['status'],flush=True)
    except BaseException as error:
        failure=OUT/'failure.json'
        if not failure.exists():write_new(failure,dict(error=repr(error),partial_counts=meter.counts if meter else {},campaign_usage=lock['campaign_reservation'],conservative_reservation_charge=True,automatic_retry=False))
        if not (CAMPAIGN/'accounting/phase-04-joint-controller-selection.json').exists():record_phase(ROOT,'04-joint-controller-selection','joint_controller_selection/failure.json')
        raise
    finally:signal.setitimer(signal.ITIMER_REAL,0)

def verify():
    lock,source=load();e=read(OUT/'execution.json');hashes_ok({('results/quality_tolerant/campaign_20261029/joint_controller_selection/'+p):h for p,h in e['artifact_sha256'].items()})
    report=read(OUT/'candidate-results.json');policy=read(OUT/'policy.json');specs=read(OUT/'candidate-specs.json')
    if e['status']!='complete' or e['candidate_count']!=len(specs) or e['candidate_count']>81 or sha(OUT/'policy.json')!=e['selected_policy_sha256'] or e['new_fits'] or e['model_requests']:raise ValueError('Invalid selection receipt')
    if select(report['candidates'],lock['fixed_profile_ms']['11'])!=report['selection'] or policy['policy']['name']!=report['selection']['selected']:raise ValueError('Selection differs')
    if e['analysis_counts']['trajectory_bodies']!=101 or e['analysis_counts']['reference_materializations']!=101 or e['analysis_counts']['saved_feature_records']!=366:raise ValueError('Access differs')
    print(json.dumps(dict(verified=True,protected_files=len(source['protected_sha256']),selected=policy['policy']['name'],ready_for_allocated_evaluation=policy['ready_for_allocated_evaluation'],campaign=verify_campaign(ROOT),new_inference_or_fitting=0)))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=('run','verify'));p.add_argument('--commit');a=p.parse_args();run(a.commit) if a.mode=='run' else verify()
