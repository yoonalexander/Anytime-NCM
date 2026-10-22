"""Run a single frozen R3 stage or verify the completed saved-data report."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("baseline", "collect", "profile", "analyze", "verify"))
    args = parser.parse_args()
    if args.stage in ("analyze", "verify"):
        from anytime_ncm.audit import analyze, verify
        result = analyze(ROOT) if args.stage == "analyze" else verify(ROOT)
        print("R3 easy: " + result["decision"])
        print("Development estimated reduction: " + str(result["profile_costs"]["development"]["paired"]))
    else:
        from anytime_ncm.audit_inference import baseline, collect, profile
        {"baseline": baseline, "collect": collect, "profile": profile}[args.stage](ROOT)


if __name__ == "__main__":
    main()
