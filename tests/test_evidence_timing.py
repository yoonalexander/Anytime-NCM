"""E1 synthetic CPU tests. No released-checkpoint inference or output access."""
from collections import Counter
import importlib.util
from pathlib import Path
import numpy as np
import pytest
import torch
from test_phase4 import tiny
from anytime_ncm.evidence_timing import make_schedule, validate_schedule, analyze
from anytime_ncm.forced_wmt import forced_request, ForwardCounter
from anytime_ncm.upstream_adapter import reconstruct_prefixes
from anytime_ncm.wmt_data import identity


def entries():
    return [{'identity': f'{i:064x}', 'index': i, 'indices': [i]} for i in range(16)]


def test_exact_schedule_budget_and_balanced_paired_orders():
    plan = make_schedule(entries())
    assert plan == make_schedule(entries())
    assert sum(r['phase'] == 'warmup' for r in plan) == 40
    assert sum(r['phase'] == 'timed' for r in plan) == 960
    assert sum(r['depth'] for r in plan) == 6600
    assert sum(1 if r['schedule'] == 'terminal' else r['depth'] for r in plan) == 3800
    for cell in {(r['schedule'], r['depth']) for r in plan}:
        counts = Counter(r['order'] for r in plan if r['phase'] == 'timed' and (r['schedule'], r['depth']) == cell)
        assert max(counts.values()) - min(counts.values()) <= 1


@pytest.mark.parametrize('problem', ['missing', 'duplicate', 'forbidden', 'depth', 'warmup'])
def test_schedule_changes_rejected(problem):
    plan = make_schedule(entries())
    if problem == 'missing': plan.pop()
    if problem == 'duplicate': plan[30] = dict(plan[31])
    if problem == 'forbidden': plan[0]['identity'] = 'f'*64
    if problem == 'depth': plan[0]['depth'] = 2
    if problem == 'warmup': plan[0]['phase'] = 'timed'
    with pytest.raises(ValueError): validate_schedule(plan, entries())


@pytest.mark.parametrize('depth', [1, 4, 7, 10, 11])
@pytest.mark.parametrize('schedule', ['terminal', 'every_level'])
def test_forced_exit_skips_real_tiny_model_work_and_preserves_every_prefix(depth, schedule):
    model, context = tiny()
    full = model.net.generate(None, context, **model.kwargs)
    snapshots = reconstruct_prefixes(model.vq, full)
    with torch.no_grad():
        expected = [model.pick(model.tokenizer.vqvae.decoder(z))[0].tolist() for z in snapshots]
    limit = {'inputs': 1, 'generator_levels': depth, 'decoder': 1 if schedule == 'terminal' else depth, 'encoder': 0}
    counter = ForwardCounter(model, limit)
    try:
        counter.take('inputs')
        result = forced_request(model, 'synthetic only', depth, schedule)
        assert counter.counts == limit
        assert torch.equal(result['codes'], full[:, :sum(model.vq.levels[:depth])])
        assert result['ids'] == expected[depth-1]
        assert [x['level'] for x in result['observations']] == ([depth] if schedule == 'terminal' else list(range(1, depth+1)))
        assert all(x['ids'] == expected[x['level']-1] for x in result['observations'])
        with pytest.raises(RuntimeError): counter.take('inputs')
    finally:
        counter.close()


@pytest.mark.parametrize('depth,schedule', [(0, 'terminal'), (12, 'terminal'), (True, 'terminal'), (1, 'bad')])
def test_invalid_requests_fail_before_generator(depth, schedule):
    model, _ = tiny()
    counter = ForwardCounter(model, dict(inputs=0, generator_levels=0, decoder=0, encoder=0))
    try:
        with pytest.raises(ValueError): forced_request(model, 'synthetic', depth, schedule)
        assert not any(counter.counts.values())
    finally: counter.close()


def test_training_mode_refused():
    model, _ = tiny()
    model.tokenizer.vqvae.train()
    with pytest.raises(ValueError): forced_request(model, 'synthetic', 1, 'terminal')


@pytest.mark.parametrize('problem', ['none', 'codes', 'ids', 'text', 'source', 'observation'])
def test_current_cached_parity_checks_reject_each_mismatch_without_extra_model_calls(problem):
    path = Path(__file__).resolve().parents[1]/'scripts/run_evidence_e1.py'
    spec = importlib.util.spec_from_file_location('e1_runner_test', path)
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    model, _ = tiny()
    result = forced_request(model, 'synthetic', 1, 'terminal')
    cached = {'prefix_ids':list(result['prefix_ids']), 'codes':result['codes'][0].tolist(),
              'levels':[{'ids':list(result['ids']), 'text':result['text']}]}
    expected = {'identity':identity(result['prefix_ids']), 'depth':1, 'schedule':'terminal'}
    if problem == 'codes': cached['codes'][0] = (cached['codes'][0]+1)%8
    if problem == 'ids': cached['levels'][0]['ids'][0] += 1
    if problem == 'text': cached['levels'][0]['text'] = 'wrong cached text'
    if problem == 'source': cached['prefix_ids'][0] += 1
    if problem == 'observation': result['observations'][0]['level'] = 2
    if problem == 'none':
        assert set(runner.parity(result,cached,expected)) == {'codes_sha256','ids_sha256','text_sha256','observations'}
    else:
        with pytest.raises(ValueError): runner.parity(result,cached,expected)


def fake_records():
    plan = make_schedule(entries())
    rows = [dict(r, parity=True, wall_ms=float(r['depth'] * 2 + (r['depth'] if r['schedule'] == 'every_level' else 1)),
                 work=dict(inputs=1, generator_levels=r['depth'], decoder=1 if r['schedule'] == 'terminal' else r['depth'], encoder=0)) for r in plan]
    return plan, rows


def test_identity_bootstrap_paired_fixed_process_analysis_and_no_winner_claim():
    plan, rows = fake_records()
    result = analyze(rows, plan, entries())
    assert result['identity_bootstrap_draws'] == 10000
    assert not result['process_population_uncertainty_identified']
    full = result['versus_terminal_11']['terminal:11']['pooled']
    assert full['relative_mean_reduction'] == 0 and full['relative_mean_reduction_ci95_nominal'] == [0, 0]
    shallow = result['versus_terminal_11']['terminal:1']['pooled']
    assert shallow['relative_mean_reduction'] == pytest.approx(1-3/23)
    assert result['every_level_versus_terminal']['11']['pooled']['relative_mean_reduction'] < 0
    assert result['decision'] == 'cheaper_forced_path_observed_not_adaptive_speedup'


@pytest.mark.parametrize('problem', ['missing', 'parity', 'work'])
def test_incomplete_or_failed_measurements_never_produce_timing_conclusion(problem):
    plan, rows = fake_records()
    if problem == 'missing': rows.pop()
    if problem == 'parity': rows[0]['parity'] = False
    if problem == 'work': rows[0]['work']['decoder'] += 1
    with pytest.raises(ValueError): analyze(rows, plan, entries())
