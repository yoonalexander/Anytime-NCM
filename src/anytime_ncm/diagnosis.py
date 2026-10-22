"""Exploration-only descriptive diagnosis of saved Sudoku trajectories; no inference."""

from collections import Counter
import csv
import io
import json
from pathlib import Path

from anytime_ncm.dataset import load_examples, select_entries, sha256
from anytime_ncm.sudoku import parse_board, validate_solution
from anytime_ncm.trajectories import validate_record

INPUTS = {
    "docs/experiment_protocol.md": "557cf1377fe49b6c8515f506856ff0a395f8aaabe32adc79c25a8f2d9a3929ef",
    "docs/partitions/sudoku-hard.json": "ed7a6b3c102fe4713a3f80f8f02b53afe37a44b53da80964936467617799bdb7",
    "results/phase1/trajectories.jsonl": "2baf2948df953d7f379f9b359091c9a40d31fe9ecafe29f99305ff8bb3e0f5d9",
    "results/phase1/trajectories.metadata.json": "c873d0f584173cbdf17e0b19f787a41a512a8db2170e45a0a01fe4a6543df342",
    "results/phase1/analysis.json": "f07902170491118523d2038339f635b260561a227b8658753e2a83fdc8236f67",
}
SOURCE_PATHS = (
    "src/anytime_ncm/diagnosis.py", "src/anytime_ncm/diagnosis_render.py",
    "scripts/diagnose_sudoku_prefixes.py", "tests/test_diagnosis.py",
    "docs/studies/sudoku-prefix-diagnosis-plan.md",
)
GROUPS = ("all", "final_success", "final_failure")
UNIT_INDICES = {
    "row": [tuple(range(r * 9, r * 9 + 9)) for r in range(9)],
    "column": [tuple(range(c, 81, 9)) for c in range(9)],
    "box": [tuple((r + dr) * 9 + c + dc for dr in range(3) for dc in range(3))
            for r in (0, 3, 6) for c in (0, 3, 6)],
}


def board_errors(puzzle, output, reference):
    result = validate_solution(puzzle, output, reference=reference)
    clues, target = parse_board(puzzle).cells, parse_board(reference).cells
    given = sum(value != 0 for value in clues)
    data = {"parseable": result.parseable, "complete": result.complete,
            "valid": result.is_valid_solution, "reference_agreement": result.reference_agreement,
            "given_cells": given, "empty_cells": 81 - given,
            "board": list(result.board.cells) if result.board else None, "metrics": None}
    if not result.parseable:
        return data
    board = result.board.cells
    wrong = [i for i, (actual, expected) in enumerate(zip(board, target)) if actual != expected]
    blank = [i for i, value in enumerate(board) if value == 0]
    metrics = {"wrong_reference_cells": len(wrong), "blank_cells": len(blank),
               "wrong_filled_cells": sum(board[i] != 0 for i in wrong),
               "clue_violations": sum(clues[i] != 0 for i in wrong)}
    for name, positions in (("given", {i for i, v in enumerate(clues) if v}),
                            ("empty", {i for i, v in enumerate(clues) if not v})):
        metrics["wrong_" + name + "_cells"] = sum(i in positions for i in wrong)
        metrics["blank_" + name + "_cells"] = sum(i in positions for i in blank)
        metrics["wrong_filled_" + name + "_cells"] = sum(i in positions and board[i] != 0 for i in wrong)
    conflicting = set()
    for family, units in UNIT_INDICES.items():
        invalid = blank_units = duplicate_units = excess = missing = 0
        for indices in units:
            values = [board[i] for i in indices]
            counts = Counter(value for value in values if value)
            invalid += sorted(values) != list(range(1, 10))
            blank_units += 0 in values
            duplicate_units += any(count > 1 for count in counts.values())
            excess += sum(counts.values()) - len(counts)
            missing += 9 - len(counts)
            conflicting.update(i for i in indices if board[i] and counts[board[i]] > 1)
        metrics.update({family + "_invalid_units": invalid, family + "_blank_units": blank_units,
                        family + "_duplicate_units": duplicate_units,
                        family + "_duplicate_excess": excess, family + "_missing_digits": missing})
    metrics["invalid_units_total"] = sum(metrics[f + "_invalid_units"] for f in UNIT_INDICES)
    metrics["duplicate_excess_total"] = sum(metrics[f + "_duplicate_excess"] for f in UNIT_INDICES)
    metrics["conflicting_cells"] = len(conflicting)
    independently_valid = not (metrics["blank_cells"] or metrics["clue_violations"] or metrics["invalid_units_total"])
    if independently_valid != data["valid"]:
        raise ValueError("Independent metric-based validity disagrees with the validator.")
    assert metrics["wrong_reference_cells"] == metrics["wrong_given_cells"] + metrics["wrong_empty_cells"]
    assert metrics["wrong_reference_cells"] == metrics["blank_cells"] + metrics["wrong_filled_cells"]
    data["metrics"] = metrics
    return data


