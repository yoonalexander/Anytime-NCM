"""Separately requested R3 easy-Sudoku audit; negative R2 evidence stays frozen."""
import json
import re
from pathlib import Path

from anytime_ncm.dataset import Example, _TokenRows, puzzle_identity, select_entries, sha256
from anytime_ncm.screening import candidate_examples, require, save, verify_candidate
from anytime_ncm.sudoku import validate_solution
from anytime_ncm.trajectories import validate_jsonl

OUTPUT = "results/followup/sudoku_easy_r3"
PROTOCOL = "docs/studies/sudoku-easy-r3-protocol.md"
CONFIG = "configs/r3_easy.json"
RUN_ID = "R3-easy"
SOURCES = (PROTOCOL, CONFIG, "src/anytime_ncm/audit.py", "src/anytime_ncm/audit_inference.py",
    "src/anytime_ncm/audit_render.py", "scripts/audit_sudoku_easy.py", "tests/test_audit.py",
    "src/anytime_ncm/timing.py", "src/anytime_ncm/report.py", "src/anytime_ncm/dataset.py",
    "src/anytime_ncm/screening.py", "src/anytime_ncm/screening_inference.py",
    "src/anytime_ncm/upstream_adapter.py", "src/anytime_ncm/trajectories.py",
    "src/anytime_ncm/features.py", "src/anytime_ncm/sudoku.py", "src/anytime_ncm/target_encoding.py",
    "third_party/ncm/evaluate.py", "third_party/ncm/scripts/eval_shard.py", "third_party/ncm/scripts/eval_merge.py")
COLLECTION_LIMITS = {"inputs": 1368, "generator_levels": 16416, "decoder": 16416, "encoder": 0,
                     "latent_parity": 1368, "independent_prefix": 1368}
PROFILE_LIMITS = {"inputs": 1010, "generator_levels": 12120, "decoder": 13120, "encoder": 0,
                  "latent_parity": 1000, "independent_prefix": 0}


def config(root):
    data = json.loads((root / CONFIG).read_text())
    require(data["study"] == "R3" and data["candidate"] == "easy"
            and data["partitions"] == {"exploration": 1000, "development": 400}
            and data["new_generation_budget"] == 4378 and data["new_decoder_budget"] == 31536
            and data["reused_R2_exploration"] == 32 and data["profile_repeats"] == 5
            and data["warmups"] == 10 and data["baseline_inputs"] == 2000
            and data["profile_inputs_per_partition"] == 100 and data["calibration_iterations"] == 100
            and data["bootstrap_resamples"] == 10000 and data["bootstrap_seed"] == 20261020
            and data["collection_batch_size"] == 1, "R3 configuration differs.")
    return data


def examples(root, counts):
    root = Path(root)
    config(root)
    # Validate candidate artifacts, reserved manifest and R2's untouched negative result.
    result = verify_candidate(root, "easy")
    require(not result["qualifies_for_R3"], "This entry exception expects the recorded negative screen.")
    _, inputs = candidate_examples(root, "easy")
    manifest = json.loads((root / "docs/partitions/sudoku-easy-r2.json").read_text())
    entries = select_entries(manifest, counts)  # refuses final selections before token reads
    indices = {e["index"] for e in entries}
    rows = [_TokenRows((root / ("data/sudoku/easy/" + name)).read_bytes()).select(indices, length, 2000)
            for name, length in (("puzzles.pickle", 91), ("solutions.pickle", 89))]
    selected = []
    for entry in entries:
        i = entry["index"]
        require(puzzle_identity(rows[0][i]) == entry["puzzle_sha256"], "Selected R3 identity differs.")
        require(validate_solution(rows[0][i], rows[1][i], reference=rows[1][i]).is_valid_solution,
                "Invalid easy reference.")
        selected.append(Example(i, entry["partition"], entry["puzzle_sha256"], rows[0][i], rows[1][i]))
    return tuple(selected), inputs


def parse_baseline_log(text):
    matches = re.findall(r"^\s*([\d.]+)\s+(\d+)/(\d+)\s+([\d.]+)\s+([\d.]+)\s*$", text, re.MULTILINE)
    require(len(matches) == 1, "Expected one official aggregate Sudoku score line.")
    solved_percent, solved, total, cell_percent, valid_percent = matches[0]
    require(int(total) == 2000 and 0 <= int(solved) <= 2000, "Official baseline coverage differs.")
    return {"solved": int(solved), "total": int(total), "solved_percent": float(solved_percent),
            "cell_percent": float(cell_percent), "valid_grid_percent": float(valid_percent),
            "score_precision": "percentages rounded by unchanged official evaluator",
            "scoring": "official decoded-text metrics; no independent clue rescoring of reserved outputs"}


def source_hashes(root):
    return {name: sha256(root / name) for name in SOURCES}


