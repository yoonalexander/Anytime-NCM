"""Deterministic fixtures only, no empirical or checkpoint access."""
import numpy as np
import pytest
from anytime_ncm.q0_multiplicity import CLAIM, EXCLUSION, joint_gate, bounds_gate
from anytime_ncm.q0_statistics import cp_upper, minimum_coverage, power_rows
from scipy.stats import binom


def fixtures():
    return np.zeros(4),np.zeros(11),np.ones((10,4))

@pytest.mark.parametrize('j',range(4))
def test_every_quality_endpoint_required(j):
    q,c,e=fixtures(); q[j]=CLAIM+.00001
    assert not joint_gate(q,c,e,.1)[0]
    q[j]=CLAIM
    assert joint_gate(q,c,e,.1)[0]

@pytest.mark.parametrize('d',range(11))
def test_every_fixed_depth_required(d):
    q,c,e=fixtures(); c[d]=CLAIM+.001
    assert not joint_gate(q,c,e,.1)[0]
    if d<10:
        e[d,0]=EXCLUSION
        passed,excluded=joint_gate(q,c,e,.1)
        assert passed and excluded[d]

@pytest.mark.parametrize('point,expected',[(.049,False),(.05,True),(.1,True),(float('nan'),False)])
def test_point_threshold(point,expected):
    assert bool(joint_gate(*fixtures(),point)[0]) is expected

@pytest.mark.parametrize('kind',['quality','cost','exclusion'])
def test_unavailable_is_never_a_favorable_route(kind):
    q,c,e=fixtures()
    if kind=='quality':q[2]=np.nan
    elif kind=='cost':c[2]=np.nan
    else:
        c[2]=.5; e[2,:]=np.nan
    assert not joint_gate(q,c,e,.1)[0]


def test_excluded_depth_cannot_hide_missing_timing():
    q,c,e=fixtures(); c[0]=np.nan; e[0,0]=0
    assert not joint_gate(q,c,e,.1)[0]
    assert not joint_gate(*fixtures(),.1,complete=False)[0]

@pytest.mark.parametrize('bad',[-.01,1.01,float('inf')])
def test_invalid_p_values_rejected(bad):
    q,c,e=fixtures(); q[0]=bad
    with pytest.raises(ValueError):joint_gate(q,c,e,.1)


def test_no_missing_comparators_or_extra_candidates():
    q,c,e=fixtures()
    with pytest.raises(ValueError):joint_gate(q,c[:-1],e,.1)
    with pytest.raises(ValueError):joint_gate(q,c,e[:9],.1)
    with pytest.raises(ValueError):joint_gate(np.zeros((2,4)),c,e,.1)


def test_bound_orientations_and_strict_exclusion():
    q=np.array([.5,1.,.02,.02]); f=np.zeros((10,4)); s=np.ones(11)*.01
    assert bounds_gate(q,f,s,.05)['global_go']
    s[0]=0.; f[0,0]=.5
    assert not bounds_gate(q,f,s,.1)['global_go']
    f[0,0]=.500001
    result=bounds_gate(q,f,s,.1)
    assert result['global_go'] and result['excluded_depths']==[1]
    assert 11 in result['retained_depths']
    s[10]=0.
    assert not bounds_gate(q,f,s,.1)['global_go']


def test_sparse_bounds_do_not_exclude_or_certify():
    q=np.array([.1,.1,float(cp_upper(0,48,CLAIM)),.0]); f=np.full((10,4),np.nan); s=np.ones(11)
    assert not bounds_gate(q,f,s,.1)['global_go']
    assert bounds_gate(q,f,s,.1)['excluded_depths']==[]
    assert minimum_coverage(CLAIM)==183
    assert float(cp_upper(0,182,CLAIM))>.02
    assert float(cp_upper(0,183,CLAIM))<=.02
    assert minimum_coverage(CLAIM,.01)==368

@pytest.mark.parametrize('n',[48,183,192,240,384,512,1024])
def test_exact_power_inverts_same_test(n):
    k,p=power_rows([n],alpha=CLAIM,alternative=.005)
    counts=np.arange(n+1); passing=cp_upper(counts,n,CLAIM)<=.02
    assert p[0]==pytest.approx(binom.pmf(counts,n,.005)[passing].sum())
    assert p[0]==pytest.approx(binom.cdf(k[0],n,.005))


def test_simultaneous_exclusion_allocation():
    assert 40*EXCLUSION==pytest.approx(.025)
    assert CLAIM+40*EXCLUSION==pytest.approx(.05)
    assert CLAIM+4*EXCLUSION<=.05


def test_no_model_libraries_imported():
    import sys
    assert not any(m == 'torch' or m.startswith('torch.') or m == 'transformers' or m.startswith('transformers.') for m in sys.modules)
