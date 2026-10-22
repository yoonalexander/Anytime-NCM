"""Verify current Phase 1 evidence; optionally record a fresh review, without models/CUDA."""

import argparse
from datetime import date
from collections import Counter
import csv
import json
import math
from pathlib import Path
import re
import statistics
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from anytime_ncm.dataset import MANIFEST_SHA256, PROTOCOL_SHA256, sha256, select_entries
from anytime_ncm.timing import estimate_costs


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-review-record", action="store_true",
                        help="Record the current compatibility review after a fresh full-suite run.")
    parser.add_argument("--review-date", help="ISO date for a new review; default preserves the recorded date.")
    args = parser.parse_args()
    base = ROOT / "results/phase1"
    review_date = args.review_date or json.loads((base / "review_validation.json").read_text())["date"]
    date.fromisoformat(review_date)
    metadata = json.loads((base / "profiles/run.json").read_text())
    analysis = json.loads((base / "analysis.json").read_text())
    provenance = json.loads((base / "report_provenance.json").read_text())
    require(sha256(ROOT / "docs/experiment_protocol.md") == PROTOCOL_SHA256, "Protocol changed.")
    require(sha256(ROOT / "docs/partitions/sudoku-hard.json") == MANIFEST_SHA256, "Manifest changed.")
    require(metadata["status"] == "complete", "Profile incomplete.")
    require(metadata["protocol_sha256"] == PROTOCOL_SHA256 and metadata["partition_manifest_sha256"] == MANIFEST_SHA256, "Profile frozen identifiers differ.")
    require(metadata["budget"] == {"exploration_inputs": 100, "development_inputs": 100, "warmup_requests": 10, "timed_repeats_per_input": 5}, "Budget differs.")
    require(metadata["access"]["sealed_rows_materialized"] == 0 and not metadata["access"]["holdout_predictions_or_references_inspected"], "Holdout access.")
    require(sha256(base / "profiles/components.jsonl") == metadata["components_sha256"] == provenance["profile_components_sha256"], "Profile checksum differs.")
    require(sha256(base / "profiles/run.json") == provenance["profile_metadata_sha256"], "Metadata checksum differs.")
    sources = dict(metadata["source_sha256"])
    sources.update(provenance["source_sha256"])
    for name, expected in sources.items():
        require(sha256(ROOT / name) == expected, "Source changed: " + name)
    for name, expected in provenance["artifacts_sha256"].items():
        require(sha256(base / name) == expected, "Report artifact changed: " + name)
    manifest = json.loads((ROOT / "docs/partitions/sudoku-hard.json").read_text())
    selected = select_entries(manifest, {"exploration": 100, "development": 100})
    expected_selection = [{"index": e["index"], "sample_id": e["puzzle_sha256"], "partition": e["partition"]} for e in selected]
    require(metadata["selected_examples"] == expected_selection, "Wrong profile selection.")
    require(metadata["warmup_indices"] == [e["index"] for e in selected if e["partition"] == "exploration"][:10], "Wrong warmups.")
    records = []
    with (base / "profiles/components.jsonl").open(encoding="utf-8") as stream:
        for number, line in enumerate(stream):
            require(number < 1000, "Extra repeats.")
            record = json.loads(line)
            entry = selected[number // 5]
            require((record["dataset_index"], record["sample_id"], record["partition"], record["repeat"]) ==
                    (entry["index"], entry["puzzle_sha256"], entry["partition"], number % 5), "Profile order/identity mismatch.")
            require(len(record["levels"]) == 12, "Missing level.")
            require([s["level"] for s in record["levels"]] == list(range(1, 13)), "Wrong level order.")
            estimate_costs(record)
            records.append(record)
    require(len(records) == metadata["timed_records"] == 1000, "Wrong timed count.")
    require(metadata["profiled_level_records"] == 12000, "Wrong level count.")
    require(metadata["hook_vs_uninstrumented_code_parity_checks"] == 50 and metadata["repeated_code_parity_checks"] == 800 and metadata["final_reconstruction_parity_checks"] == 1000, "Parity coverage differs.")
    for i in range(0, 1000, 5):
        require(all(r["generated_codes"] == records[i]["generated_codes"] for r in records[i:i + 5]), "Repeat generation changed.")
    development = [estimate_costs(r) for r in records if r["partition"] == "development"]
    baseline = statistics.mean(r["baseline_ms"] for r in development)
    candidate = statistics.mean(r["candidate_ms"] for r in development)
    reduction = 1 - candidate / baseline
    paired = analysis["profile_costs"]["development"]["paired"]
    require(math.isclose(reduction, paired["relative_mean_reduction"], abs_tol=1e-12), "Reported estimate differs.")
    require(paired["resamples"] == 10000 and paired["seed"] == 20261020 and paired["identities"] == 100 and paired["repeats_per_identity"] == 5, "Bootstrap contract differs.")
    require(analysis["decision"] == analysis["uncorrected_gate"] == analysis["calibration_sensitivity_gate"] == "no-go", "Recorded decision differs.")
    require(paired["relative_mean_reduction_ci95"][1] < .05, "No-go gate not met.")
    require(analysis["false_verifier_accepts"] == analysis["independent_validity_disagreements"] == 0, "Correctness blocker.")
    require(analysis["coverage"]["headline_online_latency_measurements"] == 0 and analysis["coverage"]["sealed_holdout_inputs"] == 0, "Incorrect measurement/access claim.")
    for name, count in (("exploration", 1000), ("development", 400)):
        data = analysis["trajectory_summary"][name]
        require(data["inputs"] == count and sum(data["first_valid_counts"].values()) == count, "Trajectory coverage differs.")
        require(not any(data["valid_solution_count_by_level"][:-1]), "Early valid result contradicts no-opportunity finding.")
    with (base / "trajectory_table.csv").open(encoding="utf-8", newline="") as stream:
        require(sum(1 for _ in csv.DictReader(stream)) == 16800, "Wrong table row count.")
    with (base / "trajectories.jsonl").open(encoding="utf-8") as stream:
        trajectories = [json.loads(line) for line in stream]
    with (base / "trajectory_table.csv").open(encoding="utf-8", newline="") as stream:
        table = list(csv.DictReader(stream))
    for record, table_rows in zip(trajectories, (table[i:i + 12] for i in range(0, len(table), 12))):
        for state, row in zip(record["levels"], table_rows):
            diagnostics = state["diagnostics"]
            require(row["official_valid_grid"] == str(diagnostics["official_valid_grid"]), "CSV valid-grid differs.")
            expected = diagnostics["official_cell_accuracy"]
            require(row["official_cell_accuracy"] == ("" if expected is None else str(expected)), "CSV cell accuracy differs.")
    for partition in ("exploration", "development"):
        selected_rows = [r for r in trajectories if r["partition"] == partition]
        breakdown = analysis["trajectory_summary"][partition]["quality_by_level"]
        require(len(breakdown) == 12, "Missing quality levels.")
        for k, row in enumerate(breakdown):
            flags = [r["levels"][k]["correctness"] for r in selected_rows]
            diagnostics = [r["levels"][k]["diagnostics"] for r in selected_rows]
            checks = {
                "parseable_count": sum(c["parseable"] for c in flags),
                "unparseable_count": sum(not c["parseable"] for c in flags),
                "complete_count": sum(c["complete"] for c in flags),
                "parseable_incomplete_count": sum(c["parseable"] and not c["complete"] for c in flags),
                "grid_valid_count": sum(c["grid_valid"] for c in flags),
                "clue_consistent_count": sum(c["clue_consistent"] for c in flags),
                "valid_solution_count": sum(c["is_valid_solution"] for c in flags),
                "reference_agreement_count": sum(d["reference_agreement"] for d in diagnostics),
                "official_solved_count": sum(d["official_solved"] for d in diagnostics),
                "official_valid_grid_count": sum(d["official_valid_grid"] for d in diagnostics),
                "official_cell_accuracy_defined_count": sum(d["official_cell_accuracy"] is not None for d in diagnostics),
                "official_cell_accuracy_undefined_count": sum(d["official_cell_accuracy"] is None for d in diagnostics),
            }
            require(row["level"] == k + 1 and all(row[name] == value for name, value in checks.items()), "Quality counts differ.")
            accuracy = [d["official_cell_accuracy"] for d in diagnostics]
            if any(value is None for value in accuracy):
                require(row["official_cell_accuracy_mean"] is None, "Undefined accuracy was dropped.")
            else:
                require(math.isclose(row["official_cell_accuracy_mean"], statistics.mean(accuracy), abs_tol=1e-12), "Mean accuracy differs.")
            require(row["unparseable_count"] + row["parseable_incomplete_count"] + row["complete_count"] == len(selected_rows), "Failure categories overlap or omit inputs.")
    collection = json.loads((base / "trajectories.metadata.json").read_text())
    require(sha256(base / "trajectories.jsonl") == collection["trajectory_sha256"], "Original trajectories changed.")
    report_name = "results/phase1/review_tests.xml"
    suite = ET.parse(ROOT / report_name).getroot().find("testsuite")
    require(suite is not None, "Missing JUnit suite.")
    test_count = int(suite.attrib["tests"])
    require(test_count >= 189 and all(suite.attrib[k] == "0" for k in ("failures", "errors", "skipped")), "Review suite incomplete or unsuccessful.")
    require(len(suite.findall("testcase")) == test_count, "JUnit case count differs.")
    counts = Counter(case.attrib["classname"] for case in suite.findall("testcase"))
    historical = ET.parse(base / "phase1d_tests.xml").getroot().find("testsuite")
    minimum_counts = Counter(case.attrib["classname"] for case in historical.findall("testcase"))
    minimum_counts["tests.test_report"] += 3
    require(all(counts[name] >= minimum for name, minimum in minimum_counts.items()), "Review suite omits milestone coverage.")
    historical_record = json.loads((base / "phase1d_validation.json").read_text())
    for name, expected in historical_record["report_artifacts_sha256"].items():
        if name.endswith(".png"):
            require(sha256(base / name) == expected, "Plot changed since its recorded visual inspection.")

    for name in [*(p.relative_to(ROOT).as_posix() for directory in ("src", "tests")
                   for p in (ROOT / directory).rglob("*.py")),
                 "scripts/verify_phase1d.py", ".gitattributes", "README.md", "ROADMAP.md",
                 "docs/phase1_review.md", "docs/phase1d_profiling.md"]:
        sources[name] = sha256(ROOT / name)
    record = {
        "schema_version": 1, "milestone": "Phase 1 review", "date": review_date,
        "historical_phase1d_completion_sha256": sha256(base / "phase1d_validation.json"),
        "status": "complete", "decision": "no-go", "reason": "zero observed early valid solutions; correctness passed",
        "base_commit": metadata["base_commit"], "source_sha256": sources,
        "profile_metadata": "results/phase1/profiles/run.json",
        "profile_metadata_sha256": sha256(base / "profiles/run.json"),
        "profiles_sha256": metadata["components_sha256"], "report_artifacts_sha256": provenance["artifacts_sha256"],
        "tests": {"passed": test_count, "failed": 0, "errors": 0, "skipped": 0, "exit_code": 0,
                  "junit_suite_seconds": float(suite.attrib["time"]),
                  "report": report_name, "report_sha256": sha256(ROOT / report_name), "by_module": dict(counts)},
        "development_relative_estimated_reduction": paired["relative_mean_reduction"],
        "development_relative_estimated_reduction_ci95": paired["relative_mean_reduction_ci95"],
        "development_estimated_baseline_ms": baseline, "development_estimated_verified_ms": candidate,
        "quality_difference": paired["quality_difference"], "quality_difference_ci95": paired["quality_difference_ci95"],
        "scope": analysis["coverage"], "frozen_protocol_sha256": PROTOCOL_SHA256, "partition_manifest_sha256": MANIFEST_SHA256,
        "figures_visually_inspected": True, "native_verification_command": "python scripts/verify_phase1d.py",
        "next_action": "Stop after Phase 1 report; Phase 2 go entry requirement not met.",
    }
    for name in ["README.md", "ROADMAP.md", "docs/phase1_review.md", "docs/phase1d_profiling.md", "results/phase1/summary.md"]:
        path = ROOT / name
        text = path.read_text(encoding="utf-8")
        require(text.count(chr(96) * 3) % 2 == 0, "Unbalanced fence.")
        for target in re.findall(r"\]\(([^)]+)\)", text):
            if "://" not in target and not target.startswith("#"):
                require((path.parent / target.split("#")[0]).exists(), "Broken link: " + name + " -> " + target)
    review_path = base / "review_validation.json"
    if args.write_review_record:
        review_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    else:
        require(json.loads(review_path.read_text(encoding="utf-8")) == record, "Review record is stale; rerun the full suite and record the review.")
    print(f"PASS: {test_count} tests; 200 identities x 5 repeats; frozen inputs; source/artifact hashes; 16,800 table rows; no-go reproduced.")


if __name__ == "__main__":
    main()
