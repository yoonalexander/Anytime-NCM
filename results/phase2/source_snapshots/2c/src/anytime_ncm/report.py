"""Offline trajectory analysis, paired clustered statistics, and frozen gate."""

from collections import Counter
import csv
import json
from pathlib import Path

import numpy as np
from anytime_ncm.collect import save_json, verify_run
from anytime_ncm.dataset import load_examples, sha256
from anytime_ncm.sudoku import parse_board
from anytime_ncm.timing import estimate_costs


def independent_valid(puzzle, ids):
    try:
        board, clues = parse_board(ids).cells, parse_board(puzzle).cells
    except ValueError:
        return False
    if any(given and given != value for given, value in zip(clues, board)):
        return False
    units = [board[i:i + 9] for i in range(0, 81, 9)] + [board[i::9] for i in range(9)]
    units += [tuple(board[(r + dr) * 9 + c + dc] for dr in range(3) for dc in range(3))
              for r in (0, 3, 6) for c in (0, 3, 6)]
    return all(sorted(unit) == list(range(1, 10)) for unit in units)


def paired_bootstrap(baseline, candidate, quality_difference=None, *, resamples=10000, seed=20261020):
    """Resample identities, retaining every repeat within each sampled cluster."""
    baseline, candidate = np.asarray(baseline, dtype=float), np.asarray(candidate, dtype=float)
    if baseline.shape != candidate.shape or baseline.ndim != 2 or baseline.shape[0] == 0:
        raise ValueError("Paired costs require [identities, repeats] shape.")
    if not np.isfinite(baseline).all() or not np.isfinite(candidate).all() or (baseline <= 0).any() or (candidate < 0).any():
        raise ValueError("Costs must be finite; baseline must be positive.")
    quality = np.zeros_like(baseline) if quality_difference is None else np.asarray(quality_difference, dtype=float)
    if quality.shape != baseline.shape or not np.isfinite(quality).all():
        raise ValueError("Quality must match paired clusters.")
    rng, reductions, differences = np.random.default_rng(seed), [], []
    for start in range(0, resamples, 250):
        indices = rng.integers(0, baseline.shape[0], size=(min(250, resamples - start), baseline.shape[0]))
        b, c = baseline[indices].mean(axis=(1, 2)), candidate[indices].mean(axis=(1, 2))
        reductions.extend((1 - c / b).tolist())
        differences.extend(quality[indices].mean(axis=(1, 2)).tolist())
    return {"relative_mean_reduction": float(1 - candidate.mean() / baseline.mean()),
            "relative_mean_reduction_ci95": np.percentile(reductions, [2.5, 97.5]).tolist(),
            "quality_difference": float(quality.mean()),
            "quality_difference_ci95": np.percentile(differences, [2.5, 97.5]).tolist(),
            "resamples": resamples, "seed": seed,
            "identities": baseline.shape[0], "repeats_per_identity": baseline.shape[1]}


def decision_gate(estimate, *, correctness_passed=True, costs_available=True, quality_loss=0.0, false_accepts=0):
    if not correctness_passed or quality_loss > 0 or false_accepts > 0:
        return "no-go"
    if not costs_available or estimate is None:
        return "inconclusive"
    low, high = estimate["relative_mean_reduction_ci95"]
    if estimate["relative_mean_reduction"] >= 0.05 and low > 0:
        return "go"
    return "no-go" if high < 0.05 else "inconclusive"



def quality_by_level(records):
    """Keep structural failure modes and official metric denominators explicit."""
    result = []
    for k in range(12):
        states = [r["levels"][k] for r in records]
        correctness = [s["correctness"] for s in states]
        diagnostics = [s["diagnostics"] for s in states]
        accuracies = [d["official_cell_accuracy"] for d in diagnostics]
        defined = [value for value in accuracies if value is not None]
        result.append({
            "level": k + 1,
            "parseable_count": sum(c["parseable"] for c in correctness),
            "unparseable_count": sum(not c["parseable"] for c in correctness),
            "complete_count": sum(c["complete"] for c in correctness),
            "parseable_incomplete_count": sum(c["parseable"] and not c["complete"] for c in correctness),
            "grid_valid_count": sum(c["grid_valid"] for c in correctness),
            "clue_consistent_count": sum(c["clue_consistent"] for c in correctness),
            "valid_solution_count": sum(c["is_valid_solution"] for c in correctness),
            "reference_agreement_count": sum(d["reference_agreement"] for d in diagnostics),
            "official_solved_count": sum(d["official_solved"] for d in diagnostics),
            "official_valid_grid_count": sum(d["official_valid_grid"] for d in diagnostics),
            "official_cell_accuracy_defined_count": len(defined),
            "official_cell_accuracy_undefined_count": len(states) - len(defined),
            # Upstream averages per-example values, propagating undefined values.
            # JSON null represents that undefined aggregate, never a zero score.
            "official_cell_accuracy_mean": sum(defined) / len(states) if len(defined) == len(states) else None,
        })
    return result