def transition_errors(puzzle, before, after, reference):
    clues, target = parse_board(puzzle).cells, parse_board(reference).cells
    try:
        a, b = parse_board(before).cells, parse_board(after).cells
    except ValueError:
        return None
    positions = {
        "changed_cells": [i for i in range(81) if a[i] != b[i]],
        "corrected_cells": [i for i in range(81) if a[i] != target[i] and b[i] == target[i]],
        "corrupted_cells": [i for i in range(81) if a[i] == target[i] and b[i] != target[i]],
        "wrong_to_different_wrong_cells": [i for i in range(81) if a[i] != b[i] and a[i] != target[i] and b[i] != target[i]],
        "stable_correct_cells": [i for i in range(81) if a[i] == b[i] == target[i]],
        "stable_wrong_cells": [i for i in range(81) if a[i] == b[i] and a[i] != target[i]],
        "blanks_filled": [i for i in range(81) if a[i] == 0 and b[i] != 0],
        "blanks_created": [i for i in range(81) if a[i] != 0 and b[i] == 0],
    }
    data = {name: len(indices) for name, indices in positions.items()}
    for name in ("changed_cells", "corrected_cells", "corrupted_cells", "wrong_to_different_wrong_cells"):
        for kind, given in (("given", True), ("empty", False)):
            data[name.removesuffix("_cells") + "_" + kind + "_cells"] = sum(bool(clues[i]) == given for i in positions[name])
    assert data["changed_cells"] == sum(data[k] for k in ("corrected_cells", "corrupted_cells", "wrong_to_different_wrong_cells"))
    assert sum(x != y for x, y in zip(b, target)) == sum(x != y for x, y in zip(a, target)) - data["corrected_cells"] + data["corrupted_cells"]
    assert data["changed_cells"] + data["stable_correct_cells"] + data["stable_wrong_cells"] == 81
    return data


def distribution(values):
    defined = sorted(v for v in values if v is not None)
    data = {"defined_count": len(defined), "undefined_count": len(values) - len(defined)}
    if not defined:
        return data | dict.fromkeys(("sum", "mean", "median", "p90", "p95", "min", "max", "zero_count", "positive_count")) | {"histogram": {}}
    def quantile(q):
        index = (len(defined) - 1) * q
        low = int(index)
        high = min(low + 1, len(defined) - 1)
        return defined[low] + (defined[high] - defined[low]) * (index - low)
    return data | {"sum": sum(defined), "mean": sum(defined) / len(defined),
                   "median": quantile(.5), "p90": quantile(.9), "p95": quantile(.95),
                   "min": defined[0], "max": defined[-1], "zero_count": defined.count(0),
                   "positive_count": sum(value > 0 for value in defined),
                   "histogram": {str(k): v for k, v in sorted(Counter(defined).items())}}


