"""Deterministic synthetic fixtures only; no checkpoint or empirical-data access."""
import io
import math
import numpy as np
import pytest
from scipy.stats import binom, binomtest
from anytime_ncm.q0_statistics import (TAIL, Budget, cp_upper, minimum_coverage,
    cue_interval, eb_upper, power_rows, rank_guard, interval, crossed_savings,
    quality_state, success)

@pytest.mark.parametrize('a,floor',[(.05/178,405),(.05/118,385),(.05,149)])
def test_floor_is_minimal(a,floor):
    assert minimum_coverage(a)==floor
    assert float(cp_upper(0,floor,a)) <= .02
    assert float(cp_upper(0,floor-1,a)) > .02

@pytest.mark.parametrize('n,k',[(1,0),(1,1),(48,0),(48,1),(48,48),(385,0),(1024,20)])
def test_cp_against_independent_scipy_public_api(n,k):
    expected=binomtest(k,n).proportion_ci(confidence_level=1-2*TAIL,method='exact').high
    assert float(cp_upper(k,n))==pytest.approx(expected,abs=2e-10)

@pytest.mark.parametrize('x',[[1.01],[float('nan')],[[0.]]])
def test_invalid_cues(x):
    with pytest.raises(ValueError): cue_interval(x)

@pytest.mark.parametrize('k,n',[(-1,5),(6,5),(.5,5),(0,0)])
def test_invalid_counts(k,n):
    with pytest.raises(ValueError): cp_upper(k,n)

def test_sparse_undefined_and_empirical_equality():
    assert cue_interval([]) is None
    assert cue_interval([0.]*48)[1] > .02
    assert .98**48 > .05
    assert cue_interval([0.]*384)[1] > .02
    assert cue_interval([0.]*385)[1] <= .02

def test_fractional_not_bernoulli_endpoint_and_signs():
    assert cue_interval([.001]*48)==cue_interval([1.]*48)
    lo,hi=cue_interval([1.,-1.])
    assert lo == -hi and 0 < hi < 1
    assert eb_upper(0,0,1) is None
    assert float(eb_upper(0,0,385)) > .02
    assert float(eb_upper(-1024,1024,1024)) < 0

def test_exact_power_matches_enumeration():
    for n in [48,385,1024]:
        counts=np.arange(n+1); accept=cp_upper(counts,n)<=.02
        k,p=power_rows([n])
        assert p[0]==pytest.approx(binom.pmf(counts,n,.005)[accept].sum())
        assert p[0]==pytest.approx(binom.cdf(k[0],n,.005))

def test_dependence_does_not_create_units():
    assert float(cp_upper(0,1024))<=.02
    assert float(cp_upper(0,1024//8))>.02
    assert .98**(1024//8)>TAIL

def test_paired_ratio_and_undefined_cells():
    b=np.array([[10.],[100.]]); c=np.array([[9.],[50.]])
    got=crossed_savings(b,c,np.array([[0,1]]),np.array([[0]]))[0]
    assert got==pytest.approx(1-59/110)
    assert got!=pytest.approx(np.mean(1-c/b))
    with pytest.raises(ValueError): crossed_savings(b,np.zeros_like(b),np.array([[0]]),np.array([[0]]))
    with pytest.raises(ValueError): crossed_savings(b,np.full_like(b,np.nan),np.array([[0]]),np.array([[0]]))

def test_crossed_pair_identity():
    b=np.array([[1.,10.],[3.,5.]])
    assert np.all(crossed_savings(b,b,np.array([[1,0],[0,0]]),np.array([[1,1],[0,1]]))==0)
    assert np.allclose(crossed_savings(b,.9*b,np.array([[1,0],[0,0]]),np.array([[1,1],[0,1]])),.1)

def test_tail_guard_reports_inadequate_draws():
    assert rank_guard(10000)['rank']==0
    assert interval([0.]*10000)['lower'] is None
    assert rank_guard(100000)['rank']==18

def test_budget_failure_charged_before_work():
    stream=io.StringIO(); b=Budget({'trials':2,'bootstrap_draws':1,'datasets':1},stream)
    b.charge('trials',2,'fixture')
    with pytest.raises(RuntimeError): b.charge('trials',1,'exhausted')
    assert b.counts['trials']==2
    assert 'fixture' in stream.getvalue()

def test_quality_and_comparator_rules():
    good={'bleu':(0,.5),'chrf':(0,1),'numeric':(0,.02),'negation':(0,.02)}
    assert quality_state(good)=='certified'
    assert quality_state(dict(good,numeric=None))=='unresolved'
    assert quality_state(dict(good,bleu=(.50001,.6)))=='ruled_out'
    assert quality_state(dict(good,bleu=(.4,.6)))=='unresolved'
    assert success('certified',.05,.001,[.001])
    for state,point,lower,fixed in [('unresolved',.1,.01,[.01]),('certified',.049,.01,[.01]),('certified',.1,0,[.01]),('certified',.1,.01,[None]),('certified',.1,.01,[])]:
        assert not success(state,point,lower,fixed)
