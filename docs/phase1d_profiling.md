# Phase 1D: profiling, figures, and the Phase 1 decision

**Completed:** October 20, 2026 (America/Toronto). **Decision: no-go.**

The [Phase 1 report](../results/phase1/summary.md) closes the offline research milestone. None of the 1,400 exploration/development puzzles produced a clue-consistent valid solution at levels 1-11. Every-level verification skipped zero levels and zero code positions. This is limited opportunity in the frozen hard-Sudoku checkpoint/reconstruction/sampling setting; correctness checks passed.

On the 100 profiled development identities, estimated verified-stopping cost was 217.735 ms versus 151.021 ms for full depth: **44.18% added estimated cost**, paired 95% interval **43.45%-45.02%**. Equivalently, relative mean reduction was -44.18% with interval [-45.02%, -43.45%]. The interval upper bound is below the frozen 5% worthwhile-reduction threshold. Instrumentation-calibration sensitivity also gives no-go. These are diagnostic component sums, not observed online latency.

## Reproduce

Recorded commands in the validated WSL environment:

```powershell
.\scripts\wsl_python.ps1 -PythonArguments @('-u', 'scripts/profile_phase1.py')
.\scripts\wsl_python.ps1 -PythonArguments @('-u', 'scripts/report_phase1.py')
```

The profile directory is never overwritten. The completed run used the full declared budget; no additional profiling was performed after inspecting its results. Independent reproduction on a recreated environment can use fresh paths with the same budget:

```powershell
.\scripts\wsl_python.ps1 -PythonArguments @('-u', 'scripts/profile_phase1.py', '--output', 'results/phase1_reproduction/profiles')
.\scripts\wsl_python.ps1 -PythonArguments @('-u', 'scripts/report_phase1.py', '--profiles', 'results/phase1_reproduction/profiles', '--output', 'results/phase1_reproduction')
```

To rebuild only the generated report from the existing profiles:

```powershell
.\scripts\wsl_python.ps1 -PythonArguments @('-u', 'scripts/report_phase1.py', '--replace-report')
```

That explicit option replaces only the fixed report artifact names. It preserves trajectory JSONL, collection metadata, raw profiles, and profiling metadata. Without it, existing report artifacts are refused.

## Fixed budget and access

The [analysis plan](phase1d_analysis_plan.md) was written before inspecting Phase 1D quality results or profiling. The frozen protocol and manifest were not amended.

- First 100 exploration indices and first 100 development indices, selected through the existing manifest-gated reader.
- Ten exploration-only warmup requests using the first ten selected exploration indices.
- Exactly five timed repeats per selected identity: 1,000 timed requests / 12,000 profiled levels.
- Descriptive trajectory analysis covers all 1,000 exploration and 400 development inputs.
- Both sealed final partitions remain excluded. No sealed token rows were materialized and no full-set prediction/reference pickle was opened.
- Preflight verification rechecks the permitted collection and pinned artifact hashes. The selective reader traverses raw file bytes/structure while materializing selected token rows only.

Execution: WSL2/Python 3.12.3/Torch 2.10.0+cu128/RTX 5060, GPU 0, four CPU threads, float32/no autocast, no compilation or KV-cache override, released greedy sampling. Profiling batch size 1 is an explicit override from baseline/collection batch size 128.

Across the 200 profiled identities, final tokens and final validity matched the collection; intermediate tokens differed for five identities. Costs and primary profiled quality use the same batch-one outputs, so batch compositions are not mixed within the gate.

## Measurement boundaries

[timing.py](../src/anytime_ncm/timing.py) leaves upstream generation unchanged. Non-mutating codebook-embedding prehooks record CUDA events immediately after each preceding sampled level is ready; start and final markers bracket full generation. The final marker follows original code concatenation. No internal CUDA synchronization or stopping occurs inside generation.

Feedback upsampling/reconstruction used to prepare the next level is charged to that next generation stage. Monitoring reconstructs each cumulative prefix separately at full resolution, using learned upsampling and residual transforms. Prefix code assembly is measured; the estimate reuses original full-code concatenation at level 12 and charges assembly only for earlier checks.

For each level, isolated timings record CUDA-event and synchronized wall costs for assembly, reconstruction, and decoder/token selection. Host timers separately record token transfer, text decoding, reference-free Sudoku verification, causal feature extraction, and the current Boolean decision. Reference diagnostics are computed outside these measured inference components.

