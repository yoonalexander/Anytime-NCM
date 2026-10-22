"""Executable learned early stops, fallback, scoring and held-out analysis guards."""
from copy import deepcopy
import math
import pytest
import torch
from anytime_ncm.learned_features import FeatureTracker,feature_names,probability,LENGTHS
from anytime_ncm.learned_online import LearnedRunner
from anytime_ncm.phase3 import calibration
from anytime_ncm.online_policy import policy_spec
from pathlib import Path
from tests.test_online import tiny
from tests.test_policy_no_future_leakage import model,states

def test_portable_logistic_probability_known_values_and_extremes():
    m=model();m["intercept"]=0
    assert probability(m,[0]*len(m["weights"]))==.5
    m["intercept"]=1000;assert probability(m,[0]*len(m["weights"]))==1
    m["intercept"]=-1000;assert probability(m,[0]*len(m["weights"]))==0
    with pytest.raises(ValueError):probability(m,[0])

@pytest.mark.parametrize("family",["base","internal"])
@pytest.mark.parametrize("depth",[1,6,12])
def test_learned_callback_really_skips_generator_calls_and_preserves_prefix(family,depth):
    adapter,old,context=tiny();runner=LearnedRunner(adapter,Path(__file__).resolve().parents[1]/"third_party/ncm")
    full=old.request(context[0].tolist(),policy_spec("full"))
    calls=[];h=adapter.generator.transformer.blocks[0].register_forward_pre_hook(lambda *a:calls.append(1))
    result=runner.request(context[0].tolist(),{"kind":"learned","model":model(family,100),"minimum":depth,"threshold":.5})
    h.remove()
    assert len(calls)==result["exit_level"]==depth
    assert torch.equal(result["generated_codes"],full["generated_codes"][:,:sum(LENGTHS[:depth])])
    assert result["inspected_levels"]==[depth] and len(result["learned_trace"])==1

def test_learned_never_stop_fallback_matches_original_full_output():
    adapter,old,context=tiny()
    from pathlib import Path
    runner=LearnedRunner(adapter,Path(__file__).resolve().parents[1]/"third_party/ncm")
    full=old.request(context[0].tolist(),policy_spec("full"))
    result=runner.request(context[0].tolist(),{"kind":"learned","model":model("internal"),"minimum":10,"threshold":1.})
    assert result["exit_level"]==12 and result["decoded_ids"]==full["decoded_ids"]
    assert torch.equal(result["generated_codes"],full["generated_codes"])
    assert result["inspected_levels"]==[10,11,12]
    assert all(t["feature_policy_ms"]>=0 for t in result["learned_trace"])

def test_feature_families_explicit_and_no_verifier_flags():
    assert len(feature_names("base"))==17 and len(feature_names("internal"))==37
    assert not any("valid" in x or "reference" in x or "future" in x for x in feature_names("internal"))
    with pytest.raises(ValueError):feature_names("unknown")

def test_internal_histogram_entropy_concentration_have_independent_expected_values():
    t=FeatureTracker((0,)*91,"internal");f=t.observe(2,[0]*89,[0,1])
    assert f[-4]==pytest.approx(math.log(2)/math.log(16))
    assert f[-3:]==(.5,2/16,1.)

@pytest.mark.parametrize("ids,codes", [([0]*88,[0]),([12]*89,[0]),([0]*89,[16]),([0]*89,[0,0])])
def test_invalid_current_tokens_and_codes_fail(ids,codes):
    with pytest.raises(ValueError):FeatureTracker((0,)*91,"base").observe(1,ids,codes)

def test_calibration_reliability_bins_preserve_endpoints_and_counts():
    c=calibration([0.,.1,.99,1.],[0,0,1,1])
    assert c["states"]==4 and c["positives"]==2 and sum(b["count"] for b in c["bins"])==4
    assert c["bins"][-1]["count"]==2 and c["brier"]==pytest.approx((.1**2+.01**2)/4)
    with pytest.raises(ValueError):calibration([],[])

def test_development_threshold_selection_rejects_early_invalid_predictions():
    from types import SimpleNamespace
    from anytime_ncm.train_policy import select_policy
    rows=[]
    for i in range(400):
        s=states();s[-1]["correctness"]["is_valid_solution"]=True
        rows.append({"partition":"development","sample_id":str(i),"levels":s})
    selected={str(i):SimpleNamespace(puzzle=(0,)*91) for i in range(400)}
    chosen,candidates=select_policy(model(bias=0),rows,selected)
    assert any(c["invalid_early"]==400 for c in candidates)
    assert chosen["minimum"]==10 and chosen["threshold"]==.9 and chosen["invalid_early"]==0
    assert len(candidates)==15

def test_verification_modules_do_not_import_torch_or_sklearn_in_fresh_process():
    import subprocess,sys
    code="import sys;sys.path.insert(0,'src');import anytime_ncm.train_policy,anytime_ncm.phase3;assert 'torch' not in sys.modules;assert 'sklearn' not in sys.modules"
    subprocess.run([sys.executable,"-c",code],check=True)
