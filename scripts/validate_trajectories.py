"""Validate saved trajectories without loading models or requiring CUDA."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from anytime_ncm.cli import main

if __name__ == "__main__":
    raise SystemExit(main(["validate-trajectories", *sys.argv[1:]]))
