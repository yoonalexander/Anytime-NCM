"""Synthetic metadata-only allocation, contamination and budget checks."""
import copy,hashlib
import pytest
from anytime_ncm.development_eligibility import allocate,summarize,feasible,ROLES

def h(v):return hashlib.sha256(str(v).encode()).hexdigest()
def rows(n=20):
    out=[]
    for component in range(n):
        for j in range(3):out.append(dict(year=2015,index=len(out),identity=h('input'+str(len(out))),component=h('doc'+str(component)),role='confirmation' if component>=n-5 else 'development'))
    return out

def test_hash_allocation_order_invariance_whole_groups_no_confirmation_reallocation():
    data=rows();a=allocate(data);assert a==allocate(list(reversed(data)))
    assert [len(a['parts'][k]) for k in ROLES]==[27,9,9]
    groups=[{r['component'] for r in a['parts'][k]} for k in ROLES]
    assert not(groups[0]&groups[1] or groups[0]&groups[2] or groups[1]&groups[2])
    assert not {r['identity'] for p in a['parts'].values() for r in p}&{r['identity'] for r in data if r['role']=='confirmation'}
    assert all(r['prior_role']=='development' for p in a['parts'].values() for r in p)

def test_duplicate_identity_key_and_cross_role_components_reject():
    data=rows()
    for change in ('identity','index'):
        bad=copy.deepcopy(data);bad[1][change]=bad[0][change]
        with pytest.raises(ValueError,match='Duplicate'):allocate(bad)
    bad=copy.deepcopy(data);bad[-1]['component']=bad[0]['component']
    with pytest.raises(ValueError,match='crossed'):allocate(bad)

def test_schema_poison_outcomes_and_oversize_component_reject():
    data=rows();data[0]['quality']=.9
    with pytest.raises(ValueError,match='Invalid'):allocate(data)
    data=rows(50)
    for row in data:row['role']='development';row['component']=h('same')
    with pytest.raises(ValueError,match='cap'):allocate(data)

def test_floor_rounding_empty_small_support_and_no_invented_cue_counts():
    a=allocate(rows(8));s=summarize(a);assert [v['components'] for v in s.values()]==[1,0,2]
    assert all(v['numeric_coverage']=='not inspected by role' for v in s.values())
    charge={k:0 for k in ('model_requests','model_orchestration_seconds','cpu_seconds','real_fits','controller_families','download_bytes','artifact_bytes','confirmation_evaluations','paid_dollars')};caps=dict.fromkeys(charge,10**9)
    assert feasible(s,charge,caps)['status']=='development_extension_not_supported'

def test_future_capacity_not_execution_and_budget_boundary():
    s={k:dict(inputs=n,components=g) for k,n,g in zip(ROLES,(3000,1000,1000),(178,59,60))};charge={k:0 for k in ('model_requests','model_orchestration_seconds','cpu_seconds','real_fits','controller_families','download_bytes','artifact_bytes','confirmation_evaluations','paid_dollars')};caps=dict.fromkeys(charge,10**9)
    decision=feasible(s,charge,caps);assert decision['status']=='development_extension_metadata_supported' and decision['actual_new_model_requests']==0 and not decision['confirmation_ready']
    caps['model_requests']=decision['planned_future_envelope']['model_requests'];assert feasible(s,charge,caps)['resource_capacity_ready']
    charge['model_requests']=1;assert not feasible(s,charge,caps)['resource_capacity_ready']
