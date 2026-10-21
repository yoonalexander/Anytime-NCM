"""Scaffold inspection CLI; research commands are reserved for later sections."""

import argparse
from collections.abc import Sequence

from anytime_ncm import __version__


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="anytime-ncm",
        description="Inspect the Anytime NCM repository scaffold.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command")
    commands.add_parser("status", help="Show the current implementation milestone.")
    args = parser.parse_args(argv)
    if args.command == "status":
        print("Anytime NCM research scaffold.")
        print("Setup and baseline evidence: docs/reproduction_log.md")
        print("Research modules remain placeholders; this CLI does not run inference.")
        return 0
    parser.print_help()
    return 0
