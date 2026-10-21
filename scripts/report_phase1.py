"""Generate Phase 1 tables, plots, and the frozen offline decision."""

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from anytime_ncm.collect import output_path
from anytime_ncm.report import build_report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profiles", default="results/phase1/profiles")
    parser.add_argument("--output", default="results/phase1")
    parser.add_argument("--replace-report", action="store_true", help="Rebuild generated report artifacts only; preserve trajectories and profiles.")
    args = parser.parse_args()
    analysis = build_report(ROOT, output_path(ROOT, args.profiles), output_path(ROOT, args.output), replace_report=args.replace_report)
    print("Phase 1 decision:", analysis["decision"])
    print("Report:", args.output + "/summary.md")


if __name__ == "__main__":
    main()
