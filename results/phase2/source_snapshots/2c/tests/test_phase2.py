"""Frozen candidate selection, protected final access and paired online statistics."""
from copy import deepcopy
from types import SimpleNamespace
import pytest

from anytime_ncm.online_policy import policy_spec, simulated_exit
from anytime_ncm.phase2 import (select_entries,offline_policies,analyze_requests,warm_order,LIMITS)

@pytest.mark.parametrize("kwargs",[
    {"kind":"unknown"},{"kind":"fixed","depth":0},{"kind":"fixed","depth":13},
    {"kind":"verified","levels":[1,2]},{"kind":"verified","levels":[]},{"kind":"verified","levels":[12,10]},
    {"kind":"verified","levels":[1,12],"min_level":2},{"kind":"stability","patience":0},
    {"kind":"stability","min_level":13}])
def test_invalid_policy_boundaries_and_schedules_cannot_be_frozen(kwargs):
    with pytest.raises(ValueError):policy_spec(**kwargs)

def states():
    return [{"cumulative_codes":i+1,"decoded_ids":[i%9+1]*89,
             "correctness":{"is_valid_solution":i==11}} for i in range(12)]

def test_policy_simulation_stability_requires_past_equal_tokens_and_safe_fallback():
    rows=states()
    rows[2]["decoded_ids"]=rows[1]["decoded_ids"][:]
    spec=policy_spec("stability",min_level=2,patience=1)
    assert simulated_exit(spec,rows)==3
    assert simulated_exit(policy_spec("verified",levels=[10,11,12]),rows)==12
    for row in rows:row["correctness"]["is_valid_solution"]=False
    assert simulated_exit(policy_spec("verified",levels=list(range(1,13))),rows)==12

def manifest():
    return {"partitions":{"exploration":[{"index":i} for i in range(1000)],
        "development":[{"index":i} for i in range(1000,1400)],
        "phase2_final":[{"index":i} for i in range(1400,1700)],
        "phase3_final":[{"index":i} for i in range(1700,2000)]}}

def test_final_access_is_denied_before_policy_freeze():
    with pytest.raises(ValueError,match="policy lock"):select_entries(manifest(),"2c")
    with pytest.raises(ValueError):select_entries(manifest(),"phase3_final")

def test_final_selection_never_materializes_phase3_identities():
    lock={"status":"frozen","phase3_final_access":False}
    rows=select_entries(manifest(),"2c",lock)
    assert len(rows)==300 and {r["partition"] for r in rows}=={"phase2_final"}
    assert [r["index"] for r in rows]==list(range(1400,1700))

def test_development_and_exploration_access_counts_are_bounded():
    assert len(select_entries(manifest(),"2a"))==32
    assert len(select_entries(manifest(),"2b"))==100
    assert len(select_entries(manifest(),"warmup"))==10

def test_offline_selection_rejects_unsafe_stability_and_keeps_strong_fixed_depth():
    rows=[{"partition":"development","levels":deepcopy(states())} for _ in range(400)]
    for row in rows:
        row["levels"][2]["decoded_ids"]=row["levels"][1]["decoded_ids"][:]
    fixed=[{"level":i+1,"collection_valid_rate":int(i==11),"mean_estimated_ms":i+1} for i in range(12)]
    selected=offline_policies(rows,{"fixed_depth_comparison":{"development":fixed}})
    assert selected["fixed_depth"]==12 and len(selected["methods"])==7
    bad=next(c for c in selected["stability_candidates"] if c["spec"]["min_level"]==2 and c["spec"]["patience"]==1)
    assert bad["invalid_early"]==400 and not bad["feasible"]
    assert selected["selected_stability"]["feasible"]

def test_balanced_orders_rotate_without_dropping_a_method():
    methods={"a":{},"b":{},"c":{}}
    orders=[warm_order(methods,i) for i in range(3)]
    assert [x[0] for x in orders]==["a","b","c"]
    assert all(set(x)==set(methods) for x in orders)

def paired_fixture():
    examples=[SimpleNamespace(identity=str(i)) for i in range(3)]
    methods={"full":policy_spec("full"),"fixed":policy_spec("fixed")}
    rows=[]
    for e in examples:
        for repeat in range(3):
            for name in methods:
                rows.append({"sample_id":e.identity,"repeat":repeat,"method":name,"decoded_ids":[1]*89,
                    "generated_codes":[0]*322,"exit_level":12,"valid":True,"false_early_accept":False,
                    "wall_ms":100.0 if name=="full" else 90.0,"gpu_elapsed_ms":80.0,"peak_allocated_bytes":100,
                    "generator_levels":12,"inspected_levels":[]})
    return rows,methods,examples

def test_bootstrap_retains_three_paired_repeats_and_detects_measured_improvement():
    rows,methods,examples=paired_fixture()
    result=analyze_requests(rows,methods,examples)
    paired=result["fixed"]["paired_vs_full"]
    assert paired["seed"]==20261022 and paired["resamples"]==10000
    assert paired["repeats_per_identity"]==3 and paired["identities"]==3
    assert paired["relative_mean_reduction"]==pytest.approx(.1)
    assert result["fixed"]["gate_vs_full"]=="go"

@pytest.mark.parametrize("change",["missing","duplicate","final_parity","repeat_drift"])
def test_missing_pairs_and_deterministic_output_disagreements_are_rejected(change):
    rows,methods,examples=paired_fixture()
    if change=="missing":rows.pop()
    elif change=="duplicate":rows[-1]=deepcopy(rows[0])
    elif change=="final_parity":rows[-1]["decoded_ids"]=[2]*89
    else:
        for row in rows:
            if row["sample_id"]=="2" and row["repeat"]==2:row["decoded_ids"]=[2]*89
    with pytest.raises(ValueError):analyze_requests(rows,methods,examples)

def test_phase_caps_include_warmups_and_are_not_batched_call_claims():
    assert sum(v["inputs"] for v in LIMITS.values())==6912
    assert sum(v["generator_levels"] for v in LIMITS.values())==82400
    assert sum(v["decoder"] for v in LIMITS.values())==45694
