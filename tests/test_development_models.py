"""Prospective classical-model and ablation tests on invented arrays only."""
import copy
import numpy as np
import pytest
from anytime_ncm.development_models import COLUMNS,fit_model,predict_model,candidate_specs,decide
from anytime_ncm.quality_controller import Meter

def test_exact_ablation_columns_no_identity_or_future_inputs():
    assert {k:len(v) for k,v in COLUMNS.items()}==dict(cheap=19,logit=22,cue=24,full=27)
    assert COLUMNS['cue']==tuple(range(19))+tuple(range(22,27))
    assert set(COLUMNS['full'])==set(range(27))

def test_ridge_fit_only_scaling_and_unchanged_prediction_model():
    x=np.column_stack([np.arange(100),np.ones(100)]);y=(x[:,0]>49).astype(float);meter=Meter(dict(fits=1));model=fit_model(x,y,'ridge',meter);frozen=copy.deepcopy(model)
    assert model['mean']==[49.5,1.] and model['scale'][1]==1 and model['penalty']==10.
    pred=predict_model(model,np.array([[100,1],[200,1]]));assert pred[1]>pred[0] and model==frozen and meter.counts['fits']==1

def test_depth_three_tree_learns_supported_interaction_with_training_only_thresholds():
    x=np.repeat(np.array([[0,0],[0,1],[1,0],[1,1]],dtype=float),32,axis=0);y=(x[:,0]*x[:,1]).astype(float);m=Meter(dict(fits=1,tree_thresholds=126));model=fit_model(x,y,'tree',m)
    np.testing.assert_array_equal(predict_model(model,x),y);assert m.counts['fits']==1 and m.counts['tree_thresholds']<=126 and model['root']['feature']==0
    assert set(np.unique(predict_model(model,[[.2,.2],[99,99]])))<={0.,1.}

def test_rare_or_absent_classes_skip_and_constant_features_are_explicit_leaf():
    x=np.ones((128,2));m=Meter(dict(fits=1,tree_thresholds=126))
    for y in [np.zeros(128),np.r_[np.ones(19),np.zeros(109)]]:assert fit_model(x,y,'tree',m)['status']=='insufficient_classes'
    assert m.counts['fits']==0
    model=fit_model(x,np.r_[np.zeros(64),np.ones(64)],'tree',m);assert 'feature' not in model['root'];np.testing.assert_array_equal(predict_model(model,x),np.full(128,.5));assert m.counts['fits']==1

def test_tree_depth_leaf_size_and_split_budget_bounds():
    x=np.arange(240,dtype=float)[:,None];y=(x[:,0]>119).astype(float);m=Meter(dict(fits=1,tree_thresholds=63));model=fit_model(x,y,'tree',m)
    def visit(n,depth):
        assert depth<=3
        if 'feature' in n:
            assert n['gain']>1e-12 and n['left']['n']>=32 and n['right']['n']>=32;visit(n['left'],depth+1);visit(n['right'],depth+1)
    visit(model['root'],0);assert m.counts['fits']==1 and m.counts['tree_thresholds']<=63
    print('SYNTHETIC_DEVELOPMENT_FITS 4')

def test_bounded_candidates_exact_threshold_guard_and_unused_feature_isolation():
    models={method:{str(d):{} for d in (8,10)} for method in ('ridge','tree')}
    for d in (8,10):
        for group,columns in COLUMNS.items():models['ridge'][str(d)][group]=dict(status='fitted',method='ridge',mean=[0]*len(columns),scale=[1]*len(columns),coef=[0]*len(columns)+[.2])
        for group in ('cheap','full'):models['tree'][str(d)][group]=dict(status='fitted',method='tree',n_features=len(COLUMNS[group]),root=dict(probability=.2))
    specs=candidate_specs(models);assert len(specs)==241 and len({s['name'] for s in specs})==241
    spec=next(s for s in specs if s.get('method')=='ridge' and s.get('group')=='cheap' and s['decision_levels']==[8] and s['threshold']==.2 and not s['cue_guard']);v=np.r_[np.zeros(25),[1.,1.]]
    assert decide(spec,8,v);v[19:25]=1e6;assert decide(spec,8,v)
    spec=copy.deepcopy(spec);spec['cue_guard']=True;v[25]=0;assert not decide(spec,8,v)
    with pytest.raises(ValueError):decide(spec,10,v)

def test_invalid_arrays_models_and_family_reject_before_fit():
    meter=Meter(dict(fits=1,tree_thresholds=63))
    with pytest.raises(ValueError):fit_model([[0],[1]],[0,2],'tree',meter)
    with pytest.raises(ValueError):fit_model([[0],[1]],[0,1],'unknown',meter)
    with pytest.raises(ValueError):predict_model(dict(method='tree',status='fitted',n_features=1,root=dict(probability=float('nan'))),[[0]])
    assert meter.counts['fits']==0