def verify_stage(root, name):
    out = root / OUTPUT
    record = json.loads((out / (name + ".json")).read_text())
    require(record["status"] == "complete" and record["stage"] == name, "Incomplete R3 stage: " + name)
    require(record["source_sha256"] == source_hashes(root), "R3 execution source changed.")
    for path, expected in record["inputs_sha256"].items():
        require(sha256(root / path) == expected, "R3 input changed: " + path)
    for path, expected in record["artifacts_sha256"].items():
        require(sha256(out / path) == expected, "R3 stage artifact changed: " + path)
    if name == "baseline":
        require(record["reserved_input_generations"] == record["completed_input_generations"] == 2000
                and record["batch_size"] == 1 and not record["raw_predictions_opened_by_analyst"],
                "Official baseline budget/access differs.")
    if name in ("collection", "profiles"):
        require(record["counts"] == record["limits"] == (COLLECTION_LIMITS if name == "collection" else PROFILE_LIMITS),
                "R3 model budget differs.")
        require(record["state_before"] == record["state_after"], "Model state changed during R3.")
    return record


def calculate(root):
    """Recompute every label/cost/gate with NumPy, without model imports."""
    from anytime_ncm.report import (independent_valid, summarize_trajectories, cost_summary,
                                   decision_gate, load_profiles, representative_cases)
    import numpy as np
    root = Path(root)
    out = root / OUTPUT
    baseline = verify_stage(root, "baseline")
    collection = verify_stage(root, "collection")
    profile_stage = verify_stage(root, "profiles")
    all_examples, _ = examples(root, {"exploration": 1000, "development": 400})
    indexed = {e.identity: e for e in all_examples}
    validation = validate_jsonl(out / "trajectories.jsonl", all_examples, RUN_ID)
    trajectories = [json.loads(line) for line in (out / "trajectories.jsonl").read_text().splitlines()]
    inherited = [json.loads(line)["trajectory"] for line in
                 (root / "results/followup/sudoku_checkpoint_screen/easy/records.jsonl").read_text().splitlines()]
    require(trajectories[:32] == [dict(row, run_id=RUN_ID) for row in inherited], "Reused R2 outputs differ.")
    checks = [json.loads(line) for line in (out / "prefix_checks.jsonl").read_text().splitlines()]
    require([r["dataset_index"] for r in checks] == [r["dataset_index"] for r in trajectories[32:]],
            "New prefix-check coverage differs.")
    require(all(r["independent_prefix_equal"] is True and r["final_latent_bitwise_equal"] is True
                and r["independent_storage"] is True and r["finite"] is True
                and r["prefix_shapes"] == [[1, 89, 256]] * 12 for r in checks),
            "Stored prefix-parity declaration differs.")
    selected, _ = examples(root, {"exploration": 100, "development": 100})
    metadata, profiles = load_profiles(root, out / "profiles", selected)
    require(profile_stage["timed_records"] == 1000 and metadata["repeated_code_parity_checks"] == 800,
            "Profile repeat coverage differs.")
    by_id = {r["sample_id"]: r for r in trajectories}
    mismatches = false_accepts = code_mismatches = output_mismatches = 0
    for record in trajectories + profiles:
        example = indexed[record["sample_id"]]
        for state in record["levels"]:
            actual = independent_valid(example.puzzle, state["decoded_ids"])
            claimed = state["valid"] if "valid" in state else state["correctness"]["is_valid_solution"]
            mismatches += actual != claimed
            false_accepts += claimed and not actual
    for record in profiles:
        original = by_id[record["sample_id"]]
        code_mismatches += record["generated_codes"] != [code for s in original["levels"] for code in s["code_ids"]]
        output_mismatches += any(a["decoded_ids"] != b["decoded_ids"] for a, b in zip(record["levels"], original["levels"], strict=True))
    require(code_mismatches == output_mismatches == 0, "Profile/collection output parity differs.")
    summaries = summarize_trajectories(trajectories)
    costs, corrected, fixed = {}, {}, {}
    for partition in ("exploration", "development"):
        subset = [r for r in profiles if r["partition"] == partition]
        costs[partition], raw_costs = cost_summary(subset)
        corrected[partition], _ = cost_summary(subset, metadata["instrumentation_calibration"])
        fixed[partition] = [{"level": k + 1,
             "mean_estimated_ms": float(np.mean([c["fixed_ms"][k] for c in raw_costs])),
             "profile_valid_rate": float(np.mean([r["levels"][k]["valid"] for r in subset])),
             "collection_valid_rate": summaries[partition]["valid_solution_count_by_level"][k] / summaries[partition]["inputs"]}
             for k in range(12)]
    collection_loss = {}
    for p in ("exploration", "development"):
        rows = [r for r in trajectories if r["partition"] == p]
        collection_loss[p] = max(0, sum(r["levels"][-1]["correctness"]["is_valid_solution"] for r in rows)
                                - sum(any(s["correctness"]["is_valid_solution"] for s in r["levels"]) for r in rows))
    correctness = mismatches == false_accepts == code_mismatches == output_mismatches == 0
    loss = max(collection_loss["development"] / 400,
               costs["development"]["baseline_valid_rate"] - costs["development"]["verified_valid_rate"], 0)
    primary = decision_gate(costs["development"]["paired"], correctness_passed=correctness,
                            quality_loss=loss, false_accepts=false_accepts)
    sensitivity = decision_gate(corrected["development"]["paired"], correctness_passed=correctness,
                                quality_loss=loss, false_accepts=false_accepts)
    feasible = [f for f in fixed["development"] if
        f["profile_valid_rate"] >= costs["development"]["baseline_valid_rate"] and
        f["collection_valid_rate"] >= summaries["development"]["valid_solution_count_by_level"][-1] / 400]
    analysis = {"study": "R3", "setting": "easy", "entry_exception": config(root)["entry_exception"],
        "R2_qualified": False, "decision": primary if primary == sensitivity else "inconclusive",
        "uncorrected_gate": primary, "calibration_sensitivity_gate": sensitivity,
        "official_baseline": json.loads((out / "baseline_metrics.json").read_text()),
        "trajectory_summary": summaries, "profile_costs": costs, "calibration_sensitivity_costs": corrected,
        "fixed_depth_comparison": fixed, "development_selected_quality_feasible_fixed_depth":
            min(feasible, key=lambda r: r["mean_estimated_ms"]),
        "independent_validity_disagreements": mismatches, "false_verifier_accepts": false_accepts,
        "collection_primary_solve_loss_counts": collection_loss,
        "profile_collection_code_disagreements": code_mismatches,
        "profile_collection_any_output_disagreements": output_mismatches,
        "representative_cases": representative_cases(trajectories),
        "coverage": {"trajectory_inputs": 1400, "trajectory_levels": 16800, "reused_R2_inputs": 32,
                     "new_collection_inputs": 1368, "profile_identities": 200, "timed_requests": 1000,
                     "profile_repeats": 5, "warmups": 10, "official_baseline_inputs": 2000,
                     "total_new_generations": 4378, "total_new_decoder_forwards": 31536,
                     "adapter_profile_final_rows_materialized": 0, "headline_online_requests": 0},
        "measurement": "instrumented component-sum estimates; no observed online latency or speedup"}
    rows = []
    for record in trajectories:
        for state in record["levels"]:
            rows.append({"sample_id": record["sample_id"], "dataset_index": record["dataset_index"],
                "partition": record["partition"], "level": state["level"],
                **state["correctness"], **state["diagnostics"]})
    return analysis, rows, validation


