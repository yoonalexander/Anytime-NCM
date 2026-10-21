# Phase 1C: offline trajectory collection and storage

**Completed:** October 20, 2026 (America/Toronto).

The offline collector runs all 12 generator levels before decoding and recording prefixes. The smoke collection and the full frozen exploration/development collection are complete. Profiling, plots, and the Phase 1 decision are the next subphase, 1D.

## Recorded artifacts

| Run | Inputs | Level records | Partition counts |
| --- | ---: | ---: | --- |
| Smoke | 32 | 384 | 32 exploration |
| Exploration/development | 1,400 | 16,800 | 1,000 exploration; 400 development |

- Full [JSONL](../results/phase1/trajectories.jsonl), [metadata](../results/phase1/trajectories.metadata.json), and [validation report](../results/phase1/trajectories.validation.json).
- Smoke [JSONL](../results/phase1/phase1c_smoke/trajectories.jsonl), [metadata](../results/phase1/phase1c_smoke/trajectories.metadata.json), and [validation report](../results/phase1/phase1c_smoke/trajectories.validation.json).
- [Completion evidence](../results/phase1/phase1c_validation.json) and [140-test JUnit report](../results/phase1/phase1c_tests.xml).

The smoke records were validated before expansion. The full run regenerated the same smoke identities within its 1,000 exploration inputs; it did not add 32 new identities to the frozen budget. Rows are ordered by original dataset index. The full run used ten batches of 128 and a final batch of 120; the smoke run used one batch of 32.

## Commands

From PowerShell in the repository, using the existing validated WSL environment:

```powershell
.\scripts\wsl_python.ps1 -PythonArguments @('-u', 'scripts/collect_trajectories.py', '--config', 'configs/sudoku_smoke.yaml')
.\scripts\wsl_python.ps1 -PythonArguments @('-u', 'scripts/collect_trajectories.py', '--config', 'configs/sudoku_full.yaml')
```

These output paths already contain the recorded artifacts. The collector refuses to overwrite its JSONL, metadata, or validation file. To repeat collection, supply a fresh output path and run ID, for example:

```powershell
.\scripts\wsl_python.ps1 -PythonArguments @('-u', 'scripts/collect_trajectories.py', '--config', 'configs/sudoku_full.yaml', '--output-path', 'results/phase1/repeat/trajectories.jsonl', '--run-id', 'phase1c_repeat')
```

The full config requires the successful smoke metadata and revalidates its records, source hashes, frozen identifiers, and exact exploration-only selection before expansion. Changing scientific collector code requires regenerating compatible smoke evidence first.

Recheck saved files without loading models or using CUDA:

```powershell
python scripts/validate_trajectories.py --metadata results/phase1/trajectories.metadata.json
python scripts/validate_trajectories.py --metadata results/phase1/phase1c_smoke/trajectories.metadata.json
```

Both commands passed on native Windows Python after the WSL collection. They recompute labels, features, identities, completeness, order, and checksums against the selected pinned dataset rows. They verify the config/source versions rather than trusting the saved success flag.

The package CLI exposes the same operations as `collect --config ...` and `validate-trajectories --metadata ...`. The wrapper scripts add `src/` to the import path, so an editable installation is unnecessary.

## Configuration and provenance

[Smoke config](../configs/sudoku_smoke.yaml) and [full config](../configs/sudoku_full.yaml) now use the implemented strict schema:

| Field | Contract |
| --- | --- |
| `schema_version`, `task` | Version 1; hard Sudoku |
| `run_id` | Short lowercase identifier |
| `partitions` | Positive counts for exploration and/or development only; caps 1,000 and 400 |
| `batch_size` | Integer 1–128; any departure from baseline batch size 128 is disclosed |
| `output_path` | Fresh JSONL path under repository `results/` |
| `smoke_metadata` | Required for expansion beyond the 32-input exploration smoke config |

Missing/unknown fields, invalid types, sealed partitions, excess counts, and paths outside `results/` are rejected. The old full-template setting of 2,000 examples has been replaced by the allowed 1,400-input collection. Official full-set reproduction continues to use its separate unchanged evaluator command.