def summarize_rows(rows, metrics, *, boards):
    available = [r for r in rows if r["parseable"]]
    denominators = {name: sum(r[name] for r in available) for name in ("given_cells", "empty_cells")}
    summary = {"inputs": len(rows), "parseable_inputs": len(available),
               "unparseable_inputs": len(rows) - len(available),
               "given_cell_opportunities": denominators["given_cells"],
               "empty_cell_opportunities": denominators["empty_cells"],
               "all_cell_opportunities": 81 * len(available),
               "metrics": {name: distribution([r[name] for r in rows]) for name in metrics}}
    if boards:
        summary.update({"valid_count": sum(r["valid"] for r in rows),
                        "reference_agreement_count": sum(r["reference_agreement"] for r in rows)})
        summary["pooled_wrong_reference_rate"] = summary["metrics"]["wrong_reference_cells"]["sum"] / (81 * len(available)) if available else None
        for kind in ("given", "empty"):
            denom = denominators[kind + "_cells"]
            summary["pooled_wrong_" + kind + "_rate"] = summary["metrics"]["wrong_" + kind + "_cells"]["sum"] / denom if denom else None
    return summary


def read_exploration_records(path, selection, examples, run_id):
    if any(e.partition != "exploration" for e in examples):
        raise ValueError("Diagnosis accepts exploration examples only.")
    expected = {e.index: e for e in examples}
    records, skipped, count = [], 0, 0
    with Path(path).open(encoding="utf-8") as stream:
        for count, line in enumerate(stream, 1):
            if count > len(selection):
                raise ValueError("Unexpected extra trajectory.")
            entry = selection[count - 1]
            if entry["partition"] != "exploration":
                skipped += 1
                continue  # Deliberately before json.loads.
            if entry["index"] not in expected:
                raise ValueError("Unselected exploration input.")
            record = json.loads(line)
            validate_record(record, expected[entry["index"]], run_id)
            records.append(record)
    if count != len(selection) or len(records) != len(examples) or len({r["dataset_index"] for r in records}) != len(examples):
        raise ValueError("Missing or duplicated exploration trajectories.")
    return records, {"trajectory_lines_traversed": count, "exploration_records_deserialized": len(records),
                     "development_lines_skipped_before_json": skipped,
                     "development_records_deserialized": 0, "holdout_records_deserialized": 0}


def select_representatives(records, observations, transitions, examples):
    cases = {}
    for record in sorted(records, key=lambda r: r["dataset_index"]):
        index = record["dataset_index"]
        rows, changes = observations[index], transitions[index]
        predicates = {
            "early_primary_success": any(r["valid"] for r in rows[:-1]),
            "final_primary_success": rows[-1]["valid"],
            "final_primary_failure": not rows[-1]["valid"],
            "correct_cell_corrupted": any(r["corrupted_cells"] for r in changes if r["parseable"]),
            "level11_clue_violation_then_final_success": rows[10]["clue_violations"] is not None and rows[10]["clue_violations"] > 0 and rows[-1]["valid"],
            "final_complete_clue_consistent_grid_invalid": rows[-1]["parseable"] and rows[-1]["blank_cells"] == 0 and rows[-1]["clue_violations"] == 0 and rows[-1]["invalid_units_total"] > 0,
        }
        for name, applies in predicates.items():
            if name in cases or not applies:
                continue
            example = examples[index]
            cases[name] = {"dataset_index": index, "sample_id": record["sample_id"],
                           "puzzle": list(parse_board(example.puzzle).cells),
                           "reference": list(parse_board(example.reference).cells),
                           "boards": [record["levels"][k]["board_cells"] for k in (9, 10, 11)],
                           "metrics_levels_10_12": rows[9:12],
                           "transitions_10_12": changes[9:11]}
    names = ("early_primary_success", "final_primary_success", "final_primary_failure", "correct_cell_corrupted",
             "level11_clue_violation_then_final_success", "final_complete_clue_consistent_grid_invalid")
    return {name: cases.get(name) for name in names}


