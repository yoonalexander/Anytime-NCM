#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
task_python=/home/ncm/.venvs/anytime-ncm/bin/python
"$task_python" -m pip install 'torch==2.10.0' --index-url https://download.pytorch.org/whl/cu128
"$task_python" -m pip install -c requirements.constraints.txt -r third_party/ncm/requirements.txt
"$task_python" -m pip install -c requirements.constraints.txt pandas scipy scikit-learn matplotlib pyarrow pytest pyyaml setuptools wheel
"$task_python" -m pip check
