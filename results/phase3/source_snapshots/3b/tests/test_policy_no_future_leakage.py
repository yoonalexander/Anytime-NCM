"""Learned policies receive current/past observations, never future labels or identities."""
from copy import deepcopy
import pytest
from anytime_ncm.learned_features import FeatureTracker,feature_names,offline_trace,LENGTHS
from anytime_ncm.phase3 import select_entries
from anytime_ncm.train_policy import matrix

def model(family="base",bias=-100):
    n=len(feature_names(family))
    return {"family":family,"weights":[0.0]*n,"intercept":bias,"mean":[0.0]*n,"scale":[1.0]*n}

def states():
    return [{"decoded_ids":[i%12]*89,"code_ids":[i%16]*length,
             "correctness":{"is_valid_solution":False}} for i,length in enumerate(LENGTHS)]

def test_future_suffix_labels_references_and_identity_cannot_change_early_decision():
    a=states();b=deepcopy(a)
    for s in b[2:]:s["decoded_ids"]=[11]*89;s["code_ids"]=[15]*len(s["code_ids"])
    for s in b:s["correctness"]={"is_valid_solution":True};s["reference"]=[9]*89
    m=model(bias=100)
    assert offline_trace(m,a,(0,)*91,2,.5)==offline_trace(m,b,(0,)*91,2,.5)

def test_input_data_labels_change_targets_but_never_features():
    from types import SimpleNamespace
    row={"sample_id":"a","partition":"exploration","levels":states()}
    e={"a":SimpleNamespace(puzzle=(0,)*91)}
    x,y=matrix([row],e,"internal","exploration")
    other=deepcopy(row)
    for s in other["levels"]:s["correctness"]["is_valid_solution"]=True
    xx,yy=matrix([other],e,"internal","exploration")
    assert x==xx and y!=yy

def test_observation_storage_is_independent_of_caller_mutation():
    tracker=FeatureTracker((0,)*91,"base");ids=[1]*89
    first=tracker.observe(1,ids,[0]);ids[:]=[2]*89
    second=tracker.observe(2,[1]*89,[0,0])
    assert first[-1]==0 and second[-2]==0 and second[-1]==1

def test_skipped_observations_compare_only_previous_inspected_output():
    tracker=FeatureTracker((0,)*91,"base")
    a=tracker.observe(10,[1]*89,[0]*LENGTHS[9]);b=tracker.observe(11,[1]*89,[0]*LENGTHS[10])
    assert a[-2:]==(1.,0.) and b[-2:]==(0.,1.)

def test_internal_features_use_only_current_codebook():
    t=FeatureTracker((0,)*91,"internal")
    with pytest.raises(ValueError):t.observe(2,[0]*89,[0]*sum(LENGTHS[:2]))
    f=t.observe(2,[0]*89,[1,2])
    assert f[len(feature_names("base"))+1]==.5

def test_training_selection_rejects_final_without_release_and_unknown_stage():
    manifest={"partitions":{n:[{"index":i,"puzzle_sha256":str(i)} for i in range(k)]
                            for n,k in (("exploration",1000),("development",400),("phase3_final",300))}}
    assert len(select_entries(manifest,"train"))==1000
    assert len(select_entries(manifest,"development"))==400
    with pytest.raises(ValueError):select_entries(manifest,"3c")
    with pytest.raises(ValueError):select_entries(manifest,"phase2_final")
    assert len(select_entries(manifest,"3c",True))==300

@pytest.mark.parametrize("level",[0,13,True,1.0])
def test_invalid_current_level_rejected(level):
    with pytest.raises(ValueError):FeatureTracker((0,)*91,"base").observe(level,[0]*89,[0])
