"""Frozen descriptive failure diagnosis: no fitting, model loads or inference."""
import json
import re
import numpy as np
from anytime_ncm.quality_controller import FEATURES,TARGETS,MARGINS,features,sentence_targets
from anytime_ncm.latency_diagnostic import LEVELS

THRESHOLDS=(0.,.5,1.,2.,4.)
FACTORS=(0.,.5,1.,2.)
def timing_header(raw):
    # Worker plan dictionaries were loaded from sorted-key JSON. Do not assume field order.
    cut=raw.find(b', "wall_ms":')
    if not raw.startswith(b'{') or cut<0 or cut>1024:raise ValueError('Invalid cost-record header before JSON decode')
    header=raw[:cut];result={}
    for field in ('request_id','session','index','identity'):
        pattern=(rb'"'+field.encode()+rb'":\s*"([a-f0-9]{64})"') if field=='identity' else (rb'"'+field.encode()+rb'":\s*(\d+)')
        matches=re.findall(pattern,header)
        if len(matches)!=1:raise ValueError('Ambiguous cost-record identity header')
        result[field]=matches[0].decode() if field=='identity' else int(matches[0])
    return result


def auc(y,score):
    """Exact pairwise descriptive AUC, unsafe/adverse is positive; ties score 1/2."""
    y=np.asarray(y,dtype=bool);score=np.asarray(score,dtype=float)
    if len(y)!=len(score) or not np.isfinite(score).all():raise ValueError('Invalid AUC inputs')
    pos=score[y];neg=score[~y]
    if not len(pos) or not len(neg):return None
    d=pos[:,None]-neg[None,:]
    return float(np.mean((d>0)+.5*(d==0)))

def summary(values):
    v=np.asarray(values,dtype=float);v=v[np.isfinite(v)]
    return dict(n=len(v),mean=float(v.mean()) if len(v) else None,
        quantiles=dict(zip(('min','p10','p25','median','p75','p90','max'),np.quantile(v,[0,.1,.25,.5,.75,.9,1]).tolist())) if len(v) else None)

def joint_truth(labels):
    labels=np.asarray(labels,dtype=float)
    # Missing reference-number endpoints do not contribute to a per-input diagnostic constraint.
    # Corpus F1 still uses the unchanged reference-covered denominator.
    return np.maximum(0.,np.max(np.where(np.isnan(labels),0.,labels),axis=1))

def exits_from_scores(scores8,scores10,threshold):
    a=np.asarray(scores8);b=np.asarray(scores10)
    if a.shape!=b.shape or a.ndim!=1 or not np.isfinite(a).all() or not np.isfinite(b).all():raise ValueError('Invalid diagnostic scores')
    return np.where(a<=threshold,8,np.where(b<=threshold,10,11)).tolist()

def estimate_cost(exits,profile,h,factor):
    if factor not in FACTORS or any(d not in (8,10,11) for d in exits):raise ValueError('Invalid frozen cost sensitivity')
    visits={8:1,10:2,11:3}
    return float(np.mean([profile[d]+(visits[d]-1)*h*factor for d in exits]))

def collect_arrays(rows,sources,references,models,meter):
    x={8:[],10:[]};y={8:[],10:[]};p={8:[],10:[]}
    for row in rows:
        target=sentence_targets(row,references[row['index']],meter);previous=None
        for d in (8,10):
            meter.take('features');o=row['levels'][d-1]
            v=features(sources[row['index']],d,row['codes'][:sum(LEVELS[:d])],o['ids'],o['text'],previous)
            m=models[str(d)];pred=np.r_[(v-np.asarray(m['mean']))/np.asarray(m['scale']),1.]@np.asarray(m['coef'])
            x[d].append(v);y[d].append([np.nan if z is None else z for z in target[d]]);p[d].append(pred)
            previous=dict(level=d,ids=o['ids'],text=o['text'])
    return {d:dict(x=np.asarray(x[d]),y=np.asarray(y[d]),pred=np.asarray(p[d])) for d in (8,10)}

