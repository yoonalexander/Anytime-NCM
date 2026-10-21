"""Timing boundaries, observer isolation, and complete offline cost accounting."""

from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest
import torch
from omegaconf import OmegaConf

from anytime_ncm.timing import (
    GenerationObserver, cuda_region, estimate_costs, finite_ms, first_valid_exit,
    host_region, reconstruct_at_depth, verified_decision,
)
from anytime_ncm.upstream_adapter import _import_upstream, reconstruct_prefixes
from anytime_ncm.trajectories import LEVEL_LENGTHS

_import_upstream(Path(__file__).resolve().parents[1] / "third_party/ncm")
from models.quant import MultiscaleResidualVectorQuantizer


def profile(flags=None):
    flags = flags or [False, True] + [False] * 10
    return {
        "input_prepare": {"wall_ms": 3.0, "gpu_ms": 2.0},
        "generation": {"level_gpu_ms": [1.0] * 12, "host_residual_ms": 2.0, "wall_ms": 14.0},
        "levels": [dict(
            valid=valid, prefix_assembly={"wall_ms": 1.0}, reconstruction={"wall_ms": 2.0},
            decode_select={"wall_ms": 3.0}, transfer_ms=4.0, text_ms=5.0,
            verifier_ms=6.0, features_ms=8.0, policy_ms=7.0,
        ) for valid in flags],
    }


@pytest.mark.parametrize("bad", [-1, float("nan"), float("inf"), None, True, "1"])
def test_invalid_timing_is_not_treated_as_zero(bad):
    with pytest.raises(ValueError):
        finite_ms(bad)


def test_host_region_boundaries_and_unit_conversion(monkeypatch):
    ticks = iter([1_000_000, 1_500_000])
    monkeypatch.setattr("anytime_ncm.timing.time.perf_counter_ns", lambda: next(ticks))
    result, ms = host_region(lambda: 42)
    assert result == 42 and ms == 0.5


def test_cuda_region_syncs_only_at_diagnostic_region_boundaries(monkeypatch):
    events = []
    class Event:
        def __init__(self, **kwargs):
            pass
        def record(self):
            events.append("record")
        def synchronize(self):
            events.append("end_sync")
        def elapsed_time(self, other):
            return 0.25
    monkeypatch.setattr(torch.cuda, "Event", Event)
    monkeypatch.setattr(torch.cuda, "synchronize", lambda: events.append("start_sync"))
    def operation():
        events.append("operation")
        return 9
    result, cost = cuda_region(operation)
    assert events == ["start_sync", "record", "operation", "record", "end_sync"]
    assert result == 9 and cost["gpu_ms"] == 0.25 and cost["wall_ms"] >= 0


def test_estimator_charges_every_check_and_only_generation_through_exit():
    result = estimate_costs(profile())
    assert result["exit_level"] == 2
    assert result["baseline_ms"] == 31
    assert result["candidate_ms"] == 63
    assert result["fixed_ms"][1] == 22
    assert result["fixed_ms"][-1] == result["baseline_ms"]
    assert result["skipped_levels"] == 10
    assert result["skipped_codes"] == sum(LEVEL_LENGTHS[2:])


def test_never_valid_pays_full_generation_and_all_twelve_checks():
    result = estimate_costs(profile([False] * 12))
    assert result["candidate_ms"] == 352
    assert result["exit_level"] == 12
    assert result["candidate_valid"] is False
    assert result["skipped_levels"] == result["skipped_codes"] == 0


def test_early_valid_then_invalid_does_not_lose_the_early_solution():
    result = estimate_costs(profile([True] + [False] * 11))
    assert result["candidate_valid"] is True
    assert result["baseline_valid"] is False
    assert result["exit_level"] == 1


def test_unused_feature_cost_does_not_enter_verifier_only_candidate():
    record = profile()
    before = estimate_costs(record)
    for state in record["levels"]:
        state["features_ms"] = 99999
    assert estimate_costs(record) == before


