"""Known-count fixtures, retrospective groups, access isolation, and evidence guards."""

from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from anytime_ncm import diagnosis as d

REFERENCE = tuple(map(int, "534678912672195348198342567859761423426853791713924856961537284287419635345286179"))


def puzzle(*indices):
    return tuple(value if i in indices else 0 for i, value in enumerate(REFERENCE))


def test_valid_board_has_zero_errors_in_every_metric():
    result = d.board_errors(puzzle(0, 7), REFERENCE, REFERENCE)
    assert result["valid"] and result["reference_agreement"]
    assert result["given_cells"] == 2 and result["empty_cells"] == 79
    assert not any(result["metrics"].values())


def test_single_duplicate_has_known_unit_excess_and_overlapping_conflicting_cells():
    board = list(REFERENCE)
    board[0] = 3
    m = d.board_errors(puzzle(0), board, REFERENCE)["metrics"]
    assert m["wrong_reference_cells"] == m["wrong_given_cells"] == m["clue_violations"] == 1
    assert m["wrong_empty_cells"] == m["blank_cells"] == 0
    assert m["invalid_units_total"] == m["duplicate_excess_total"] == 3
    for family in ("row", "column", "box"):
        assert m[family + "_duplicate_units"] == m[family + "_duplicate_excess"] == m[family + "_missing_digits"] == 1
    assert m["conflicting_cells"] == 3  # Union {0, 1, 72}, not sum of pairs.


def test_blank_is_an_error_and_missing_digit_but_not_a_duplicate():
    board = list(REFERENCE)
    board[0] = 0
    m = d.board_errors(puzzle(0), board, REFERENCE)["metrics"]
    assert m["wrong_reference_cells"] == m["blank_given_cells"] == m["clue_violations"] == 1
    assert m["wrong_filled_cells"] == m["duplicate_excess_total"] == m["conflicting_cells"] == 0
    assert m["invalid_units_total"] == 3
    for family in ("row", "column", "box"):
        assert m[family + "_blank_units"] == m[family + "_missing_digits"] == 1
        assert m[family + "_duplicate_units"] == 0


def test_all_blank_board_has_no_duplicate_digits_and_explicit_position_split():
    m = d.board_errors(puzzle(0, 1), [0] * 81, REFERENCE)["metrics"]
    assert m["blank_cells"] == m["wrong_reference_cells"] == 81
    assert m["blank_given_cells"] == 2 and m["blank_empty_cells"] == 79
    assert m["invalid_units_total"] == 27
    assert m["duplicate_excess_total"] == m["conflicting_cells"] == 0
    assert m["row_missing_digits"] == 81


def test_swap_within_row_and_box_only_breaks_two_columns():
    board = list(REFERENCE)
    board[0], board[1] = board[1], board[0]
    m = d.board_errors(puzzle(0), board, REFERENCE)["metrics"]
    assert m["wrong_reference_cells"] == 2
    assert m["wrong_given_cells"] == m["wrong_empty_cells"] == 1
    assert m["row_invalid_units"] == m["box_invalid_units"] == 0
    assert m["column_invalid_units"] == 2


def test_valid_grid_with_corrupted_clue_is_not_accepted():
    board = [2 if value == 1 else 1 if value == 2 else value for value in REFERENCE]
    data = d.board_errors(puzzle(7), board, REFERENCE)
    assert not data["valid"]
    assert data["metrics"]["invalid_units_total"] == 0
    assert data["metrics"]["clue_violations"] == 1


def test_alternative_valid_solution_is_not_rejected_for_reference_disagreement():
    board = [2 if value == 1 else 1 if value == 2 else value for value in REFERENCE]
    data = d.board_errors(puzzle(), board, REFERENCE)
    assert data["valid"] and not data["reference_agreement"]
    assert data["metrics"]["wrong_reference_cells"] == 18


def test_unparseable_board_is_undefined_not_zero_error():
    data = d.board_errors(puzzle(), REFERENCE[:-1], REFERENCE)
    assert data["metrics"] is None and not data["parseable"] and not data["valid"]


def test_transitions_partition_changes_and_preserve_net_error_identity():
    before, after = list(REFERENCE), list(REFERENCE)
    before[0], before[1], before[2] = 3, 4, 7
    after[1], after[2], after[3] = 6, 7, 0
    m = d.transition_errors(puzzle(0, 3), before, after, REFERENCE)
    assert m["changed_cells"] == 3
    assert m["corrected_cells"] == m["corrupted_cells"] == m["wrong_to_different_wrong_cells"] == 1
    assert m["stable_wrong_cells"] == 1 and m["stable_correct_cells"] == 77
    assert m["corrected_given_cells"] == m["corrupted_given_cells"] == 1
    assert m["wrong_to_different_wrong_empty_cells"] == m["blanks_created"] == 1


