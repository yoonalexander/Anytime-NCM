# Anytime NCM

**Can a frozen Next-Concept Modeling checkpoint stop at a different hierarchy level for each input and improve the quality-versus-compute frontier?**

Anytime NCM is a research repository for answering that question with reproducible experiments. It starts with hard Sudoku, where a complete solution can be checked directly, and plans later studies on translation and summarization.

**Current stage:** **Phase 2A–2C are complete; the measured speedup gate is no-go.** On 300 reserved easy-Sudoku inputs and 4,500 timed requests, every method solved 299/300 inputs and none exited early. Full depth averaged **100.98 ms**, the development-selected verifier **101.84 ms** (0.85% slower), and every-level verification **116.03 ms** (14.91% slower). The [online report](results/phase2/summary.md) includes paired intervals, quality, costs and access disclosures. All **353 tests pass**. Original Phase 1/R2/R3 negative findings remain unchanged; Phase 3 is deferred.

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
2. **Online stopping:** introduce a minimal hook that actually prevents later generator evaluations. Phase 2 was explicitly requested despite the unmet offline opportunity gate, under a separate entry-exception protocol. Measure the total cost of generation, reconstruction, decoding, transfers, verification, and the stopping policy.

The hard-Sudoku checkpoint has 12 levels with per-level code lengths `1, 2, 4, 6, 9, 13, 18, 26, 37, 50, 67, 89`, totaling 322 generated code positions. The last level's length of 89 is not the total hierarchy size.

Useful intermediate solutions, real latency savings, and a benefit from learning a controller are open questions. Negative and inconclusive results are legitimate research outcomes.

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
| Offline trajectory collector | Complete; 1,400 trajectories / 16,800 level records; [Phase 1C](docs/phase1c_collection.md) |
| Diagnostic profiling, plots, and Phase 1 decision report | Complete; [Phase 1D measurements and limits](docs/phase1d_profiling.md) |
| Online request benchmarks | Complete; five frozen methods, 300 inputs × three repeats; practical speedup no-go |
| Online stopping hook | Complete; true skipped-work and parity checks; upstream remains unmodified |
| Learned controller | Deferred; separate headroom justification required |
| Executable research tests | 353 passed, including online halting, causality, statistics and report checks |
| Translation, summarization, viewer, and Concept Firewall integration | Later or optional phases |

The `anytime-ncm` package CLI offers status, offline `collect`, and `validate-trajectories`. Wrapper scripts below work without an editable installation. Official baseline execution remains separate; the bounded online experiment uses scripts/run_phase2.py and its frozen study protocol.

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
| [Research paper](RESEARCH_PAPER.md) | Paper-style account of the completed study, methods, results, sources, and limits |
| [Revised next steps](NEXT_STEPS.md) | Post-no-go diagnostic milestones, bounded checkpoint screening, and conditional online work |
| [R1A error diagnosis](results/followup/sudoku_prefix_diagnosis/summary.md) | Exploration-only reference/clue/unit error distributions and adjacent-level changes |
| [R1B target encoding](results/followup/sudoku_target_encoding/summary.md) | Frozen 32-reference reconstruction pilot versus cached generated prefixes |
| [R2 checkpoint screens](results/followup/sudoku_checkpoint_screen/summary.md) | Completed bounded easy/medium screens, shared-reference reservations, and negative exit |
| [R3 easy extension](results/followup/sudoku_easy_r3/summary.md) | Explicitly requested extension after negative R2; 1,400-input audit, estimated costs, and new no-go |
| [Phase 2 online report](results/phase2/summary.md) | Actual online stopping, development selection, frozen final comparison and measured no-go |
| [Design document](Anytime_NCM_Design_Document.md) | Technical design and scientific requirements |
| [DESIGN.md](DESIGN.md) | Entry point to the original design document |
| [Experiment protocol](docs/experiment_protocol.md) | Frozen partitions, budgets, metrics, timing boundaries, and statistical procedure |
| [Reproduction log](docs/reproduction_log.md) | Actual setup commands, hardware/software, results, errors, and access disclosures |
| [Known limitations](docs/known_limitations.md) | Current implementation and evidence boundaries |
| [Phase 1C collection](docs/phase1c_collection.md) | Tested collection/validation commands, schema, access controls, provenance, and artifacts |
| [Phase 1 report](results/phase1/summary.md) | Quality curves, repeated cost profiles, uncertainty, fixed depths, and no-go decision |
| [Phase 1D profiling](docs/phase1d_profiling.md) | Reproduction commands, diagnostic boundaries, budget, and limitations |
| [Setup summary](results/setup/summary.md) | Compact operational results |

