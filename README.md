<h1 align="center">Anytime NCM</h1>
<p align="center"><strong>Can a frozen generator stop early without losing quality?</strong></p>
<p align="center">
  <a href="https://github.com/yoonalexander/Anytime-NCM/releases/tag/research-v0.1.0"><img src="https://img.shields.io/badge/Research_snapshot-0.1.0-315b8a" alt="Research snapshot 0.1.0" /></a>
  <a href="docs/PROJECT_OUTCOME.md"><img src="https://img.shields.io/badge/Studies-closed-687787" alt="Bounded research studies closed" /></a>
  <a href="docs/delivery/INSTALL.md"><img src="https://img.shields.io/badge/Python-3.10%2B-3776ab?logo=python&amp;logoColor=white" alt="Python 3.10 or newer for snapshot inspection" /></a>
  <a href="https://github.com/yoonalexander/Anytime-NCM/actions/workflows/snapshot.yml"><img src="https://github.com/yoonalexander/Anytime-NCM/actions/workflows/snapshot.yml/badge.svg?branch=main" alt="Portable distribution installation checks" /></a>
  <a href="RIGHTS.md"><img src="https://img.shields.io/badge/Rights-see_notice-687787" alt="Rights and third-party notices" /></a>
</p>
<p align="center"><a href="#highlights">Highlights</a> &bull; <a href="#results">Results</a> &bull; <a href="#installation">Installation</a> &bull; <a href="#usage">Usage</a> &bull; <a href="#verification">Verification</a></p>