def test_filling_blank_incorrectly_is_wrong_to_different_wrong():
    before, after = list(REFERENCE), list(REFERENCE)
    before[0], after[0] = 0, 3
    m = d.transition_errors(puzzle(), before, after, REFERENCE)
    assert m["blanks_filled"] == m["wrong_to_different_wrong_cells"] == 1
    assert m["corrected_cells"] == m["corrupted_cells"] == 0


def test_malformed_transition_has_undefined_metrics():
    assert d.transition_errors(puzzle(), REFERENCE[:-1], REFERENCE, REFERENCE) is None


def test_histogram_quantiles_use_declared_interpolation_and_coverage():
    m = d.distribution([0, 0, 2, 8, None])
    assert m["defined_count"] == 4 and m["undefined_count"] == 1
    assert m["sum"] == 10 and m["mean"] == 2.5 and m["median"] == 1
    assert m["p90"] == pytest.approx(6.2) and m["p95"] == pytest.approx(7.1)
    assert m["histogram"] == {"0": 2, "2": 1, "8": 1}
    assert m["zero_count"] == m["positive_count"] == 2


@pytest.mark.parametrize("values", [[], [None], [None, None]])
def test_undefined_or_empty_distribution_does_not_invent_zero(values):
    m = d.distribution(values)
    assert m["mean"] is None and m["sum"] is None and m["histogram"] == {}
    assert m["undefined_count"] == len(values)


def test_pooled_rates_use_summed_position_opportunities():
    rows = [
        {"parseable": True, "given_cells": 1, "empty_cells": 80, "valid": False, "reference_agreement": False,
         "wrong_reference_cells": 3, "wrong_given_cells": 1, "wrong_empty_cells": 2},
        {"parseable": True, "given_cells": 3, "empty_cells": 78, "valid": False, "reference_agreement": False,
         "wrong_reference_cells": 5, "wrong_given_cells": 1, "wrong_empty_cells": 4},
    ]
    m = d.summarize_rows(rows, ("wrong_reference_cells", "wrong_given_cells", "wrong_empty_cells"), boards=True)
    assert m["pooled_wrong_given_rate"] == .5  # Not mean(1/1, 1/3).
    assert m["pooled_wrong_empty_rate"] == pytest.approx(6 / 158)
    assert m["pooled_wrong_reference_rate"] == pytest.approx(8 / 162)


def test_reader_skips_development_before_json_deserialization(tmp_path, monkeypatch):
    source = tmp_path / "rows.jsonl"
    source.write_text('{"dataset_index": 0}\nNOT JSON AND MUST NOT BE PARSED\n{"dataset_index": 2}\n')
    examples = tuple(SimpleNamespace(index=i, partition="exploration") for i in (0, 2))
    selection = [{"index": 0, "partition": "exploration"}, {"index": 1, "partition": "development"},
                 {"index": 2, "partition": "exploration"}]
    seen = []
    monkeypatch.setattr(d, "validate_record", lambda record, example, run: seen.append((record["dataset_index"], example.index)))
    records, access = d.read_exploration_records(source, selection, examples, "run")
    assert seen == [(0, 0), (2, 2)] and len(records) == 2
    assert access["development_lines_skipped_before_json"] == 1
    assert access["development_records_deserialized"] == 0


@pytest.mark.parametrize("partition", ["development", "phase2_final", "phase3_final"])
def test_reader_rejects_nonexploration_examples_before_opening_file(tmp_path, partition):
    with pytest.raises(ValueError, match="exploration"):
        d.read_exploration_records(tmp_path / "missing", [], [SimpleNamespace(partition=partition)], "run")


@pytest.mark.parametrize("lines", ["", '{"dataset_index":0}\n{"dataset_index":1}\n'])
def test_reader_rejects_missing_or_extra_rows(tmp_path, monkeypatch, lines):
    source = tmp_path / "rows.jsonl"
    source.write_text(lines)
    monkeypatch.setattr(d, "validate_record", lambda *args: None)
    with pytest.raises(ValueError):
        d.read_exploration_records(source, [{"index": 0, "partition": "exploration"}],
                                   [SimpleNamespace(index=0, partition="exploration")], "run")


def synthetic_records():
    bad = list(REFERENCE)
    bad[0] = 3
    examples = {0: SimpleNamespace(index=0, partition="exploration", puzzle=puzzle(0), reference=REFERENCE),
                6: SimpleNamespace(index=6, partition="exploration", puzzle=puzzle(), reference=REFERENCE)}
    records = []
    for index in (6, 0):  # Representative selection must sort by dataset index.
        states = [bad] * 12 if index == 6 else [bad] * 11 + [REFERENCE]
        records.append({"dataset_index": index, "sample_id": str(index), "partition": "exploration",
                        "levels": [{"decoded_ids": list(board), "board_cells": list(board)} for board in states]})
    return records, examples


