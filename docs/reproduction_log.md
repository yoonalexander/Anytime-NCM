# Reproduction log

## Section 6 — October 20, 2026

- Created the repository scaffold in the existing Anytime-NCM Git repository.
- Preserved `Anytime_NCM_Design_Document.md` as the authoritative design; `DESIGN.md` links to it.
- Added official upstream source as `third_party/ncm`, pinned to `c70274273f489abc73832b2b98584a8483b6b203`.
- Upstream source was not modified.
- The detected host interpreter is Python 3.14.2. It is used only for scaffold inspection; upstream compatibility is unvalidated.
- `requirements.lock` is an explicit placeholder, not an environment lock.
- Research modules and test files are placeholders. No research test pass or model performance is claimed.
- Scaffold verification passed on the detected host: all 19 package/test Python files parse; the package and CLI help/version/status load; TOML metadata parses; all planned directories exist; ignore rules exclude local data, credentials, and raw tensors while retaining summaries and figures; the clean submodule checkout matches its recorded Git entry.

## Section 7 — October 20, 2026

**Operational setup and both official baselines completed. Exact paper-number parity is not claimed.**

### Environment

Windows 11 Pro `10.0.26200`; WSL `2.7.12.0`, kernel `6.18.33.2-microsoft-standard-WSL2`. At preflight, the Windows volume had approximately 369 GB free. WSL initially contained only Docker's distribution. Installed Ubuntu using `wsl --install --distribution Ubuntu-24.04 --no-launch`. Docker's default distribution was not changed.

Provisioned the non-root research user `ncm` and environment `/home/ncm/.venvs/anytime-ncm` using `scripts/setup_wsl.sh`. Apt installed Git, Python venv support, and CA certificates. Validated Python: 3.12.3. Host Python 3.14.2 was used only for scaffold/metadata tasks.