def test_instrumentation_sensitivity_cannot_produce_negative_costs():
    result = estimate_costs(profile(), calibration={
        "cuda_region_wall_ms": 1000, "marker_trace_wall_ms": 1000, "host_region_ms": 1000})
    assert result["baseline_ms"] == result["candidate_ms"] == 2


def test_missing_or_invalid_costs_cannot_support_an_estimate():
    record = profile()
    record["levels"][0]["verifier_ms"] = None
    with pytest.raises(ValueError):
        estimate_costs(record)
    record = profile()
    record["generation"]["level_gpu_ms"].pop()
    with pytest.raises(ValueError):
        estimate_costs(record)


@pytest.mark.parametrize("flags", [[False] * 11, [0] * 12, [None] * 12])
def test_exit_requires_a_complete_boolean_trajectory(flags):
    with pytest.raises(ValueError):
        first_valid_exit(flags)


def test_current_verified_decision_has_no_reference_or_future_input():
    assert verified_decision(True) is True
    assert verified_decision(False) is False
    with pytest.raises(ValueError):
        verified_decision(1)


def test_observer_preserves_outputs_and_removes_hooks_on_exit():
    embeddings = torch.nn.ModuleList([torch.nn.Embedding(3, 2) for _ in range(12)])
    vq = SimpleNamespace(levels=list(range(12)), embeddings=embeddings)
    synchronization = []
    ticks = iter([0, 12_000_000])
    class Event:
        def record(self):
            pass
        def elapsed_time(self, other):
            return 1.0
    expected = [embedding(torch.tensor([1])) for embedding in embeddings[:-1]]
    with GenerationObserver(vq, event_factory=Event, synchronize=lambda: synchronization.append(True),
                            clock=lambda: next(ticks)) as observer:
        actual = [embedding(torch.tensor([1])) for embedding in embeddings[:-1]]
        assert len(synchronization) == 1  # no synchronization at internal markers
        timing = observer.finish()
    assert len(synchronization) == 2
    assert timing["level_gpu_ms"] == [1.0] * 12
    assert timing["wall_ms"] == 12 and timing["host_residual_ms"] == 0
    assert all(torch.equal(a, b) for a, b in zip(expected, actual))
    assert all(not embedding._forward_pre_hooks for embedding in embeddings)


def test_observer_rejects_changed_stage_order_and_cleans_up():
    embeddings = torch.nn.ModuleList([torch.nn.Embedding(3, 2) for _ in range(12)])
    class Event:
        def record(self):
            pass
    vq = SimpleNamespace(levels=list(range(12)), embeddings=embeddings)
    with pytest.raises(RuntimeError, match="boundary order"):
        with GenerationObserver(vq, event_factory=Event, synchronize=lambda: None):
            embeddings[1](torch.tensor([1]))
    assert all(not embedding._forward_pre_hooks for embedding in embeddings)


def test_profile_reconstruction_matches_independent_snapshots_and_ignores_future_codes():
    torch.manual_seed(71)
    vq = MultiscaleResidualVectorQuantizer(
        vqvae_vocab_size=[4, 4, 4], embed_dim=8,
        levels=OmegaConf.create({"use_manual_levels": True, "manual_levels": [1, 2, 6]}),
        learned_l1_sampling=True, quant_resi=OmegaConf.create({"enabled": True, "ratio": 0.5, "share_mode": 0}),
    ).eval()
    ids = torch.tensor([[1, 2, 3, 1, 1, 2, 2, 3, 3]])
    expected = reconstruct_prefixes(vq, ids)
    for depth in range(1, 4):
        assembled = ids[:, :sum(vq.levels[:depth])]
        assert torch.equal(reconstruct_at_depth(vq, assembled, depth), expected[depth - 1])
    changed = ids.clone()
    changed[:, 3:] = 99
    assert torch.equal(reconstruct_at_depth(vq, changed, 2), expected[1])
    for bad in [0, 4, True]:
        with pytest.raises(ValueError):
            reconstruct_at_depth(vq, ids, bad)