def test_groups_counts_absent_categories_and_representatives_are_reproducible():
    records, examples = synthetic_records()
    analysis, boards, transitions = d.analyze_records(records, examples)
    assert len(boards) == 24 and len(transitions) == 22
    assert analysis["reconfirmed_primary_counts"]["valid_solution_count_by_level"] == [0] * 11 + [1]
    assert analysis["groups"]["final_success"]["inputs"] == analysis["groups"]["final_failure"]["inputs"] == 1
    assert analysis["groups"]["final_success"]["retrospective_group"]
    cases = analysis["representative_cases"]
    assert cases["early_primary_success"] is None and cases["correct_cell_corrupted"] is None
    assert cases["final_primary_success"]["dataset_index"] == 0
    assert cases["final_primary_failure"]["dataset_index"] == 6
    assert cases["final_complete_clue_consistent_grid_invalid"]["dataset_index"] == 6
    assert cases["level11_clue_violation_then_final_success"]["dataset_index"] == 0


@pytest.mark.parametrize("partition", ["development", "phase2_final"])
def test_analysis_rejects_nonexploration_data(partition):
    records, examples = synthetic_records()
    records[0]["partition"] = partition
    with pytest.raises(ValueError):
        d.analyze_records(records, examples)


def test_output_guard_rejects_overwrite_and_outside_path_before_dataset_access(tmp_path, monkeypatch):
    monkeypatch.setattr(d, "analyze_saved", lambda *args: pytest.fail("Must not read datasets"))
    existing = tmp_path / "results/followup/existing"
    existing.mkdir(parents=True)
    with pytest.raises(ValueError, match="existing"):
        d.run_diagnosis(tmp_path, existing)
    with pytest.raises(ValueError, match="inside"):
        d.run_diagnosis(tmp_path, tmp_path / "other")


def test_verify_recomputes_tables_and_rejects_changed_evidence(tmp_path, monkeypatch):
    output = tmp_path / "results/followup/test"
    output.mkdir(parents=True)
    analysis, boards, changes = {"study": "fixture"}, [{"metric": 1}], [{"metric": 2}]
    monkeypatch.setattr(d, "analyze_saved", lambda *args: (analysis, boards, changes))
    for name, text in {"analysis.json": json.dumps(analysis, indent=2, sort_keys=True) + "\n",
                       "board_metrics.csv": d.csv_text(boards), "transition_metrics.csv": d.csv_text(changes)}.items():
        (output / name).write_text(text, newline="\n")
    provenance = {"inputs_sha256": {}, "source_sha256": {},
                  "artifacts_sha256": {p.name: d.sha256(p) for p in output.iterdir()}}
    (output / "provenance.json").write_text(json.dumps(provenance))
    assert d.run_diagnosis(tmp_path, output, verify=True) == analysis
    (output / "board_metrics.csv").write_text("metric\n999\n")
    with pytest.raises(ValueError, match="checksum"):
        d.run_diagnosis(tmp_path, output, verify=True)


@pytest.mark.parametrize("mismatch", [False, True])
def test_saved_loader_accepts_original_identity_schema_and_stops_on_count_mismatch(tmp_path, monkeypatch, mismatch):
    records, examples = synthetic_records()
    records.sort(key=lambda r: r["dataset_index"])
    selection = [{"index": index, "partition": "exploration", "puzzle_sha256": str(index)} for index in (0, 6)]
    base = tmp_path / "results/phase1"
    base.mkdir(parents=True)
    manifest = tmp_path / "docs/partitions"
    manifest.mkdir(parents=True)
    (manifest / "sudoku-hard.json").write_text("{}")
    metadata = {"status": "complete", "record_count": 1400, "source_sha256": {},
                "checkpoint_artifacts": [], "selected_examples": selection, "run_id": "fixture"}
    (base / "trajectories.metadata.json").write_text(json.dumps(metadata))
    (base / "trajectories.jsonl").write_text("".join(json.dumps(r) + "\n" for r in records))
    expected = d.analyze_records(records, examples)[0]["reconfirmed_primary_counts"]
    if mismatch:
        expected["valid_solution_count_by_level"][-1] = 999
    (base / "analysis.json").write_text(json.dumps({"trajectory_summary": {"exploration": expected}}))
    monkeypatch.setattr(d, "INPUTS", {})
    monkeypatch.setattr(d, "load_examples", lambda *args: (tuple(examples.values()), {
        "artifacts": [], "selected_rows_per_file": 2, "sealed_rows_materialized": 0}))
    monkeypatch.setattr(d, "select_entries", lambda *args: tuple(selection))
    monkeypatch.setattr(d, "validate_record", lambda *args: None)
    if mismatch:
        with pytest.raises(ValueError, match="primary counts disagree"):
            d.analyze_saved(tmp_path)
    else:
        analysis, boards, changes = d.analyze_saved(tmp_path)
        assert len(boards) == 24 and len(changes) == 22
        assert analysis["access"]["development_records_deserialized"] == 0
