# Anytime NCM

**Can a frozen Next-Concept Modeling checkpoint choose a stopping level per input and improve quality versus actual latency?**

Anytime NCM is a reproducible research repository studying that question through hard/easy Sudoku audits, a bounded medium-Sudoku screen, actual online verified/learned stopping, and WMT14 German-to-English evaluation.

**Status: the original Phase 5 scope and stronger-research saved-data cycle are complete within their evidence gates; practical adaptive speedup has not been demonstrated.** The new WMT audit finds point-feasible mixed exits, but practical headroom is inconclusive. S3 is blocked; S2B/S4 are deferred. The fresh full suite passed **451 tests**. A compiled internal manuscript is prepared; human authorship, rights and scientific review remain unresolved.

[Research synthesis v3](RESEARCH_SYNTHESIS.md) · [Compiled manuscript](paper/stronger-research-v3/main.pdf) · [Historical report v2](RESEARCH_PAPER.md) · [Results and project status](#results-and-project-status) · [Portable viewer](results/phase5/viewer.html) · [Full roadmap](ROADMAP.md) · [Stronger research roadmap](RESEARCH_ROADMAP.md) · [Agent instructions](AGENTS.md)

The repository now provides validated full-resolution prefix reconstruction, controlled trajectory data, an actual generation-stopping hook, frozen policy comparisons, reports and an inspection interface. Current-validity controllers were tested; a true continuation-value model, XSum, and a live CF-driven stopping/intervention policy remain untested.

[Evidence-gap resolution plan](docs/studies/evidence-gap-resolution-plan.md): proposed timing, fresh diagnostic and conditional policy-confirmation studies with numeric ceilings and stopping gates. Planning only; no new experiments have begun.

## Contents

- [Research approach](#research-approach)
- [Implementation status](#implementation-status)
- [Results and project status](#results-and-project-status)
- [Remaining research questions](#remaining-research-questions)
- [Recorded baseline results](#recorded-baseline-results)
- [Documentation](#documentation)
- [Validated environment](#validated-environment)
- [Clone the repository](#clone-the-repository)
- [Use the existing local environment](#use-the-existing-local-environment)
- [Set up a new Windows machine with WSL2](#set-up-a-new-windows-machine-with-wsl2)
- [Run the official baselines](#run-the-official-baselines)
- [Inspect results and provenance](#inspect-results-and-provenance)
- [Partitions and research controls](#partitions-and-research-controls)
- [Repository layout](#repository-layout)
- [Scripts and configurations](#scripts-and-configurations)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)
- [Roadmap and contribution scope](#roadmap-and-contribution-scope)
- [Limitations](#limitations)
- [Upstream and attribution](#upstream-and-attribution)

## Research approach

[Next-Concept Modeling (NCM)](https://github.com/HazyResearch/ncm) generates discrete latent codes from coarse to fine, predicting the positions within each hierarchy level in parallel. A tokenizer decoder reconstructs the output from those codes. This project keeps the released model checkpoint frozen and studies when further refinement is useful.

The completed experiments distinguish two modes:

1. **Offline audit:** run every generator level, reconstruct full-resolution outputs after each cumulative prefix, and measure early-exit opportunities. This mode saves no generator work.
2. **Online stopping:** introduce a minimal hook that actually prevents later generator evaluations. Phase 2 was explicitly requested despite the unmet offline opportunity gate, under a separate entry-exception protocol. Measure the total cost of generation, reconstruction, decoding, transfers, verification, and the stopping policy.

The hard-Sudoku checkpoint has 12 levels with per-level code lengths `1, 2, 4, 6, 9, 13, 18, 26, 37, 50, 67, 89`, totaling 322 generated code positions. The last level's length of 89 is not the total hierarchy size.

The tested Sudoku trajectories offer no early exact solutions, and the selected WMT policies reach full depth. Measured monitoring/controller overhead is not recovered by skipped work in the final comparisons. These are bounded negative results; they do not rule out every checkpoint, stopping signal or adaptive-inference objective.

## Implementation status

| Component | Status |
| --- | --- |
| Repository/package structure, collection and verification CLI | Available |
| Official upstream source submodule | Pinned; unmodified |
| WSL2/CUDA environment and dependency lock | Validated on the recorded machine |
| Narrow Sudoku downloads and artifact hashes | Complete locally; large files excluded from Git |
| Input-identity partitions and experiment protocol | Frozen before baseline inference |
| Official 32-input and 2,000-input baselines | Completed; evidence included |
| Independent Sudoku parser/validator | Implemented; [Phase 1A contract](docs/phase1a_validation.md) |
| Upstream adapter and full-resolution partial decoder | Implemented; [Phase 1B contract and parity](docs/phase1b_partial_decoding.md) |
| Offline trajectory collectors | Hard/easy Sudoku and WMT audits complete; viewer covers 2,992 recorded trajectories /35,712 levels; [scope](docs/phase5_scope.md) |
| Diagnostic profiling, plots, and Phase 1 decision report | Complete; [Phase 1D measurements and limits](docs/phase1d_profiling.md) |
| Online request benchmarks | Complete; five frozen methods, 300 inputs × three repeats; practical speedup no-go |
| Online stopping hook | Complete; true skipped-work and parity checks; upstream remains unmodified |
| Current-validity controller | Complete; six logistic fits, causal ablation, development selection and 6,300-request final comparison; measured no-go; not a continuation-value model |
| Executable research tests | Latest fresh full suite: 451 passed; [JUnit](results/stronger_research/s5a/tests.xml) |
| WMT14 translation | Complete; four-method frozen final comparison; [report](results/phase4/wmt14/summary.md) |
| Recorded-trajectory viewer | Complete; source, levels, issues, exits, costs and provenance; [viewer](results/phase5/viewer.html) |
| Concept Firewall bridge | Exact matching saved forecasts only; [contract](docs/phase5_firewall_contract.md); no live joint policy or safety claim |
| Continuation-value model / XSum / live CF stopping | Not tested; require separately scoped research |

The `anytime-ncm` package CLI offers status, offline `collect`, and `validate-trajectories`. Wrapper scripts below work without an editable installation. Official baseline execution remains separate. The bounded online/task studies use scripts/run_phase2.py, scripts/run_phase3.py and scripts/run_phase4.py; scripts/view_trajectories.py builds/verifies/serves recorded evidence. Their completed model-work allocations must not be silently rerun.


## Results and project status

| Final study / primary method | Full mean ms | Primary mean ms | Slower than full / paired 95% interval | Recorded quality |
| --- | ---: | ---: | --- | --- |
| [Phase 2 · selected verifier](results/phase2/analysis.json) | 100.98 | 101.84 | 0.85% [0.39%, 1.34%] | 299/300 solved by every method |
| [Phase 3 · learned internal](results/phase3/analysis.json) | 98.85 | 101.80 | 2.98% [2.54%, 3.44%] | 299/300 solved by every method |
| [Phase 4 · guarded stability](results/phase4/wmt14/analysis.json) | 134.91 | 137.53 | 1.95% [1.40%, 2.49%] | Identical outputs; 22.687 BLEU /50.105 chrF |

Every final method in these comparisons reaches full depth, with zero early requests. These within-study comparisons have different subsets/runs; absolute times are not a cross-phase optimization trend. All primary practical-speedup and adaptive-frontier gates fail. Reported intervals are paired identity-bootstrap intervals under the recorded process, not universal hardware/population guarantees.

Earlier hard-Sudoku and extended easy-Sudoku audits each cover 1,400 exploration/development trajectories with zero early valid outputs. R1B's 32 target encodings also yield no early valid solution, while final target reconstructions round-trip exactly. Diagnostic component-sum cost estimates are separate from the actual online measurements above. [Consolidated methods and results](RESEARCH_PAPER.md).

**What is finished:** the declared audits, follow-up screens, finite online experiments, current-validity learning, WMT study, viewer and saved-forecast bridge. **What remains unachieved:** the intended useful per-input quality–latency advantage. Phase 0's 86.25% versus published 86.1% hard-Sudoku discrepancy also remains unresolved.

The [viewer](results/phase5/viewer.html) makes the saved evidence inspectable. Its CF bridge retains 3,468 exact matching states across 289 hard-Sudoku puzzles; it generates no new forecasts and changes no stopping decisions.

## Remaining research questions

A fitted estimate of expected benefit from further refinement is still absent. Phase 3 predicts current Sudoku validity; CF forecasts eventual failure. Neither is automatically a continuation value. XSum and live risk-driven stopping/interventions were not evaluated.

The stronger-research saved WMT audit is complete: the found development assignment exits early on 18/64 inputs and meets point corpus tolerances, but conditional quality lower bounds fail noninferiority and actual early-exit latency remains unmeasured. Practical headroom is inconclusive. Saved diagnosis finds early visible final-text matches on 13/64 development inputs. See the [current synthesis](RESEARCH_SYNTHESIS.md); these are reused diagnostic data, not fresh confirmation.

Only if meaningful headroom exists would a separately frozen continuation-value experiment be justified, with a resource budget and suitable fresh evaluation data. Changing the base checkpoint/training objective would be a new research scope. This cycle is closed at its recorded gates; further experiments require a separately justified protocol and budget.

## Recorded baseline results

These results came from the unchanged official evaluator, the released hard-Sudoku checkpoint, one GPU, batch size 128, and deterministic greedy sampling:

| Official run | Solved | Solve rate | Cell accuracy | Valid-grid rate |
| --- | --- | --- | --- | --- |
| Smoke | 24 / 32 | 75.00% | 97.26% | 75.00% |
| Full hard Sudoku | 1,725 / 2,000 | 86.25% | 98.36% | 86.25% |

Both runs exited successfully without an upstream patch, checkpoint conversion, OOM retry, or batch-size override. Sampling remained temperature `0.0`, top-k `0`, top-p `1.0`, and guidance scale `0.0`. The wrapper sets OMP/MKL CPU threads to four and disables tokenizer parallelism.

The [paper, Table 3](https://arxiv.org/html/2610.14162v1#S4.SS4) reports 86.1% on hard Sudoku. This run is **0.15 percentage points higher**, and the cause has not been established. Exact paper-number or per-input prediction parity is not claimed.

These are upstream reference-based solved/cell/valid-grid metrics. An independent complete-valid-clue-consistent checker is now available; these recorded baseline metrics still come from the official scorer and have not been rescored with that checker. Whole evaluator-process durations include loading and scoring; they are not warm inference latency or adaptive speedup measurements.

Evidence: [full metrics](results/upstream_full/metrics.json), [smoke metrics](results/upstream_smoke/metrics.json), [full evaluator log](results/upstream_full/evaluate.log), and [reproduction log](docs/reproduction_log.md).

## Documentation

| Document | Purpose |
| --- | --- |
| [ROADMAP.md](ROADMAP.md) | Phase 0–5 execution checklist, milestones, acceptance criteria, and decision gates |
| [Current synthesis and manuscript](RESEARCH_SYNTHESIS.md) | Stronger-research S1/S2A findings, evidence-gated branch decisions, compiled local candidate and remaining issues |
| [Historical report, draft v2](RESEARCH_PAPER.md) | Preserved Phase 1–5 methods/results and evidence boundaries |
| [Revised next steps](NEXT_STEPS.md) | Completed follow-ups/studies and the recorded stopping point; new research requires a separate scope |
| [R1A error diagnosis](results/followup/sudoku_prefix_diagnosis/summary.md) | Exploration-only reference/clue/unit error distributions and adjacent-level changes |
| [R1B target encoding](results/followup/sudoku_target_encoding/summary.md) | Frozen 32-reference reconstruction pilot versus cached generated prefixes |
| [R2 checkpoint screens](results/followup/sudoku_checkpoint_screen/summary.md) | Completed bounded easy/medium screens, shared-reference reservations, and negative exit |
| [R3 easy extension](results/followup/sudoku_easy_r3/summary.md) | Explicitly requested extension after negative R2; 1,400-input audit, estimated costs, and new no-go |
| [Phase 2 online report](results/phase2/summary.md) | Actual online stopping, development selection, frozen final comparison and measured no-go |
| [Phase 3 learned report](results/phase3/summary.md) | Current-validity controllers, internal-feature ablation, final costs and no-go |
| [Phase 4 WMT report](results/phase4/wmt14/summary.md) | Full-resolution translation audit, task-specific quality margins and final no-go |
| [Phase 5 inspection report](results/phase5/summary.md) | Portable viewer, saved CF correspondence checks and unavailable-value limits |
| [Design document](Anytime_NCM_Design_Document.md) | Technical design and scientific requirements |
| [DESIGN.md](DESIGN.md) | Entry point to the original design document |
| [Experiment protocol](docs/experiment_protocol.md) | Frozen partitions, budgets, metrics, timing boundaries, and statistical procedure |
| [Reproduction log](docs/reproduction_log.md) | Actual setup commands, hardware/software, results, errors, and access disclosures |
| [Known limitations](docs/known_limitations.md) | Current implementation and evidence boundaries |
| [Phase 1C collection](docs/phase1c_collection.md) | Tested collection/validation commands, schema, access controls, provenance, and artifacts |
| [Phase 1 report](results/phase1/summary.md) | Quality curves, repeated cost profiles, uncertainty, fixed depths, and no-go decision |
| [Phase 1D profiling](docs/phase1d_profiling.md) | Reproduction commands, diagnostic boundaries, budget, and limitations |
| [Setup summary](results/setup/summary.md) | Compact operational results |

The [research paper](RESEARCH_PAPER.md) consolidates saved findings through Phase 5. The design records the original research aims; the roadmap records delivered scope and entry exceptions, including negative outcomes. [Documentation-revision provenance](docs/research_paper_update_2026-10-23.json) identifies this narrative update. Historical empirical artifacts, protocols and milestone completion records remain unchanged.

## Validated environment

| Item | Recorded value |
| --- | --- |
| Host | Windows 11 Pro |
| Linux runtime | WSL2, distribution `Ubuntu-24.04`; Ubuntu 24.04.5 LTS |
| Research user | `ncm` |
| Python | 3.12.3 |
| Virtual environment | `/home/ncm/.venvs/anytime-ncm` |
| GPU | NVIDIA GeForce RTX 5060, 8,151 MiB VRAM |
| NVIDIA driver | 610.88 |
| PyTorch | `2.10.0+cu128` |
| Wheel CUDA runtime | 12.8 |
| Inference | Default float32; no compilation/autocast override |

An actual CUDA matrix operation and both official model runs passed. The driver-reported maximum CUDA compatibility version is separate from the runtime shipped with the Torch wheel.

[requirements.lock](requirements.lock) records exact installed dependencies for **Linux x86_64 / Python 3.12** and includes the official CUDA wheel index. It is not a native Windows dependency lock. The host's Python 3.14 was used for scaffold/metadata tasks, not validated model inference.

Model/dataset payloads total approximately 163 MB; the CUDA/Python environment requires substantially more storage. The recorded 8 GB GPU configuration succeeded, but this is not a measured minimum-VRAM guarantee.

## Clone the repository

```powershell
git clone --recurse-submodules https://github.com/yoonalexander/Anytime-NCM.git
cd Anytime-NCM
```

For an existing clone without the upstream checkout:

```powershell
git submodule update --init third_party/ncm
```

The Git submodule entry pins the upstream revision. Do not replace it with the latest upstream branch during a reproduction run without recording the change. [configs/setup_sources.json](configs/setup_sources.json) also records the upstream, checkpoint, and dataset pins.

## Use the existing local environment

On the original machine, the WSL distribution, `ncm` user, environment, and downloads already exist. From the repository root in PowerShell:

```powershell
.\scripts\wsl_python.ps1 --version
.\scripts\wsl_python.ps1 -m pip check
```

The helper derives this repository's mounted Linux path and invokes `/home/ncm/.venvs/anytime-ncm/bin/python` as `ncm` in `Ubuntu-24.04`. It does not install packages into host Python.

For an interactive Linux session:

```powershell
wsl --distribution Ubuntu-24.04 --user ncm
```

```bash
# Use your clone's actual mounted path.
cd /mnt/c/Users/Admin/Documents/Projects/Anytime-NCM
source /home/ncm/.venvs/anytime-ncm/bin/activate
python -m pip check
PYTHONPATH=src python -m anytime_ncm status
```

## Set up a new Windows machine with WSL2

Use a CUDA-capable NVIDIA GPU and compatible Windows driver. The checked path is Ubuntu WSL2 with Python 3.12; other configurations need their own validation. The official evaluator uses CUDA directly.

### 1. Check Windows GPU access and install Ubuntu

```powershell
nvidia-smi
wsl --status
wsl --list --verbose
wsl --install --distribution Ubuntu-24.04 --no-launch
```

If Ubuntu is already installed, skip its installation command. If Windows requests a restart while enabling WSL, complete that before continuing.

### 2. Provision the dedicated environment

From the clone root in PowerShell:

```powershell
$projectPath = (Get-Location).Path
wsl --distribution Ubuntu-24.04 --user root --cd $projectPath --exec bash scripts/setup_wsl.sh
```

The script installs Ubuntu Git, CA certificates, and Python venv support; creates the dedicated `ncm` user if absent; and prepares the environment on Linux storage. It uses root for provisioning and the non-root user for Python packages and inference. It does not change Docker's default distribution.

The helper/setup scripts assume distribution `Ubuntu-24.04`, user `ncm`, and environment `/home/ncm/.venvs/anytime-ncm`. Adapt those scripts explicitly if you choose different names.

### 3. Install the recorded dependencies

```powershell
.\scripts\wsl_python.ps1 -m pip install -r requirements.lock
.\scripts\wsl_python.ps1 -m pip check
```

The original dependency-resolution procedure is preserved in `scripts/install_dependencies.sh` and [requirements.constraints.txt](requirements.constraints.txt). For reproduction, use the recorded lock rather than resolving newer versions. Regenerating the lock is a maintainer operation after validating the local environment and baseline runs.

### 4. Download only the pinned Sudoku artifacts

```powershell
$projectPath = (Get-Location).Path
wsl --distribution Ubuntu-24.04 --user ncm --cd $projectPath --exec bash scripts/download_sudoku.sh
```

Expected local files:

```text
artifacts/sudoku/hard/config.yaml
artifacts/sudoku/hard/tokenizer.pt
artifacts/sudoku/hard/generator.pt
data/sudoku/hard/puzzles.pickle
data/sudoku/hard/solutions.pickle
```

The download script uses explicit Hugging Face revision IDs and the `sudoku/hard/*` filter. Weights, datasets, and caches are excluded from Git. No paid/cloud GPU service was used for the recorded setup.

### 5. Verify CUDA, record artifacts, and verify partitions

```powershell
wsl --distribution Ubuntu-24.04 --user ncm --exec /usr/lib/wsl/lib/nvidia-smi
.\scripts\wsl_python.ps1 scripts/record_setup.py
.\scripts\wsl_python.ps1 scripts/prepare_sudoku_partitions.py
```

`record_setup.py` executes a CUDA matrix operation and records the current machine and local artifact checksums under `results/setup/`. Those files initially describe the original machine; regenerating them records your environment and may modify the checkout. Compare downloaded sizes/hashes with the recorded artifact manifest before replacing the original evidence if you need that comparison.

The partition script reads only input puzzles, keeps duplicate identities together, and refuses to replace an existing manifest with different content. It preserves the original split when the pinned input data and algorithm match.

## Run the official baselines

The commands in this section document inference reproduction in a fresh allocation. The recorded studies' model-work budgets are consumed; use saved-data verification below for ordinary checks and obtain a new research scope before rerunning experiments.

From the repository root in PowerShell:

```powershell
.\scripts\wsl_python.ps1 scripts/run_upstream_baseline.py --n 32 --output results/reproduction_smoke
.\scripts\wsl_python.ps1 scripts/run_upstream_baseline.py --n 2000 --output results/reproduction_full
```

The checked-in evidence is under `results/upstream_smoke/` and `results/upstream_full/`, so these examples use new directories. The wrapper refuses any nonempty output directory. Choose a new path for every subsequent run.

The wrapper accepts `--n 32` or `--n 2000`, an output directory beneath `results/`, and an optional positive `--batch-size` override. Its default is the official batch size of 128. If hardware requires an override, record it and distinguish those results from the original configuration.

Equivalent commands in the activated WSL environment:

```bash
python scripts/run_upstream_baseline.py --n 32 --output results/reproduction_smoke
python scripts/run_upstream_baseline.py --n 2000 --output results/reproduction_full
```

Each invocation calls the official `third_party/ncm/evaluate.py` in its expected working directory. It preserves the released generation settings and saves the command, source pins, config hash, partition/protocol hashes, CPU-thread settings, exit status, and evaluator-process duration.

## Inspect results and provenance

Each successful baseline directory contains:

| File | Contents |
| --- | --- |
| `evaluate.log` | Official merged/scored output |
| `shard_0.log` | Model-loading and generation progress/errors |
| `run.json` | Commands, source/config/protocol/partition identifiers, settings, timestamps, and process status |
| `shard_0.pkl` | Local raw predictions/references; ignored by Git |

The original setup also includes `metrics.json` files extracted from the logs; the runner itself does not generate these summaries for new runs. Consult `evaluate.log` for a rerun's scores.

Original provenance: [environment](results/setup/environment.json), [artifact hashes](results/setup/artifacts.json), [source pins](configs/setup_sources.json), [full run](results/upstream_full/run.json), and [setup summary](results/setup/summary.json).

A whole evaluator-process duration includes model loading and reference scoring. Future headline inference measurements require the separate timing methodology in the protocol. No timing in the existing setup establishes adaptive compute savings.

## Partitions and research controls

The [frozen manifest](docs/partitions/sudoku-hard.json) groups puzzles by input-token identity:

| Partition | Puzzles | Intended use |
| --- | --- | --- |
| Exploration/training | 1,000 | Correctness development, trajectory exploration, later controller fitting |
| Development | 400 | Policy/threshold selection and the offline decision gate |
| `phase2_final` | 300 | Frozen online verified-stopping comparison |
| `phase3_final` | 300 | Separate learned-policy final comparison |

All 32 smoke inputs belong to exploration. The split seed is `20261020`; the [manifest digest](docs/partitions/sudoku-hard.sha256) identifies the exact assignment.

The official descriptive full-set baseline necessarily scored all examples internally. Only aggregate scores and execution logs were inspected; individual holdout predictions/references were not used to select a policy. This access is disclosed in the reproduction log. The Phase 2/3 online final allocations have since been evaluated after their respective released locks, and WMT's assigned final subset is also consumed. Any additional study must disclose that history and use suitable fresh evaluation data.

The predeclared offline gate requires an estimated reduction of at least 5% in mean total latency, a paired 95% interval with lower bound above zero, no empirical solve-rate loss for verified stopping, and zero false verifier accepts. Missing cost estimates can produce an inconclusive result. The full [protocol](docs/experiment_protocol.md) defines no-go conditions, budgets, monitoring costs, and statistics.

The collector now enforces manifest-selected exploration/development access through a selective token-row reader. It skips sealed rows without materializing their tokens, validates selected identities, and requires validated smoke evidence before expansion. Current/past feature inputs are separate from offline reference diagnostics. Online policy/controller isolation was subsequently implemented and tested in Phases 2/3; the original [Phase 1C access details](docs/phase1c_collection.md) retain their historical scope.

## Repository layout

```text
Anytime-NCM/
|-- README.md
|-- ROADMAP.md
|-- DESIGN.md
|-- Anytime_NCM_Design_Document.md
|-- pyproject.toml
|-- requirements.lock
|-- requirements.constraints.txt
|-- configs/                  # Research templates and pinned setup sources
|-- third_party/ncm/          # Official Git submodule
|-- scripts/                 # Executable setup/reproduction helpers
|-- src/anytime_ncm/          # Validators, decoders, online policies, studies, viewer
|-- tests/                   # Validator, prefix, causality, timing, policy and viewer tests
|-- docs/                    # Protocol, partitions, log, limitations
|-- data/                    # Ignored local datasets
|-- artifacts/               # Ignored local model files
`-- results/                 # Metadata/logs/summaries; raw pickles ignored
```

The original design file remains authoritative. `DESIGN.md` is a navigation entry point, not a second copy of the design.

## Scripts and configurations

| Script | Purpose |
| --- | --- |
| `scripts/setup_wsl.sh` | Provision Ubuntu packages, dedicated user, and isolated environment |
| `scripts/install_dependencies.sh` | Preserve the original dependency-resolution procedure |
| `scripts/download_sudoku.sh` | Download pinned hard-Sudoku model/data files only |
| `scripts/wsl_python.ps1` | Invoke the research interpreter from PowerShell |
| `scripts/record_setup.py` | Validate CUDA and record machine/artifact metadata |
| `scripts/prepare_sudoku_partitions.py` | Generate/verify the frozen input-identity partition manifest |
| `scripts/run_upstream_baseline.py` | Run the official smoke/full evaluator with recorded metadata |
| `scripts/verify_phase1b.py` | Verify exploration-only full-resolution prefixes and exact final-output parity against a fresh official smoke run |
| `scripts/collect_trajectories.py` | Collect permitted offline trajectories from validated smoke/full configs |
| `scripts/validate_trajectories.py` | Recheck saved trajectories and provenance without models/CUDA |
| `scripts/profile_phase1.py` | Execute only the frozen 200-input / five-repeat diagnostic budget |
| `scripts/report_phase1.py` | Generate tables, plots, paired bootstrap statistics, and the offline gate |
| `scripts/verify_phase1d.py` | Read-only audit of current Phase 1 evidence and no-go calculation; explicit flag records a fresh review |
| `scripts/lock_environment.py` | Generate the initial dependency lock after recorded canonical baseline runs |

`configs/setup_sources.json` records actual setup pins. `configs/sudoku_smoke.yaml` and `configs/sudoku_full.yaml` now drive the strict Phase 1C collector schema. Full collection means the 1,000 exploration plus 400 development inputs; both sealed holdouts are excluded. `configs/stopping_policies.yaml` remains a proposed template. The official baseline wrapper uses `third_party/ncm/config/eval/sudoku-hard.yaml` directly.

## Verification

The fresh S5A full suite passed 451 tests ([new JUnit](results/stronger_research/s5a/tests.xml)); the Phase 5 snapshot retains its historical 433-test record. Historical milestone counts describe their own source versions. A read-only rerun without overwriting any frozen JUnit artifacts is:

~~~powershell
.\scripts\wsl_python.ps1 -PythonArguments @('-m','pytest','tests','-q','-p','no:cacheprovider')
~~~

To verify saved results without NCM checkpoint inference:

~~~powershell
python scripts/validate_trajectories.py --metadata results/phase1/trajectories.metadata.json
python scripts/verify_phase1d.py
.\scripts\wsl_python.ps1 -PythonArguments @('scripts/run_phase2.py','verify')
.\scripts\wsl_python.ps1 -PythonArguments @('scripts/run_phase3.py','verify')
.\scripts\wsl_python.ps1 -PythonArguments @('scripts/run_phase4.py','verify')
python scripts/view_trajectories.py verify
~~~

Pinned local inputs are needed for scientific integrity checks; viewing the committed HTML needs no model weights or ML environment. These commands verify saved data, not a new online reproduction. Existing inference/test outputs and stage budgets must be preserved. Historical completion receipts retain hashes for their original commit; later documentation changes are recorded separately, with the current compatibility review archived/refreshed.

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| `nvidia-smi` missing inside noninteractive WSL | Use `/usr/lib/wsl/lib/nvidia-smi`; this path worked in the recorded setup |
| CUDA unavailable after installation | Check GPU passthrough, the installed Torch build/runtime, and the official CUDA wheel index; do not substitute a CPU baseline |
| Checkpoints/data not found | Confirm the `sudoku/hard/` paths, pinned revision IDs, and completed narrow downloads |
| Hugging Face cannot chmod cache files on the Windows mount | This warning occurred locally without preventing download/loading; verify completion and recorded checksums |
| Baseline returns nonzero | Read `evaluate.log` and `shard_0.log` and preserve the failed run directory |
| Out of GPU memory | Check available VRAM and record any supported batch-size override in a fresh run |
| Output directory already exists | Pick a new empty `results/` path |
| PowerShell helper uses the wrong distro/user/environment | Check its explicit defaults against the provisioning script |
| Scores differ from the recorded baseline or paper | Record hardware/software/config/artifact differences; do not tune on final holdouts to force a matching number |

## Roadmap and contribution scope

[ROADMAP.md](ROADMAP.md) retains the full Phase 0–5 plan and milestone history:

1. **Phase 0:** operational setup/reproduction complete; exact hard-Sudoku paper-number discrepancy remains open.
2. **Phase 1 and R1A–R3:** audits/diagnoses/screens complete, with no observed useful early-valid Sudoku opportunity.
3. **Phase 2:** actual online verified stopping complete under an explicit entry exception; measured no-go.
4. **Phase 3:** current-validity controllers and final comparisons complete under an explicit entry exception; measured no-go.
5. **Phase 4:** WMT14 generalization complete; measured no-go. XSum was not included.
6. **Phase 5:** trajectory viewer and saved-evidence CF bridge complete; no joint predictive/latency/safety benefit claim.

Further experimentation needs a new hypothesis, bounded scope, quality/cost criteria and suitable evaluation data. Completing the scoped deliverables does not establish all original research ambitions. Code correctness/parity, an optimistic opportunity bound and a measured practical-speedup claim remain distinct requirements.

## Limitations

- No valid solution appears before the final level in the audited Sudoku trajectories. Selected final WMT methods also execute all levels. Primary measured comparisons fail the practical-speedup/frontier gates.
- Phase 3 learns current correctness, not continuation value. XSum and live CF-driven stopping/intervention remain untested.
- The 86.25% hard-Sudoku official result versus published 86.1% remains unexplained; operational reproduction is not exact paper-number replication.
- Results concern recorded checkpoints, policies, finite allocations and one GPU/WSL pathway. They do not establish that all adaptive NCM methods are ineffective.
- Final allocations are consumed; prior full-baseline aggregate scoring, shared identities and unknown training overlap are disclosed. Reusing those final results cannot establish untouched-test performance.
- Diagnostic estimates, actual online wall latency, CUDA stream elapsed, generated work and batched throughput are different measurements. Intervals are conditional on the recorded sampling/process.
- BLEU/chrF, literal number/negation cues and Sudoku correctness do not establish general factuality or AI safety.
- CF scores are retained producer forecasts on exact matching hard-Sudoku states. No cross-batch bitwise latent/probe parity or new benefit is claimed; unmatched/easy/WMT risk stays unavailable.
- The portable viewer embeds its recorded data; rebuilding/integrity verification needs the original pinned local inputs. Browser checks covered HTTP serving; direct file-URL testing was tool-restricted.

See [known limitations](docs/known_limitations.md) and [the manuscript](RESEARCH_PAPER.md#9-limitations-and-threats-to-validity) for the evidence boundaries.

## Upstream and attribution

Anytime NCM builds on [HazyResearch/ncm](https://github.com/HazyResearch/ncm) and Kumbong et al., [Next-Concept Modeling: Fast, Parallel Coarse-to-Fine Text Generation](https://arxiv.org/abs/2610.14162).

The NCM source remains a separate pinned submodule with its [upstream license](https://github.com/HazyResearch/ncm/blob/c70274273f489abc73832b2b98584a8483b6b203/LICENSE). Checkpoint and dataset provenance is recorded separately in the source/artifact manifests. This repository does not yet contain a separate project license file.

## R1A saved-prefix diagnosis

The [R1A report](results/followup/sudoku_prefix_diagnosis/summary.md) analyzes 1,000 exploration puzzles, 12,000 states, and 11,000 transitions with zero model calls. At level 11, 999 boards violate a supplied clue; at level 12 all preserve clues but 146 remain invalid. R1A completed with 218 passing tests, including 29 tests of its metrics and access guards. The [pre-analysis plan](docs/studies/sudoku-prefix-diagnosis-plan.md) defines counts, denominators, overlaps, and fixed example rules.

Recheck the report without inference or figure rendering:

~~~powershell
python scripts/diagnose_sudoku_prefixes.py --verify
~~~

To reproduce, run the same script in the validated WSL environment without --verify, using a fresh --output directory under results/followup/. [Completion evidence](results/followup/sudoku_prefix_diagnosis/completion.json) records source/artifact hashes, test coverage, and scope. The completed R1B pilot is documented below.

## R1B target-encoded prefixes

The [R1B report](results/followup/sudoku_target_encoding/summary.md) compares 32 reference-encoded targets with their saved generated trajectories. The pilot used exactly 32 encodings, 384 prefix decodes, and 32 declared latent-only parity checks. All target final outputs matched the reference exactly, but neither path produced a valid board before level 12. No generator calls, timing study, or holdout access occurred. R1B completed with 244 passing tests, including 26 new R1B tests.

Recheck without model or plotting imports:

~~~powershell
python scripts/diagnose_target_encoding.py --verify
~~~

The [protocol](docs/studies/sudoku-target-encoding-protocol.md) is separate from the original frozen study. Its inference allocation is consumed; do not rerun encoding to reproduce a report. [Completion evidence](results/followup/sudoku_target_encoding/completion.json) records call counts, parity, state integrity, source hashes, and tests. The subsequent R2 checkpoint screens are documented below.


## R2 bounded checkpoint screens

The [R2 report](results/followup/sudoku_checkpoint_screen/summary.md) records easy then medium screens on 32 exploration inputs per candidate. Neither produced a valid board before level 12. Final validity was 32/32 easy and 31/32 medium; all 64 official/adapter final comparisons matched token IDs/text exactly. No candidate qualified for R3. The released-Sudoku first-valid path is closed at the declared budget; the original Phase 2 no-go remains unchanged.

Each candidate used 32 official comparator plus 32 adapter generations, 768 generator level evaluations, and 416 decoder forwards. No timing profile, warmups, retries, training, or development/final board/reference materialization occurred. Since released difficulties share identical solution files, all original row-index reservations were inherited. Identity-only hashing traversed every candidate puzzle row, including reserved operands, while only rows 0–31 were materialized for inference/scoring. These related difficulty views are not independent datasets.

~~~powershell
python scripts/screen_sudoku_checkpoints.py --verify
~~~

The verifier checks saved records without model or plotting imports; it does not rerun CUDA parity. The inference budget is consumed. [Frozen protocol](docs/studies/sudoku-checkpoint-screen-protocol.md), [pinned release inventory](configs/r2_sources.json), and [completion evidence](results/followup/sudoku_checkpoint_screen/completion.json) document the execution. All 282 tests pass, including 38 new R2 tests. At R2 completion R3 had not started; subsequent R3 and Phase 2 work is documented below. At R2 completion a new task study had not started; the later WMT14 study is documented below.


## R3 easy-Sudoku extension

R3 easy-Sudoku extension is complete with **no-go**: no early valid solution among 1,000 exploration and 400 development inputs. Final primary validity was 994/1,000 and 396/400. Development component-sum estimates were 104.22 ms full depth versus 145.20 ms every-level verified, an estimated 39.31% cost increase (paired 95% interval 38.96%–39.68%). These are not measured online latencies. All 310 tests pass, including 28 new R3/resumption tests.

The user requested this extension after receiving the negative R2 results. Its [separate protocol](docs/studies/sudoku-easy-r3-protocol.md) selects easy by the existing candidate order and preserves the failed R2 entry gate. It reuses the original 32 screen trajectories within the 1,400 total, adds the unchanged official 2,000-input aggregate baseline (1,988 solved), and profiles exactly 100 identities per permitted partition, five repeats each, after ten exploration warmups. At R3 completion both final adaptive-policy partitions remained reserved; the official baseline scored them internally with aggregate-only inspection. Subsequent Phase 2 access is disclosed below. Difficulty views share solution rows and are not independent datasets.

A metadata-write interruption was retained and completed under the [resumption amendment](docs/studies/sudoku-easy-r3-resumption-amendment.md), with no repeated model generation. The total allocation stayed 4,378 new generations and 31,536 decoder forwards. Report-only plot correction uses the same 100 development profiling identities for both methods.

~~~powershell
.\scripts\wsl_python.ps1 -PythonArguments @('scripts/finalize_sudoku_easy_r3.py','--verify')
~~~

This verifies original execution sources, amendment/report-only sources, pre-resumption file prefixes, labels, costs, bootstrap and gates without torch/matplotlib or official raw-prediction access. It does not replay CUDA parity. [Report](results/followup/sudoku_easy_r3/summary.md), [configuration](configs/r3_easy.json), and [completion evidence](results/followup/sudoku_easy_r3/completion.json). At R3 completion Phase 2 and task-change work had not started. Phase 2 is now complete as documented below.


## Phase 2 online experiment

The user explicitly requested finishing Phase 2 after the negative offline audits. Its [separate frozen protocol](docs/studies/phase2-easy-online-protocol.md) preserves those no-go decisions and the 5%/zero-loss claim rule while permitting an online engineering/measurement experiment. Incremental reconstruction and deferred verifier schedules are bounded attempts to reduce monitoring cost; they do not create early valid solutions.

**2A is complete:** an isolated pinned-generation hook, unchanged upstream checkout, actual one/six-level stop checks, 192 real parity requests and 353 passing tests. [Completion](results/phase2/2a_completion.json), [recorded patch](results/phase2/upstream_level_hook.patch.txt). A diff-only newline-marker correction passed git apply --check without repeating model work. 2B and 2C are complete. The frozen policy lock was committed/pushed before per-input Phase 2 final access. At Phase 2 completion Phase 3 final data remained reserved; its subsequent use is disclosed below.

~~~powershell
python scripts/run_phase2.py verify-a
~~~

**2B is complete:** [development results](results/phase2/development_analysis.json), [completion](results/phase2/2b_completion.json), [policy lock](results/phase2/policy_lock.json). All 2,100 timed requests matched offline policy outputs. Level-12-only verification won development latency among the verifier schedules, preserving quality but providing no possible early generation savings. The lock was released at commit 2687a46 before the final comparison. At Phase 2 completion Phase 3 remained reserved; Phase 3 evaluation is now complete.


**2C is complete:** five frozen methods on 300 phase2_final identities × three repeats, plus 50 exploration warmups. Every method produced 299/300 valid solutions, no early exits and zero false early accepts. The primary verifier was 0.85% slower than full depth (paired 95% overhead interval 0.39%–1.34%); every-level verification was 14.91% slower. The selected schedule checks level 12 only and therefore has no possible early-generation savings. No practical speedup or adaptive-frontier claim passes.

[Final report](results/phase2/summary.md), [analysis](results/phase2/analysis.json), [Phase 2 completion](results/phase2/completion.json), [2C completion](results/phase2/2c_completion.json), [policy release](results/phase2/policy_lock_release.json). Recompute the saved-data analysis without model/plotting imports:

~~~powershell
.\scripts\wsl_python.ps1 -PythonArguments @('scripts/run_phase2.py','verify')
~~~

All Phase 2 model-evaluation allocations are consumed. Report verification reuses saved results; do not rerun 2a/2b/2c. The final evaluation has prior aggregate baseline exposure, shared solution identities across difficulty masks, and unknown base-model overlap. Integrity hashing traverses all puzzle identities; inference/scoring materializes only permitted rows. Phase 2 inspected no per-input Phase 3 board, reference or prediction. Phase 3 was subsequently explicitly requested and completed using its assigned subset, as documented below. Task changes remain outside the current work order.

## Phase 3 learned stopping

The user explicitly requested finishing Phase 3 regardless of the failed headroom gate. The [separate frozen protocol](docs/studies/phase3-easy-learned-protocol.md) preserves all earlier no-go results and the zero-loss/5% practical threshold. Six logistic fits use only 1,000 exploration inputs; 400 development inputs select regularization, threshold and inspection minimum. No final split supplies fitting/normalization/selection examples. Base features exclude Sudoku validity flags; the internal ablation adds only current codebook statistics.

3A is complete: both models selected minimum level 10 and threshold 0.5; base C=10 and internal C=0.1. There are zero positive pre-final labels. [Training evidence](results/phase3/training.json), [completion](results/phase3/3a_completion.json). At 3A completion final per-input rows remained reserved. Subsequent 3B/3C completion is documented below.

**3B complete:** 2,100 timed development requests and 70 exploration warmups; all match saved offline codes/outputs and causal scores. Every method solves 98/100 inputs, with zero early exits/invalid early accepts. Full depth averages 98.36 ms versus 100.66 ms for the internal model. The [policy lock](results/phase3/policy_lock.json) and [completion](results/phase3/3b_completion.json) precede final access. A report-only source alignment retains the initial lock; no policies, models or measured execution changed. The lock was committed/pushed as 4bcccc0 and released before final token/output access.


**3C complete:** 6,300 final timed requests plus 70 exploration warmups, with all policies frozen before the 300 phase3_final inputs were opened. All seven methods solve 299/300; none exits early. The primary internal-feature model is 2.98% slower than full depth and 2.73% slower than the strong fixed-depth comparator. Code statistics worsen matched-state Brier prediction error in this bounded ablation; they establish no added predictive-value or speedup benefit. The final report includes calibration, feature/score overhead, all baselines, uncertainty, empty-subgroup disclosure and access history.

[Report](results/phase3/summary.md), [analysis](results/phase3/analysis.json), [3C completion](results/phase3/3c_completion.json), [whole-phase completion](results/phase3/completion.json), [380-test receipt](results/phase3/3c_tests.xml). Both phase-specific final subsets have now been used and cannot be presented as untouched later holdouts. Prior aggregate exposure/shared identities remain disclosed.

~~~powershell
.\scripts\wsl_python.ps1 -PythonArguments @('scripts/run_phase3.py','verify')
~~~

This recomputes saved-data evidence without torch/matplotlib; the pinned local input files are still needed for integrity checks. Phase 3's six CPU fits and all 8,540 new NCM input-generations are complete; do not rerun fitting or inference to recreate the report. The pretrained NCM checkpoint and upstream checkout remain unchanged. The Phase 3 work order ended there; the later user request authorized Phase 4 below. Phase 5 was subsequently requested and is complete below. The hard-baseline 86.25% versus paper 86.1% discrepancy remains unexplained.

## Phase 4 WMT14 study

The user requested completing Phase 4 after Phase 3. [Frozen protocol](docs/studies/phase4-wmt14-protocol.md), [pinned sources](configs/phase4_wmt_sources.json), [group manifest](docs/partitions/wmt14-phase4.json). WMT14 De-En was selected; XSum and Phase 5 are outside this study. The pinned download is 1.143 GB including checkpoints/tokenizer/data; no Qwen language-model weights or paid compute are used.

4A is complete: the verbatim official baseline bodies score 3,003 rows at the predeclared batch-8 override, **21.72 BLEU /49.57 chrF**. All 192 full-resolution trajectories match independent learned-cascade/GroupNorm arithmetic, with 32 exact official/disabled-hook code/token/text parity cases. Quality improves in aggregate but 147/640 development adjacent sentence-chrF transitions deteriorate. Development selects fixed depth 11 and two final-only adaptive fallbacks; no early headroom is claimed. [Audit](results/phase4/wmt14/audit_analysis.json), [completion](results/phase4/wmt14/4a_completion.json). The subsequent 4B and locked 4C comparisons are complete below.

**4B complete:** 768 timed requests +32 exploration warmups, all offline/online prefix/exit/output checks passed. Full depth averages 132.57 ms, guarded stability 135.65 ms; all four methods have identical 19.966 BLEU /48.220 chrF and no early exits. [Development](results/phase4/wmt14/development_analysis.json), [lock](results/phase4/wmt14/policy_lock.json), [completion](results/phase4/wmt14/4b_completion.json). The lock was committed/pushed as 45ec152 and released before final per-input access.

**4C complete:** Four frozen methods evaluated 256 assigned final inputs × three repeats (3,072 timed requests), plus 32 exploration warmups. All methods produce identical outputs at level 11: **22.687 BLEU /50.105 chrF**, with zero early exits. Full depth averages **134.91 ms**; primary guarded stability averages **137.53 ms**, **1.95% slower** (paired 95% overhead interval **1.40%–2.49%**). It is 2.13% slower than the selected fixed comparator. Both practical-speedup and adaptive-frontier gates fail. These selected rules are full-depth fallbacks; this is not a universal impossibility claim about adaptive translation.

[Report and figures](results/phase4/wmt14/summary.md), [analysis](results/phase4/wmt14/analysis.json), [4C completion](results/phase4/wmt14/4c_completion.json), [whole-phase completion](results/phase4/wmt14/completion.json). All 404 tests and saved-data checks pass. Actual Phase 4 work is 7,163 input-generations /78,793 sample-weighted level evaluations /11,035 decodes /zero full encoder forwards, within caps; zero failed model calls/retries, training or paid compute. Prior Sudoku evidence is unchanged. BLEU/chrF and number/negation heuristics do not establish factual correctness.

~~~powershell
.\scripts\wsl_python.ps1 -PythonArguments @('scripts/run_phase4.py','verify')
~~~

Verification uses saved records without model/plotting imports; pinned local assets are required for hashes. The model-work allocation is consumed. To regenerate the report from saved data, run the report stage and then python scripts/finalize_phase4_report.py; original renderer text and narrow reporting clarification are retained. Do not rerun inference. Phase 5 was subsequently requested and is complete below.

## Phase 5: recorded-trajectory viewer and Concept Firewall bridge

[Portable viewer](results/phase5/viewer.html) · [Completion report](results/phase5/summary.md) · [Integration contract](docs/phase5_firewall_contract.md)

The self-contained HTML includes all **2,992 audited exploration/development trajectories and 35,712 levels** from hard Sudoku, easy Sudoku and WMT14. Choose a study/input/method, then inspect levels with the buttons or keyboard-accessible slider. Source, current issues, full-depth output, chosen exit, policy traces, timing repeats, configuration/hardware and source hashes are inspectable. Offline replay, measured request latency and separate cohort cost estimates have distinct labels. Unfitted continuation values and unmeasured request costs remain unavailable.

The saved-evidence CF bridge attaches **3,468 exact matching states across 289 hard-Sudoku puzzles**. It checks checkpoint hashes, explicit canonical identity conversion, cumulative codes and decoded board before copying the producer's two predeclared forecast families. Missing/easy/WMT risk stays unavailable. It predicts eventual Sudoku failure, not safety or continuation benefit; it does not change stopping decisions. CF's original negative primary result is retained.

Open the HTML locally, or serve the committed artifact with standard-library Python:

~~~powershell
python scripts/view_trajectories.py serve
~~~

Then open http://127.0.0.1:8765/. The server binds loopback and serves only the single viewer. The HTML contains its data/styles/scripts and makes no external requests; serving/viewing needs no model weights or ML packages. Python 3.11+ is recommended for the build/verification commands. Browser automation verified the HTTP viewer; direct file-URL navigation is restricted by the browser tool.

~~~powershell
python scripts/view_trajectories.py verify
python scripts/view_trajectories.py build --firewall-root ..\Concept-Firewall
python scripts/view_trajectories.py verify --firewall-root ..\Concept-Firewall
~~~

Rebuilding requires the original saved artifacts and pinned local datasets; the CF checkout is optional for building with unavailable risk, and required for recreating/external rechecking the retained forecasts. The normal verifier checks source/artifact digests, all displayed reconstructions, diagnostics, decisions and timing repeats. The historical Phase 5 suite passed 433 tests, including 29 viewer regressions. Phase 5 adds zero model calls, fits, retuning or final-input materialization. Earlier empirical artifacts and frozen sources remain unchanged.