GPU: RTX 5060, 8,151 MiB VRAM, driver 610.88, compute capability 12.0. WSL GPU passthrough works; the noninteractive executable is `/usr/lib/wsl/lib/nvidia-smi`. PyTorch `2.10.0+cu128`, CUDA runtime 12.8, cuDNN 9.10.2; actual CUDA matrix multiplication and official model inference passed. The wheel came from the [official CUDA 12.8 index](https://download.pytorch.org/whl/cu128/torch/). [PyTorch release documentation](https://pytorch.org/blog/pytorch-2-7/) establishes Blackwell support in CUDA 12.8 builds. The driver-reported maximum CUDA version is distinct from the installed wheel runtime.

Installed upstream requirements with constraints protecting the selected CUDA Torch build and retaining the Transformers 4.x API family. Added pandas, scipy, scikit-learn, matplotlib, pyarrow, pytest, PyYAML, setuptools, and wheel. `pip check` passed. Generated `requirements.lock` with `pip freeze --all` after both baselines succeeded; the lock includes the CUDA wheel index and exact installed versions. No global Windows Python environment was modified.

### Artifacts and partitions

Downloaded only `sudoku/hard/*` through the Hugging Face CLI, at model revision `d342ce8aaea58830eef3b8ad473664673e41f692` and dataset revision `6580ba41a4b0a976dde876fbe84d25327617b0e6`.

Paths: `artifacts/sudoku/hard/{tokenizer.pt,generator.pt,config.yaml}` and `data/sudoku/hard/{puzzles.pickle,solutions.pickle}`. [artifacts.json](../results/setup/artifacts.json) records all five sizes and SHA-256 hashes. Total file payload is 163,114,518 bytes, excluding environment packages.

Before baseline inference, froze 2,000 unique puzzle identities into 1,000 exploration/training, 400 development, 300 Phase 2 final, and 300 Phase 3 final inputs. The first 32 inputs are exploration-only. Seed: `20261020`; manifest SHA-256: `ed7a6b3c102fe4713a3f80f8f02b53afe37a44b53da80964936467617799bdb7`. The partition generator does not deserialize solutions. Protocol revision 1 was frozen before smoke inference; both run metadata files record its hash.

### Baseline commands and results

PowerShell, repository root:

```powershell
.\scripts\wsl_python.ps1 scripts/run_upstream_baseline.py --n 32 --output results/upstream_smoke
.\scripts\wsl_python.ps1 scripts/run_upstream_baseline.py --n 2000 --output results/upstream_full
.\scripts\wsl_python.ps1 scripts/lock_environment.py
```

Both runs use upstream commit `c70274273f489abc73832b2b98584a8483b6b203`, one GPU, batch size 128, float32/default precision, no compilation/autocast override, and the released greedy sampling settings. The wrapper sets OMP/MKL threads to four and disables tokenizer parallelism; metadata records these settings. No OOM retry, batch-size override, upstream patch, or checkpoint conversion was needed.

| Run | Solved | Official solved % | Official cell % | Official valid-grid % | Exit |
| --- | --- | --- | --- | --- | --- |
| Smoke | 24 / 32 | 75.00 | 97.26 | 75.00 | 0 |
| Full | 1,725 / 2,000 | 86.25 | 98.36 | 86.25 | 0 |

Evidence: `results/upstream_smoke/` and `results/upstream_full/` contain `run.json`, `metrics.json`, `evaluate.log`, `shard_0.log`, and ignored local raw pickles. These are official evaluator metrics; the independent clue-consistency validator is not implemented. Whole evaluation process durations were approximately 17.73 seconds and 39.62 seconds, including loading/scoring. They are not warm inference latency measurements or adaptive speedup evidence.

[Paper v1, Table 3](https://arxiv.org/html/2610.14162v1#S4.SS4) reports 86.1% hard-Sudoku accuracy. This environment produced 86.25%, a +0.15 percentage-point difference (equivalent to three boards on 2,000 inputs). The specific cause is not established. Code/config/checkpoint/dataset revisions are recorded; settings were not tuned to fit the published number. Exact paper-number/prediction parity is not claimed. Future comparisons must use this environment's observed baseline and disclose this limitation.

### Errors, warnings, and resolutions

- Initial WSL `nvidia-smi` lookup failed because the directory was absent from the noninteractive PATH; the absolute executable path succeeded.
- An early Torch probe ran while NumPy was still being installed and failed with a missing OpenBLAS library. After installation completed, the CUDA probe, dependency check, and both baselines passed without changing NumPy. No failed inference run was discarded.
- Installation temporarily accumulated substantial WSL filesystem cache. A filesystem sync and one `vm.drop_caches=3` request released caches. No data, applications, or global WSL memory settings were changed.
- Hugging Face could not chmod cache files on the Windows-mounted filesystem. Downloads completed, hashes were recorded, and both checkpoints loaded successfully.
- Chat permissions changed during setup. Remaining project writes/GPU runs used approved escalation because this project is outside the chat's writable folders. No approval rejection remained unresolved.

### Holdout access

The official full-set evaluator necessarily read predictions and references internally for all 2,000 inputs. Only aggregate scores and execution logs were inspected; individual holdout predictions/references were not examined for policy selection. Adaptive-policy final evaluation has not started. The phase-specific holdouts remain reserved under the protocol's disclosure rules. Reproduction results must not be used to tune a policy.

### Scope boundary

Section 7 is operationally complete. Section 8 adapter/validator/trajectory implementations, executable research tests, online stopping, and controller training remain pending. The paper-number discrepancy remains an explicit limitation.

### Final setup verification

Passed Python syntax and project metadata checks, artifact sizes/SHA-256 checks, frozen manifest/protocol/config hash checks, disjoint partition and smoke-placement checks, upstream/Hub config semantic parity, exact installed dependency-lock parity, `pip check`, ignore-rule checks, and clean upstream revision checks. Both official baseline processes exited zero. No Section 8 research tests or trajectory runs were represented as completed.

## Phase 1A - October 20, 2026

Implemented Sudoku parsing and correctness in src/anytime_ncm/sudoku.py and focused fixtures in tests/test_sudoku_validator.py. Pytest now adds src to its import path through pyproject.toml.

The parser supports actual upstream token IDs, 91-token BOS-wrapped input prompts, correctly separated 89-token boards, flat 81-cell forms, and decoded text. Malformed candidate outputs cannot be accepted. Puzzle clues and any supplied reference are validated as caller data. Independent flags distinguish parseability, completeness, grid validity, clue consistency, and normalized reference agreement. A distinct valid solution to a nonunique puzzle remains acceptable.

Separate official decoded-text metrics preserve exact text equality, zipped-cell scoring (including NaN for no comparisons), and valid-grid rules without clue checks. Synthetic tests compare directly against the pinned tokenizer and actual upstream Sudoku scorer extracted without CLI/data-loading side effects.

Focused verification: .\scripts\wsl_python.ps1 -PythonArguments @('-m', 'pytest', 'tests/test_sudoku_validator.py', '-q', '-p', 'no:cacheprovider') -> **59 passed in 0.64 seconds**. Cache is disabled because WSL pytest encountered a cache-file permission warning on the Windows mount. Explicit argument forwarding avoids a PowerShell -p parameter-name collision.

Only the token structure of the first exploration puzzle was inspected; no holdout predictions/references were examined and no new model inference or baseline rescoring ran. Upstream source, environment lock, checkpoints, frozen protocol/partitions, and original baseline evidence remain unchanged. Phase 1B onward remains pending. See docs/phase1a_validation.md and results/phase1/phase1a_validation.json for the contract and completion evidence.

## Phase 1B - October 20, 2026

Implemented the hard-Sudoku adapter in src/anytime_ncm/upstream_adapter.py. It loads the pinned local tokenizer/generator in float32 eval mode, delegates unchanged full-depth greedy generation, snapshots full-resolution cumulative latents inside the reconstruction loop, and reuses the actual pinned evaluator's pick_tokens/dec definitions without executing its top-level CLI. Private dependencies _up_to_full and _apply_quant_resi and their pin are documented in docs/phase1b_partial_decoding.md.

Command: .\scripts\wsl_python.ps1 -PythonArguments @('-u', 'scripts/verify_phase1b.py', '--output', 'results/phase1/phase1b_verified'). The fresh unchanged official smoke comparator completed at 24/32 solved (75.00%), 97.26% cell accuracy, and 75.00% valid grids. Adapter verification passed: 12 independent [32, 89, 256] latent snapshots, [32, 89] decoded token batches at each level, isolation at depths 1-11, bitwise final-latent equality, unchanged generated codes, and 32/32 exact final decoded-text matches. Batch-size setting 128, effective batch 32, float32/no autocast, greedy generation, no compilation/KV-cache override, four CPU threads, GPU 0 on the validated WSL2/RTX 5060 environment. This is correctness evidence; no inference-latency or speedup claim follows.

Final suite command: .\scripts\wsl_python.ps1 -PythonArguments @('-m', 'pytest', 'tests', '-q', '-p', 'no:cacheprovider', '--junitxml=results/phase1/phase1b_tests.xml') -> **88 passed in 4.57 seconds**. Includes 59 existing Sudoku, 26 adapter/prefix, and 3 parity-input isolation tests. Synthetic accumulation independently computes learned transformations instead of calling adapter reconstruction helpers.

Preflight failures: WSL Git initially rejected checkout ownership before inference; a retry exposed empty-directory creation handling, also before inference. A later attempt completed official smoke scoring but rejected adapter loading because WSL Git interpreted Windows CRLF files as changes. Read-only Git commands now use an exception scoped to the known checkout and Windows-compatible newline normalization; config comparison normalizes newlines. Empty output directories can be used, while nonempty evidence is preserved. The failed attempt and its successful official smoke subprocess are retained under results/phase1/phase1b; the complete fresh successful run is under results/phase1/phase1b_verified. No global Git setting or upstream source changed.

Access disclosure: checksummed the frozen artifacts/protocol/manifest; deserialized the puzzle pickle and selected only identity-verified exploration indices 0-31. The official evaluator internally deserializes the reference pickle then restricts to those 32 inputs; the exploration-only output pickle remains ignored. Compared its hypotheses and index list; did not inspect reference fields or any holdout predictions/references. No new full-set evaluation or intermediate-quality analysis occurred. Original baseline evidence, upstream, environment lock, and frozen protocol/partitions are unchanged. Phase 1C has not started. See docs/phase1b_partial_decoding.md and results/phase1/phase1b_validation.json.

## Phase 1C - October 20, 2026

Implemented src/anytime_ncm/{collect,dataset,trajectories,features}.py, collection/validation CLI commands and wrapper scripts, and strict smoke/full collection configs. Selection is capped at 1,000 exploration and 400 development identities. The full config requires successful saved-file validation of the first 32 exploration smoke inputs and compatible source hashes before expansion. Original 2,000-input baseline reproduction remains a separate command.

Commands, in order: .\scripts\wsl_python.ps1 -PythonArguments @('-u', 'scripts/collect_trajectories.py', '--config', 'configs/sudoku_smoke.yaml'), then the same command with configs/sudoku_full.yaml. Both exited zero. Smoke: **32 trajectories / 384 level records**. Full: **1,400 trajectories / 16,800 level records**, exactly 1,000 exploration and 400 development. Full generation used ten batches of 128 plus 120; smoke used 32. Greedy sampling, float32/no autocast, no compile/KV-cache override, four CPU threads, GPU 0, validated WSL2/Python 3.12.3/Torch 2.10.0+cu128/RTX 5060. Every required level is stored, and saved-file validation recomputes correctness, reference diagnostics, boards, current/past features, identities, ordering, code counts, and complete coverage.

Full suite: .\scripts\wsl_python.ps1 -PythonArguments @('-m', 'pytest', 'tests', '-q', '-p', 'no:cacheprovider', '--junitxml=results/phase1/phase1c_tests.xml') -> **140 passed in 4.69 seconds**. This includes the earlier 88 tests plus 52 collection/config/access/schema/feature tests. Native Windows commands python scripts/validate_trajectories.py --metadata results/phase1/trajectories.metadata.json and the same command for results/phase1/phase1c_smoke/trajectories.metadata.json both exited zero and reproduced the recorded counts/hashes without models or CUDA. No failed Phase 1C inference attempt occurred.

Access disclosure: frozen artifacts/protocol/manifest were checksummed. Serialization opcode names/counts were inspected for both dataset files to establish their plain protocol-4 integer-list grammar, without printing token values. The collector uses a non-executing selective reader: file bytes and structural opcodes, including sealed row structure, are traversed; unselected integer operands are skipped without decoding/materializing token rows. Only selected exploration/development puzzles and references reach generation, reference validation, scoring, or features. Both final holdouts remain excluded; no official full-set prediction/reference output was opened. The smoke identities repeat within the full exploration allocation, keeping the unique count at 1,400.

All per-level component timings are null, with explicit unmeasured provenance and zero measured coverage. Reference/official scoring is offline diagnostics; the feature interface accepts only current/past decoded token observations and code counts. No oracle labels or future outputs enter features. Full JSONL SHA-256: 2baf2948df953d7f379f9b359091c9a40d31fe9ecafe29f99305ff8bb3e0f5d9. See docs/phase1c_collection.md, results/phase1/phase1c_validation.json, and adjacent trajectory metadata/validation reports. Upstream, checkpoint files, original baselines, frozen protocol/partitions, and dependency lock remain unchanged. Profiling, plots, aggregate quality/opportunity analysis, and go/no-go/inconclusive decision remain Phase 1D; no speedup is claimed.
