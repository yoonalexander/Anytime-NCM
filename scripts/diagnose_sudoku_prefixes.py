"""Diagnose saved exploration trajectories, or verify an existing R1A report."""

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from anytime_ncm.diagnosis import run_diagnosis


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="results/followup/sudoku_prefix_diagnosis")
    parser.add_argument("--verify", action="store_true", help="Recompute results and check hashes without inference or figure rendering.")
    args = parser.parse_args()
    analysis = run_diagnosis(ROOT, ROOT / args.output, verify=args.verify)
    print("R1A:", "verified" if args.verify else "complete")
    print("Exploration primary counts:", analysis["reconfirmed_primary_counts"]["valid_solution_count_by_level"])
    print("Access:", analysis["access"])


if __name__ == "__main__":
    main()
