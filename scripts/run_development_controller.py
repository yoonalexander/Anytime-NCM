"""Final bounded development fitting/ablation/selection; evaluation outcomes stay closed."""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='4'
os.environ['PYTHONDONTWRITEBYTECODE']='1'
import argparse,json,math,signal,subprocess,sys,time,zipfile,importlib.metadata
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from run_signal_discrimination import git,cpu,rss,now,hashes_ok
from anytime_ncm.evidence_preflight import sha,write_new
from anytime_ncm.development_reporting import plain
from anytime_ncm.development_models import COLUMNS,fit_model,predict_model,candidate_specs
from anytime_ncm.development_selection import key,select_private,replay_scores,estimated_cost
from anytime_ncm.signal_discrimination import labels,diagnose
from anytime_ncm.quality_controller import Meter,point_losses,point_pass
from anytime_ncm.wmt_metrics import scores
from anytime_ncm.quality_campaign import campaign_root,verify_campaign,record_phase,usage_zero
BASE=ROOT/'docs/studies/quality-tolerant';CAMPAIGN=campaign_root(ROOT);DATA=CAMPAIGN/'development_collection';OUT=CAMPAIGN/'development_controller';PRIVATE=ROOT/'data/quality_tolerant_campaign_20261029/development_collection'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,v):write_new(p,plain(v))
def size():return sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file())
def load():
    lock=read(BASE/'development-controller-lock.json');source=read(BASE/'development-controller-source-lock.json');hashes_ok(source['source_sha256']);hashes_ok(source['protected_sha256']);hashes_ok(source['private_input_sha256'])
    if git('-C','third_party/ncm','rev-parse','HEAD')!=source['upstream_commit'] or git('-C','third_party/ncm','status','--porcelain'):raise ValueError('Upstream changed')
    return lock,source

