"""Pure schedule, ratio and fail-fast environment tests; no model API calls."""
import json
import numpy as np
import pytest
from anytime_ncm.first_timing_diagnostic import plans,paired_draws
from anytime_ncm.evaluation_reporting import native_environment
from anytime_ncm.controller_study import sum_work

def test_two_methods_complete_pairing_year_identity_and_exact_cap():
    entries=[dict(year=2015+i%6,index=i//6,identity=str(i)) for i in range(1188)];pred=[(8,[8]) if i%4==0 else (11,[8,11]) for i in range(1188)]
    for session in (0,1):
        plan=plans(entries,pred,session);assert len(plan)==2386 and sum(r['warmup'] for r in plan)==10
        assert len({(r['position'],r['method']) for r in plan if not r['warmup']})==2376
        assert all(r['year']==entries[r['position']]['year'] and r['index']==entries[r['position']]['index'] for r in plan)
        w=sum_work(plan);assert w['inputs']==2386 and w['generator_levels']<=26246 and w['decoder']<=3579 and w['encoder']==0
        assert plan==plans(entries,pred,session)
    with pytest.raises(ValueError):plans(entries[:-1],pred,0)

def test_whole_component_input_weights_null_five_percent_boundary_and_invalid():
    cells=np.array([[10.,100.],[10.,100.],[90.,100.]]);picks=np.array([[0,1],[0,0],[1,1]])
    np.testing.assert_allclose(paired_draws(cells,['a','a','b'],picks),[1-110/300,.9,.1])
    cells[:,0]=95;np.testing.assert_allclose(paired_draws(cells,['a','a','b'],picks),.05)
    cells[:,0]=100;np.testing.assert_allclose(paired_draws(cells,['a','a','b'],picks),0.)
    with pytest.raises(ValueError):paired_draws(cells,['a','a','a'],picks)
    cells[0,0]=np.nan
    with pytest.raises(ValueError):paired_draws(cells,['a','a','b'],picks)

def test_full_worker_receipt_normalizes_before_any_request_and_failure_path():
    class Version(str):pass
    info=dict(environment=native_environment(dict(torch=Version('2.10.0+cu128'),cuda='12.8',physical_gpu_bytes=8546484224)),state_before=dict(generator='x',tokenizer='y'),prefix_calls=1188)
    assert json.loads(json.dumps(info))==info
    assert json.loads(json.dumps(dict(info,error='invented')))==dict(info,error='invented')
