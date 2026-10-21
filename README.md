# Anytime NCM

**Can a frozen Next-Concept Modeling checkpoint stop at a different hierarchy level for each input and improve the quality-versus-compute frontier?**

Anytime NCM is a research repository for answering that question with reproducible experiments. It starts with hard Sudoku, where a complete solution can be checked directly, and plans later studies on translation and summarization.

**Current stage:** repository setup and official full-depth baseline reproduction are complete. Adaptive stopping has not been implemented or measured. The next milestone is **Phase 1A: Sudoku parsing and correctness** in [ROADMAP.md](ROADMAP.md).

## Contents

- [Research approach](#research-approach)
- [Implementation status](#implementation-status)
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

The proposed experiments have two distinct modes:

1. **Offline audit:** run every generator level, reconstruct full-resolution outputs after each cumulative prefix, and measure early-exit opportunities. This mode saves no generator work.
2. **Online stopping:** after the offline decision gate justifies it, introduce a minimal hook that actually prevents later generator evaluations. Measure the total cost of generation, reconstruction, decoding, transfers, verification, and the stopping policy.

The hard-Sudoku checkpoint has 12 levels with per-level code lengths `1, 2, 4, 6, 9, 13, 18, 26, 37, 50, 67, 89`, totaling 322 generated code positions. The last level's length of 89 is not the total hierarchy size.

Useful intermediate solutions, real latency savings, and a benefit from learning a controller are open questions. Negative and inconclusive results are legitimate research outcomes.

## Implementation status

| Component | Status |
| --- | --- |
| Repository/package structure and inspection CLI | Available |
| Official upstream source submodule | Pinned; unmodified |
| WSL2/CUDA environment and dependency lock | Validated on the recorded machine |
| Narrow Sudoku downloads and artifact hashes | Complete locally; large files excluded from Git |
| Input-identity partitions and experiment protocol | Frozen before baseline inference |
| Official 32-input and 2,000-input baselines | Completed; evidence included |
| Independent Sudoku parser/validator | Planned; placeholder module |
| Correct full-resolution partial decoder and trajectory collector | Planned; placeholder modules |
| Diagnostic profiling and adaptive benchmark/report commands | Planned |
| Online stopping and learned controller | Planned, conditional on research gates |
| Executable research tests | Not implemented; current named test modules are placeholders |
| Translation, summarization, viewer, and Concept Firewall integration | Later or optional phases |

The `anytime-ncm` package CLI currently offers help, version, and scaffold status. Official baseline execution uses the scripts below; the package does not yet expose a trajectory or adaptive-inference command.

## Recorded baseline results

These results came from the unchanged official evaluator, the released hard-Sudoku checkpoint, one GPU, batch size 128, and deterministic greedy sampling:

| Official run | Solved | Solve rate | Cell accuracy | Valid-grid rate |
| --- | --- | --- | --- | --- |
| Smoke | 24 / 32 | 75.00% | 97.26% | 75.00% |
| Full hard Sudoku | 1,725 / 2,000 | 86.25% | 98.36% | 86.25% |

Both runs exited successfully without an upstream patch, checkpoint conversion, OOM retry, or batch-size override. Sampling remained temperature `0.0`, top-k `0`, top-p `1.0`, and guidance scale `0.0`. The wrapper sets OMP/MKL CPU threads to four and disables tokenizer parallelism.

The [paper, Table 3](https://arxiv.org/html/2610.14162v1#S4.SS4) reports 86.1% on hard Sudoku. This run is **0.15 percentage points higher**, and the cause has not been established. Exact paper-number or per-input prediction parity is not claimed.

These are upstream reference-based solved/cell/valid-grid metrics. The project's planned independent complete-valid-clue-consistent metric is not implemented. Whole evaluator-process durations include loading and scoring; they are not warm inference latency or adaptive speedup measurements.

Evidence: [full metrics](results/upstream_full/metrics.json), [smoke metrics](results/upstream_smoke/metrics.json), [full evaluator log](results/upstream_full/evaluate.log), and [reproduction log](docs/reproduction_log.md).

## Documentation

| Document | Purpose |
| --- | --- |
| [ROADMAP.md](ROADMAP.md) | Phase 0–5 execution checklist, milestones, acceptance criteria, and decision gates |
| [Design document](Anytime_NCM_Design_Document.md) | Technical design and scientific requirements |
| [DESIGN.md](DESIGN.md) | Entry point to the original design document |
| [Experiment protocol](docs/experiment_protocol.md) | Frozen partitions, budgets, metrics, timing boundaries, and statistical procedure |
| [Reproduction log](docs/reproduction_log.md) | Actual setup commands, hardware/software, results, errors, and access disclosures |
| [Known limitations](docs/known_limitations.md) | Current implementation and evidence boundaries |
| [Setup summary](results/setup/summary.md) | Compact operational results |

The design describes the intended system; the roadmap records implementation progress. Recorded run metadata identifies the exact protocol and source versions used for the existing results.

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

The official descriptive full-set baseline necessarily scored all examples internally. Only aggregate scores and execution logs were inspected; individual holdout predictions/references were not used to select a policy. This access is disclosed in the reproduction log. Future work must preserve the phase-specific holdout boundaries and document additional access.

The predeclared offline gate requires an estimated reduction of at least 5% in mean total latency, a paired 95% interval with lower bound above zero, no empirical solve-rate loss for verified stopping, and zero false verifier accepts. Missing cost estimates can produce an inconclusive result. The full [protocol](docs/experiment_protocol.md) defines no-go conditions, budgets, monitoring costs, and statistics.

The collector and policy isolation checks are still planned. The existing manifest/protocol do not themselves implement those runtime access controls.

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
|-- src/anytime_ncm/          # CLI and future research modules
|-- tests/                   # Named research-test placeholders
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
| `scripts/lock_environment.py` | Generate the initial dependency lock after recorded canonical baseline runs |

`configs/setup_sources.json` records actual setup pins. The other YAML files are proposed local research templates; no implemented research runner consumes that schema yet. The baseline wrapper uses the official `third_party/ncm/config/eval/sudoku-hard.yaml` directly.

## Verification

Completed setup checks include:

- An actual CUDA matrix multiplication and both official GPU baseline processes.
- `pip check` and exact installed-version parity with `requirements.lock`.
- Downloaded artifact sizes/SHA-256 values and semantic equality of upstream/Hub Sudoku configs.
- Disjoint puzzle partitions, exploration-only smoke placement, and frozen manifest/protocol/config identifiers.
- Python syntax, package/CLI loading, and TOML metadata parsing.
- Git ignore rules and a clean upstream checkout at the pinned commit.

These checks are not a completed research test suite. The named files under `tests/` currently contain placeholders, so a passing validator/partial-decoder/halting test result is not claimed.

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

[ROADMAP.md](ROADMAP.md) preserves the full study:

1. **Phase 0:** operational setup and reproduction, completed with the disclosed paper-number discrepancy.
2. **Phase 1:** validator, correct partial decoder, offline trajectories, profiling, and go/no-go/inconclusive report.
3. **Phase 2:** conditional real online verified stopping and held-out benchmark.
4. **Phase 3:** conditional learned controller only if measurable headroom remains.
5. **Phase 4:** task-specific translation and/or summarization studies.
6. **Phase 5:** optional trajectory viewer and Concept Firewall integration.

Work on the selected milestone, add its meaningful correctness/parity checks, record commands and artifact provenance, and update the roadmap with evidence. Preserve the frozen model and sampling semantics. Protocol changes require a dated amendment before affected evaluation, while historical run hashes remain traceable.

## Limitations

- No early-exit opportunity or adaptive speedup has been measured yet.
- Exact agreement with the paper's hard-Sudoku number remains unresolved.
- An independent Sudoku correctness validator and partial-reconstruction tests remain unimplemented.
- The validated runtime is one WSL2/RTX 5060 configuration; other platforms and resource limits need validation.
- BLEU/ROUGE, future heuristic confidence, and Sudoku correctness do not establish general semantic correctness or AI safety.
- Raw datasets, weights, environments, caches, and prediction pickles are intentionally local; a clone must recreate them.
- There is no chatbot, browser/mobile product, or trained foundation model in this repository.

See [docs/known_limitations.md](docs/known_limitations.md) for the current evidence boundaries.

## Upstream and attribution

Anytime NCM builds on [HazyResearch/ncm](https://github.com/HazyResearch/ncm) and Kumbong et al., [Next-Concept Modeling: Fast, Parallel Coarse-to-Fine Text Generation](https://arxiv.org/abs/2610.14162).

The NCM source remains a separate pinned submodule with its [upstream license](https://github.com/HazyResearch/ncm/blob/c70274273f489abc73832b2b98584a8483b6b203/LICENSE). Checkpoint and dataset provenance is recorded separately in the source/artifact manifests. This repository does not yet contain a separate project license file.
