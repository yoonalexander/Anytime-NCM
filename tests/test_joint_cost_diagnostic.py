"""Synthetic actual stopping and paired diagnostic validation; no real checkpoint."""
import copy
import numpy as np
import pytest
import torch
from test_phase4 import tiny
from anytime_ncm.joint_risk_wmt import joint_request
from anytime_ncm.forced_wmt import ForwardCounter
from anytime_ncm.quality_controller import Meter
from anytime_ncm.latency_diagnostic import LEVELS,cluster_draws,value_hash
from anytime_ncm.controller_study import schedule,sum_work,timing_analysis

def spec(intercept):return dict(kind='joint_ridge',group='selected_logit',decision_levels=[8],cue_guard=False,threshold=.6,models={'8':dict(status='fitted',mean=[0]*27,scale=[1]*27,coef=[0]*27+[intercept])})

def test_tiny_real_stopping_exact_prefix_output_work_state_and_cleanup():
    torch.set_num_threads(1);model,_=tiny();counter=ForwardCounter(model,dict(inputs=4,generator_levels=30,decoder=4,encoder=0));meter=Meter(dict(cheap_features=2,selected_logit_features=2,cue_features=2,decisions=2))
    states={name:{k:v.detach().clone() for k,v in net.state_dict().items()} for name,net in [('g',model.net),('t',model.tokenizer.vqvae)]}
    try:
        counter.take('inputs');full=joint_request(model,'source 2',dict(kind='full'))
        counter.take('inputs');early=joint_request(model,'source 2',spec(0),meter)
        counter.take('inputs');late=joint_request(model,'source 2',spec(1),meter)
        assert early['exit_level']==8 and [v['level'] for v in early['observations']]==[8]
        assert late['exit_level']==11 and [v['level'] for v in late['observations']]==[8,11]
        assert torch.equal(early['codes'],full['codes'][:,:sum(LEVELS[:8])]) and torch.equal(late['codes'],full['codes'])
        assert early['observations'][0]==late['observations'][0] and full['ids']==late['ids'] and full['text']==late['text']
        assert early['features']==late['features'] and model.net._cfg is None
        for name,net in [('g',model.net),('t',model.tokenizer.vqvae)]:
            assert all(torch.equal(v,states[name][k]) for k,v in net.state_dict().items())
        counter.take('inputs');model.net.train()
        with pytest.raises(ValueError):joint_request(model,'source',spec(0),meter)
        assert counter.counts==dict(inputs=4,generator_levels=30,decoder=4,encoder=0)
        assert meter.counts==dict(cheap_features=2,selected_logit_features=2,cue_features=2,decisions=2)
        print('SYNTHETIC_JOINT_REQUESTS 4')
    finally:counter.close()

def test_two_session_pairing_schedule_exact_8_only_history_work():
    entries=[dict(index=i,identity=str(i)) for i in range(101)];pred=[(8,[8]) if i<23 else (11,[8,11]) for i in range(101)]
    for session in (0,1):
        plan=schedule(entries,pred,session);assert len(plan)==2484 and sum(r['warmup'] for r in plan)==60
        assert len({(r['position'],r['repeat'],r['method']) for r in plan if not r['warmup']})==2424
        counts=sum_work(plan);assert counts['inputs']==2484 and counts['generator_levels']<=15801 and counts['decoder']<=2645
        assert all(10 not in r['visits'] for r in plan if r['method']=='controller')
    assert schedule(entries,pred,0)!=schedule(entries,pred,1)

def test_cluster_totals_null_and_five_percent_boundary():
    values=np.full((3,12),100.);values[:,0]=[10,10,90];picks=np.array([[0,1],[0,0],[1,1]])
    np.testing.assert_allclose(cluster_draws(values,['a','a','b'],picks)[:,0],[1-110/300,.9,.1])
    values[:,0]=95;np.testing.assert_allclose(cluster_draws(values,['a','a','b'],picks),.05)
    values[:,0]=100;np.testing.assert_allclose(cluster_draws(values,['a','a','b'],picks),0)

def test_missing_duplicate_and_inadequate_component_timings_reject_before_draws():
    entries=[dict(index=i,identity=str(i),component='same') for i in range(16)];pred=[(11,[8,11])]*16
    with pytest.raises(ValueError,match='Missing'):timing_analysis([],entries,{},'fixed:11',0)
    records=[dict(r,wall_ms=100.,parity=True,work=dict(inputs=1,generator_levels=r['depth'],decoder=len(r['visits']),encoder=0)) for s in (0,1) for r in schedule(entries,pred,s)]
    with pytest.raises(ValueError,match='Inadequate'):timing_analysis(records,entries,{},'fixed:11',0)
    records.append(next(copy.deepcopy(r) for r in records if not r['warmup']))
    with pytest.raises(ValueError,match='duplicate'):timing_analysis(records,entries,{},'fixed:11',0)