The [research paper](RESEARCH_PAPER.md) documents the completed findings. The [revised next-steps roadmap](NEXT_STEPS.md) records completed R1A/R1B diagnostics and the negative R2 easy/medium screens. R1B used tokenizer-only inference; R2 used its separately declared 128 full-depth input-generation allocation. Further research needs a new task/objective decision. The design describes the intended system; the roadmap records implementation progress. Recorded run metadata identifies the exact protocol and source versions used for the existing results.

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

The collector now enforces manifest-selected exploration/development access through a selective token-row reader. It skips sealed rows without materializing their tokens, validates selected identities, and requires validated smoke evidence before expansion. Current/past feature inputs are separate from offline reference diagnostics. Future policy/controller isolation remains a later milestone; see [Phase 1C access details](docs/phase1c_collection.md).

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
|-- src/anytime_ncm/          # CLI, adapter, validator, collector, later research scaffolds
|-- tests/                   # Validator, prefix, collector tests; timing/halting placeholders
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

Completed setup checks include:

- An actual CUDA matrix multiplication and both official GPU baseline processes.
- `pip check` and exact installed-version parity with `requirements.lock`.
- Downloaded artifact sizes/SHA-256 values and semantic equality of upstream/Hub Sudoku configs.
- Disjoint puzzle partitions, exploration-only smoke placement, and frozen manifest/protocol/config identifiers.
- Python syntax, package/CLI loading, and TOML metadata parsing.
- Git ignore rules and a clean upstream checkout at the pinned commit.

Phase 1A adds 59 passing synthetic correctness and upstream tokenizer/scorer compatibility tests. Run the focused suite from PowerShell:

```powershell
.\scripts\wsl_python.ps1 -PythonArguments @('-m', 'pytest', 'tests/test_sudoku_validator.py', '-q', '-p', 'no:cacheprovider')
```

See the [validator contract and API](docs/phase1a_validation.md) and [completion evidence](results/phase1/phase1a_validation.json). The parser and validator use only the Python standard library.

Phase 1B adds the pinned upstream adapter, independent full-resolution prefix decoding, and tests for learned reconstruction, storage isolation, future-code isolation, generator delegation, and exploration-only parity inputs. The complete implemented suite passed **88 tests**:

```powershell
.\scripts\wsl_python.ps1 -PythonArguments @('-m', 'pytest', 'tests', '-q', '-p', 'no:cacheprovider', '--junitxml=results/phase1/phase1b_tests.xml')
```

A separate real-checkpoint GPU run verified all 12 full-resolution prefixes and **32/32 final decoded outputs matching** the unchanged official evaluator on the exploration smoke inputs. See [Phase 1B API and repeat commands](docs/phase1b_partial_decoding.md), [GPU evidence](results/phase1/phase1b_verified/verification.json), and [completion record](results/phase1/phase1b_validation.json). The parity script requires a fresh output directory. Timing and halting tests remain placeholders.

Phase 1C completed the smoke collection first, then all **1,400 allowed inputs / 16,800 level records**, with independent saved-file validation. All **140 implemented tests passed**:

```powershell
.\scripts\wsl_python.ps1 -PythonArguments @('-m', 'pytest', 'tests', '-q', '-p', 'no:cacheprovider', '--junitxml=results/phase1/phase1c_tests.xml')
```

Recorded [trajectories](results/phase1/trajectories.jsonl), [metadata](results/phase1/trajectories.metadata.json), [validation](results/phase1/trajectories.validation.json), and [completion evidence](results/phase1/phase1c_validation.json) include provenance and explicit null timings. To regenerate, follow [Phase 1C commands](docs/phase1c_collection.md); existing artifacts are preserved. To recheck the saved full collection:

```powershell
python scripts/validate_trajectories.py --metadata results/phase1/trajectories.metadata.json
```