def analyze(root):
    from anytime_ncm.diagnosis import csv_text
    from anytime_ncm.audit_render import render
    root = Path(root)
    out = root / OUTPUT
    require(not (out / "analysis.json").exists(), "Analysis already exists; use saved verification.")
    analysis, rows, validation = calculate(root)
    save(out / "analysis.json", analysis)
    (out / "trajectory_table.csv").write_text(csv_text(rows), encoding="utf-8", newline="\n")
    render(root, analysis)
    save(out / "report_provenance.json", {"study": "R3", "source_sha256": source_hashes(root),
        "stage_metadata_sha256": {name: sha256(out / (name + ".json")) for name in ("baseline", "collection", "profiles")},
        "artifacts_sha256": {name: sha256(out / name) for name in
            ("analysis.json", "trajectory_table.csv", "summary.md", "audit_comparison.png")},
        "trajectory_validation": validation})
    return analysis


def verify(root):
    from anytime_ncm.diagnosis import csv_text
    root = Path(root)
    out = root / OUTPUT
    provenance = json.loads((out / "report_provenance.json").read_text())
    require(provenance["source_sha256"] == source_hashes(root), "Report source hashes differ.")
    for name, expected in provenance["artifacts_sha256"].items():
        require(sha256(out / name) == expected, "R3 report artifact changed: " + name)
    for name, expected in provenance["stage_metadata_sha256"].items():
        require(sha256(out / (name + ".json")) == expected, "Stage metadata changed.")
    analysis, rows, validation = calculate(root)
    require(analysis == json.loads((out / "analysis.json").read_text()), "Recomputed R3 analysis differs.")
    require((out / "trajectory_table.csv").read_text() == csv_text(rows), "Recomputed R3 table differs.")
    require(provenance["trajectory_validation"] == validation, "Trajectory validation differs.")
    log = (out / "baseline.log").read_text()
    require(parse_baseline_log(log) == analysis["official_baseline"], "Official aggregate receipt differs.")
    return analysis
