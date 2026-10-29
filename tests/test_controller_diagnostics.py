"""Synthetic descriptive diagnosis checks; zero fitted models or GPU imports."""
import json
import numpy as np
import pytest
from sacrebleu.metrics import BLEU
from anytime_ncm.controller_diagnostics import (auc,joint_truth,exits_from_scores,estimate_cost,timing_header,proxy_audit,diagnosis_decision,errors_and_features)

def test_exact_auc_perfect_reversed_tied_and_no_class():
    assert auc([0,0,1,1],[0,1,2,3])==1
    assert auc([0,0,1,1],[3,2,1,0])==0
    assert auc([0,1],[1,1])==.5
    assert auc([0,0],[0,1]) is None and auc([1],[0]) is None
    with pytest.raises(ValueError):auc([0,1],[0,np.nan])

def test_undefined_numeric_does_not_create_fake_individual_truth_constraint():
    y=np.array([[.2,.5,np.nan,0],[.2,.5,2.,0],[-1.,-2.,np.nan,-1.]])
    np.testing.assert_equal(joint_truth(y),[.5,2,0])

def test_true_history_order_and_threshold_boundary():
    assert exits_from_scores([.5,2,2],[9,.5,2],.5)==[8,10,11]
    with pytest.raises(ValueError):exits_from_scores([0],[0,1],1)

def test_cost_grid_charges_sparse_fallback_and_zero_cost_limit():
    profile={8:80.,10:95.,11:100.}
    assert estimate_cost([11],profile,3.,1.)==106.
    assert estimate_cost([8],profile,3.,2.)==80.
    assert estimate_cost([8,10,11],profile,3.,0.)==pytest.approx(275/3)
    with pytest.raises(ValueError):estimate_cost([9],profile,3.,1.)

def test_metadata_headers_allow_sorted_or_insertion_order_and_skip_poison_body():
    d=dict(request_id=0,session=1,position=2,index=7,identity='a'*64,method='assigned_sparse',depth=8,warmup=False,repeat=0)
    for raw in [json.dumps(d).encode(),json.dumps(d,sort_keys=True).encode()]:
        poison=raw[:-1]+b', "wall_ms": POISON NOT JSON'
        assert timing_header(poison)==dict(request_id=0,session=1,index=7,identity='a'*64)
    with pytest.raises(ValueError):timing_header(b'{}')
    with pytest.raises(ValueError):timing_header(b'{"index":7, "index":8, "wall_ms":0}')

def test_proxy_residual_pairing_and_missing_duplicate_rejection():
    base=dict(index=7,session=0,repeat=0,warmup=False)
    records=[dict(base,method='fixed:'+str(d),depth=d,wall_ms=95 if d==10 else 100.) for d in range(1,12)]
    records.append(dict(base,method='assigned_sparse',depth=10,wall_ms=100.))
    a=proxy_audit(records,3.);assert a['paired_cells']==1 and a['bias_ms']==2. and a['mae_ms']==2.
    with pytest.raises(ValueError):proxy_audit(records[:-2]+records[-1:],3.)
    with pytest.raises(ValueError):proxy_audit(records+[records[0]],3.)

def oracle_policy(a,b):return dict(kind='future_label_oracle',point_pass=True,cost_grid={'0.0':dict(savings=a),'1.0':dict(savings=b)})

@pytest.mark.parametrize('policies,rank,route',[
    ([oracle_policy(.1,.1)],.7,'corpus_objective_design_review'),
    ([oracle_policy(.1,.1)],.6,'richer_causal_signal_study'),
    ([oracle_policy(.1,.1)],None,'richer_causal_signal_study'),
    ([oracle_policy(.1,.01)],.7,'direct_sparse_cost_or_schedule_review'),
    ([oracle_policy(.01,0.)],.7,'label_or_schedule_redesign_before_more_fits')])
def test_prospective_route_decision_tree(policies,rank,route):
    assert diagnosis_decision(policies,{'8':{'joint_unsafe_gt1_auc':rank}})['recommended_route']==route

def test_constant_features_missing_numeric_and_class_imbalance_are_explicit():
    train={};cal={};models={}
    for d in (8,10):
        y=np.zeros((3,4));y[:,2]=np.nan
        train[d]=dict(x=np.zeros((3,19)),y=y,pred=np.ones((3,4)))
        x=np.zeros((3,19));x[:,1]=4
        cal[d]=dict(x=x,y=y,pred=np.ones((3,4)))
        models[str(d)]=dict(mean=[0.]*19,scale=[1.]*19)
    r=errors_and_features(train,cal,models)
    assert r['8']['joint_unsafe_gt1_auc'] is None
    assert r['8']['targets']['numeric_reference_f1']['cal_mae'] is None
    assert len(r['8']['constant_train_features'])==19
    assert r['8']['cal_outside_three_training_scales']['source_length']==3

def test_mean_sentence_bleu_is_not_the_corpus_endpoint():
    refs=['the cat sat on the mat','one two three four five six seven eight nine ten']
    hyps=['the cat sat on the mat','one two'];b=BLEU(effective_order=True)
    mean=np.mean([b.sentence_score(h,[r]).score for h,r in zip(hyps,refs)])
    corpus=BLEU().corpus_score(hyps,[refs]).score
    assert abs(mean-corpus)>1.
    print(json.dumps(dict(synthetic_mean_sentence_bleu=float(mean),synthetic_corpus_bleu=corpus)))