def summarize_trajectories(records):
    summaries = {}
    for partition in ("exploration", "development"):
        selected = [r for r in records if r["partition"] == partition]
        if not selected:
            raise ValueError("Both permitted partitions are required.")
        histogram, transitions, unstable = Counter(), [0] * 11, 0
        for record in selected:
            flags = [s["correctness"]["is_valid_solution"] for s in record["levels"]]
            first = next((k for k, valid in enumerate(flags, 1) if valid), None)
            histogram[str(first) if first else "never"] += 1
            losses = [int(a and not b) for a, b in zip(flags[:-1], flags[1:])]
            transitions = [a + b for a, b in zip(transitions, losses)]
            unstable += any(losses)
        summaries[partition] = {
            "inputs": len(selected),
            "quality_by_level": quality_by_level(selected),
            "valid_solution_count_by_level": [sum(r["levels"][k]["correctness"]["is_valid_solution"] for r in selected) for k in range(12)],
            "reference_solved_count_by_level": [sum(r["levels"][k]["diagnostics"]["official_solved"] for r in selected) for k in range(12)],
            "first_valid_counts": {str(k): histogram[str(k)] for k in range(1, 13)} | {"never": histogram["never"]},
            "never_solved_count": histogram["never"], "never_solved_fraction": histogram["never"] / len(selected),
            "valid_to_invalid_transition_counts": transitions, "puzzles_with_valid_to_invalid": unstable,
            "ever_valid_count": len(selected) - histogram["never"]}
    return summaries


def representative_cases(records):
    result = {}
    for record in sorted((r for r in records if r["partition"] == "exploration"), key=lambda r: r["dataset_index"]):
        flags = [s["correctness"]["is_valid_solution"] for s in record["levels"]]
        first = next((i for i, value in enumerate(flags) if value), None)
        cases = {"early_success": first is not None and first < 11 and flags[-1],
                 "late_recovery": any(flags[i] and not flags[i + 1] and any(flags[i + 2:]) for i in range(10)),
                 "late_success": first == 11, "never_solved": first is None}
        for name, matches in cases.items():
            if matches and name not in result:
                result[name] = {"dataset_index": record["dataset_index"], "sample_id": record["sample_id"],
                                "valid_by_level": flags, "decoded_text_by_level": [s["decoded_text"] for s in record["levels"]]}
    return result


