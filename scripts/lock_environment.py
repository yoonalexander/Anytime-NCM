"""Freeze the environment only after both official setup baselines succeed."""

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    for name in ("upstream_smoke", "upstream_full"):
        record = json.loads((ROOT / "results" / name / "run.json").read_text())
        if record["status"] != "complete" or record["exit_code"] != 0:
            raise RuntimeError(f"The {name} baseline has not succeeded.")
    subprocess.run([sys.executable, "-m", "pip", "check"], check=True)
    frozen = subprocess.check_output([sys.executable, "-m", "pip", "freeze", "--all"], text=True)
    header = (
        "# Validated environment: Ubuntu 24.04 / WSL2, Python 3.12, Linux x86_64.\n"
        "# Official 32-input smoke and 2000-input full baselines completed.\n"
        "# CUDA wheels require this additional official package index.\n"
        "--extra-index-url https://download.pytorch.org/whl/cu128\n"
    )
    (ROOT / "requirements.lock").write_text(header + frozen)
    print("Wrote requirements.lock from the baseline-validated environment.")


if __name__ == "__main__":
    main()
