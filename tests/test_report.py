"""Clustered statistics, exact decision boundaries, and trajectory classification."""

from copy import deepcopy
import json
from types import SimpleNamespace

import numpy as np
import pytest

from anytime_ncm.dataset import sha256
from anytime_ncm.report import (
    decision_gate, independent_valid, load_profiles, paired_bootstrap,
    representative_cases, summarize_trajectories,
)


def estimate(mean, low, high):
    return {"relative_mean_reduction": mean, "relative_mean_reduction_ci95": [low, high]}


@pytest.mark.parametrize("value,expected", [
    (estimate(.05, .001, .10), "go"),
    (estimate(.049, .01, .04999), "no-go"),
    (estimate(.04, -.01, .05), "inconclusive"),
    (estimate(.06, 0, .12), "inconclusive"),
    (estimate(-.2, -.3, -.1), "no-go"),
])
def test_gate_uses_frozen_thresholds_and_strict_interval_boundaries(value, expected):
    assert decision_gate(value) == expected


@pytest.mark.parametrize("kwargs", [
    {"correctness_passed": False}, {"quality_loss": .001}, {"false_accepts": 1},
])
def test_correctness_blockers_override_a_large_estimated_gain(kwargs):
    assert decision_gate(estimate(.9, .8, .99), **kwargs) == "no-go"


def test_missing_costs_are_inconclusive_not_a_measured_negative():
    assert decision_gate(None, costs_available=False) == "inconclusive"


def test_bootstrap_preserves_pairing_and_all_five_repeats():
    baseline = np.array([[1, 3, 5, 7, 9], [10, 30, 50, 70, 90], [100, 300, 500, 700, 900]])
    candidate = baseline * .9
    result = paired_bootstrap(baseline, candidate, resamples=10000)
    assert result["identities"] == 3 and result["repeats_per_identity"] == 5
    assert result["relative_mean_reduction"] == pytest.approx(.1)
    assert result["relative_mean_reduction_ci95"] == pytest.approx([.1, .1])
    assert result["quality_difference_ci95"] == [0, 0]
    assert result == paired_bootstrap(baseline, candidate, resamples=10000)


def test_quality_intervals_resample_identities_without_dropping_repeats():
    baseline = np.ones((2, 5)) * 10
    quality = np.array([[1] * 5, [0] * 5])
    result = paired_bootstrap(baseline, baseline, quality)
    assert result["quality_difference"] == .5
    assert result["quality_difference_ci95"] == [0, 1]


@pytest.mark.parametrize("baseline,candidate", [
    ([1, 2], [1, 2]), ([[1]], [[1, 2]]), ([[0]], [[1]]),
    ([[float("nan")]], [[1]]), ([[1]], [[-1]]),
])
def test_bootstrap_rejects_invalid_or_unpaired_costs(baseline, candidate):
    with pytest.raises(ValueError):
        paired_bootstrap(baseline, candidate)


def record(index, flags, partition="exploration"):
    return {"dataset_index": index, "sample_id": str(index), "partition": partition,
            "levels": [{"correctness": {"is_valid_solution": value},
                        "diagnostics": {"official_solved": value}, "decoded_text": str(level)}
                       for level, value in enumerate(flags, 1)]}


def test_summary_counts_first_valid_instability_and_never_solved_separately():
    records = [
        record(0, [False, True, False, True] + [False] * 7 + [True]),
        record(1, [False] * 11 + [True]), record(2, [False] * 12),
        record(3, [False] * 9 + [True] * 3, "development"),
    ]
    summary = summarize_trajectories(records)
    e = summary["exploration"]
    assert e["first_valid_counts"]["2"] == 1
    assert e["first_valid_counts"]["12"] == 1
    assert e["never_solved_count"] == 1
    assert e["never_solved_fraction"] == pytest.approx(1 / 3)
    assert e["puzzles_with_valid_to_invalid"] == 1
    assert sum(e["valid_to_invalid_transition_counts"]) == 2
    cases = representative_cases(records)
    assert {k: v["dataset_index"] for k, v in cases.items()} == {
        "early_success": 0, "late_recovery": 0, "late_success": 1, "never_solved": 2}


