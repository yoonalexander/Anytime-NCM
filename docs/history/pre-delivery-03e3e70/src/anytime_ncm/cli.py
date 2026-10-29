"""Repository status, offline collection, and trajectory verification CLI."""

import argparse
from collections.abc import Sequence
import json
from pathlib import Path

from anytime_ncm import __version__


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="anytime-ncm", description="Frozen NCM research tools.")
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command")
    commands.add_parser("status", help="Show the current implementation milestone.")
    collector = commands.add_parser("collect", help="Collect offline full-depth exploration/development trajectories.")
    collector.add_argument("--config", type=Path, required=True)
    collector.add_argument("--output-path", help="Fresh JSONL path beneath results/.")
    collector.add_argument("--run-id", help="Override the recorded run identifier.")
    verifier = commands.add_parser("validate-trajectories", help="Recheck JSONL against selected pinned examples.")
    verifier.add_argument("--metadata", type=Path, required=True)
    args = parser.parse_args(argv)
    repository = Path(__file__).resolve().parents[2]
    if args.command == "status":
        print("Anytime NCM: Sudoku validation, full-resolution prefixes, and offline collection implemented.")
        print("Evidence: ROADMAP.md and docs/reproduction_log.md")
        return 0
    if args.command in {"collect", "validate-trajectories"}:
        from anytime_ncm.collect import run_collection, verify_run
        try:
            if args.command == "collect":
                overrides = {key: value for key, value in (
                    ("output_path", args.output_path), ("run_id", args.run_id)) if value is not None}
                report = run_collection(repository, args.config, overrides=overrides)
            else:
                report = verify_run(repository, args.metadata)
        except (ValueError, RuntimeError, OSError) as error:
            parser.exit(1, f"{error}\n")
        print(json.dumps({key: value for key, value in report.items() if key != "source_sha256"}, indent=2, sort_keys=True))
        return 0
    parser.print_help()
    return 0
