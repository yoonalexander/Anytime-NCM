"""One prospective CPU-only fit/calibration diagnosis; no new fits or GPU work."""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='1'
os.environ['PYTHONDONTWRITEBYTECODE']='1'
import argparse
from datetime import datetime,timezone
import json,resource,signal,subprocess,sys,time,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'scripts'))
from anytime_ncm.evidence_preflight import sha,write_new
from anytime_ncm.quality_controller import Meter,Controller,replay,point_losses,point_pass
from anytime_ncm.controller_diagnostics import (THRESHOLDS,FACTORS,TARGETS,MARGINS,collect_arrays,errors_and_features,joint_truth,exits_from_scores,estimate_cost,proxy_audit,timing_header,diagnosis_decision)
from anytime_ncm.wmt_metrics import scores
from run_quality_controller import read_data
import numpy as np
BASE=ROOT/'docs/studies/quality-tolerant';OUT=ROOT/'results/quality_tolerant/controller_diagnostic';RUN=OUT/'run'

def read(p):return json.loads(p.read_text(encoding='utf-8'))
def git(*a):return subprocess.check_output(['git.exe',*a],cwd=ROOT,text=True,timeout=60).strip()
def now():return datetime.now(timezone.utc).isoformat()
def hashes_ok(values,base=ROOT):
    for p,h in values.items():
        if sha(base/p)!=h:raise ValueError('Frozen bytes differ: '+p)
def load():
    lock=read(BASE/'controller-diagnostic-lock.json');source=read(BASE/'controller-diagnostic-source-lock.json')
    hashes_ok(source['source_sha256']);hashes_ok(source['protected_sha256'])
    if git('-C','third_party/ncm','rev-parse','HEAD')!=source['upstream_commit'] or git('-C','third_party/ncm','status','--porcelain'):raise ValueError('Upstream changed')
    return lock,source

