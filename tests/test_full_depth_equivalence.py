"""Input isolation for the standalone real-checkpoint parity command.

Real CUDA parity is run explicitly by scripts/verify_phase1b.py, not silently
during the synthetic suite. Its machine-readable evidence is saved separately.
"""

import importlib.util
import hashlib
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/verify_phase1b.py"
spec = importlib.util.spec_from_file_location("phase1b_verification", SCRIPT)
verification = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verification)


def smoke_fixture():
    items = [[11] + [i % 10] * 89 + [11] for i in range(32)]
    manifest = {"partitions": {"exploration": [
        {"index": i, "puzzle_sha256": hashlib.sha256(
            json.dumps(item, separators=(",", ":")).encode()).hexdigest()}
        for i, item in enumerate(items)
    ]}}
    return manifest, items


def test_parity_selects_only_predeclared_smoke_inputs():
    manifest, items = smoke_fixture()

    class GuardedInputs:
        def __getitem__(self, index):
            assert 0 <= index < 32, "Accessed an input outside smoke."
            return items[index]

    assert verification.smoke_inputs(manifest, GuardedInputs()) == items


def test_parity_rejects_smoke_input_outside_exploration():
    manifest, items = smoke_fixture()
    manifest["partitions"]["exploration"].pop()
    with pytest.raises(RuntimeError, match="not in exploration"):
        verification.smoke_inputs(manifest, items)


def test_parity_rejects_changed_input_identity():
    manifest, items = smoke_fixture()
    items[0][1] = 3
    with pytest.raises(RuntimeError, match="identity mismatch"):
        verification.smoke_inputs(manifest, items)