def analyze_records(records, examples):
    if not records:
        raise ValueError("No exploration trajectories.")
    observations, transitions = {}, {}
    for record in records:
        if record["partition"] != "exploration":
            raise ValueError("Development and holdouts cannot enter diagnosis.")
        example = examples[record["dataset_index"]]
        if example.partition != "exploration":
            raise ValueError("Non-exploration reference input.")
        rows, changes = [], []
        final = validate_solution(example.puzzle, record["levels"][-1]["decoded_ids"]).is_valid_solution
        header = {"sample_id": record["sample_id"], "dataset_index": record["dataset_index"],
                  "final_group": "final_success" if final else "final_failure"}
        for k, state in enumerate(record["levels"], 1):
            measured = board_errors(example.puzzle, state["decoded_ids"], example.reference)
            flat = measured.pop("metrics")
            measured.pop("board")
            rows.append(header | {"level": k} | measured | (flat or {}))
            if k > 1:
                delta = transition_errors(example.puzzle, record["levels"][k - 2]["decoded_ids"], state["decoded_ids"], example.reference)
                changes.append(header | {"from_level": k - 1, "to_level": k,
                                         "parseable": delta is not None, "given_cells": measured["given_cells"],
                                         "empty_cells": measured["empty_cells"]} | (delta or {}))
        observations[example.index], transitions[example.index] = rows, changes
    board_metrics = list(next(r for rows in observations.values() for r in rows if r["parseable"]))
    board_metrics = [name for name in board_metrics if name not in {"sample_id", "dataset_index", "final_group", "level", "parseable", "complete", "valid", "reference_agreement", "given_cells", "empty_cells"}]
    transition_metrics = [name for name in next(r for rows in transitions.values() for r in rows if r["parseable"])
                          if name not in {"sample_id", "dataset_index", "final_group", "from_level", "to_level", "parseable", "given_cells", "empty_cells"}]
    board_rows = [r for rows in observations.values() for r in rows]
    change_rows = [r for rows in transitions.values() for r in rows]
    for rows, metrics in ((board_rows, board_metrics), (change_rows, transition_metrics)):
        for row in rows:
            for name in metrics:
                row.setdefault(name, None)
    groups = {}
    for group in GROUPS:
        members = [index for index, rows in observations.items() if group == "all" or rows[-1]["final_group"] == group]
        groups[group] = {
            "inputs": len(members), "retrospective_group": group != "all",
            "levels": [summarize_rows([observations[i][k] for i in members], board_metrics, boards=True) | {"level": k + 1} for k in range(12)],
            "boundaries": [summarize_rows([transitions[i][k] for i in members], transition_metrics, boards=False) |
                           {"from_level": k + 1, "to_level": k + 2} for k in range(11)]}
    histogram = Counter()
    losses = [0] * 11
    for rows in observations.values():
        first = next((row["level"] for row in rows if row["valid"]), None)
        histogram[str(first) if first else "never"] += 1
        for k in range(11):
            losses[k] += rows[k]["valid"] and not rows[k + 1]["valid"]
    original_counts = {"inputs": len(records),
                       "valid_solution_count_by_level": [sum(rows[k]["valid"] for rows in observations.values()) for k in range(12)],
                       "first_valid_counts": {str(k): histogram[str(k)] for k in range(1, 13)} | {"never": histogram["never"]},
                       "never_solved_count": histogram["never"],
                       "valid_to_invalid_transition_counts": losses}
    return {"schema_version": 1, "study": "R1A", "partition": "exploration",
            "groups": groups, "reconfirmed_primary_counts": original_counts,
            "representative_cases": select_representatives(records, observations, transitions, examples)}, board_rows, change_rows


