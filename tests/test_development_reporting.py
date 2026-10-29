"""Invented NumPy/native report parity; no references or model work."""
from pathlib import Path
import json,sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from run_development_collection import support
from anytime_ncm.development_reporting import plain

def test_reproduces_numpy_boolean_serialization_failure_and_preserves_value():
    v=dict(ready=np.bool_(True),missing=None,count=np.int64(3),rate=np.float64(.25))
    with pytest.raises(TypeError):json.dumps(v,allow_nan=False)
    p=plain(v);assert p==dict(ready=True,missing=None,count=3,rate=.25)
    assert json.loads(json.dumps(p,allow_nan=False))==p and type(p['ready'])is bool and type(p['count'])is int

def test_support_same_statistics_for_numpy_and_native_labels():
    entries=[dict(year=2015,index=i,role='development_fit' if i<30 else 'development_calibration',component=str(i//3)) for i in range(60)]
    values={str(e['year'])+':'+str(e['index']):{str(d):[np.float64(5 if e['index']%2 else 0),np.float64(0),None,np.float64(0)] for d in (8,10)} for e in entries}
    with pytest.raises(TypeError):json.dumps(support(values,entries),allow_nan=False)
    repaired=plain(support(values,entries));native=json.loads(json.dumps(plain(values)));assert repaired==support(native,entries)
    assert repaired['roles']['development_fit']['levels']['8']['adverse']==15 and repaired['roles']['development_fit']['levels']['8']['endpoints']['numeric_reference_f1']['missing']==30
    assert not repaired['fit_cue_endpoint_heads_meet_5each_sanity_floor'] and not repaired['Q0_passed']

def test_recursive_exact_numeric_values_none_and_no_input_mutation():
    raw=dict(x=[np.float32(.5),np.int32(-2),np.bool_(False),None],nested=dict(y=np.float64(1e-9)))
    p=plain(raw);assert p==dict(x=[.5,-2,False,None],nested=dict(y=1e-9)) and isinstance(raw['x'][0],np.generic)
    assert plain(p)==p

def test_nonfinite_unsupported_and_nonstring_keys_reject():
    for v in [float('nan'),np.float64(float('inf')),np.array([1]),{1:'bad'}]:
        with pytest.raises((ValueError,TypeError)):plain(v)
