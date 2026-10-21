"""Collector integration, configuration, and selective holdout-access contracts."""

from dataclasses import fields
import json
from pathlib import Path
import pickle
from types import SimpleNamespace

import pytest
import torch

from anytime_ncm.collect import output_path, validate_config, write_records
from anytime_ncm.dataset import Example, _TokenRows, load_examples, puzzle_identity, select_entries
from anytime_ncm.features import CausalFeatureTracker, PrefixObservation
from anytime_ncm.sudoku import parse_board
from anytime_ncm.trajectories import (
    LEVEL_LENGTHS, make_record, validate_jsonl, validate_record,
)
from anytime_ncm.upstream_adapter import SUDOKU_LEVELS

ROOT = Path(__file__).resolve().parents[1]
SOLUTION = "534678912672195348198342567859761423426853791713924856961537284287419635345286179"


def encode(text):
    return tuple("_123456789|".index(c) for c in text)


def example(index=0, partition="exploration"):
    cells = list(SOLUTION)
    for bit in range(6):
        if (index + 1) & (1 << bit):
            cells[bit] = "0"
    puzzle = (11,) + encode(parse_board("".join(cells)).to_text()) + (11,)
    reference = encode(parse_board(SOLUTION).to_text())
    return Example(index, partition, puzzle_identity(puzzle), puzzle, reference)


def outputs(batch_size):
    ids = torch.tensor([list(example().reference)] * batch_size, dtype=torch.long)
    result, total = [], 0
    for level, length in enumerate(LEVEL_LENGTHS, 1):
        total += length
        result.append(SimpleNamespace(level=level, code_length=length, cumulative_codes=total,
                                      token_ids=ids.clone(), texts=(parse_board(SOLUTION).to_text(),) * batch_size))
    return result


def valid_config():
    return dict(schema_version=1, task="sudoku-hard", run_id="synthetic_smoke",
                partitions={"exploration": 32}, batch_size=128,
                output_path="results/synthetic.jsonl", smoke_metadata=None)


@pytest.mark.parametrize("change", [
    {"partitions": {"phase2_final": 1}}, {"partitions": {"phase3_final": 1}},
    {"partitions": {"exploration": 1001}}, {"partitions": {"development": 401}},
    {"partitions": {"exploration": True}}, {"partitions": {}},
    {"batch_size": 0}, {"batch_size": 129}, {"batch_size": True},
    {"run_id": "../bad"}, {"task": "other"}, {"schema_version": True},
    {"output_path": "results/file.txt"}, {"unknown": 1},
    {"partitions": {"development": 20}}, {"smoke_metadata": 12},
])
def test_bad_configuration_is_rejected(change):
    config = valid_config()
    config.update(change)
    with pytest.raises(ValueError):
        validate_config(config)


def test_expansion_requires_smoke_evidence():
    config = valid_config()
    config.update(partitions={"exploration": 1000, "development": 400},
                  smoke_metadata="results/smoke.metadata.json")
    assert validate_config(config) == config


def test_output_must_stay_in_results(tmp_path):
    with pytest.raises(ValueError):
        output_path(tmp_path, "../escape.jsonl")
    assert output_path(tmp_path, "results/run.jsonl") == tmp_path / "results/run.jsonl"


def manifest_fixture():
    return {"partitions": {
        "exploration": [{"index": 0, "puzzle_sha256": "a"}, {"index": 2, "puzzle_sha256": "c"}],
        "development": [{"index": 1, "puzzle_sha256": "b"}],
        "phase2_final": [{"index": 3, "puzzle_sha256": "d"}],
        "phase3_final": [{"index": 4, "puzzle_sha256": "e"}],
    }}


def test_selection_is_in_dataset_order_and_never_includes_holdouts():
    selected = select_entries(manifest_fixture(), {"exploration": 2, "development": 1})
    assert [e["index"] for e in selected] == [0, 1, 2]
    assert {e["partition"] for e in selected} == {"exploration", "development"}


@pytest.mark.parametrize("partition", ["phase2_final", "phase3_final"])
def test_loader_rejects_holdouts_before_any_dataset_access(partition, monkeypatch):
    original = Path.open

    def guarded(path, *args, **kwargs):
        if path.name in {"puzzles.pickle", "solutions.pickle", "generator.pt", "tokenizer.pt"}:
            raise AssertionError("Opened dataset/artifact before rejecting holdout selection.")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guarded)
    with pytest.raises(ValueError, match="only exploration"):
        load_examples(ROOT, {partition: 1})


@pytest.mark.parametrize("field,value", [("index", 0), ("puzzle_sha256", "a")])
def test_cross_partition_duplicates_are_rejected(field, value):
    manifest = manifest_fixture()
    manifest["partitions"]["phase3_final"][0][field] = value
    with pytest.raises(ValueError, match="disjoint"):
        select_entries(manifest, {"exploration": 1})


def test_selective_reader_does_not_decode_unselected_operands(monkeypatch):
    rows = [[1] * 89, [255] * 89, [2] * 89, [255] * 89]
    reader = _TokenRows(pickle.dumps(rows, protocol=4))
    called = []
    original = _TokenRows.token

    def monitored(self):
        value = original(self)
        called.append(value)
        return value

    monkeypatch.setattr(_TokenRows, "token", monitored)
    assert reader.select({0, 2}, 89, 4) == {0: (1,) * 89, 2: (2,) * 89}
    assert called == [1] * 89 + [2] * 89


def test_selective_reader_handles_frames_and_two_thousand_row_batches():
    rows = [[index % 12] * 91 for index in range(2000)]
    raw = pickle.dumps(rows, protocol=4)
    assert raw.count(b"\x95") > 1
    chosen = {0, 999, 1000, 1999}
    actual = _TokenRows(raw).select(chosen, 91, 2000)
    assert actual == {index: tuple(rows[index]) for index in chosen}