def run(commit):
    started=time.monotonic();lock,source_lock=load()
    if git('branch','--show-current')!='main' or git('rev-parse','HEAD')!=commit or git('status','--porcelain') or git('ls-remote','origin','refs/heads/main').split()[0]!=commit:raise ValueError('Need clean main at pushed lock')
    RUN.mkdir(parents=True,exist_ok=False);write_new(RUN/'started.json',dict(source_commit=commit,started_utc=now(),fits=0,GPU_requests=0))
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('Diagnostic wall allocation')));signal.setitimer(signal.ITIMER_REAL,lock['wall_seconds']);meter=None
    try:
        with zipfile.ZipFile(RUN/'execution-sources.zip','x',compression=zipfile.ZIP_DEFLATED) as z:
            for p in source_lock['source_sha256']:z.writestr(p,(ROOT/p).read_bytes())
            z.writestr('source-lock.json',json.dumps(source_lock,indent=2))
        with (RUN/'synthetic-tests.log').open('x',encoding='utf-8',newline='\n') as stream:
            test=subprocess.run([sys.executable,'-m','pytest','tests/test_controller_diagnostics.py','-q','-s','-p','no:cacheprovider',
                '--junitxml=results/quality_tolerant/controller_diagnostic/run/synthetic-tests.xml'],cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,timeout=lock['test_wall_seconds'])
        if test.returncode:raise RuntimeError('Synthetic diagnostics failed before outcome access')
        print('Diagnostic synthetic checks passed; fit/calibration data only released',flush=True)
        import sacrebleu
        if sacrebleu.__version__!='2.6.0':raise ValueError('Metric version drift')
        config=read(ROOT/'configs/phase4_wmt_sources.json')
        for p in ('data/wmt14/sources.pickle','data/wmt14/reference_translations.pickle'):
            if sha(ROOT/p)!=config['files'][p]['sha256']:raise ValueError('Pinned dataset differs')
        split=read(BASE/'controller-split.json');fit=split['parts']['fit'];cal=split['parts']['calibration'];entries=sorted(fit+cal,key=lambda e:e['index'])
        write_new(RUN/'access-release.json',dict(source_commit=commit,roles=['fit','calibration'],entries=entries,test_87_bodies_released=False,E3_E4_outputs_released=False))
        with (RUN/'ledger.jsonl').open('x',encoding='utf-8',newline='\n') as ledger:
            meter=Meter(lock['caps'],ledger);rows,sources,references=read_data(entries,split,meter)
            models=read(ROOT/'results/quality_tolerant/controller/development/models.json');fit_ids={e['index'] for e in fit};cal_ids={e['index'] for e in cal}
            fit_rows=[r for r in rows if r['index'] in fit_ids];cal_rows=[r for r in rows if r['index'] in cal_ids]
            train=collect_arrays(fit_rows,sources,references,models,meter);calibration=collect_arrays(cal_rows,sources,references,models,meter)
            model_report=errors_and_features(train,calibration,models);write_new(RUN/'prediction-diagnostics.json',model_report)
            baseline=read(ROOT/'results/quality_tolerant/controller/development/candidate-results.json')
            old_timing=read(ROOT/'results/quality_tolerant/latency_diagnostic/analysis.json')
            profile={d:old_timing['methods']['fixed:'+str(d)]['mean_ms'] for d in (8,10,11)}
            h=read(ROOT/'results/quality_tolerant/q1/cost-calibration.json')['observation_step_proxy_ms']
            refs=[references[r['index']] for r in cal_rows]
            meter.take('corpus_scores');full=scores([r['levels'][-1]['text'] for r in cal_rows],refs)
            policies=[]
            def describe(name,kind,exits):
                meter.take('diagnostic_assignments')
                if name=='full':metric=full
                else:
                    meter.take('corpus_scores');metric=scores([r['levels'][d-1]['text'] for r,d in zip(cal_rows,exits)],refs)
                costs={}
                for f in FACTORS:
                    meter.take('cost_grid_evaluations');value=profile[11] if name=='full' else estimate_cost(exits,profile,h,f)
                    costs[str(f)]=dict(mean_ms=value,savings=1-value/profile[11])
                result=dict(name=name,kind=kind,metrics=metric,losses=point_losses(metric,full),point_pass=point_pass(metric,full),
                    exits={str(d):exits.count(d) for d in (8,10,11)},early_inputs=sum(d<11 for d in exits),cost_grid=costs)
                policies.append(result);return result
            describe('full','original',[11]*len(cal_rows))
            for epsilon in (0.,2/64,4/64):
                controller=Controller(dict(kind='stability',epsilon=epsilon),meter);exits=[]
                for row in cal_rows:meter.take('replay_inputs');exits.append(replay(controller,sources[row['index']],row)[0])
                describe('stability:'+str(epsilon),'original',exits)
            pred={d:np.maximum(0.,calibration[d]['pred'].max(axis=1)) for d in (8,10)}
            for t in THRESHOLDS:
                exits=exits_from_scores(pred[8],pred[10],t);describe('ridge:'+str(t),'original',exits)
                if t==2.:
                    controller=Controller(dict(kind='ridge',threshold=2.,models=models),meter)
                    for row,expected in zip(cal_rows,exits):
                        meter.take('replay_inputs')
                        if replay(controller,sources[row['index']],row)[0]!=expected:raise ValueError('Vector/scalar controller mismatch')
            prior={p['name']:p for p in baseline['candidates']}
            for p in policies:
                before=prior[p['name']]
                if p['early_inputs']!=before['early_inputs'] or p['point_pass']!=before['point_pass'] or p['exits']!=before['exits']:raise ValueError('Old candidate replay differs')
                if any(abs(p['losses'][k]-before['losses'][k])>1e-9 for k in p['losses']) or abs(p['cost_grid']['1.0']['mean_ms']-before['estimated_mean_ms'])>1e-9:
                    raise ValueError('Old candidate score/cost parity differs')
            truth={d:joint_truth(calibration[d]['y']) for d in (8,10)}
            for t in THRESHOLDS:describe('perfect-label:'+str(t),'future_label_oracle',exits_from_scores(truth[8],truth[10],t))
            for j,name in enumerate(TARGETS):
                ablated={d:np.maximum(0.,np.delete(calibration[d]['pred'],j,axis=1).max(axis=1)) for d in (8,10)}
                describe('omit-predicted-'+name+'-at4','endpoint_omission_counterfactual',exits_from_scores(ablated[8],ablated[10],4.))
            write_new(RUN/'diagnostic-assignments.json',dict(policies=policies,selection_performed=False,original_candidates_reproduced=9,oracle_and_omission_rules_not_deployable=True))
            aggregation={}
            fixed={v['method']:v for v in baseline['fixed']}
            for d in (8,10):
                aggregation[str(d)]={k:dict(mean_sentence_proxy_loss=float(np.nanmean(calibration[d]['y'][:,i])*MARGINS[i]),
                    unchanged_corpus_loss=fixed['fixed:'+str(d)]['losses'][k]) for i,k in enumerate(TARGETS[:2])}
            write_new(RUN/'aggregation-diagnostics.json',aggregation)
            all_e2={e['index']:e['identity'] for es in split['parts'].values() for e in es if e['origin']=='E2_audit'}
            active_e2={e['index'] for e in entries if e['origin']=='E2_audit'};records=[]
            for s in (0,1):
                seen=set()
                with (ROOT/f'results/quality_tolerant/latency_diagnostic/{s}-requests.jsonl').open('rb') as stream:
                    for raw in stream:
                        meter.take('timing_headers');head=timing_header(raw)
                        if (head['session']!=s or head['index'] not in all_e2 or head['identity']!=all_e2[head['index']] or head['request_id'] in seen):raise ValueError('Forbidden/duplicate cost header')
                        seen.add(head['request_id'])
                        if head['index'] not in active_e2:continue
                        meter.take('timing_bodies');record=json.loads(raw)
                        if any(record[k]!=v for k,v in head.items()):raise ValueError('Cost header/body mismatch')
                        records.append(record)
                if seen!=set(range(6204)):raise ValueError('Missing cost headers')
            audit=proxy_audit(records,h);audit.update(source='prior Q2 forced sparse versus terminal paths, fit/calibration E2 subset only',active_inputs=len(active_e2),
                earlier_Q3_test_timing_bodies=0,controller_decision_overhead_in_this_audit=False)
            write_new(RUN/'cost-proxy-diagnostics.json',audit)
            decision=diagnosis_decision(policies,model_report);write_new(RUN/'decision.json',decision)
        if any(k=='torch' or k.startswith('torch.') or k=='transformers' or k.startswith('transformers.') for k in sys.modules):raise RuntimeError('Unexpected model-library import')
        hashes_ok(source_lock['protected_sha256']);hashes_ok(source_lock['source_sha256'])
        wall=time.monotonic()-started;rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024;size=sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file())
        if wall>lock['wall_seconds'] or resource.getrusage(resource.RUSAGE_SELF).ru_utime+resource.getrusage(resource.RUSAGE_SELF).ru_stime>lock['cpu_seconds'] or rss>lock['memory_bytes'] or size>lock['storage_bytes']:raise RuntimeError('Diagnostic resource cap')
        write_new(RUN/'execution.json',dict(status='complete',source_commit=commit,counts=meter.counts,wall_seconds=wall,cpu_seconds=resource.getrusage(resource.RUSAGE_SELF).ru_utime+resource.getrusage(resource.RUSAGE_SELF).ru_stime,max_rss_bytes=rss,artifact_bytes=size,
            new_fits=0,model_loads=0,GPU_requests=0,target_encodings=0,bootstrap_draws=0,paid_compute_dollars=0,test_87_outcome_bodies=0,reserved_outputs_released=False,
            automatic_retries=0,finished_utc=now(),artifact_sha256={str(p.relative_to(RUN)):sha(p) for p in RUN.rglob('*') if p.is_file()}))
        print('CONTROLLER DIAGNOSTIC COMPLETE: '+decision['recommended_route'],flush=True)
    except BaseException as error:
        write_new(RUN/'failure.json',dict(error=repr(error),counts=meter.counts if meter else {},wall_seconds=time.monotonic()-started,automatic_retry=False));raise
    finally:signal.setitimer(signal.ITIMER_REAL,0)

def verify():
    lock,source=load();e=read(RUN/'execution.json');hashes_ok(e['artifact_sha256'],RUN)
    if e['status']!='complete' or any(e['counts'][k]>v for k,v in lock['caps'].items()) or e['new_fits'] or e['GPU_requests'] or e['test_87_outcome_bodies']:raise ValueError('Invalid diagnostic receipt')
    print(json.dumps(dict(verified=True,protected_files=len(source['protected_sha256']),artifact_hashes=len(e['artifact_sha256']),new_fits=0,new_outcome_body_reads=0,counts=e['counts'])))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=('run','verify'));p.add_argument('--commit');a=p.parse_args()
    run(a.commit) if a.mode=='run' else verify()
