"""Run the fixed R1B pilot, or verify its saved evidence without model imports."""

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from anytime_ncm.target_diagnostic import DEFAULT_OUTPUT, collect_pilot, verify_pilot


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    method = verify_pilot if args.verify else collect_pilot
    analysis = method(ROOT, ROOT / args.output)
    print("R1B:", "verified" if args.verify else "complete")
    print("Outcome:", analysis["outcome"])
    for name, path in analysis["paths"].items():
        print(name, "early valid", path["early_valid_inputs"], "final valid", path["levels"][-1]["valid_count"])


if __name__ == "__main__":
    main()
