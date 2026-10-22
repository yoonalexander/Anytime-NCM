"""Metadata I/O retry and exact pending-slot accounting for the R3 amendment."""
import importlib.util
import json
from pathlib import Path

import pytest

PATH = Path(__file__).resolve().parents[1] / "scripts/resume_sudoku_easy_r3.py"
spec = importlib.util.spec_from_file_location("r3_resume", PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_atomic_save_retries_filesystem_replace_without_model_calls(tmp_path, monkeypatch):
    calls = []
    real = module.os.replace
    def replace(a, b):
        calls.append(1)
        if len(calls) < 3:
            raise OSError(22, "synthetic transient metadata error")
        real(a, b)
    monkeypatch.setattr(module.os, "replace", replace)
    monkeypatch.setattr(module.time, "sleep", lambda *a: None)
    path = tmp_path / "record.json"
    module.atomic_save(path, {"count": 1})
    assert json.loads(path.read_text()) == {"count": 1} and len(calls) == 3
    assert list(tmp_path.glob(".r3-write-*")) == []


def test_persistent_io_failure_is_bounded_and_retains_previous_receipt(tmp_path, monkeypatch):
    path = tmp_path / "record.json"
    path.write_text("original")
    calls = []
    def fail(*args):
        calls.append(1)
        raise OSError(22, "synthetic persistent error")
    monkeypatch.setattr(module.os, "replace", fail)
    monkeypatch.setattr(module.time, "sleep", lambda *a: None)
    with pytest.raises(OSError):
        module.atomic_save(path, {"count": 1})
    assert path.read_text() == "original" and len(calls) == 10
    assert list(tmp_path.glob(".r3-write-*")) == []


def fixture():
    return {"status": "failed", "counts": {"inputs": 468, "generator_levels": 5604, "decoder": 5604,
        "encoder": 0, "latent_parity": 467, "independent_prefix": 467},
        "completed_inputs": 499, "new_completed_inputs": 467}


def test_only_one_reserved_but_unexecuted_input_is_resumable_under_amendment_1():
    module.check_resume_counts(fixture(), [{}] * 499, [{}] * 467)


@pytest.mark.parametrize("field", ["inputs", "generator_levels", "decoder", "latent_parity", "independent_prefix", "encoder"])
def test_partial_or_repeated_model_work_cannot_be_silently_resumed(field):
    record = fixture()
    record["counts"][field] += 1
    with pytest.raises(ValueError):
        module.check_resume_counts(record, [{}] * 499, [{}] * 467)
