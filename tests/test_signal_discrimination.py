"""Synthetic leakage, rare-class, ranking and decision checks; no checkpoint calls."""
import numpy as np
import pytest
from anytime_ncm.signal_discrimination import labels,fit_ridge,predict,diagnose,decide,analyze
from anytime_ncm.quality_controller import Meter

def test_proxy_boundary_missing_and_unchanged_numeric_domain():
    np.testing.assert_array_equal(labels([[4,0,None,0],[4.00001,0,None,0],[0,0,5,0],[0,0,None,0],[0,0,None,50]]),[0,1,1,0,1])
    for bad in ([[None,0,0,0]],[[0,0,float('inf'),0]],[[0,0,0]]):
        with pytest.raises(ValueError):labels(bad)

def test_rare_or_absent_training_classes_never_fit():
    m=Meter(dict(fits=1));x=np.ones((30,2))
    for y in (np.zeros(30),np.r_[np.ones(9),np.zeros(21)]):assert fit_ridge(x,y,m)['status']=='insufficient_classes'
    assert m.counts['fits']==0

def test_training_only_scaling_constant_and_shifted_validation():
    x=np.column_stack([np.arange(40),np.ones(40)]);y=(x[:,0]>19).astype(float);m=Meter(dict(fits=2));model=fit_ridge(x,y,m)
    assert model['mean']==[19.5,1.] and model['scale'][1]==1
    frozen=str(model);score=predict(model,np.array([[100,1],[200,1]]));assert score[1]>score[0] and str(model)==frozen
    other=fit_ridge(x+np.array([0,99]),y,m)
    np.testing.assert_allclose(predict(model,x),predict(other,x+np.array([0,99])),atol=1e-12)
    assert m.counts['fits']==2


def test_tied_null_reverse_and_single_class_auc():
    y=[0,0,1,1];c=['a','a','b','b']
    assert diagnose(y,[0,0,1,1],c)['auc']==1
    assert diagnose(y,[1,1,0,0],c)['auc']==0
    assert diagnose(y,[.4]*4,c)['auc']==.5
    absent=diagnose([0,0],[.1,.2],['a','b']);assert absent['auc'] is None
    assert all(v['auc'] is None for v in diagnose(y,[0,0,1,1],c)['component_deletion'])

def test_reliability_bins_boundaries_clip_and_dependence_not_new_samples():
    r=diagnose([0,0,1,1,1],[-1,0,.2,.8,2],['same']*5)
    assert [b['n'] for b in r['reliability_bins']]==[2,1,0,0,2]
    assert r['clipping_count']==2 and len(r['component_deletion'])==1
    assert r['component_deletion'][0]['n']==0

def test_invalid_scores_models_and_shapes():
    with pytest.raises(ValueError):diagnose([0,1],[float('nan'),0],['a','b'])
    with pytest.raises(ValueError):fit_ridge([[0],[1]],[0,2],Meter(dict(fits=1)))
    with pytest.raises(ValueError):predict(dict(status='fitted',mean=[0],scale=[0],coef=[0,0]),[[0]])

def test_all_prospective_gate_branches_and_sparse_coverage():
    def reports(c,r,n=20):return {str(d):dict(probes={g:dict(auc=a,adverse=n,nonadverse=n) for g,a in [('cheap',c),('selected_logit',r)]}) for d in (8,10)}
    assert decide(reports(.55,.60))['status']=='richer_probe_supported'
    assert decide(reports(.61,.61))['status']=='joint_probe_supported_without_established_richer_gain'
    assert decide(reports(.59,.59))['status']=='linear_probe_not_supported'
    assert decide(reports(.8,.9,9))['status']=='linear_probe_not_supported'

def test_poisoned_test_outcomes_not_accepted_as_extra_allocation():
    with pytest.raises(ValueError):analyze([dict(index=1,warmup=False),dict(index=999,warmup=False)],{},[1],[],{},Meter(dict(fits=4)))


def test_penalized_normal_equations_and_unpenalized_intercept():
    x=np.arange(80,dtype=float).reshape(40,2);y=np.r_[np.zeros(20),np.ones(20)];m=Meter(dict(fits=1));model=fit_ridge(x,y,m)
    z=np.column_stack([(x-np.asarray(model['mean']))/np.asarray(model['scale']),np.ones(40)]);coef=np.asarray(model['coef'])
    penalty=np.r_[np.full(2,10.),0.]
    np.testing.assert_allclose(z.T@(z@coef-y)+penalty*coef,np.zeros(3),atol=1e-10)
    assert m.counts['fits']==1
    print('SYNTHETIC_PROBE_FITS 3')
