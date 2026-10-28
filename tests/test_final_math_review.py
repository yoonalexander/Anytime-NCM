"""Invented deterministic cases only; no metadata files, models or randomness."""
from fractions import Fraction as F
import json,math
import pytest
from anytime_ncm.final_math_review import *

@pytest.mark.parametrize('J',[1,2,10,64])
def test_equal_weights_sharp_formula(J):
    z=zero_extremum([2]*J,F(1,50));assert z['probability']==F(49,50)**J
    assert sum((F(c,2*J)*p for c,p in zip(z['active_counts'],z['probabilities'])),F(0))==F(1,50)

def test_single_heavy_component():
    z=zero_extremum([0,1,3,9],F(1,50))
    assert z['active_counts']==[9] and z['probability']==1-F(13,450)

def test_active_boundary_tie():
    z=zero_extremum([1,3],F(1,2));assert z['tau']==1 and z['probability']==F(1,3)

def test_exact_endpoints_and_empty():
    assert zero_extremum([1,3],0)['probability']==1
    assert zero_extremum([1,3],1)['probability']==0
    assert zero_extremum([0,0],F(1,50)) is None
    assert sharp_zero_bracket([0,0]) is None

@pytest.mark.parametrize('counts,delta',[([-1,2],F(1,50)),([True,2],F(1,50)),([1.5,2],F(1,50)),([1,2],.02),([1,2],-1),([1,2],2)])
def test_invalid(counts,delta):
    with pytest.raises(ValueError):zero_extremum(counts,delta)

def test_permutation_and_zero_invariance():
    a=zero_extremum([1,2,5,9],F(201,10000));b=zero_extremum([9,0,5,1,2],F(201,10000));assert a==b
    assert zero_extremum([1,2,5,9],F(1,100))['probability']>a['probability']

def test_full_weight_optimality_conditions():
    counts=[1,2,5,9];z=zero_extremum(counts,F(3,10));t=z['tau'];C=sum(counts)
    assert sum((max(F(0),F(c)-t) for c in counts),F(0))==F(3,10)*C
    assert all(0<p<1 for p in z['probabilities'])
    assert all(c>t for c in z['active_counts'])
    assert all(c<=t for c in sorted(counts,reverse=True)[len(z['active_counts']):])

def test_root_bracket_conservative():
    lo,hi=sharp_zero_bracket([1]*20,'1/40',steps=16)
    assert hi-lo==F(1,65536)
    assert zero_extremum([1]*20,lo)['probability']>F(1,40)
    assert zero_extremum([1]*20,hi)['probability']<=F(1,40)

@pytest.mark.parametrize('delta',[F(1,100),F(1,50),F(201,10000)])
def test_independent_equal_top_witness(delta):
    counts=[1,2,5,9];s=equal_top_witness(counts,delta)
    assert F(s['top_count_total'],sum(counts))*s['event_probability']==delta
    assert s['probability']==(1-s['event_probability'])**s['k']
    assert s['probability']<=zero_extremum(counts,delta)['probability']

def profiles():return {'development':{'inputs':[2,3],'numeric':[0,1]},'confirmation':{'inputs':[4],'numeric':[2]}}
def raw(p=None):return b'{"rows":["'+bytes([255])+b'"],\n  "profiles": '+json.dumps(profiles() if p is None else p).encode()+b'\n}\n'

def test_profile_selection_never_decodes_excluded_bytes():
    assert extract_profiles(raw())==profiles()
    with pytest.raises(UnicodeDecodeError):raw().decode('utf-8')

@pytest.mark.parametrize('fault',['missing','duplicate','bad_counts','extra_field','size'])
def test_profile_guards(fault):
    data=raw()
    if fault=='missing':data=data.replace(b'"profiles"',b'"other"')
    elif fault=='duplicate':data+=b'\n  "profiles": {}'
    elif fault=='bad_counts':p=profiles();p['development']['numeric']=[3,1];data=raw(p)
    elif fault=='extra_field':p=profiles();p['confirmation']['rows']=[];data=raw(p)
    with pytest.raises(ValueError):extract_profiles(data,max_bytes=2 if fault=='size' else 1<<20)

def test_inference_targets_are_different():
    examples=target_counterexamples()
    parse=lambda v:F(v['numerator'])/F(v['denominator'])
    assert parse(examples[0]['expected_realized_ratio'])==F(1,2)
    assert parse(examples[0]['ratio_of_expected_totals'])==F(1,10)
    assert parse(examples[1]['expected_realized_ratio'])==F(1,100)
    assert parse(examples[1]['ratio_of_expected_totals'])==F(100,199)

def test_alpha_constraint_is_a_limit_even_without_an_optimizer():
    s=equal_top_witness([20,20,1,1],F(201,10000));alpha=F(1,40)
    assert s['probability']>alpha
    assert alpha/s['probability']<F(4,5)
