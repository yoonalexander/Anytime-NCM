#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
task_hf=/home/ncm/.venvs/anytime-ncm/bin/hf
"$task_hf" download hazyresearch/ncm-checkpoints --revision d342ce8aaea58830eef3b8ad473664673e41f692 --include 'sudoku/hard/*' --local-dir artifacts
"$task_hf" download hazyresearch/ncm-datasets --repo-type dataset --revision 6580ba41a4b0a976dde876fbe84d25327617b0e6 --include 'sudoku/hard/*' --local-dir data