def test_absent_example_categories_are_not_fabricated():
    records = [record(1, [False] * 12), record(2, [False] * 12, "development")]
    assert set(representative_cases(records)) == {"never_solved"}


def test_independent_acceptance_checks_grid_and_clues():
    solution = "534678912672195348198342567859761423426853791713924856961537284287419635345286179"
    assert independent_valid(solution, solution)
    assert not independent_valid(solution, "0" * 81)
    assert not independent_valid(solution, solution.translate(str.maketrans("12", "21")))
    assert not independent_valid(solution, solution[:-1])


@pytest.fixture
def profile_fixture(tmp_path):
    examples = tuple(SimpleNamespace(identity=f"id{i}", index=i,
                                    partition="exploration" if i < 100 else "development") for i in range(200))
    state = {"valid": False, "prefix_assembly": {"wall_ms": 1},
             "reconstruction": {"wall_ms": 1}, "decode_select": {"wall_ms": 1},
             "transfer_ms": 1, "text_ms": 1, "verifier_ms": 1, "features_ms": 1, "policy_ms": 1}
    rows = []
    for example in examples:
        for repeat in range(5):
            rows.append({"sample_id": example.identity, "dataset_index": example.index,
                         "partition": example.partition, "repeat": repeat,
                         "input_prepare": {"wall_ms": 1}, "generation": {"level_gpu_ms": [1] * 12, "host_residual_ms": 1},
                         "levels": [deepcopy(state) for _ in range(12)]})
    components = tmp_path / "components.jsonl"
    components.write_text("".join(json.dumps(r) + "\n" for r in rows))
    metadata = {
        "status": "complete", "timed_records": 1000,
        "budget": {"exploration_inputs": 100, "development_inputs": 100, "warmup_requests": 10, "timed_repeats_per_input": 5},
        "source_sha256": {}, "components_sha256": sha256(components),
        "selected_examples": [{"index": e.index, "sample_id": e.identity, "partition": e.partition} for e in examples],
        "final_reconstruction_parity_checks": 1000, "hook_vs_uninstrumented_code_parity_checks": 50}
    (tmp_path / "run.json").write_text(json.dumps(metadata))
    return tmp_path, examples, rows, metadata


def test_profile_loader_requires_every_fixed_budget_identity_and_repeat(profile_fixture):
    directory, examples, _, _ = profile_fixture
    metadata, records = load_profiles(directory, directory, examples)
    assert len(records) == metadata["timed_records"] == 1000


@pytest.mark.parametrize("corruption", ["duplicate", "sealed", "missing", "extra"])
def test_profile_loader_rejects_changed_access_or_coverage(profile_fixture, corruption):
    directory, examples, rows, metadata = profile_fixture
    if corruption == "duplicate":
        rows[1] = rows[0]
    elif corruption == "sealed":
        rows[0]["partition"] = "phase2_final"
    elif corruption == "missing":
        rows.pop()
    else:
        rows.append(rows[-1])
    path = directory / "components.jsonl"
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    metadata["components_sha256"] = sha256(path)
    (directory / "run.json").write_text(json.dumps(metadata))
    with pytest.raises(ValueError):
        load_profiles(directory, directory, examples)


def test_markdown_tables_and_source_links_survive_report_relocation(tmp_path):
    from pathlib import Path
    import re
    from anytime_ncm.report_render import write_summary
    root = Path(__file__).resolve().parents[1]
    analysis = json.loads((root / "results/phase1/analysis.json").read_text())
    analysis["component_diagnostics_ms"] = {name: {"generation_full": 1.0} for name in ("exploration", "development")}
    metadata = json.loads((root / "results/phase1/profiles/run.json").read_text())
    write_summary(tmp_path, analysis, metadata, repository=root, profiles=root / "results/phase1/profiles")
    text = (tmp_path / "summary.md").read_text(encoding="utf-8")
    width = None
    for line in text.splitlines():
        if line.startswith("|"):
            cells = len(line.split("|")) - 2
            if width is None:
                width = cells
            assert cells == width
        else:
            width = None
    profile_link = next(target for target in re.findall(r"\]\(([^)]+)\)", text) if target.endswith("profiles/run.json"))
    assert (tmp_path / profile_link).resolve() == root / "results/phase1/profiles/run.json"
