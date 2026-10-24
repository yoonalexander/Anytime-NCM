"""Deterministic synthetic E0 checks. No actual input/output files or study trials."""
import json
import hashlib
import io
import numpy as np
import pytest
from scipy.stats import binomtest
from anytime_ncm.evidence_preflight import (Budget, allocate, cp_upper, cue_interval, crossed_ratio,
    header_inventory, mc_precision, minimum_coverage, order_interval, write_new)


def test_header_only_reader_accepts_poisoned_outcome_body(tmp_path):
    path = tmp_path / 'raw.jsonl'
    path.write_bytes(b'{"identity":"' + b'a'*64 + b'","index":7,"partition":"phase4_final","outcome":POISON}\n')
    assert header_inventory(path) == {('phase4_final', 7, 'a'*64): 1}
    path.write_bytes(b'{"wrong":"identity first required"}\n')
    with pytest.raises(ValueError):
        header_inventory(path)


def fixture_population():
    rows = [{'identity': f'{i:064x}', 'index': i, 'indices': [i]} for i in range(6)]
    return {'partitions': {'exploration': rows[:1], 'reserved': rows[1:]}}, {i: f'input {i}' for i in range(6)}, {
        'role_counts': [2, 1, 1, 1], 'role_order': ['E2', 'E3', 'E4', 'closed'], 'allocation_salt': 'test|'}


def test_allocation_is_disjoint_closed_and_deterministic():
    manifest, sources, lock = fixture_population()
    first, _ = allocate(manifest, sources, lock)
    second, _ = allocate(manifest, sources, lock)
    assert first == second
    rows = [e for entries in first.values() for e in entries]
    assert len({e['identity'] for e in rows}) == 5
    assert all(not e['outcome_access_released'] for e in rows)
    assert all(e['source_text_sha256'] == hashlib.sha256(sources[e['index']].encode()).hexdigest() for e in rows)


@pytest.mark.parametrize('problem', ['source_duplicate', 'identity_duplicate', 'missing', 'noncanonical'])
def test_grouping_fails_closed_without_replacements(problem):
    manifest, sources, lock = fixture_population()
    if problem == 'source_duplicate': sources[1] = sources[0]
    if problem == 'identity_duplicate': manifest['partitions']['reserved'][0]['identity'] = manifest['partitions']['exploration'][0]['identity']
    if problem == 'missing': manifest['partitions']['reserved'].pop()
    if problem == 'noncanonical': manifest['partitions']['reserved'][0]['index'] = 2
    with pytest.raises(ValueError): allocate(manifest, sources, lock)


@pytest.mark.parametrize('n,k', [(8, 0), (8, 2), (8, 8), (256, 0)])
def test_cp_upper_matches_independent_scipy_exact_interface(n, k):
    alpha = .005
    expected = binomtest(k, n, alternative='less').proportion_ci(confidence_level=1-alpha, method='exact').high
    assert cp_upper(k, n, alpha) == pytest.approx(expected, abs=1e-12)


def test_zero_event_is_not_zero_risk_and_coverage_floor_is_minimal():
    for alpha in [.05/(2*89), .005]:
        minimum = minimum_coverage(alpha)
        assert cp_upper(0, minimum, alpha) <= .02
        assert cp_upper(0, minimum-1, alpha) > .02
    interval = cue_interval(np.zeros(256), .05/(2*89))
    assert interval['lower'] < -.02 and interval['upper'] > .02


def test_structural_equality_exception_is_explicit_and_checked():
    assert cue_interval([], .005)['lower'] is None
    assert cue_interval([0, 0], .005, structural=True)['lower'] == 0
    assert cue_interval([0, 0], .005)['lower'] < 0
    with pytest.raises(ValueError): cue_interval([-.1], .005, structural=True)
    with pytest.raises(ValueError): cue_interval([2], .005)


def test_crossed_ratio_preserves_pairing_and_resamples_shared_block_axis():
    base = np.array([[10., 20.], [100., 200.]])
    candidate = base * .9
    ix = np.array([[0, 1], [1, 1], [0, 0]])
    blocks = np.array([[0, 1], [1, 1], [0, 0]])
    assert crossed_ratio(base, candidate, ix, blocks) == pytest.approx([.1, .1, .1])
    assert crossed_ratio(base, base, ix, blocks) == pytest.approx([0., 0., 0.])


def test_extreme_tail_precision_fails_closed_at_small_B():
    assert not mc_precision(10000, .05/(2*89), 89)['quantile_resolved']
    assert mc_precision(100000, .05/(2*89), 89)['quantile_resolved']
    interval = order_interval(np.arange(10000), .05/(2*89), 89)
    assert interval['lower'] is None and interval['upper'] is None


def test_results_refuse_overwrite(tmp_path):
    path = tmp_path / 'receipt.json'
    write_new(path, {'consumed': True})
    with pytest.raises(FileExistsError): write_new(path, {'consumed': False})
    assert json.loads(path.read_text())['consumed']


def test_budget_charges_before_work_and_stops_exactly_at_cap():
    stream = io.StringIO()
    budget = Budget({'trials': 2, 'bootstrap_draws': 3, 'representative_datasets': 1}, stream)
    budget.consume('trials', 2, 'failed attempt still charged')
    with pytest.raises(RuntimeError): budget.consume('trials', 1, 'retry forbidden')
    with pytest.raises(ValueError): budget.consume('trials', -1, 'cannot refund')
    assert budget.counts['trials'] == 2
    assert len(stream.getvalue().splitlines()) == 1
