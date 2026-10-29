# Install and inspect the research snapshot

## What is released

`research-v0.1.0` packages a **closed research snapshot**, not a translation service or a successful adaptive-stopping policy. The Python package has no runtime dependencies for aggregate inspection. Python 3.10+ is supported; clean-install and CI records state the platforms actually checked.

Download the wheel, source distribution, compact research snapshot, historical viewer, verification record and `SHA256SUMS` from the [GitHub release](https://github.com/yoonalexander/Anytime-NCM/releases/tag/research-v0.1.0). No package-registry release is published.

## Clean installation

From a directory outside the checkout, create a virtual environment and install the downloaded wheel:

```bash
python -m venv .venv
# macOS / Linux
.venv/bin/python -m pip install --no-deps ./anytime_ncm-0.1.0-py3-none-any.whl
.venv/bin/python -m anytime_ncm --version
.venv/bin/python -m anytime_ncm status
.venv/bin/python -m anytime_ncm status --json
```

```powershell
# Windows
.venv\Scripts\python.exe -m pip install --no-deps .\anytime_ncm-0.1.0-py3-none-any.whl
.venv\Scripts\anytime-ncm.exe status
.venv\Scripts\python.exe -m anytime_ncm status --json
```

Expected summary: 1,188 development-evaluation inputs, 315 early exits, 5.076% mean time saving, BLEU loss 0.664892 against 0.5 allowed, combined success **not established**. `status --json` includes the exact aggregate values, source links and qualifications. It works offline without Torch, CUDA, checkpoints or corpora.

The installed API example is:

```python
from anytime_ncm.snapshot import load_snapshot
snapshot = load_snapshot()
print(snapshot["outcome"])
print(snapshot["latest_evaluation"])
```

An executable version is retained at `examples/inspect_snapshot.py`.

## Portable historical viewer

Open the downloaded `anytime-ncm-legacy-viewer.html` directly in a browser. It is the retained Phase 1-5 artifact, covering 2,992 recorded trajectories and the saved Concept Firewall matching-state bridge. It makes **no new forecasts** and does not include the later October 29 controller campaign. No installation or model is needed. In a clone, the same artifact is `results/phase5/viewer.html`.

For localhost serving from the repository:

```bash
python scripts/view_trajectories.py serve --port 8765
```

Open http://127.0.0.1:8765/. This command only serves the existing HTML; it does not rebuild the viewer or run inference.

## Full research checkout and saved audits

The wheel includes research modules, but model/data-dependent operations require the original checkout, pinned submodule, authorized local assets and the recorded WSL2 Ubuntu 24.04 / Python 3.12 environment. `requirements.lock` is the historical Linux/CUDA lock, not a portable base dependency list. Do not upgrade that environment to inspect the snapshot.

```bash
git clone --recurse-submodules https://github.com/yoonalexander/Anytime-NCM.git
cd Anytime-NCM
python -m pip install --no-deps .
python -m anytime_ncm status
```

The legacy `validate-trajectories` command supports `--repository PATH` before the subcommand. It verifies existing local trajectory metadata; it needs the pinned research dependencies and selected local data. `collect` is a historical research entry point, not a quickstart. This closeout does not authorize rerunning consumed collection, model experiments or confirmation.

The delivery audit documents preserved historical metadata under `docs/history/pre-delivery-03e3e70/`. Strict historical source-hash verifiers apply to their frozen checkout. Current-tree compatibility checks use archived metadata bytes while requiring unchanged experimental files; original locks and receipts are never overwritten.

## Source distribution

Build or install the downloaded `.tar.gz` in a separate environment with standard Python build tools. The source distribution is the buildable Python/research-inspection subset; the Git repository retains the full research evidence and submodule pointer. Models, corpora, raw arrays, credentials, local caches and environments are excluded from distributions.

No project-wide license is inferred from upstream NCM's MIT license. Read `RIGHTS.md` and `NOTICE.md`.