def errors_and_features(train,cal,models):
    result={}
    for d in (8,10):
        tr,ca=train[d],cal[d];targets={}
        for t,name in enumerate(TARGETS):
            active=np.isfinite(ca['y'][:,t]);truth=ca['y'][active,t];pred=ca['pred'][active,t]
            training=tr['y'][:,t];training=training[np.isfinite(training)]
            reference_mean=float(training.mean()) if len(training) else None
            targets[name]=dict(train_normalized_target=summary(training),cal_normalized_target=summary(truth),cal_prediction=summary(pred),
                cal_bias=float(np.mean(pred-truth)) if len(truth) else None,cal_mae=float(np.mean(np.abs(pred-truth))) if len(truth) else None,
                cal_mse=float(np.mean((pred-truth)**2)) if len(truth) else None,
                cal_mse_at_train_marginal_mean=float(np.mean((reference_mean-truth)**2)) if len(truth) else None,
                cal_adverse_gt_margin=int(np.sum(truth>1)),cal_nonadverse=int(np.sum(truth<=1)),
                cal_adverse_ranking_auc=auc(truth>1,pred))
        true=joint_truth(ca['y']);pred=np.maximum(0.,ca['pred'].max(axis=1));covered=np.isfinite(ca['y'][:,2]);groups={}
        for name,mask in [('all',np.ones(len(pred),dtype=bool)),('numeric_reference_covered',covered),('numeric_reference_uncovered',~covered)]:
            z=ca['pred'][mask];groups[name]=dict(n=int(mask.sum()),joint_prediction=summary(pred[mask]),joint_truth=summary(true[mask]),
                predicted_above4=int(np.sum(pred[mask]>4)),actual_above4=int(np.sum(true[mask]>4)),
                dominant_target_at_rejection={k:int(np.sum((pred[mask]>4)&(np.argmax(z,axis=1)==i))) for i,k in enumerate(TARGETS)},
                sole_target_veto_at4={k:int(np.sum((z[:,i]>4)&np.all(np.delete(z,i,axis=1)<=4,axis=1))) for i,k in enumerate(TARGETS)})
        raw_std=tr['x'].std(axis=0);scale=np.asarray(models[str(d)]['scale']);mean=np.asarray(models[str(d)]['mean'])
        outliers=np.abs((ca['x']-mean)/scale)>3
        result[str(d)]=dict(targets=targets,joint_unsafe_gt1_auc=auc(true>1,pred),joint_unsafe_gt1=int(np.sum(true>1)),joint_safe_le1=int(np.sum(true<=1)),
            groups=groups,constant_train_features=[FEATURES[i] for i,v in enumerate(raw_std) if v<1e-12],
            cal_outside_three_training_scales={FEATURES[i]:int(outliers[:,i].sum()) for i in range(len(FEATURES))})
    return result

def proxy_audit(records,h):
    cells={}
    for r in records:
        if r['warmup']:continue
        key=(r['index'],r['session'],r['repeat']);method=r['method']
        if method in cells.setdefault(key,{}):raise ValueError('Duplicate cost cell')
        cells[key][method]=r
    residuals=[];by={8:[],10:[],11:[]}
    for key,methods in cells.items():
        if len(methods)!=12 or 'assigned_sparse' not in methods:raise ValueError('Missing paired cost methods')
        r=methods['assigned_sparse'];d=r['depth'];base=methods['fixed:'+str(d)]['wall_ms'];obs=len([v for v in (8,10,11) if v<=d])
        error=r['wall_ms']-(base+(obs-1)*h)
        residuals.append(error);by[d].append(error)
    return dict(paired_cells=len(cells),residual_definition='actual assigned sparse ms minus paired terminal ms plus declared extra-observation proxy',
        bias_ms=float(np.mean(residuals)) if residuals else None,mae_ms=float(np.mean(np.abs(residuals))) if residuals else None,
        by_exit={str(d):summary(v) for d,v in by.items()},new_component_or_controller_cost_measurement=False)

def diagnosis_decision(policies,model_report):
    oracle=[p for p in policies if p['kind']=='future_label_oracle' and p['point_pass']]
    at_frozen=any(p['cost_grid']['1.0']['savings']>=.05 for p in oracle)
    at_zero=any(p['cost_grid']['0.0']['savings']>=.05 for p in oracle)
    original_optimistic=any(p['kind']=='original' and p['point_pass'] and p['cost_grid']['0.0']['savings']>=.05 for p in policies)
    rank=model_report['8']['joint_unsafe_gt1_auc']
    if at_frozen:
        route='corpus_objective_design_review' if rank is not None and rank>=.65 else 'richer_causal_signal_study'
    elif at_zero:route='direct_sparse_cost_or_schedule_review'
    else:route='label_or_schedule_redesign_before_more_fits'
    return dict(recommended_route=route,perfect_label_family_point_feasible_5_percent_at_frozen_cost=at_frozen,
        perfect_label_family_point_feasible_5_percent_at_zero_observation_cost=at_zero,
        original_point_feasible_5_percent_at_zero_observation_cost=original_optimistic,
        cal_level8_joint_ranking_auc=rank,ranking_heuristic_threshold=.65,
        cost_values_are_estimates=True,oracle_is_not_deployable=True,Q0_passed=False,reserved_outputs_released=False,
        new_fitting_or_GPU_authorized_by_this_receipt=False)