def load_profiles(repository, directory, examples):
    metadata = json.loads((directory / "run.json").read_text())
    budget = {"exploration_inputs": 100, "development_inputs": 100, "warmup_requests": 10, "timed_repeats_per_input": 5}
    if metadata["status"] != "complete" or metadata["timed_records"] != 1000 or metadata["budget"] != budget:
        raise ValueError("Complete frozen-budget profiling evidence is required.")
    if sha256(directory / "components.jsonl") != metadata["components_sha256"]:
        raise ValueError("Profile artifact changed.")
    for name, expected in metadata["source_sha256"].items():
        if sha256(repository / name) != expected:
            raise ValueError("Profile source changed: " + name)
    selected = [{"index": e.index, "sample_id": e.identity, "partition": e.partition} for e in examples]
    if metadata["selected_examples"] != selected:
        raise ValueError("Profile selection differs from frozen first-100 selection.")
    records = []
    with (directory / "components.jsonl").open(encoding="utf-8") as stream:
        for number, line in enumerate(stream):
            if number >= 1000:
                raise ValueError("Extra diagnostic requests.")
            record, example = json.loads(line), examples[number // 5]
            if (record["sample_id"], record["dataset_index"], record["partition"], record["repeat"]) != (
                example.identity, example.index, example.partition, number % 5):
                raise ValueError("Profile input missing, duplicated, reordered, or sealed.")
            estimate_costs(record)
            records.append(record)
    if len(records) != 1000 or metadata["final_reconstruction_parity_checks"] != 1000 or metadata["hook_vs_uninstrumented_code_parity_checks"] != 50:
        raise ValueError("Incomplete profile/parity coverage.")
    return metadata, records


def cost_summary(records, calibration=None):
    costs = [estimate_costs(r, calibration=calibration) for r in records]
    baseline = np.array([r["baseline_ms"] for r in costs]).reshape(-1, 5)
    candidate = np.array([r["candidate_ms"] for r in costs]).reshape(-1, 5)
    quality = np.array([int(r["candidate_valid"]) - int(r["baseline_valid"]) for r in costs]).reshape(-1, 5)
    def distribution(values):
        return {"mean": float(values.mean()), "median": float(np.median(values)), "p95": float(np.percentile(values, 95))}
    return {"paired": paired_bootstrap(baseline, candidate, quality),
            "baseline_ms": distribution(baseline), "verified_ms": distribution(candidate),
            "baseline_valid_rate": float(np.mean([r["baseline_valid"] for r in costs])),
            "verified_valid_rate": float(np.mean([r["candidate_valid"] for r in costs])),
            "mean_skipped_levels": float(np.mean([r["skipped_levels"] for r in costs])),
            "mean_skipped_codes": float(np.mean([r["skipped_codes"] for r in costs]))}, costs


def build_report(repository, profiles, output, *, replace_report=False):
    from anytime_ncm.report_render import write_figures, write_summary
    repository, profiles, output = Path(repository).resolve(), Path(profiles).resolve(), Path(output).resolve()
    if not output.is_relative_to(repository / "results"):
        raise ValueError("Report output must be beneath results/.")
    names = ["analysis.json", "summary.md", "report_provenance.json", "trajectory_table.csv",
             "solve_rate_by_level.png", "first_valid_distribution.png", "estimated_cost_comparison.png", "representative_trajectories.png"]
    if not replace_report and any((output / name).exists() for name in names):
        raise ValueError("Report artifacts exist; choose a fresh directory.")
    validation = verify_run(repository, Path("results/phase1/trajectories.metadata.json"))
    all_examples, _ = load_examples(repository, {"exploration": 1000, "development": 400})
    examples = {e.identity: e for e in all_examples}
    with (repository / "results/phase1/trajectories.jsonl").open(encoding="utf-8") as stream:
        trajectories = [json.loads(line) for line in stream]
    selected, _ = load_examples(repository, {"exploration": 100, "development": 100})
    metadata, profile_records = load_profiles(repository, profiles, selected)
    mismatches = false_accepts = 0
    for record in trajectories + profile_records:
        for state in record["levels"]:
            actual = independent_valid(examples[record["sample_id"]].puzzle, state["decoded_ids"])
            claimed = state["valid"] if "valid" in state else state["correctness"]["is_valid_solution"]
            mismatches += actual != claimed
            false_accepts += claimed and not actual
    summaries = summarize_trajectories(trajectories)
    costs, corrected, raw_costs, fixed = {}, {}, {}, {}
    for partition in ("exploration", "development"):
        subset = [r for r in profile_records if r["partition"] == partition]
        costs[partition], raw_costs[partition] = cost_summary(subset)
        corrected[partition], _ = cost_summary(subset, metadata["instrumentation_calibration"])
        fixed[partition] = [
            {"level": k + 1, "mean_estimated_ms": float(np.mean([c["fixed_ms"][k] for c in raw_costs[partition]])),
             "profile_valid_rate": float(np.mean([r["levels"][k]["valid"] for r in subset])),
             "collection_valid_rate": summaries[partition]["valid_solution_count_by_level"][k] / summaries[partition]["inputs"]}
            for k in range(12)]
    feasible = [r for r in fixed["development"] if r["profile_valid_rate"] >= costs["development"]["baseline_valid_rate"]
                and r["collection_valid_rate"] >= summaries["development"]["valid_solution_count_by_level"][-1] / 400]
    best = min(feasible, key=lambda r: r["mean_estimated_ms"])
    primary = decision_gate(costs["development"]["paired"], correctness_passed=mismatches == 0, false_accepts=false_accepts,
                            quality_loss=max(0, costs["development"]["baseline_valid_rate"] - costs["development"]["verified_valid_rate"]))
    sensitivity = decision_gate(corrected["development"]["paired"], correctness_passed=mismatches == 0, false_accepts=false_accepts)
    decision = primary if primary == sensitivity else "inconclusive"
    component_diagnostics = {}
    for partition in ("exploration", "development"):
        subset = [r for r in profile_records if r["partition"] == partition]
        components = {"input_prepare": float(np.mean([r["input_prepare"]["wall_ms"] for r in subset])),
                      "generation_full": float(np.mean([sum(r["generation"]["level_gpu_ms"]) + r["generation"]["host_residual_ms"] for r in subset]))}
        for name in ("prefix_assembly", "reconstruction", "decode_select"):
            components[name] = float(np.mean([sum(s[name]["wall_ms"] for s in (r["levels"][:11] if name == "prefix_assembly" else r["levels"])) for r in subset]))
        for name in ("transfer_ms", "text_ms", "verifier_ms", "features_ms", "policy_ms"):
            components[name] = float(np.mean([sum(s[name] for s in r["levels"]) for r in subset]))
        component_diagnostics[partition] = components
    by_id = {r["sample_id"]: r for r in trajectories}
    batch = {"final_token_different_identities": 0, "any_level_token_different_identities": 0, "final_validity_different_identities": 0}
    for record in profile_records[::5]:
        original = by_id[record["sample_id"]]
        batch["final_token_different_identities"] += original["levels"][-1]["decoded_ids"] != record["levels"][-1]["decoded_ids"]
        batch["any_level_token_different_identities"] += any(a["decoded_ids"] != b["decoded_ids"] for a, b in zip(original["levels"], record["levels"]))
        batch["final_validity_different_identities"] += original["levels"][-1]["correctness"]["is_valid_solution"] != record["levels"][-1]["valid"]
    analysis = {"schema_version": 1, "decision": decision, "uncorrected_gate": primary,
                "calibration_sensitivity_gate": sensitivity, "trajectory_summary": summaries,
                "profile_costs": costs, "calibration_sensitivity_costs": corrected,
                "fixed_depth_comparison": fixed, "development_selected_quality_feasible_fixed_depth": best,
                "independent_validity_disagreements": mismatches, "false_verifier_accepts": false_accepts,
                "profile_batch1_vs_collection_batch128": batch, "component_diagnostics_ms": component_diagnostics,
                "representative_cases": representative_cases(trajectories),
                "coverage": {"trajectory_inputs": 1400, "trajectory_levels": 16800, "profile_inputs": 200,
                             "profile_repeats": 1000, "profile_levels": 12000, "warmups": 10,
                             "sealed_holdout_inputs": 0, "headline_online_latency_measurements": 0}}
    output.mkdir(parents=True, exist_ok=True)
    save_json(output / "analysis.json", analysis)
    with (output / "trajectory_table.csv").open("w" if replace_report else "x", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["sample_id", "dataset_index", "partition", "level", "code_length", "cumulative_codes",
                         "parseable", "complete", "grid_valid", "clue_consistent", "valid_solution", "reference_agreement", "official_solved",
                         "official_valid_grid", "official_cell_accuracy"])
        for record in trajectories:
            for s in record["levels"]:
                c, d = s["correctness"], s["diagnostics"]
                writer.writerow([record["sample_id"], record["dataset_index"], record["partition"], s["level"],
                                 s["code_length"], s["cumulative_codes"], c["parseable"], c["complete"], c["grid_valid"],
                                 c["clue_consistent"], c["is_valid_solution"], d["reference_agreement"], d["official_solved"],
                                 d["official_valid_grid"], d["official_cell_accuracy"]])
    write_figures(output, analysis)
    write_summary(output, analysis, metadata, repository=repository, profiles=profiles)
    source_names = ["src/anytime_ncm/report.py", "src/anytime_ncm/report_render.py", "scripts/report_phase1.py", "docs/phase1d_analysis_plan.md"]
    save_json(output / "report_provenance.json", {
        "collection_validation": validation, "profile_metadata_path": profiles.relative_to(repository).as_posix() + "/run.json",
        "profile_metadata_sha256": sha256(profiles / "run.json"), "profile_components_sha256": metadata["components_sha256"],
        "source_sha256": {name: sha256(repository / name) for name in source_names},
        "bootstrap": {"resamples": 10000, "seed": 20261020, "unit": "paired identity; all five repeats retained"},
        "artifacts_sha256": {name: sha256(output / name) for name in names if name != "report_provenance.json"},
        "command": "scripts/report_phase1.py --profiles " + profiles.relative_to(repository).as_posix() + " --output " + output.relative_to(repository).as_posix()})
    return analysis