def run(commit):
    started=time.monotonic();lock,source=load();verify_campaign(ROOT,lock['campaign_reservation'])
    if git('rev-parse','HEAD')!=commit or git('branch','--show-current')!='main' or git('status','--porcelain') or git('ls-remote','origin','refs/heads/main').split()[0]!=commit:raise ValueError('Need clean main at pushed final fitting lock')
    OUT.mkdir(parents=True,exist_ok=False);save(OUT/'started.json',dict(source_commit=commit,started_utc=now()))
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('Final development fitting wall cap')));signal.setitimer(signal.ITIMER_REAL,lock['wall_seconds']);meter=Meter(lock['analysis_caps']);models={}
    try:
        with zipfile.ZipFile(OUT/'execution-sources.zip','x',compression=zipfile.ZIP_DEFLATED) as z:
            for p in source['source_sha256']:z.writestr(p,(ROOT/p).read_bytes())
            z.writestr('source-lock.json',json.dumps(source,indent=2))
        if sys.version_info[:3]!=(3,12,3) or any(importlib.metadata.version(k)!=v for k,v in lock['versions'].items()):raise RuntimeError('Pinned fitting/metric environment drift')
        with (OUT/'synthetic-tests.log').open('x',encoding='utf-8',newline='\n') as log:
            test=subprocess.run([sys.executable,'-m','pytest','tests/test_development_models.py','tests/test_development_selection.py','-q','-s','-p','no:cacheprovider','--basetemp=results/quality_tolerant/campaign_20261029/development_controller/pytest-tmp','--junitxml=results/quality_tolerant/campaign_20261029/development_controller/synthetic-tests.xml'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=lock['test_wall_seconds'])
        if test.returncode:raise RuntimeError('Synthetic model/access tests failed before fitting/outcome replay')
        if 'SYNTHETIC_DEVELOPMENT_FITS 4' not in (OUT/'synthetic-tests.log').read_text(encoding='utf-8'):raise ValueError('Missing toy fit count')
        ready=read(CAMPAIGN/'development_collection_reporting/label-support.json')
        if not ready['joint_controller_development_supported']:raise ValueError('Original collection support gate failed')
        allocation=read(CAMPAIGN/'development_eligibility/source-only-allocation.json');fit=sorted(allocation['parts']['development_fit'],key=lambda e:(e['year'],e['index']));cal=sorted(allocation['parts']['development_calibration'],key=lambda e:(e['year'],e['index']));entries=fit+cal
        fit_keys=[key(e) for e in fit];cal_keys=[key(e) for e in cal];allowed={key(e):e for e in entries}
        if len(fit)!=3408 or len(cal)!=891 or len(allowed)!=4299:raise ValueError('Fixed development allocation mismatch')
        save(OUT/'access-release.json',dict(fit_entries=fit,calibration_entries=cal,development_evaluation1188_released=False,proposed_confirmation7700_released=False,old87_E3_E4_unallocated_released=False,training_only_on_fit=True,selection_on_consumed_calibration=True))
        records={}
        for line in (DATA/'requests.jsonl').read_text(encoding='utf-8').splitlines():
            meter.take('saved_feature_records');r=json.loads(line)
            if r['warmup']:continue
            k=key(r)
            if k not in allowed or k in records or r['identity']!=allowed[k]['identity'] or r['role']!=allowed[k]['role']:raise ValueError('Saved feature allocation mismatch')
            records[k]=r
        targets=read(DATA/'proxy-labels.json');meter.take('saved_label_rows',len(targets))
        if set(records)!=set(allowed) or set(targets)!=set(allowed):raise ValueError('Missing fixed development features/labels')
        cal_rows=select_private(PRIVATE/'trajectories.jsonl',cal,entries,'trace',meter);cal_refs=select_private(PRIVATE/'references.jsonl',cal,entries,'reference',meter);refs=[cal_refs[k]['reference'] for k in cal_keys]
        xs={};ys={};truth={};component_report={}
        for d in (8,10):
            x={}
            for role,keys in [('fit',fit_keys),('calibration',cal_keys)]:
                values=[]
                for k in keys:
                    f=records[k]['features'][0 if d==8 else 1]
                    if f['level']!=d or len(f['values'])!=27 or not all(math.isfinite(v) for v in f['values']):raise ValueError('Invalid current/past feature cache')
                    values.append(f['values'])
                x[role]=np.asarray(values,dtype=float)
            train_values=np.asarray([targets[k][str(d)] for k in fit_keys],dtype=float);cal_values=np.asarray([targets[k][str(d)] for k in cal_keys],dtype=float);yfit=labels(train_values);ycal=labels(cal_values)
            if min(int(yfit.sum()),len(yfit)-int(yfit.sum()))<20 or min(int(ycal.sum()),len(ycal)-int(ycal.sum()))<10:raise ValueError('Joint class floor failed')
            xs[d]=x;ys[d]=yfit;truth[d]=ycal;component_report[str(d)]={}
            for role,keys,rows in [('fit',fit_keys,train_values),('calibration',cal_keys,cal_values)]:
                component_report[str(d)][role]={}
                for t,name in enumerate(('bleu','chrf','numeric_reference_f1','negation_cue_mismatch_rate')):
                    active=np.isfinite(rows[:,t]);positive=active&(rows[:,t]>0);negative=active&(rows[:,t]<=0)
                    component_report[str(d)][role][name]=dict(defined=int(active.sum()),missing=int((~active).sum()),adverse=int(positive.sum()),adverse_components=len({allowed[k]['component'] for k,flag in zip(keys,positive) if flag}),nonadverse=int(negative.sum()),nonadverse_components=len({allowed[k]['component'] for k,flag in zip(keys,negative) if flag}))
        save(OUT/'endpoint-component-support.json',component_report)
        models={method:{str(d):{} for d in (8,10)} for method in ('ridge','tree')};predictions={};diagnostics={};cal_components=[allowed[k]['component'] for k in cal_keys]
        for method,groups in [('ridge',('cheap','logit','cue','full')),('tree',('cheap','full'))]:
            predictions[method]={};diagnostics[method]={}
            for d in (8,10):
                predictions[method][str(d)]={};diagnostics[method][str(d)]={}
                for group in groups:
                    columns=list(COLUMNS[group]);model=fit_model(xs[d]['fit'][:,columns],ys[d],method,meter);models[method][str(d)][group]=model
                    if model['status']!='fitted':raise ValueError('Prospective model lacked declared class support')
                    cx=xs[d]['calibration'][:,columns];meter.take('prediction_rows',len(cx));pred=np.asarray([predict_model(model,row[None,:])[0] for row in cx]);predictions[method][str(d)][group]=pred.tolist()
                    diag=diagnose(truth[d],pred,cal_components);diag.update(training_prevalence=float(ys[d].mean()),training_prevalence_squared_error=float(np.mean((ys[d].mean()-truth[d])**2)),constant_fit_features=int((xs[d]['fit'][:,columns].std(0)<1e-12).sum()))
                    diagnostics[method][str(d)][group]=diag
        save(OUT/'models.json',models);save(OUT/'calibration-predictions.json',dict(calibration_keys=cal_keys,scores=predictions));save(OUT/'prediction-diagnostics.json',diagnostics)
        specs=candidate_specs(models)
        if len(specs)!=241 or meter.counts['fits']!=12:raise ValueError('Fixed model/candidate work mismatch')
        save(OUT/'candidate-specs.json',specs);profile={int(k):v for k,v in lock['fixed_profile_ms'].items()}
        def metric(hyps):meter.take('corpus_scores');return scores(hyps,refs)
        full=metric([cal_rows[k]['levels'][-1]['text'] for k in cal_keys]);reports=[]
        for spec in specs:
            meter.take('candidate_inputs',len(cal_keys))
            if spec['kind']=='full':s8=s10=None
            else:s8=predictions[spec['method']]['8'][spec['group']];s10=predictions[spec['method']]['10'][spec['group']]
            assignments=replay_scores(spec,s8,s10,xs[8]['calibration'],xs[10]['calibration']);logical=sum(sum(v<11 for v in visits) for d,visits in assignments)
            if logical:meter.take('logical_decisions',logical)
            m=full if spec['kind']=='full' else metric([cal_rows[k]['levels'][d-1]['text'] for k,(d,visits) in zip(cal_keys,assignments)])
            estimated=estimated_cost(spec,assignments,profile,lock['observation_proxy_ms'],lock['extra_per_decision_ms'])
            reports.append(dict(name=spec['name'],metrics=m,losses=point_losses(m,full),point_pass=point_pass(m,full),estimated_mean_ms=estimated,estimated_saving=(profile[11]-estimated)/profile[11],early_inputs=sum(d<11 for d,visits in assignments),exits={str(d):sum(x[0]==d for x in assignments) for d in (8,10,11)},depths=[d for d,v in assignments],visits=[v for d,v in assignments]))
        fixed=[]
        for d in range(1,12):
            m=full if d==11 else metric([cal_rows[k]['levels'][d-1]['text'] for k in cal_keys]);fixed.append(dict(method='fixed:'+str(d),metrics=m,losses=point_losses(m,full),point_pass=point_pass(m,full),profile_mean_ms=profile[d],adjusted_quality_exclusion=False))
        chosen=min((v for v in reports if v['point_pass']),key=lambda v:(v['estimated_mean_ms'],v['name']));spec=next(v for v in specs if v['name']==chosen['name']);comparator=min((v for v in fixed if v['point_pass']),key=lambda v:(v['profile_mean_ms'],v['method']))['method'];ready=chosen['name']!='full' and chosen['estimated_saving']>=.05
        selection=dict(selected=chosen['name'],estimated_saving=chosen['estimated_saving'],ready_for_development_evaluation=ready,status='development_candidate_ready_for_once_only_evaluation' if ready else 'final_development_families_did_not_clear_spend_gate',next_branch='prospectively_lock_development_evaluation' if ready else 'bounded_campaign_closeout',Q0_passed=False,independent_confirmation=False,locked_fixed_comparator=comparator)
        save(OUT/'candidate-results.json',dict(calibration_keys=cal_keys,candidates=reports,fixed=fixed,full=full,selection=selection,all_fixed_controls_remain_potentially_feasible_for_inference=True));save(OUT/'policy.json',dict(policy=spec,locked_fixed_comparator=comparator,source_commit=commit,fit_inputs=3408,calibration_inputs=891,development_evaluation_inputs=1188,evaluation_outcomes_seen_for_selection=0,ready_for_development_evaluation=ready,Q0_passed=False,independent_confirmation=False,all_fixed_controls_required=True));save(OUT/'decision.json',selection)
        if any(k=='torch' or k.startswith('torch.') or k=='transformers' or k.startswith('transformers.') for k in sys.modules):raise ValueError('Unexpected generator framework import')
        hashes_ok(source['protected_sha256']);hashes_ok(source['private_input_sha256'])
        if time.monotonic()-started>lock['wall_seconds'] or cpu()>lock['execution_cpu_cap_seconds'] or rss()>lock['parent_rss_bytes'] or size()>lock['artifact_bytes']:raise RuntimeError('Final fitting resource cap')
        usage=usage_zero();usage.update(cpu_seconds=cpu()+lock['reporting_cpu_charge_seconds'],real_fits=meter.counts['fits'],controller_families=1,artifact_bytes=lock['artifact_bytes']);verify_campaign(ROOT,usage)
        save(OUT/'execution.json',dict(status='complete',source_commit=commit,analysis_counts=meter.counts,new_model_requests=0,new_checkpoint_loads=0,new_source_payload_decodes=0,calibration_reference_body_reads=891,calibration_trace_body_reads=891,new_fits=12,new_controller_families=1,family1_extended_fits=8,family2_tree_fits=4,synthetic_model_requests=0,synthetic_classical_fits=4,target_encodings=0,bootstrap_draws=0,simulations=0,evaluation_outcomes_released=False,selected_policy_sha256=sha(OUT/'policy.json'),total_wall_seconds=time.monotonic()-started,cpu_seconds_before_reporting_charge=cpu(),max_parent_rss_bytes=rss(),campaign_usage=usage,automatic_retries=0,paid_dollars=0,finished_utc=now(),artifact_sha256={p.relative_to(OUT).as_posix():sha(p) for p in OUT.rglob('*') if p.is_file()}))
        print(json.dumps(record_phase(ROOT,'08-development-controller','development_controller/execution.json')),flush=True);print('FINAL DEVELOPMENT SELECTION COMPLETE: '+chosen['name']+'; ready='+str(ready),flush=True)
    except BaseException as error:
        if models and not (OUT/'partial-models.json').exists():save(OUT/'partial-models.json',models)
        failure=OUT/'failure.json'
        if not failure.exists():save(failure,dict(error=repr(error),counts=meter.counts,campaign_usage=lock['campaign_reservation'],conservative_reservation_charge=True,automatic_retry=False))
        if not (CAMPAIGN/'accounting/phase-08-development-controller.json').exists():record_phase(ROOT,'08-development-controller','development_controller/failure.json')
        raise
    finally:signal.setitimer(signal.ITIMER_REAL,0)

def verify():
    lock,source=load();e=read(OUT/'execution.json');hashes_ok({('results/quality_tolerant/campaign_20261029/development_controller/'+p):h for p,h in e['artifact_sha256'].items()});report=read(OUT/'candidate-results.json');p=read(OUT/'policy.json')
    if e['status']!='complete' or e['new_fits']!=12 or e['new_controller_families']!=1 or e['new_model_requests'] or len(report['candidates'])!=241 or sha(OUT/'policy.json')!=e['selected_policy_sha256']:raise ValueError('Invalid final fitting receipt')
    chosen=min((v for v in report['candidates'] if v['point_pass']),key=lambda v:(v['estimated_mean_ms'],v['name']))
    if chosen['name']!=p['policy']['name'] or any(len(v['depths'])!=891 or len(v['visits'])!=891 for v in report['candidates']):raise ValueError('Saved selection differs')
    print(json.dumps(dict(verified=True,protected_files=len(source['protected_sha256']),selected=chosen['name'],ready_for_development_evaluation=p['ready_for_development_evaluation'],new_models_or_fits_or_reference_scores=0,campaign=verify_campaign(ROOT))))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=('run','verify'));p.add_argument('--commit');a=p.parse_args();run(a.commit) if a.mode=='run' else verify()
