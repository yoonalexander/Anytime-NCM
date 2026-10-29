"""Synthetic fixed-family replay, causal schedule, guards and selection tests."""
import copy
import pytest
from anytime_ncm.joint_risk_controller import candidates,decision,replay,estimated_cost,select
from anytime_ncm.quality_controller import Meter

def models():return {str(d):{g:dict(status='fitted',mean=[0]*n,scale=[1]*n,coef=[0]*n+[.2]) for g,n in [('cheap',19),('selected_logit',27)]} for d in (8,10)}
def record():return dict(features=[dict(level=d,values=[0.]*25+[1.,1.]) for d in (8,10)])

def test_bounded_candidate_grid_and_unfitted_skip():
    specs=candidates(models());assert len(specs)==81 and len({s['name'] for s in specs})==81
    assert {tuple(s['decision_levels']) for s in specs[1:]}=={(8,),(8,10)}
    m=models();m['10']['selected_logit']['status']='insufficient_classes';assert len(candidates(m))==61

def test_threshold_equality_guard_veto_and_source_endpoint_separation():
    spec=next(s for s in candidates(models()) if s.get('group')=='selected_logit' and s.get('cue_guard') and s.get('threshold')==.2)
    x=record()['features'][0]['values'];assert decision(spec,8,x)
    for c in (25,26):
        changed=x.copy();changed[c]=0;assert not decision(spec,8,changed)
    spec=copy.deepcopy(spec);spec['threshold']=.1;assert not decision(spec,8,x)

def test_early_exit_never_reads_poisoned_future_and_skip10_schedule():
    spec=next(s for s in candidates(models()) if s.get('group')=='selected_logit' and s.get('threshold')==.2)
    r=record();r['features'][1]=dict(level=10,values=[float('nan')]*27)
    assert replay(spec,r)==(8,[8])
    spec=copy.deepcopy(spec);spec['threshold']=.1;assert replay(spec,r)==(11,[8,11])
    with pytest.raises(ValueError):decision(spec,10,[0.]*27)

def test_actual_history_order_and_finite_current_features():
    spec=next(s for s in candidates(models()) if s.get('decision_levels')==[8,10] and s.get('threshold')==.1)
    r=record();assert replay(spec,r)==(11,[8,10,11])
    r['features'][1]['level']=8
    with pytest.raises(ValueError):replay(spec,r)
    with pytest.raises(ValueError):decision(spec,8,[float('inf')]*27)

def test_full_fallback_does_not_access_features_and_meter_counts():
    meter=Meter(dict(replay_inputs=2,decisions=1));assert replay(dict(name='full',kind='full'),{},meter)==(11,[11])
    spec=next(s for s in candidates(models()) if s.get('threshold')==.2);assert replay(spec,record(),meter)==(8,[8])
    assert meter.counts==dict(replay_inputs=2,decisions=1)

def test_costs_pay_every_extra_observation_and_feature_visit():
    spec=next(s for s in candidates(models()) if s.get('group')=='selected_logit')
    assert estimated_cost(spec,[(8,[8]),(11,[8,11])],{8:100,11:140},2,.5)==121.5
    assert estimated_cost(dict(kind='full'),[],{11:140},2,.5)==140
    with pytest.raises(ValueError):estimated_cost(spec,[],{11:140},-1,.5)

def test_selection_point_quality_ties_exact5_and_failed_gate():
    r=[dict(name='full',point_pass=True,estimated_mean_ms=100),dict(name='a',point_pass=False,estimated_mean_ms=50),dict(name='b',point_pass=True,estimated_mean_ms=95)]
    assert select(r,100)['ready_for_allocated_evaluation']
    r[-1]['estimated_mean_ms']=95.1;assert not select(r,100)['ready_for_allocated_evaluation']
    r[-1]['point_pass']=False;assert select(r,100)['selected']=='full'
