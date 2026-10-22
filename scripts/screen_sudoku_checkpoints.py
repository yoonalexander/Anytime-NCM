"""Prepare, execute, report, or verify the bounded R2 checkpoint screen."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from anytime_ncm.screening import prepare_candidate, verify_candidate, verify_screen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", choices=("easy", "medium"))
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare", action="store_true")
    mode.add_argument("--run", action="store_true")
    mode.add_argument("--verify", action="store_true")
    mode.add_argument("--report", action="store_true")
    args = parser.parse_args()
    if args.prepare or args.run:
        parser.error("--candidate is required for preparation/execution") if not args.candidate else None
    if args.prepare:
        prepare_candidate(ROOT, args.candidate)
    elif args.run:
        from anytime_ncm.screening_inference import collect_candidate
        collect_candidate(ROOT, args.candidate)
    elif args.report:
        from anytime_ncm.screening_render import render
        render(ROOT)
    else:
        analyses = [verify_candidate(ROOT, args.candidate)] if args.candidate else verify_screen(ROOT)
        for analysis in analyses:
            print(f'R2 {analysis["candidate"]}: verified; early {len(analysis["early_valid_indices"])}/32; '
                  f'final {analysis["final_valid_count"]}/32; {analysis["decision"]}')


if __name__ == "__main__":
    main()
