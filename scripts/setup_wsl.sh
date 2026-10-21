#!/usr/bin/env bash
# Provision the dedicated WSL research user and its isolated Python environment.
set -euo pipefail
if [ "$(id -u)" -ne 0 ]; then
    printf '%s\n' 'Run this provisioning script as root in Ubuntu-24.04.' >&2
    exit 1
fi
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y python3-venv git ca-certificates
if ! id ncm >/dev/null 2>&1; then
    useradd --create-home --shell /bin/bash ncm
fi
runuser -u ncm -- mkdir -p /home/ncm/.venvs
if [ ! -x /home/ncm/.venvs/anytime-ncm/bin/python ]; then
    runuser -u ncm -- python3 -m venv /home/ncm/.venvs/anytime-ncm
fi
runuser -u ncm -- /home/ncm/.venvs/anytime-ncm/bin/python -m pip install --upgrade pip
