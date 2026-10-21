"""Versioned compact JSONL records and independent on-disk consistency checks."""

import json
import math
from pathlib import Path

from anytime_ncm.dataset import Example, sha256
from anytime_ncm.features import CausalFeatureTracker, PrefixObservation
from anytime_ncm.sudoku import official_metrics, validate_solution

LEVEL_LENGTHS = (1, 2, 4, 6, 9, 13, 18, 26, 37, 50, 67, 89)
TIMING_COMPONENTS = ("generation", "reconstruction", "decode", "transfer", "validation", "features")


def decoded_text(ids) -> str:
    return "".join(("_123456789|"[token] if token != 11 else "") for token in ids)


def label_output(example: Example, ids: list[int], text: str) -> tuple[dict, dict, list | None]:
    if len(ids) != 89 or any(type(token) is not int or not 0 <= token <= 11 for token in ids):
        raise ValueError("Output must have 89 legal token IDs.")
    if decoded_text(ids) != text:
        raise ValueError("Decoded text and raw token IDs disagree.")
    result = validate_solution(example.puzzle, ids, reference=example.reference)
    metrics = official_metrics(text, decoded_text(example.reference))
    correctness = {
        "parseable": result.parseable, "complete": result.complete,
        "grid_valid": result.grid_valid, "clue_consistent": result.clue_consistent,
        "is_valid_solution": result.is_valid_solution, "parse_error": result.parse_error,
    }
    diagnostics = {"reference_agreement": result.reference_agreement,
                   "official_solved": metrics.solved, "official_valid_grid": metrics.valid_grid,
                   "official_cell_accuracy": metrics.cell_accuracy if math.isfinite(metrics.cell_accuracy) else None}
    return correctness, diagnostics, list(result.board.cells) if result.board is not None else None


def make_record(example: Example, run_id: str, levels, codes: list[int], batch: int) -> dict:
    if len(levels) != 12 or len(codes) != sum(LEVEL_LENGTHS):
        raise ValueError("Collection requires all 12 full-depth levels.")
    tracker, states, offset = CausalFeatureTracker(), [], 0
    for level, length in enumerate(LEVEL_LENGTHS, 1):
        output = levels[level - 1]
        ids = [int(value) for value in output.token_ids[batch].tolist()]
        text = output.texts[batch]
        correctness, diagnostics, board = label_output(example, ids, text)
        cumulative = offset + length
        if (output.level, output.code_length, output.cumulative_codes) != (level, length, cumulative):
            raise ValueError("Adapter hierarchy metadata disagrees with released levels.")
        features = tracker.observe(PrefixObservation(level, length, cumulative, tuple(ids)))
        states.append({"level": level, "code_length": length, "cumulative_codes": cumulative,
                       "code_ids": codes[offset:cumulative], "decoded_ids": ids, "decoded_text": text,
                       "board_cells": board, "correctness": correctness, "diagnostics": diagnostics,
                       "features": features, "timing_ms": dict.fromkeys(TIMING_COMPONENTS)})
        offset = cumulative
    return {"schema_version": 1, "run_id": run_id, "sample_id": example.identity,
            "dataset_index": example.index, "partition": example.partition, "levels": states}


def validate_record(record: dict, example: Example, run_id: str) -> None:
    header = {"schema_version": 1, "run_id": run_id, "sample_id": example.identity,
              "dataset_index": example.index, "partition": example.partition}
    if set(record) != set(header) | {"levels"} or any(type(record[key]) is not type(value) or record[key] != value for key, value in header.items()):
        raise ValueError("Record identity, partition, run, or schema mismatch.")
    if len(record["levels"]) != 12:
        raise ValueError("Trajectory must contain every level exactly once.")
    tracker, cumulative = CausalFeatureTracker(), 0
    keys = {"level", "code_length", "cumulative_codes", "code_ids", "decoded_ids", "decoded_text",
            "board_cells", "correctness", "diagnostics", "features", "timing_ms"}
    for level, (length, state) in enumerate(zip(LEVEL_LENGTHS, record["levels"], strict=True), 1):
        cumulative += length
        if set(state) != keys or any(type(state[key]) is not int for key in ("level", "code_length", "cumulative_codes")) or (state["level"], state["code_length"], state["cumulative_codes"]) != (level, length, cumulative):
            raise ValueError("Level schema or hierarchy counts are invalid.")
        if len(state["code_ids"]) != length or any(type(value) is not int or not 0 <= value < 16 for value in state["code_ids"]):
            raise ValueError("Invalid generated code IDs.")
        correctness, diagnostics, board = label_output(example, state["decoded_ids"], state["decoded_text"])
        if state["correctness"] != correctness or state["diagnostics"] != diagnostics or state["board_cells"] != board or any(type(state["correctness"][key]) is not bool for key in ("parseable", "complete", "grid_valid", "clue_consistent", "is_valid_solution")):
            raise ValueError("Stored labels or board disagree with decoded output.")
        expected = tracker.observe(PrefixObservation(level, length, cumulative, tuple(state["decoded_ids"])))
        if state["features"] != expected:
            raise ValueError("Features disagree with current/past observations.")
        if state["timing_ms"] != dict.fromkeys(TIMING_COMPONENTS):
            raise ValueError("Unprofiled collection timings must be null.")


def validate_jsonl(path: Path, examples: tuple[Example, ...], run_id: str) -> dict:
    count = 0
    with Path(path).open(encoding="utf-8") as stream:
        for count, line in enumerate(stream, 1):
            if count > len(examples):
                raise ValueError("Unexpected extra trajectory or partition access.")
            record = json.loads(line, parse_constant=lambda value: (_ for _ in ()).throw(ValueError("Nonfinite JSON.")))
            validate_record(record, examples[count - 1], run_id)
    if count != len(examples):
        raise ValueError("Missing trajectories.")
    return {"status": "complete", "record_count": count, "level_record_count": count * 12,
            "trajectory_sha256": sha256(path), "partition_counts": {
                name: sum(example.partition == name for example in examples)
                for name in sorted({example.partition for example in examples})},
            "timed_level_records": 0, "unavailable_timing_level_records": count * 12}