Phase 1D completed all **200 profiled identities / 1,000 timed requests / 12,000 profiled levels**, plus the ten declared exploration-only warmups. All **186 tests passed**. Read the [summary and decision](results/phase1/summary.md), [analysis JSON](results/phase1/analysis.json), [trajectory table](results/phase1/trajectory_table.csv), and [profiling commands](docs/phase1d_profiling.md). Measured diagnostic components remain separate from online latency; original collection timings remain null.

```powershell
.\scripts\wsl_python.ps1 -PythonArguments @('-m', 'pytest', 'tests', '-q', '-p', 'no:cacheprovider', '--junitxml=results/phase1/phase1d_tests.xml')
```

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

- No valid solution occurred before level 12 on the 1,400 permitted inputs. This frozen Sudoku setting produced a no-go; no online adaptive speedup was measured.
- Exact agreement with the paper's hard-Sudoku number remains unresolved.
- Sudoku validation, full-resolution partial reconstruction, offline collection, diagnostic profiling, and the Phase 1 report are complete. Online stopping remains unimplemented. Phase 1B official-output parity and Phase 1D observation/reconstruction parity passed under their recorded settings.
- The validated runtime is one WSL2/RTX 5060 configuration; other platforms and resource limits need validation.
- BLEU/ROUGE, future heuristic confidence, and Sudoku correctness do not establish general semantic correctness or AI safety.
- Raw datasets, weights, environments, caches, and prediction pickles are intentionally local; a clone must recreate them.
- There is no chatbot, browser/mobile product, or trained foundation model in this repository.

See [docs/known_limitations.md](docs/known_limitations.md) for the current evidence boundaries.

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

The verifier checks saved records without model or plotting imports; it does not rerun CUDA parity. The inference budget is consumed. [Frozen protocol](docs/studies/sudoku-checkpoint-screen-protocol.md), [pinned release inventory](configs/r2_sources.json), and [completion evidence](results/followup/sudoku_checkpoint_screen/completion.json) document the execution. All 282 tests pass, including 38 new R2 tests. At R2 completion R3 had not started; subsequent R3 and Phase 2 work is documented below. A new task study remains unstarted.


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

**2A is complete:** an isolated pinned-generation hook, unchanged upstream checkout, actual one/six-level stop checks, 192 real parity requests and 353 passing tests. [Completion](results/phase2/2a_completion.json), [recorded patch](results/phase2/upstream_level_hook.patch.txt). A diff-only newline-marker correction passed git apply --check without repeating model work. 2B and 2C are complete. The frozen policy lock was committed/pushed before per-input Phase 2 final access. Phase 3 final data remains reserved.

~~~powershell
python scripts/run_phase2.py verify-a
~~~

**2B is complete:** [development results](results/phase2/development_analysis.json), [completion](results/phase2/2b_completion.json), [policy lock](results/phase2/policy_lock.json). All 2,100 timed requests matched offline policy outputs. Level-12-only verification won development latency among the verifier schedules, preserving quality but providing no possible early generation savings. The lock was released at commit 2687a46 before the final comparison. Phase 3 remains reserved.


**2C is complete:** five frozen methods on 300 phase2_final identities × three repeats, plus 50 exploration warmups. Every method produced 299/300 valid solutions, no early exits and zero false early accepts. The primary verifier was 0.85% slower than full depth (paired 95% overhead interval 0.39%–1.34%); every-level verification was 14.91% slower. The selected schedule checks level 12 only and therefore has no possible early-generation savings. No practical speedup or adaptive-frontier claim passes.

[Final report](results/phase2/summary.md), [analysis](results/phase2/analysis.json), [Phase 2 completion](results/phase2/completion.json), [2C completion](results/phase2/2c_completion.json), [policy release](results/phase2/policy_lock_release.json). Recompute the saved-data analysis without model/plotting imports:

~~~powershell
.\scripts\wsl_python.ps1 -PythonArguments @('scripts/run_phase2.py','verify')
~~~

All Phase 2 model-evaluation allocations are consumed. Report verification reuses saved results; do not rerun 2a/2b/2c. The final evaluation has prior aggregate baseline exposure, shared solution identities across difficulty masks, and unknown base-model overlap. Integrity hashing traverses all puzzle identities; inference/scoring materializes only permitted rows. No per-input Phase 3 board, reference or prediction was inspected. Full access/timing limitations are in the report. Phase 3 training and task changes require separate justification and a new work order.