The baseline estimate is input preparation + full generation + one final reconstruction/decode/transfer/text output. The first-valid candidate pays input preparation + generation through exit + every scheduled monitoring check through exit. Never-valid trajectories pay full generation and all 12 checks. Features are measured but excluded from this verifier-only candidate, which does not use them.

Generation cost uses cumulative CUDA-stage time plus the nonnegative residual between full-generation wall and event time, charged once to every exit. This allocation and component isolation are offline estimates of a prospective implementation. Model loading, warmup, reference scoring, serialization, and report generation are excluded.

Instrumentation calibration retains 100 empty-region and 13-marker-trace measurements. The primary estimate retains instrumentation; sensitivity subtracts median allowances with zero floors. Empty-region calibration does not bound all hook/launch effects. Both gates agree on no-go; zero observed early solutions also limits opportunity independently of the monitoring-cost estimate.

## Quality and statistics

[report.py](../src/anytime_ncm/report.py) revalidates the saved collection and exact 200-input/five-repeat profiling selection. It independently checks row/column/box digits and clue preservation for 16,800 stored trajectory states and 12,000 profiled states. False accepts and validity disagreements were both zero.

Exploration: final/ever valid 854/1,000, never valid 146/1,000. Development: final/ever valid 349/400, never valid 51/400. No valid-to-invalid transitions occurred. Early-success and valid-to-invalid-to-valid recovery examples were absent; the report explicitly records their absence. Representative late success is exploration index 0; never solved is index 6.

Paired bootstrap resamples puzzle identities 10,000 times with seed 20261020, retaining all five repeats within each selected cluster. The gate uses development profiling; exploration is descriptive corroboration. Estimated means, medians, p95, relative reduction intervals, quality-difference intervals, levels skipped, and code positions skipped are reported separately.

The report shows all 12 fixed-depth comparisons. Depth 12 is the only quality-feasible fixed depth in both development views. This selection is development-based; no held-out claim is made.

## Evidence and verification

- [Summary](../results/phase1/summary.md), [analysis JSON](../results/phase1/analysis.json), [16,800-row trajectory table](../results/phase1/trajectory_table.csv), and [report provenance](../results/phase1/report_provenance.json).
- [Profile metadata](../results/phase1/profiles/run.json) and [all 1,000 repeated component profiles](../results/phase1/profiles/components.jsonl), with individual measurements retained.
- [Solve-rate plot](../results/phase1/solve_rate_by_level.png), [first-valid histogram](../results/phase1/first_valid_distribution.png), [estimated costs](../results/phase1/estimated_cost_comparison.png), and [representative trajectories](../results/phase1/representative_trajectories.png).
- [Completion record](../results/phase1/phase1d_validation.json) and [JUnit report](../results/phase1/phase1d_tests.xml).

```powershell
.\scripts\wsl_python.ps1 -PythonArguments @('-m', 'pytest', 'tests', '-q', '-p', 'no:cacheprovider', '--junitxml=results/phase1/phase1d_tests.xml')
```

A model-free native Windows audit also passed: `python scripts/verify_phase1d.py`. It verifies profile selection/repeats, source/artifact checksums, the saved test report, table coverage, links, and the estimated development cost calculation.

Observed: **186 passed in 7.25 seconds**. This includes timing-boundary/unit checks, hook ordering and cleanup, unchanged outputs, reconstruction/prefix isolation, all-check cost accounting for never-valid inputs, paired-bootstrap clustering, gate boundaries, budget/holdout rejection, trajectory categories, and Markdown table/link verification. All four figures were visually inspected.

Hook-versus-uninstrumented warmup code parity passed 50 comparisons; repeat-code parity passed 800 comparisons; final reconstruction parity passed all 1,000 requests. No Phase 1D inference failure, discarded timed request, budget expansion, or cost-coverage gap occurred. Report authoring/formatting repairs and a report-only rebuild reused the same saved profiles and added no timed requests.

The paper-number discrepancy remains open: original full-set reproduction 86.25% versus paper 86.1%, +0.15 percentage points without an established cause. Base-model training overlap is unknown. No headline online latency, real halting, adaptive speedup, controller training, or final-holdout evaluation was performed. Original trajectory timings remain null and separate from diagnostic profiles. The upstream source, frozen protocol/partitions, dependency lock, and original baseline/collection evidence remain unchanged.

Phase 1 is complete with a documented no-go. Phase 2's entry gate is not met; later phases remain on the roadmap and require a subsequent work order.
