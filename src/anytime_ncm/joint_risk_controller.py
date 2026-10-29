"""Fixed-family development candidates; saved-feature replay is not online timing."""
import numpy as np
from anytime_ncm.signal_discrimination import predict
THRESHOLDS=tuple(i/10 for i in range(10))

def candidates(models):
    out=[dict(name='full',kind='full')]
    for group in ('cheap','selected_logit'):
        for decisions in ((8,),(8,10)):
            if any(models[str(d)][group]['status']!='fitted' for d in decisions):continue
            for guard in (False,True):
                for threshold in THRESHOLDS:
                    out.append(dict(name=group+':'+','.join(map(str,decisions))+':guard'+str(int(guard))+':'+str(threshold),kind='joint_ridge',group=group,
                        decision_levels=list(decisions),cue_guard=guard,threshold=threshold,models={str(d):models[str(d)][group] for d in decisions}))
    return out

def decision(spec,level,vector,meter=None):
    if level not in spec['decision_levels']:raise ValueError('Unscheduled decision')
    x=np.asarray(vector,dtype=float)
    if x.shape!=(27,) or not np.isfinite(x).all():raise ValueError('Require current complete causal vector')
    if meter:meter.take('decisions')
    if spec['cue_guard'] and (x[25]!=1 or x[26]!=1):return False
    n=19 if spec['group']=='cheap' else 27
    score=float(predict(spec['models'][str(level)],x[:n][None,:])[0])
    return score<=spec['threshold']

def replay(spec,record,meter=None):
    if meter:meter.take('replay_inputs')
    if spec['kind']=='full':return 11,[11]
    if spec['kind']!='joint_ridge' or spec['group'] not in ('cheap','selected_logit') or spec['decision_levels'] not in ([8],[8,10]):raise ValueError('Malformed frozen candidate')
    visits=[]
    for level in spec['decision_levels']:
        visits.append(level);feature=record['features'][0 if level==8 else 1]
        if feature['level']!=level:raise ValueError('Missing actual scheduled feature')
        if decision(spec,level,feature['values'],meter):return level,visits
    return 11,visits+[11]

def estimated_cost(spec,assignments,profile,observation_ms,extra_per_decision_ms):
    if spec['kind']=='full':return float(profile[11])
    if observation_ms<0 or extra_per_decision_ms<0:raise ValueError('Negative cost')
    extra=extra_per_decision_ms if spec['group']=='selected_logit' or spec['cue_guard'] else 0.
    return float(np.mean([profile[d]+(len(visits)-1)*observation_ms+sum(v<11 for v in visits)*extra for d,visits in assignments]))

def select(reports,full_mean):
    if full_mean<=0:raise ValueError('Invalid full reference')
    passing=[r for r in reports if r['point_pass']]
    chosen=min(passing,key=lambda r:(r['estimated_mean_ms'],r['name']))
    saving=(full_mean-chosen['estimated_mean_ms'])/full_mean
    ready=chosen['name']!='full' and saving>=.05
    return dict(selected=chosen['name'],estimated_saving=saving,ready_for_allocated_evaluation=ready,
        next_branch='lock_actual_controller_evaluation' if ready else 'bounded_family2_or_data_eligibility_review',
        status='candidate_ready_for_exploratory_actual_timing' if ready else 'selection_did_not_establish_worthwhile_candidate',
        quality_confirmation=False,Q0_passed=False)
