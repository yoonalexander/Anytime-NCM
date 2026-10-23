"""Evidence-boundary regressions for the offline viewer and saved-risk bridge."""
import copy
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

import pytest
from anytime_ncm.viewer import (canonical,cf_identity,checked_probabilities,embed,
                                exact_cf_state,policy_request,sudoku_level)

BOARD="123456789456789123789123456234567891567891234891234567345678912678912345912345678"


def sample():
    states=[{"level":n,"codes":[n%16],"text":BOARD} for n in range(1,13)]
    return {"cf_identity":hashlib.sha256(BOARD.encode()).hexdigest(),"levels":states}


def observed():
    s=sample()
    return {"available_feature_version":"sudoku-full-prefix-v2","puzzle_id":s["cf_identity"],
            "level":6,"predicted_board":BOARD,"codes_prefix":[r["codes"] for r in s["levels"][:6]]}


def test_canonical_identity_is_explicit_conversion():
    tokens=[11]+[int(c) if c!="|" else 10 for c in "|".join(BOARD[i:i+9] for i in range(0,81,9))]+[11]
    assert len(tokens)==91 and canonical(tokens)==BOARD
    assert cf_identity(tokens)==hashlib.sha256(BOARD.encode()).hexdigest()
    assert cf_identity(tokens)!=hashlib.sha256(json.dumps(tokens,separators=(",",":")).encode()).hexdigest()


def test_exact_recorded_state_joins():
    s=sample()
    assert exact_cf_state(s,s["levels"][5],observed())


@pytest.mark.parametrize("field,value",[
    ("available_feature_version","old"),("puzzle_id","0"*64),("level",7),
    ("predicted_board","9"+BOARD[1:]),("codes_prefix",[[0]]*6),
])
def test_incompatible_state_never_receives_risk(field,value):
    r=observed();r[field]=value;s=sample()
    assert not exact_cf_state(s,s["levels"][5],r)


def test_future_codes_are_not_part_of_join():
    s=sample();r=observed();s["levels"][6]["codes"]=[15]
    assert exact_cf_state(s,s["levels"][5],r)


def table():
    return {"puzzle_ids":["a"],"probabilities":{"input_decoded":[.2],"input_decoded_latent":[.3]}}


@pytest.mark.parametrize("value",[float("nan"),float("inf"),-.01,1.01,True,"0.1",None])
def test_invalid_probabilities_rejected(value):
    t=table();t["probabilities"]["input_decoded"]=[value]
    with pytest.raises(ValueError):checked_probabilities(t)


def test_missing_scores_are_not_zero_filled():
    t=table();t["probabilities"]["input_decoded"]=[]
    with pytest.raises(ValueError):checked_probabilities(t)


def test_duplicate_forecast_id_rejected():
    t=table();t["puzzle_ids"]=["a","a"]
    with pytest.raises(ValueError):checked_probabilities(t)


def test_forecast_labels_cannot_change_bridge_scores():
    t=table();t["failure"]=[1]
    first=checked_probabilities(t);t["failure"]=[0]
    assert checked_probabilities(t)==first


def request_group():
    return [{"repeat":r,"exit_level":12,"decoded_text":BOARD,"wall_ms":100+r,
             "inspected_levels":[10,11,12],"learned_trace":[{"level":10,"probability":.2}]} for r in range(3)]


def test_timing_keeps_all_repeats_and_target_name():
    p=policy_request(request_group(),sample())
    assert p["wall_ms"]==[100,101,102] and p["mean_ms"]==101
    assert p["sufficiency_probability"]=={"10":.2}
    assert "continuation_value" not in p


@pytest.mark.parametrize("mutation",["missing","duplicate","output","exit","time","probability"])
def test_wrong_online_evidence_rejected(mutation):
    g=request_group()
    if mutation=="missing":g.pop()
    if mutation=="duplicate":g[2]["repeat"]=1
    if mutation=="output":g[0]["decoded_text"]="wrong"
    if mutation=="exit":g[0]["exit_level"]=11
    if mutation=="time":g[0]["wall_ms"]=float("nan")
    if mutation=="probability":g[1]["learned_trace"][0]["probability"]=.3
    with pytest.raises(ValueError):policy_request(g,sample())


def test_sudoku_current_and_reference_issues_are_separate():
    row={"level":1,"decoded_text":BOARD,"decoded_ids":[int(c) for c in BOARD],
         "correctness":{"is_valid_solution":True},"code_ids":[1]}
    result=sudoku_level(row,"0"*81,BOARD)
    assert result["issues"]=={"blank cells":0,"clue violations":0,"invalid row/column/box units":0}
    assert result["offline"]=={"wrong reference cells":0} and result["continuation_value"] is None


def test_script_closing_tags_and_html_are_inert_json():
    attack='</script><img src=x onerror=alert(1)>&\u2028'
    html=embed("<html><!--DATA--></html>",{"source":attack})
    assert html.count("</script>")==1 and "<img" not in html
    raw=html.split('type="application/json">')[1].split("</script>")[0]
    assert json.loads(raw)["source"]==attack


def test_no_optional_ml_imports_in_fresh_process():
    src=str(Path(__file__).resolve().parents[1]/"src")
    code="import sys;sys.path.insert(0,"+repr(src)+");import anytime_ncm.viewer;assert not {'torch','numpy','transformers','sacrebleu'} & sys.modules.keys()"
    subprocess.run([sys.executable,"-c",code],check=True)

def test_matching_text_with_different_generated_codes_rejected():
    g=request_group()
    for row in g:row["generated_codes"]=[0]*12
    with pytest.raises(ValueError,match="codes differ"):
        policy_request(g,sample())