Run metadata records the run ID, base Git commit plus actual source-file hashes, requested/effective config and hash, original dataset/model/upstream revisions, checkpoint and dataset checksums, official config hash, frozen protocol/manifest hashes, exact selected identities, hardware/software, precision, sampling, CPU threads, and effective batch sizes.

Execution preserved the validated settings: WSL2, Python 3.12.3, Torch 2.10.0+cu128, RTX 5060/GPU 0, float32 without autocast, four CPU threads, no compilation, unchanged greedy generation, and no KV-cache override. The adapter source must match the implementation that passed Phase 1B's real official-output parity check. Collection makes no additional whole-dataset parity claim for different batch compositions.

## Data access boundary

[dataset.py](../src/anytime_ncm/dataset.py) first verifies the frozen protocol/manifest and selects only permitted indices. It rejects holdout requests before opening dataset/artifact files and verifies every selected puzzle's identity.

The pinned datasets are protocol-4 pickles containing plain lists of integer token lists. A restricted non-executing reader traverses that exact grammar. It skips integer operands for unselected rows without decoding/materializing them. It executes no pickle globals, constructors, or memo references. Unsupported formats fail explicitly.

The raw files are read for checksums and structural traversal, including bytes belonging to sealed rows. Only selected exploration/development puzzle and reference token rows are materialized or passed to the model, validator, scorer, and feature pipeline. Both sealed final partitions remain excluded. Tests monitor token operand decoding and verify that unselected rows are skipped.

No official full-set prediction/reference output was opened for collection. Selected references are used only for offline diagnostics and reference-integrity checks.

## JSONL and feature contract

Each JSONL line is one complete puzzle trajectory with schema version, run ID, puzzle identity, original dataset index, partition, and 12 level records. Each level stores:

- One-based level, that level's code length, cumulative generated-code count, and that level's code IDs.
- All 89 decoded token IDs, upstream-decoded text, and parsed 81-cell board when parseable.
- Separate parseability, completeness, grid validity, clue consistency, valid-solution acceptance, and parse-error fields.
- Offline diagnostics: normalized reference agreement and official text-based solved/cell/grid metrics.
- Current/past-only features and explicit timing fields.

`CausalFeatureTracker` accepts one current observation at a time and keeps only previous decoded tokens and counters. Features are level, per-level/cumulative code counts, and the fraction of token IDs changed from the preceding level. The first change fraction is null because there is no preceding observation. No references, verifier flags, future outputs, or oracle labels enter this interface. This does not implement a stopping policy.

Every generation/reconstruction/decode/transfer/validation/feature timing is **null**, with zero measured coverage and explicit unmeasured provenance. Nonfinite official cell accuracy is serialized as null when no comparison is possible. JSON serialization rejects NaN/Infinity literals. No zero-valued timing is used to imply a free operation.

Saved-file validation recomputes boards, acceptance flags, reference diagnostics, and sequential features. It checks all 12 level/code counts, legal codebooks/tokens, run/partition/identity fields, row ordering, and complete input coverage; missing, duplicated, extra, corrupted, or inconsistent records fail.

## Verification and scope

```powershell
.\scripts\wsl_python.ps1 -PythonArguments @('-m', 'pytest', 'tests', '-q', '-p', 'no:cacheprovider', '--junitxml=results/phase1/phase1c_tests.xml')
```

Observed: **140 passed in 4.69 seconds**, comprising the 88 earlier tests plus 52 collection/configuration/access/schema/feature tests. Integration coverage includes partial final batches and JSONL round trips; negative cases include holdout selection, crossed partition identities, unsupported pickle grammar, inconsistent flags/boards/counts, future-label feature injection, and false timing values.

Both real collections completed successfully, including independent post-write validation. Native Windows verification of both saved files also passed. Upstream source, checkpoints, frozen protocol/partitions, environment lock, and original baseline evidence are unchanged.

Phase 1D will analyze solve-rate curves, recovery/instability, cost profiles, uncertainty, and the quantitative decision gate. This subphase establishes the recorded trajectories and their consistency; it makes no online latency, adaptive speedup, or go/no-go claim.