Anytime NCM studies **adaptive stopping in frozen [Next-Concept Modeling](https://github.com/HazyResearch/ncm)**: reconstruct an answer from the current coarse-to-fine code prefix, decide whether to continue, and measure the entire cost of that decision. The project covers Sudoku and German-to-English translation, with prospective protocols, causal-feature tests, exact reconstruction checks and retained experiment receipts.

> **Final research outcome:** the tested policies did not establish the intended quality-and-latency advantage. The final translation controller saved **5.08% actual mean time**, but its **0.665 corpus BLEU loss exceeded the 0.5 tolerance**. Independent quality confirmation remains blocked and reserved outcomes remain sealed. This is a documented research snapshot, not a released translation service or a claim that every adaptive policy must fail.

<p align="center"><img src="docs/assets/architecture.svg" width="98%" alt="Architecture illustration: source enters a frozen NCM, the current prefix is reconstructed and a causal rule stops or continues; references are used only in an offline audit" /></p>
<p align="center"><em>Architecture illustration, not an execution trace. Online features use current/past information; references and future outputs stay in the offline evaluation.</em></p>

## Highlights

### Reconstruct the actual prefix

The adapters use the released learned transformations to reconstruct each full-resolution cumulative prefix. Intermediate and final parity, suffix isolation and unchanged model states are checked. A late exact answer and an early approximate answer are evaluated separately.

### Measure real skipped work

The online hook can stop generation before later levels execute. Ready-output latency includes observation, reconstruction, decoding, transfers, features, scalar decisions and synchronization. Offline full-trajectory replays and component-sum estimates are labeled separately.

### Keep the evidence inspectable

Frozen source locks, role allocations, budgets, per-stage decisions, preserved failures and paired comparisons distinguish engineering correctness from scientific success. The deliverable includes an installable aggregate inspector, a portable historical viewer, [final outcome](docs/PROJECT_OUTCOME.md), [case study](docs/portfolio/CASE_STUDY.md) and [research snapshot release](https://github.com/yoonalexander/Anytime-NCM/releases/tag/research-v0.1.0).

## Results

<p align="center"><img src="docs/assets/results.svg" width="98%" alt="Saved execution evidence: native full averages 134.710 ms and the controller 127.872 ms; BLEU loss exceeds its declared margin while three other corpus points remain within theirs" /></p>

**Final development evaluation:** 1,188 inputs, 60 document/alias components, 315 early exits and 289 numeric-covered references. The selected rule and comparator were pushed before those outcomes. Two separate processes, one timed repeat per input/method/session, 4,772 requests including warmups.

| Endpoint | Observed | Preset requirement | Interpretation |
| --- | ---: | ---: | --- |
| Actual mean ready-output time |127.872 ms vs 134.710 ms full|>=5% mean saving, positive paired lower bound|5.076% saving; timing screen passes|
| Conditional paired saving interval |[3.377%, 6.861%]|Lower bound >0|Conditional on observed sessions and component assumptions|
| Corpus BLEU loss |0.664892|<=0.5|**Point screen fails**|
| Corpus chrF loss |0.994323|<=1.0|Point only; no noninferiority bound|
| Numeric-reference mean F1 loss |0.011534|<=0.02|Point only; reference-defined denominator|
| Negation-mismatch increase |0.003367|<=0.02|Point only; literal cue diagnostic|

The original twelve-method/two-repeat evaluation was interrupted by a reporting failure. Its source, partial evidence and full conservative charge are preserved. A separately frozen controller/full diagnostic completed the measurements above; **fixed depths 1-10 were not timed in that smaller diagnostic**, and the matched-quality fixed-depth frontier is unestablished. The controller's p95 was slightly worse. No independent quality guarantee or semantic correctness guarantee follows. [Full final report and limits](docs/studies/quality-tolerant/campaign-20261029-final-report.md) · [Actual timing evidence](results/quality_tolerant/campaign_20261029/first_timing_diagnostic/analysis.json).

Earlier studies are retained rather than erased:

| Study | Supported finding | Scope |
| --- | --- | --- |
| Sudoku prefix audits and online policies |No early exact solutions in audited settings; monitoring costs did not produce practical adaptive savings|Bounded checkpoint/task studies, not an impossibility theorem|
| E2 exact-final-text diagnostic |43/256 early exact matches; charged every-level assignment 13.41% slower than full|Clairvoyant diagnostic, not a deployed selector|
| Post-E2 terminal-only assembly |2.67% estimated savings, below target|Post hoc assembly of measured cells, not an online benchmark|
| Final quality-tolerant controller |5.08% actual mean saving; BLEU point tolerance missed|Development evidence; confirmation and full frontier unestablished|

[Original Phase 1-5 history](docs/history/pre-delivery-03e3e70/ROADMAP.md) · [E2 report](results/evidence_gaps/e2/summary.md) · [Current roadmap](ROADMAP.md).

## Installation

The base inspector has **zero runtime dependencies** and needs no model, dataset or GPU. Download the wheel from the [GitHub release](https://github.com/yoonalexander/Anytime-NCM/releases/tag/research-v0.1.0), then install it in a clean environment:

```bash
python -m venv .venv
# Linux / macOS
.venv/bin/python -m pip install --no-deps ./anytime_ncm-0.1.0-py3-none-any.whl
.venv/bin/python -m anytime_ncm status
```

```powershell
# Windows
.venv\Scripts\python.exe -m pip install --no-deps .\anytime_ncm-0.1.0-py3-none-any.whl
.venv\Scripts\anytime-ncm.exe status
```

[Installation, source distribution, checksums and research-environment boundaries](docs/delivery/INSTALL.md). No package-registry publication is performed. Models and corpora are not bundled.

## Usage

```bash
python -m anytime_ncm --version
python -m anytime_ncm status --json
```

```python
from anytime_ncm.snapshot import load_snapshot
snapshot = load_snapshot()
print(snapshot["outcome"])
print(snapshot["latest_evaluation"]["quality_point_screen_passed"])  # False
```

For a visual inspection, download `anytime-ncm-legacy-viewer.html` from the release and open it directly. The same artifact is retained at [results/phase5/viewer.html](results/phase5/viewer.html). It covers **2,992 historical trajectories** and matching saved Concept Firewall forecasts; it does not include the later controller campaign or generate new forecasts.

From a clone, serve that existing artifact locally:

```bash
python scripts/view_trajectories.py serve --port 8765
```

Open http://127.0.0.1:8765/. This serves saved HTML only. Historical `collect` and `validate-trajectories` commands require the pinned research checkout/environment; they are not the dependency-free quickstart and this release does not authorize new experiments.

## Verification

Delivery records are separate from immutable research ledgers: [verification inventory](docs/delivery/VERIFICATION.md), [baseline 820-check software record](results/delivery/20261029/baseline-summary.json), and [artifact/compatibility audit](docs/delivery/ARTIFACT_AUDIT.md).

```bash
python scripts/audit_retained_evidence.py
# On the original machine, also verify already-authorized private cache digests:
python scripts/audit_retained_evidence.py --private
```

The research regression suite uses tiny CPU fixtures. Q0's no-model-library checks run in a separate process; the delivery runner blocks raw corpus/weights, GPU and remote networking. Python distribution checks build from the source distribution and install/test both wheel and sdist outside the checkout. The CI matrix exercises portable installation on Windows and Linux.

Current README/package metadata intentionally differs from historical frozen source hashes. [Exact original bytes](docs/history/pre-delivery-03e3e70/manifest.json) are preserved in a binary archive. The new audit resolves only those explicitly archived metadata paths; experimental sources, protocols, artifacts, failed gates and ledgers retain their original hashes. Strict old verifiers apply to their frozen checkout, not to a silently rewritten receipt.

## Repository layout

```text
src/anytime_ncm/       Research adapters, causal policies, validators and snapshot inspector
scripts/              Historical study entry points and read-only delivery verification
configs/              Frozen research configurations and asset manifests
results/              Saved measurements, decisions, source archives and software records
docs/studies/         Prospective protocols and scoped research reports
docs/portfolio/       Case study, website copy and curated assets
docs/assets/          Original architecture art and sourced results figures
paper/                Historical manuscripts and their claim/evidence maps
third_party/ncm/      Pinned, unmodified upstream source (Git submodule)
```

## Acknowledgements and rights

Built around [HazyResearch NCM](https://github.com/HazyResearch/ncm), pinned at `c70274273f489abc73832b2b98584a8483b6b203`. Upstream's own MIT license and copyright notice remain intact. This repository does not infer a blanket project license from that notice: see [RIGHTS.md](RIGHTS.md) and [NOTICE.md](NOTICE.md).

Substantial AI assistance is disclosed. Same-assistant checks are not independent human scientific review. Historical manuscript drafts retain their authorship, rights and review limitations; no institutional endorsement or journal publication is claimed.
