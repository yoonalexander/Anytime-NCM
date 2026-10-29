"""Prospective joint-loss probes on development data; no online quality guarantee."""
import numpy as np
from anytime_ncm.controller_diagnostics import auc,joint_truth

LEVELS=(8,10)
GROUPS=('cheap','selected_logit')
PROXY_THRESHOLD=4.

def labels(values):
    a=np.asarray(values,dtype=float)
    if a.ndim!=2 or a.shape[1]!=4 or not np.isfinite(a[:,[0,1,3]]).all() or np.isinf(a).any():
        raise ValueError('Only numeric-reference endpoint may be missing')
    return (joint_truth(a)>PROXY_THRESHOLD).astype(float)

def fit_ridge(x,y,meter):
    x=np.asarray(x,dtype=float);y=np.asarray(y,dtype=float)
    if x.ndim!=2 or y.shape!=(len(x),) or not np.isfinite(x).all() or not np.isin(y,[0.,1.]).all():raise ValueError('Invalid fit arrays')
    counts=[int((y==v).sum()) for v in (0,1)]
    if min(counts)<10:return dict(status='insufficient_classes',class_counts=counts)
    mean=x.mean(0);scale=x.std(0);scale[scale<1e-12]=1.
    z=np.column_stack([(x-mean)/scale,np.ones(len(x))]);p=np.eye(z.shape[1])*10.;p[-1,-1]=0.
    meter.take('fits');coef=np.linalg.solve(z.T@z+p,z.T@y)
    return dict(status='fitted',mean=mean.tolist(),scale=scale.tolist(),coef=coef.tolist(),class_counts=counts,penalty=10.)

def predict(model,x):
    x=np.asarray(x,dtype=float);mean=np.asarray(model['mean']);scale=np.asarray(model['scale']);coef=np.asarray(model['coef'])
    if model['status']!='fitted' or x.ndim!=2 or mean.shape!=(x.shape[1],) or scale.shape!=mean.shape or coef.shape!=(x.shape[1]+1,) or np.any(scale<=0) or not all(np.isfinite(v).all() for v in (x,mean,scale,coef)):
        raise ValueError('Invalid frozen probe')
    return np.column_stack([(x-mean)/scale,np.ones(len(x))])@coef

def diagnose(y,score,components):
    y=np.asarray(y,dtype=float);s=np.asarray(score,dtype=float);components=np.asarray(components)
    if y.shape!=s.shape or components.shape!=y.shape or not np.isin(y,[0.,1.]).all() or not np.isfinite(s).all():raise ValueError('Invalid diagnostic arrays')
    clipped=np.clip(s,0.,1.);bins=[]
    for b in range(5):
        active=(clipped>=b/5)&((clipped<(b+1)/5) if b<4 else (clipped<=1))
        bins.append(dict(lower=b/5,upper=(b+1)/5,n=int(active.sum()),mean_score=float(clipped[active].mean()) if active.any() else None,adverse_fraction=float(y[active].mean()) if active.any() else None))
    deleted=[]
    for component in sorted(set(components)):
        active=components!=component;value=auc(y[active],s[active]);deleted.append(dict(component=str(component),n=int(active.sum()),auc=value))
    return dict(n=len(y),nonadverse=int((y==0).sum()),adverse=int((y==1).sum()),auc=auc(y,s),clipped_squared_error=float(np.mean((clipped-y)**2)),
        clipping_count=int(((s<0)|(s>1)).sum()),mean_score=float(s.mean()),adverse_fraction=float(y.mean()),reliability_bins=bins,
        component_deletion=deleted,interpretation='descriptive dependent development observations; clipped score is not a calibrated probability; deletion is not a confidence interval')