def analyze_saved(repository):
    repository = Path(repository)
    for name, expected in INPUTS.items():
        if sha256(repository / name) != expected:
            raise ValueError("Original Phase 1 input changed: " + name)
    examples, access = load_examples(repository, {"exploration": 1000})
    manifest = json.loads((repository / "docs/partitions/sudoku-hard.json").read_text())
    selected = select_entries(manifest, {"exploration": 1000, "development": 400})
    metadata = json.loads((repository / "results/phase1/trajectories.metadata.json").read_text())
    for name, expected in metadata["source_sha256"].items():
        if sha256(repository / name) != expected:
            raise ValueError("Original collection source changed: " + name)
    if access["artifacts"] != metadata["checkpoint_artifacts"]:
        raise ValueError("Dataset/checkpoint artifact declarations changed.")
    if metadata["status"] != "complete" or metadata["record_count"] != 1400:
        raise ValueError("Original collection is incomplete.")
    if metadata["selected_examples"] != list(selected):
        raise ValueError("Historical selection/order changed.")
    records, routing = read_exploration_records(repository / "results/phase1/trajectories.jsonl", selected, examples, metadata["run_id"])
    analysis, board_rows, change_rows = analyze_records(records, {e.index: e for e in examples})
    expected = json.loads((repository / "results/phase1/analysis.json").read_text())["trajectory_summary"]["exploration"]
    if any(expected[name] != value for name, value in analysis["reconfirmed_primary_counts"].items()):
        raise ValueError("Original exploration primary counts disagree; stop diagnosis.")
    analysis["access"] = routing | {"selected_puzzle_rows": access["selected_rows_per_file"],
                                    "selected_reference_rows": access["selected_rows_per_file"],
                                    "sealed_rows_materialized": access["sealed_rows_materialized"],
                                    "model_calls": 0, "timed_requests": 0}
    return analysis, board_rows, change_rows


def csv_text(rows):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()


def run_diagnosis(repository, output, *, verify=False):
    repository, output = Path(repository).resolve(), Path(output).resolve()
    if not output.is_relative_to(repository / "results/followup"):
        raise ValueError("R1A output must be inside results/followup/.")
    if not verify and output.exists():
        raise ValueError("Preserve existing evidence; choose a fresh output directory.")
    analysis, boards, changes = analyze_saved(repository)
    outputs = {"analysis.json": json.dumps(analysis, indent=2, sort_keys=True) + "\n",
               "board_metrics.csv": csv_text(boards), "transition_metrics.csv": csv_text(changes)}
    if verify:
        provenance = json.loads((output / "provenance.json").read_text())
        for kind in ("inputs_sha256", "source_sha256"):
            for name, expected in provenance[kind].items():
                if sha256(repository / name) != expected:
                    raise ValueError("Input/source checksum differs: " + name)
        for name, expected in provenance["artifacts_sha256"].items():
            if sha256(output / name) != expected:
                raise ValueError("Output checksum differs: " + name)
        for name, text in outputs.items():
            if (output / name).read_text(encoding="utf-8") != text:
                raise ValueError("Recomputed result differs: " + name)
        return analysis
    from anytime_ncm.diagnosis_render import render_diagnosis
    output.mkdir(parents=True)
    for name, text in outputs.items():
        (output / name).write_text(text, encoding="utf-8", newline="\n")
    render_diagnosis(output, analysis, repository)
    artifacts = list(outputs) + ["summary.md", "error_trends.png", "transition_changes.png", "late_error_distributions.png"]
    provenance = {
        "study": "R1A", "date": "2026-10-22", "status": "complete",
        "empirical_snapshot_commit": "c1fce9311998e2d7ae9609c1e34b0c6949d6a256",
        "inputs_sha256": INPUTS, "source_sha256": {name: sha256(repository / name) for name in SOURCE_PATHS} |
                         json.loads((repository / "results/phase1/trajectories.metadata.json").read_text())["source_sha256"],
        "artifacts_sha256": {name: sha256(output / name) for name in artifacts},
        "coverage": {"exploration_inputs": len(boards) // 12, "board_rows": len(boards), "transition_rows": len(changes)},
        "access": analysis["access"],
        "command": "scripts/diagnose_sudoku_prefixes.py --output " + output.relative_to(repository).as_posix(),
    }
    (output / "provenance.json").write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return analysis