@pytest.mark.parametrize("raw,indices,length,count", [
    (pickle.dumps([[1] * 89, [2] * 89], protocol=5), {0}, 89, 2),
    (pickle.dumps([[1] * 88, [2] * 89], protocol=4), {0}, 89, 2),
    (pickle.dumps([[255] * 89, [2] * 89], protocol=4), {0}, 89, 2),
    (pickle.dumps([[1] * 89, [2] * 89], protocol=4)[:-1], {0}, 89, 2),
    (pickle.dumps([[1] * 89, [2] * 89], protocol=4) + b"extra", {0}, 89, 2),
    (pickle.dumps([[1] * 89, [2] * 89], protocol=4), {3}, 89, 2),
    (b"\x80\x04cos\nsystem\n.", {0}, 89, 1),
])
def test_selective_reader_rejects_unexpected_format(raw, indices, length, count):
    with pytest.raises(ValueError):
        _TokenRows(raw).select(indices, length, count)


def test_feature_interface_has_no_future_reference_or_verifier_fields():
    assert {field.name for field in fields(PrefixObservation)} == {
        "level", "code_length", "cumulative_codes", "decoded_ids"}
    tracker = CausalFeatureTracker()
    a = tracker.observe(PrefixObservation(1, 1, 1, (1,) * 89))
    b = tracker.observe(PrefixObservation(2, 2, 3, (1,) * 88 + (2,)))
    assert a["token_change_fraction"] is None
    assert b["token_change_fraction"] == 1 / 89
    saved = dict(a)
    tracker.observe(PrefixObservation(3, 4, 7, (3,) * 89))
    assert a == saved


def test_feature_history_cannot_skip_or_repeat_levels():
    with pytest.raises(ValueError):
        CausalFeatureTracker().observe(PrefixObservation(2, 2, 3, (1,) * 89))


def good_record():
    return make_record(example(), "synthetic", outputs(1), [0] * 322, 0)


def test_schema_keeps_current_features_separate_from_reference_diagnostics():
    record = good_record()
    validate_record(record, example(), "synthetic")
    assert LEVEL_LENGTHS == SUDOKU_LEVELS
    assert len(record["levels"]) == 12
    for level in record["levels"]:
        assert set(level["features"]) == {"level", "code_length", "cumulative_codes", "token_change_fraction"}
        assert level["correctness"]["is_valid_solution"] is True
        assert level["diagnostics"]["reference_agreement"] is True
        assert all(value is None for value in level["timing_ms"].values())


@pytest.mark.parametrize("corruption", [
    "partition", "identity", "missing_level", "level_order", "cumulative", "codebook",
    "text", "board", "flags", "reference_diagnostic", "future_feature", "timing", "schema_bool", "flag_int", "level_float",
])
def test_record_rejects_inconsistent_or_leaking_content(corruption):
    record = good_record()
    state = record["levels"][0]
    if corruption == "partition":
        record["partition"] = "phase2_final"
    elif corruption == "identity":
        record["sample_id"] = "wrong"
    elif corruption == "missing_level":
        record["levels"].pop()
    elif corruption == "level_order":
        state["level"] = 12
    elif corruption == "cumulative":
        state["cumulative_codes"] = 12
    elif corruption == "codebook":
        state["code_ids"] = [16]
    elif corruption == "text":
        state["decoded_text"] = "wrong"
    elif corruption == "board":
        state["board_cells"][0] = 0
    elif corruption == "flags":
        state["correctness"]["is_valid_solution"] = False
    elif corruption == "reference_diagnostic":
        state["diagnostics"]["reference_agreement"] = False
    elif corruption == "future_feature":
        state["features"]["oracle_exit"] = 4
    elif corruption == "timing":
        state["timing_ms"]["decode"] = 0.0
    elif corruption == "schema_bool":
        record["schema_version"] = True
    elif corruption == "flag_int":
        state["correctness"]["is_valid_solution"] = 1
    elif corruption == "level_float":
        state["level"] = 1.0
    with pytest.raises(ValueError):
        validate_record(record, example(), "synthetic")


def test_end_to_end_batches_preserve_each_input_and_disk_roundtrip(tmp_path):
    examples = (example(0), example(1), example(2, "development"))
    calls = []

    class Adapter:
        def generate_codes(self, context):
            calls.append(context.tolist())
            return torch.zeros(context.shape[0], 322, dtype=torch.long)

        def decode_prefixes(self, codes):
            return outputs(codes.shape[0])

    path = tmp_path / "trajectories.jsonl"
    with path.open("w", encoding="utf-8") as stream:
        write_records(Adapter(), examples, 2, "cpu", "synthetic", stream)
    report = validate_jsonl(path, examples, "synthetic")
    assert [len(call) for call in calls] == [2, 1]
    assert [row for call in calls for row in call] == [list(e.puzzle) for e in examples]
    assert report["record_count"] == 3 and report["level_record_count"] == 36
    assert report["partition_counts"] == {"development": 1, "exploration": 2}
    assert report["timed_level_records"] == 0
    # An appended duplicate cannot masquerade as a successful complete file.
    with path.open("a", encoding="utf-8") as stream:
        stream.write(path.read_text().splitlines()[0] + "\n")
    with pytest.raises(ValueError, match="extra trajectory"):
        validate_jsonl(path, examples, "synthetic")


def test_missing_rows_are_detected(tmp_path):
    path = tmp_path / "empty.jsonl"
    path.write_text("")
    with pytest.raises(ValueError, match="Missing"):
        validate_jsonl(path, (example(),), "synthetic")
