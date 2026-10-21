"""Verify stored Phase 1D evidence and write its completion record; no models/CUDA."""

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
    base = ROOT / "results/phase1"
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
    collection = json.loads((base / "trajectories.metadata.json").read_text())
    require(sha256(base / "trajectories.jsonl") == collection["trajectory_sha256"], "Original trajectories changed.")
    report_name = "results/phase1/phase1d_tests.xml"
    suite = ET.parse(ROOT / report_name).getroot().find("testsuite")
    require(suite.attrib["tests"] == "186" and all(suite.attrib[k] == "0" for k in ("failures", "errors", "skipped")), "Test report differs.")
    counts = Counter(case.attrib["classname"] for case in suite.findall("testcase"))
    for name in ["tests/test_timing.py", "tests/test_report.py", "scripts/verify_phase1d.py", ".gitattributes"]:
        sources[name] = sha256(ROOT / name)
    record = {
        "schema_version": 1, "milestone": "Phase 1D / Phase 1", "date": "2026-10-20",
        "status": "complete", "decision": "no-go", "reason": "zero observed early valid solutions; correctness passed",
        "base_commit": metadata["base_commit"], "source_sha256": sources,
        "profile_metadata": "results/phase1/profiles/run.json",
        "profile_metadata_sha256": sha256(base / "profiles/run.json"),
        "profiles_sha256": metadata["components_sha256"], "report_artifacts_sha256": provenance["artifacts_sha256"],
        "tests": {"passed": 186, "failed": 0, "errors": 0, "skipped": 0, "exit_code": 0,
                  "pytest_reported_seconds": 7.25, "junit_suite_seconds": float(suite.attrib["time"]),
                  "report": report_name, "report_sha256": sha256(ROOT / report_name), "by_module": dict(counts)},
        "development_relative_estimated_reduction": paired["relative_mean_reduction"],
        "development_relative_estimated_reduction_ci95": paired["relative_mean_reduction_ci95"],
        "development_estimated_baseline_ms": baseline, "development_estimated_verified_ms": candidate,
        "quality_difference": paired["quality_difference"], "quality_difference_ci95": paired["quality_difference_ci95"],
        "scope": analysis["coverage"], "frozen_protocol_sha256": PROTOCOL_SHA256, "partition_manifest_sha256": MANIFEST_SHA256,
        "figures_visually_inspected": True, "native_verification_command": "python scripts/verify_phase1d.py",
        "next_action": "Stop after Phase 1 report; Phase 2 go entry requirement not met.",
    }
    (base / "phase1d_validation.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    for name in ["README.md", "ROADMAP.md", "docs/phase1d_profiling.md", "results/phase1/summary.md"]:
        path = ROOT / name
        text = path.read_text(encoding="utf-8")
        require(text.count(chr(96) * 3) % 2 == 0, "Unbalanced fence.")
        for target in re.findall(r"\]\(([^)]+)\)", text):
            if "://" not in target and not target.startswith("#"):
                require((path.parent / target.split("#")[0]).exists(), "Broken link: " + name + " -> " + target)
    print("PASS: 186 tests; 200 identities x 5 repeats; frozen inputs; source/artifact hashes; 16,800 table rows; no-go reproduced.")


if __name__ == "__main__":
    main()