def decide(reports):
    qualified=[];richer=[]
    for d in LEVELS:
        level=reports[str(d)];c=level['probes']['cheap'];r=level['probes']['selected_logit']
        for group,report in (('cheap',c),('selected_logit',r)):
            if report.get('auc') is not None and min(report['adverse'],report['nonadverse'])>=10 and report['auc']>=.60:qualified.append(dict(level=d,group=group))
        if any(v['level']==d and v['group']=='selected_logit' for v in qualified) and c.get('auc') is not None and r['auc']-c['auc']>=.02:richer.append(d)
    if richer:return dict(status='richer_probe_supported',next_branch='lock_joint_risk_controller',richer_supported_levels=richer,qualified=qualified)
    if qualified:return dict(status='joint_probe_supported_without_established_richer_gain',next_branch='lock_joint_risk_controller',richer_supported_levels=[],qualified=qualified)
    return dict(status='linear_probe_not_supported',next_branch='bounded_nonlinear_or_data_eligibility_review',richer_supported_levels=[],qualified=[])

def analyze(records,targets,fit_ids,cal_ids,components,meter):
    by_id={r['index']:r for r in records if not r['warmup']}
    if len(by_id)!=len(fit_ids)+len(cal_ids) or sum(bool(r['warmup']) for r in records)!=5 or len(records)!=len(by_id)+5 or set(by_id)!=set(fit_ids)|set(cal_ids) or set(fit_ids)&set(cal_ids):raise ValueError('Feature allocation/count mismatch')
    models={};report={};predictions={}
    for d in LEVELS:
        def vectors(indices):
            result=[]
            for i in indices:
                fs=by_id[i]['features']
                if [f['level'] for f in fs]!=[8,10]:raise ValueError('Wrong observation order')
                v=fs[0 if d==8 else 1]['values']
                if len(v)!=27 or not np.isfinite(v).all():raise ValueError('Wrong feature vector')
                result.append(v)
            return np.asarray(result)
        tx,cx=vectors(fit_ids),vectors(cal_ids)
        ty=np.array([targets[str(i)][str(d)] for i in fit_ids],dtype=float);cy=np.array([targets[str(i)][str(d)] for i in cal_ids],dtype=float)
        train,test=labels(ty),labels(cy);cc=[components[i] for i in cal_ids]
        level=dict(probes={},raw_baselines={},targets={})
        for t,name in enumerate(('bleu','chrf','numeric_reference_f1','negation_cue_mismatch_rate')):
            level['targets'][name]={}
            for role,a in (('fit',ty),('calibration',cy)):
                active=np.isfinite(a[:,t]);v=a[active,t]
                level['targets'][name][role]=dict(defined=int(active.sum()),missing=int((~active).sum()),adverse=int((v>0).sum()),nonadverse=int((v<=0).sum()),nonzero=int((v!=0).sum()),minimum=float(v.min()) if len(v) else None,maximum=float(v.max()) if len(v) else None,learned_endpoint_head=False)
        models[str(d)]={};predictions[str(d)]={}
        for group,n in (('cheap',19),('selected_logit',27)):
            model=fit_ridge(tx[:,:n],train,meter);models[str(d)][group]=model
            if model['status']!='fitted':level['probes'][group]=dict(status=model['status'],auc=None,class_counts=model['class_counts']);continue
            score=predict(model,cx[:,:n]);level['probes'][group]=dict(status='fitted',**diagnose(test,score,cc));predictions[str(d)][group]=score.tolist()
            level['probes'][group]['training_prevalence_clipped_squared_error']=float(np.mean((train.mean()-test)**2))
        for name,score in [('negative_selected_logit_mean',-cx[:,19]),('negative_selected_logit_p10',-cx[:,20]),('negative_selected_logit_min',-cx[:,21]),('source_number_disagreement',1-cx[:,25]),('source_negation_disagreement',1-cx[:,26]),('token_change',cx[:,14])]:level['raw_baselines'][name]=diagnose(test,score,cc)
        report[str(d)]=level
    return dict(levels=report,decision=decide(report),models=models,calibration_predictions=predictions,proxy_threshold=PROXY_THRESHOLD,corpus_quality_claim=False,pvalues=False,bootstrap_draws=0)
