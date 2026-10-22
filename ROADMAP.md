# Anytime NCM roadmap

**Updated:** October 22, 2026
**Current position:** Sections 6-7, Phase 1 (1A-1D), R1A/R1B/R2/R3, and Phase 2A–2C are complete. Phase 2 measured speedup decision: no-go. Original Phase 1 decision remains no-go.
**Research exit:** R2 screens stayed negative. A separately requested R3 easy extension also returned no-go. The subsequently requested Phase 2 experiment is also complete with a measured no-go. Close this released-Sudoku first-valid path at the completed budget; no practical speedup is established. A new task/objective needs a separate work order; see the [revised roadmap](NEXT_STEPS.md).

This is the execution checklist for Section 8 onward of the [design document](Anytime_NCM_Design_Document.md). Phase numbers follow its Section 9. The design defines the technical requirements; the [frozen experiment protocol](docs/experiment_protocol.md) defines partitions, budgets, metrics, and decision rules. This roadmap tracks work and evidence without changing that protocol.

## Phase overview

| Phase | Outcome | Current status | Entry requirement |
| --- | --- | --- | --- |
| 0 | Repository, environment, and official baseline reproduction | Setup complete; paper-number discrepancy remains open | Sections 6–7 |
| 1 | Correct per-level trajectories, cost estimates, and a decision report | Complete; no-go - no early valid outputs in the audited setting | Recorded operational baseline |
| 2 | Measured online verified stopping | Complete; measured no-go | Explicit user work order and frozen entry exception after failed offline gate |
| 3 | Learned stopping against strong baselines | Conditional; not started | Documented remaining headroom and a separate Phase 3 holdout |
| 4 | Translation and/or summarization generalization | Later study; not started | A task-specific protocol and released checkpoint |
| 5 | Trajectory viewer and Concept Firewall bridge | Optional; not started | Existing research results and defined integration scope |

A negative or inconclusive Phase 1 result is a valid completed research milestone when its required artifacts and limitations are documented. Phase 2 was subsequently implemented under its explicitly requested entry exception; Phases 3–5 remain unstarted. Later studies remain on this roadmap; they do not begin automatically after a gate fails.

## Post-Phase 1 research revision — October 21, 2026

The [paper-style report](RESEARCH_PAPER.md) records the completed hard-Sudoku study. The separate [revised roadmap](NEXT_STEPS.md) defines proposed follow-ups without changing the frozen protocol or relabeling its no-go.

| Follow-up | Status | Boundary |
| --- | --- | --- |
| R0: Paper and revised research plan | Complete | Documentation of existing evidence only |
| R1A: Saved exploration error diagnosis | Complete — [report](results/followup/sudoku_prefix_diagnosis/summary.md) | 1,000 exploration inputs; no inference, profiling, or reserved holdout access |
| R1B: Target-encoded prefix pilot | Complete — [report](results/followup/sudoku_target_encoding/summary.md) | 32 encodings, 384 prefix decodes; no generator calls or holdout access |
| R2: Easy, then conditional medium Sudoku screen | Complete — [report](results/followup/sudoku_checkpoint_screen/summary.md); both negative | Two fixed 32-input screens; 128 full-depth input-generations; no early valid outputs |
| R3: Extended easy audit under explicit entry exception | Complete — [report](results/followup/sudoku_easy_r3/summary.md); no-go | Separately requested after negative R2; preserved reservations and new frozen budget |

One early valid screening example can justify a larger offline audit, not Phase 2. The default online entry rule requires a justified setting-specific go. The subsequently requested Phase 2 engineering experiment records an explicit entry exception without changing the claim gate. Original hard-Sudoku Phase 1 remains complete with no-go; Phases 0–5 and their evidence remain below.

## Phase 0 — Repository and reproduction

**Status:** Operational setup complete, with an unresolved paper-number comparison.
**Design mapping:** Sections 6–7 and 9, Phase 0.

- [x] Set up the package, configuration, test, documentation, and storage structure.
- [x] Pin the clean official upstream submodule and model/dataset revisions.
- [x] Validate WSL2 Ubuntu, Python 3.12.3, CUDA-enabled PyTorch, and the RTX 5060.
- [x] Download only the hard-Sudoku checkpoint and dataset; record sizes and hashes.
- [x] Freeze input-identity partitions and protocol before baseline inference.
- [x] Complete the 32-input official smoke baseline: 24/32 solved (75.00%).
- [x] Complete the 2,000-input official baseline: 1,725/2,000 solved (86.25%); 98.36% cell accuracy.
- [x] Lock the validated environment and document actual commands, errors, and checks.
- [ ] Establish the cause of the difference from the paper's 86.1%, if evidence permits.

**Evidence:** [reproduction log](docs/reproduction_log.md), [setup summary](results/setup/summary.md), [full run metadata](results/upstream_full/run.json), [full metrics](results/upstream_full/metrics.json), [dependency lock](requirements.lock).

The observed result is +0.15 percentage points above the paper. Its cause is not established; exact paper-number or per-input prediction parity is not claimed. Carry this limitation into subsequent reports and use the observed frozen-checkpoint baseline for comparisons in this environment. The design's full paper-difference explanation remains outstanding. Any newly found checkpoint/config mismatch or inability to reproduce the local baseline must be resolved before interpreting trajectory results.

## Phase 1 — Offline correctness and trajectory audit

**Goal:** Determine whether useful early outputs exist and whether their estimated savings justify an online stopping experiment.
**Design mapping:** Sections 8.1–8.6, 9 Phase 1, and 10–12.

Work through milestones 1A–1D in order. Each milestone has its own acceptance checks. Stop after the Phase 1 report and decision.

### 1A — Sudoku parsing and correctness contract

**Status:** Complete - October 20, 2026.
**Primary files:** `src/anytime_ncm/sudoku.py`, `tests/test_sudoku_validator.py`.

- [x] Implement parsing compatible with upstream Sudoku tokens, separators, and special-token handling.
- [x] Represent parseability, completeness, row/column/box validity, clue consistency, and reference agreement separately.
- [x] Define primary solution acceptance as complete, grid-valid, and clue-consistent.
- [x] Retain official reference-based metrics separately for baseline comparability.
- [x] Add meaningful fixtures for valid boards, malformed/incomplete outputs, illegal or duplicate digits, and corrupted clues.
- [x] Cover valid alternative solutions without making reference equality the sole acceptance rule.

**Acceptance:** The validator accepts the valid fixtures and rejects invalid/incomplete/clue-corrupted fixtures. Tests clearly distinguish structural correctness from official reference agreement.

**Evidence:** [Phase 1A contract and verification](docs/phase1a_validation.md), [completion record](results/phase1/phase1a_validation.json), and 59 passing validator/tokenizer/scorer tests.

### 1B — Upstream adapter and full-resolution partial decoding

**Status:** Complete - October 20, 2026.
**Primary files:** `src/anytime_ncm/upstream_adapter.py`, `tests/test_partial_decoder.py`.

- [x] Load the pinned tokenizer/generator through an adapter while preserving the released generation behavior.
- [x] Run full-depth generation unchanged and reconstruct all 12 cumulative prefixes afterward.
- [x] Mirror learned upsampling and residual transforms from the pinned quantizer.
- [x] Capture independent full-resolution accumulator snapshots inside the reconstruction loop.
- [x] Reuse upstream token selection and Sudoku decoding semantics.
- [x] Record the adapter's dependency on private upstream reconstruction methods.
- [x] Test full sequence length, independent storage, an independently accumulated prefix fixture, and isolation from later codes.
- [x] Prove final-level decoded output parity against the official evaluator on the same inputs, batching, precision, and sampling settings.

**Acceptance:** Every prefix yields a full-resolution latent suitable for the decoder; later code changes cannot change earlier snapshots; final outputs match upstream under matched execution settings.

Do not iterate over shortened `z_levels` as full boards or clone the aliased `z_hats` list after its method returns. Final-level parity alone is insufficient.

**Evidence:** [Phase 1B contract and commands](docs/phase1b_partial_decoding.md), [completion record](results/phase1/phase1b_validation.json), 88 passing tests, and 32/32 exact final decoded-output matches against a fresh official exploration smoke run.

### 1C — Offline trajectory collection and storage

**Status:** Complete - October 20, 2026.
**Primary files:** `trajectories.py`, `collect.py`, `features.py`, and relevant CLI/configuration code under `src/anytime_ncm/`.

- [x] Implement an executable collector and validated configuration handling; replace the relevant scaffolds.
- [x] Enforce manifest-selected input access so collection/tuning cannot read sealed adaptive-policy holdouts.
- [x] Start with the 32 exploration smoke inputs; validate records before expanding.
- [x] Collect intermediate boards/tokens and correctness flags for each input and level.
- [x] Record level index, per-level code length, and cumulative generated-code count separately.
- [x] Store run IDs, source/config/checkpoint/dataset revisions, partition/protocol hashes, precision, hardware, and execution settings.
- [x] Use only current/past information in any inference-time feature interface; keep future-derived analysis labels separate.
- [x] Store unavailable timings as null, with timing coverage and measurement provenance.
- [x] Expand only within the frozen exploration/development partitions and budgets.
- [x] Add collection-schema, partition-isolation, and record-consistency checks.

**Artifacts:** `results/phase1/trajectories.parquet` or compact JSONL, plus metadata and tested collection commands.

**Acceptance:** Complete per-input/per-level records can be regenerated from documented commands. No adaptive-policy final holdout is used, and no offline collection result is labeled an online speedup.

**Evidence:** [Phase 1C contract and commands](docs/phase1c_collection.md), [completion record](results/phase1/phase1c_validation.json), [validated full JSONL](results/phase1/trajectories.jsonl), and 140 passing tests.

### 1D — Cost profiling, plots, and the Phase 1 decision

**Status:** Complete - October 20, 2026. Phase 1 decision: no-go (limited early-exit opportunity; correctness checks passed).
**Primary files:** `timing.py`, `report.py`, `tests/test_timing.py`.

- [x] Profile the unchanged generator separately from reconstruction, decoding, transfers, validation, feature extraction, and policy overhead.
- [x] Follow the frozen diagnostic budget: first 100 exploration and first 100 development indices, ten exploration-only warmup requests, five timed repeats per profiled input.
- [x] Keep component diagnostics separate from headline end-to-end benchmarks.
- [x] Compute solve rate by level, first-valid distribution, valid-to-invalid transitions, and never-solved fraction.
- [x] Include representative early-success, late-recovery, and never-solved trajectories when such cases exist.
- [x] Report skipped levels/code work separately from estimated net latency savings.
- [x] Charge never-valid trajectories full generation work and every scheduled monitoring check.
- [x] Calculate paired 95% bootstrap intervals using 10,000 puzzle-identity resamples, seed `20261020`, retaining each puzzle's repeats.
- [x] Produce the trajectory table, solve-rate plot, diagnostic-cost evidence/coverage, and `results/phase1/summary.md`.
- [x] Document limitations, failures, discarded runs, the paper-number discrepancy, and any unavailable cost estimates.
- [x] Apply the predeclared gate below, update this roadmap, and stop after the report.

**Gate:** Minimum worthwhile relative mean end-to-end latency reduction is 5%; maximum empirical solve-rate loss for verified stopping is zero percentage points; maximum false verifier accepts is zero.

| Decision | Required evidence | Next action |
| --- | --- | --- |
| Go | Estimated reduction at least 5%, interval lower bound above zero, correctness/parity checks pass | Record a recommendation for Phase 2; await its subsequent work order |
| No-go | Interval upper bound below 5%, or correctness/parity remains unresolved | Distinguish limited opportunity from a correctness blocker; document findings |
| Inconclusive | All other cases, including missing cost estimates | Use only the predeclared remaining budget, then report uncertainty; no final-holdout inspection |

**Acceptance:** An independent developer can reproduce the trajectory table, plot, and decision from the recorded baseline, manifest, protocol, commands, and profiles. An artifact-complete negative/inconclusive report closes Phase 1 without requiring an online patch. Missing measurements support an inconclusive result, not a measured negative speedup.

**Evidence:** [Phase 1 report](results/phase1/summary.md), [diagnostic contract](docs/phase1d_profiling.md), [completion record](results/phase1/phase1d_validation.json), full budget coverage, and 186 passing tests. No-go closed Phase 1; Phase 2 was unstarted at that milestone. The [October 21 review](docs/phase1_review.md) completed parsing/completeness and official comparison summaries; that review passed 189 tests; the current suite passes 353.

## Phase 2 — True online verified stopping

**Status:** 2A–2C complete — October 22, 2026; measured practical-speedup gate no-go.
**Entry exception:** The offline opportunity gate remains unmet. After the R3 no-go the user explicitly requested unblocking and finishing Phase 2. A [separate frozen online protocol](docs/studies/phase2-easy-online-protocol.md) authorizes this engineering/measurement experiment, including a valid negative result, without relabeling any prior gate. Incremental monitoring and four development-selected schedules are the bounded unblocking attempts; no quality tolerance or checkpoint changes.
**Design mapping:** Sections 5B, 8.4–8.6, 9 Phase 2, and 10–12.

### 2A — Minimal online hook and parity

- [x] Add the smallest isolated callback or level-limit hook that actually skips later generator evaluations.
- [x] Record the upstream patch and exact base revision.
- [x] Preserve full-depth behavior when stopping is disabled.
- [x] Enforce minimum/maximum level boundaries and safe fallback.
- [x] Test no-stop parity, actual skipped generator calls, and current/past-only policy inputs.
- [x] Prove offline/online deterministic exit-output equivalence, including never-valid cases.

### 2B — Development comparisons and measured costs

- [x] Implement full-depth, fixed-depth, and first-valid verified-stopping policies.
- [x] Evaluate stability/uncertainty heuristics where their signals are available without changing sampling semantics.
- [x] Keep the retrospective oracle an analysis-only upper bound.
- [x] Select fixed depths and any thresholds, patience, minimum levels, or inspection schedules on development data.
- [x] Start with batch size 1 and identical request timing boundaries for all methods.
- [x] Include all reconstruction, decoding, verifier, transfer, feature, and policy overhead.
- [x] Record median/p95 wall-clock latency, mean GPU time, peak memory, and applicable throughput.
- [x] Freeze policies, metrics, statistical procedure, and benchmark settings before final evaluation.

### 2C — Held-out comparison and online MVP report

- [x] Evaluate the frozen methods on the 300-input `phase2_final` partition.
- [x] Keep `phase3_final` unavailable and update the holdout-access record.
- [x] Compare against full depth and development-selected strong fixed-depth baselines at matched quality/cost.
- [x] Report actual quality/cost tradeoffs and uncertainty in `results/phase2/summary.md` with supporting metadata and plots.
- [x] Record whether measured monitoring overhead agrees with or defeats the offline estimate.
- [x] Update this roadmap with completion evidence and the recommendation for further work.

**Acceptance:** Online work truly stops; required correctness/parity tests pass; another developer can reproduce the measured comparison. A valid negative experiment still completes the conditional online MVP.

**Claims:** A practical improvement under the frozen gate requires at least 5% actual mean-latency reduction versus the full-depth comparison, a paired 95% interval excluding zero reduction, no empirical solve-rate loss, and zero false verifier accepts. A quality-versus-compute frontier claim additionally requires beating the strong fixed-depth comparison at matched quality/cost; improvement over full depth alone does not establish H2. Finite-sample zero errors are not a population-wide guarantee.

**Optional follow-up:** Benchmark adaptive batching separately, with completed samples masked or compacted so claimed savings correspond to avoided work. Batch-1 findings alone do not establish batched throughput gains.

## Phase 3 — Learned stopping, only with remaining headroom

**Status:** Conditional; not started.
**Entry:** Written justification of remaining headroom and an unexposed Phase 3 holdout.
**Design mapping:** Sections 4 RQ3/H3, 8.3–8.5, and 9 Phase 3.

- [ ] Define the training target and cost/quality objective before fitting; future trajectory outcomes may supply training labels but never inference-time features.
- [ ] Train on exploration/training identities; choose thresholds/hyperparameters on development identities.
- [ ] Begin with logistic regression or a small MLP.
- [ ] Compare against full depth, tuned fixed depths, verified stopping, and available stability/uncertainty baselines.
- [ ] Keep Sudoku-verifier features separate from any task-general policy claim.
- [ ] Measure feature/policy overhead, false early accepts, calibration, and quality/cost tradeoffs.
- [ ] If assessing H3, compare internal statistics against level/input/decoded-output features alone.
- [ ] Freeze all methods and evaluate them together on the 300-input `phase3_final` partition.
- [ ] If its holdout was exposed, obtain and document a fresh appropriate final set rather than relabel an exposed set.
- [ ] Produce `results/phase3/summary.md`, training/evaluation metadata, model artifacts, and reproducible commands.

**Acceptance:** A reproducible positive or negative result against strong baselines on held-out identities, with leakage checks and measured overhead. A learned policy is not required when simpler policies or lack of headroom settle the question.

## Phase 4 — Natural-language generalization

**Status:** Later study; not started.
**Entry:** An explicit WMT14 German-to-English and/or XSum study with a task-specific protocol. A Sudoku no-go may motivate this study but does not start it automatically.
**Design mapping:** Sections 4 RQ4, 9 Phase 4, and 10.

- [ ] Select the task and inspect its actual released checkpoint, config, data layout, and resource needs.
- [ ] Reproduce that task's official baseline with pinned artifacts and environment evidence.
- [ ] Freeze task-specific partitions, quality tolerances, budgets, metrics, and final-evaluation access rules before inspecting trajectories.
- [ ] Audit full-resolution intermediate reconstructions and non-monotonic improvements/damage.
- [ ] Use WMT BLEU/chrF or XSum ROUGE, plus targeted checks such as numbers, negation, and factual consistency.
- [ ] Define stopping signals for settings without an exact cheap correctness verifier.
- [ ] Compare strong fixed-depth and adaptive methods using actual total cost and held-out quality.
- [ ] Report whether Sudoku conclusions transfer in `results/phase4/<task>/summary.md`.

**Acceptance:** A task-grounded generalization result with clear uncertainty and limitations. BLEU/ROUGE are not full semantic correctness measures, and Sudoku's zero-loss gate does not automatically define a suitable natural-language quality tolerance.

## Phase 5 — Optional visualization and Concept Firewall bridge

**Status:** Optional; not started.
**Entry:** Existing research results and a defined visualization/integration scope.
**Design mapping:** Sections 3 and 9 Phase 5.

- [ ] Build a viewer from recorded trajectories and measured results.
- [ ] Show the source, per-level reconstruction, detected issues, chosen exit, continuation-value estimate when available, measured/estimated cost labels, and full-depth comparison.
- [ ] Make run provenance and policy decisions inspectable.
- [ ] Define the Concept Firewall integration contract against its actual available implementation before connecting failure-risk signals.
- [ ] Document what the bridge measures and evaluate any claimed benefit; Sudoku correctness alone does not establish AI safety.
- [ ] Document a reproducible way to open the viewer with existing result artifacts.

**Acceptance:** The viewer faithfully represents recorded evidence and distinguishes measurements, estimates, and unavailable values. Optional integration is documented and validated within its actual scope.

## Rules for every milestone

- Work on the requested milestone and stop at its boundary; update status and evidence before moving on.
- After each completed phase and subphase, run its required checks, update the completion evidence, commit the changes, and push to `main`. Verify that local `HEAD`, `origin/main`, and GitHub `main` point to the same commit before reporting completion.
- Preserve the full Phase 0–5 plan even when only one milestone is being implemented.
- Use meaningful correctness/parity/isolation tests as each research component is added; placeholder files are not passing tests.
- Preserve sampling semantics and the frozen checkpoint. Label stochastic extensions separately.
- Record code/upstream/artifact/config/protocol/partition versions, hardware, precision, failures, and measurement coverage.
- Trace every figure/table to its source run and commands. Keep heavy weights, datasets, raw activations, and secrets out of Git.
- Make dated protocol amendments before affected evaluation when scope or budgets need to change; keep recorded historical protocol hashes valid.
- Follow the holdout-access disclosure rules; baseline scoring does not authorize per-input holdout inspection for policy selection.
- Treat estimated work savings, estimated latency, actual online latency, and batched throughput as separate quantities.
- Carry unresolved limitations into reports instead of replacing them with assumed explanations.

## Milestone completion record

For each completed milestone, add a short record with its date, final status, changed components, commands/tests, result artifact links, limitations, and next eligible milestone. Mark completed checkboxes only when their evidence exists.

| Milestone | Status | Evidence or decision |
| --- | --- | --- |
| Sections 6–7 / Phase 0 operational setup | Complete with disclosed limitation | [Reproduction log](docs/reproduction_log.md); paper-number discrepancy remains open |
| Phase 1A | Complete | [59 passing tests and contract](docs/phase1a_validation.md) |
| Phase 1B | Complete | [88 passing tests; final-output parity 32/32](docs/phase1b_partial_decoding.md) |
| Phase 1C | Complete | [1,400 trajectories / 16,800 level records; 140 passing tests](docs/phase1c_collection.md) |
| Phase 1D | Complete - no-go | [Report](results/phase1/summary.md); 186 passing tests; full frozen diagnostic coverage |
| Phase 2A | Complete | [192 real parity/stop checks](results/phase2/2a_completion.json); 353 tests |
| Phase 2B | Complete | [Development comparison and frozen lock](results/phase2/2b_completion.json) |
| Phase 2C | Complete; measured no-go | [Final report](results/phase2/summary.md), [completion](results/phase2/completion.json) |
| Phases 3–5 | Not started | Subject to their entry conditions above |

### Phase 1A completion - October 20, 2026

Implemented the standard-library Sudoku parser, immutable board, independent correctness flags, clue-consistent acceptance rule, and separate upstream-compatible scoring. Added 59 focused synthetic and pinned-upstream tokenizer/scorer tests; the WSL pytest run passed in 0.64 seconds.

Command: .\scripts\wsl_python.ps1 -PythonArguments @('-m', 'pytest', 'tests/test_sudoku_validator.py', '-q', '-p', 'no:cacheprovider').

Evidence and source hashes: [Phase 1A completion record](results/phase1/phase1a_validation.json). Contract, error behavior, and metric limitations: [validation notes](docs/phase1a_validation.md). No baseline rescoring, holdout prediction/reference inspection, model inference, or partial-decoder work occurred. Phase 1B is the next eligible milestone.

### Phase 1B completion - October 20, 2026

Implemented the pinned hard-Sudoku adapter and independent full-resolution cumulative prefix reconstruction without changing upstream generation. All 12 levels preserve learned upsampling/residual transforms and use actual upstream token-selection/decoding helpers. The full implemented suite passed **88 tests in 4.57 seconds**; separate CUDA verification established bitwise final-latent equality, independent storage, future-code isolation at every proper prefix, and **32/32 final decoded-text parity** against a fresh official evaluator run under matched settings.

Evidence: [adapter contract, commands, and limitations](docs/phase1b_partial_decoding.md), [completion record](results/phase1/phase1b_validation.json), [GPU verification](results/phase1/phase1b_verified/verification.json), and [JUnit report](results/phase1/phase1b_tests.xml). Scoped Windows/WSL preflight failures and their successful fixes are disclosed. Only the first 32 exploration inputs were selected; no holdout predictions/references or intermediate quality results were inspected. No generator modification, stored trajectory collection, profiling, or online stopping occurred. Phase 1C is the next eligible milestone.

### Phase 1C completion - October 20, 2026

Implemented the strict-config offline collector, selective manifest-gated dataset reader, versioned JSONL schema, current/past feature tracker, and model-free saved-file verifier. The 32-input smoke collection passed validation before expansion to all 1,000 exploration and 400 development identities. Full output contains **1,400 complete trajectories / 16,800 level records**. All **140 tests passed in 4.69 seconds**, and native Windows independently revalidated both saved files.

Evidence: [collection commands and contract](docs/phase1c_collection.md), [completion record](results/phase1/phase1c_validation.json), [full trajectories](results/phase1/trajectories.jsonl), [provenance](results/phase1/trajectories.metadata.json), and [validation](results/phase1/trajectories.validation.json). Both sealed partitions were excluded; no sealed token rows were materialized. References and offline diagnostics remain separate from inference-time features. Timings are null with zero measured coverage. Upstream, original baseline evidence, frozen protocol/partitions, and environment lock are unchanged. Phase 1D is next; no profiling, aggregate opportunity analysis, online stopping, or controller training occurred.

### Phase 1D / Phase 1 completion - October 20, 2026

Completed the frozen diagnostic budget: first 100 exploration and 100 development identities, ten exploration-only warmups, five repeats each (1,000 timed requests / 12,000 profiled levels). Added separate generation/component profiles, instrumentation calibration and sensitivity, the 16,800-row trajectory table, four scientific plots, independent verifier checks, fixed-depth comparisons, and a 10,000-resample paired identity bootstrap retaining repeats. All **186 tests passed in 7.25 seconds**.

**Decision: no-go for limited opportunity.** None of the 1,400 audited inputs had a valid solution at levels 1-11; valid-to-invalid transitions were zero. Every-level verified stopping skipped zero levels/codes and added **44.18% estimated development cost**, 95% interval **43.45%-45.02%**. Correctness/parity checks passed; zero false accepts and zero quality loss. Calibration sensitivity also yields no-go. Final solved counts: 854/1,000 exploration and 349/400 development. Early-success and late-recovery cases were absent and were not fabricated.

Evidence: [report](results/phase1/summary.md), [profiling contract](docs/phase1d_profiling.md), [analysis plan](docs/phase1d_analysis_plan.md), [completion record](results/phase1/phase1d_validation.json), [analysis](results/phase1/analysis.json), and [profile provenance](results/phase1/profiles/run.json). Both holdouts remain excluded; the frozen protocol/partitions, original baseline/collection evidence, environment lock, and upstream are unchanged. This closes Phase 1 with an artifact-complete negative finding. No online latency claim, halting patch, training, or Phase 2 work occurred. Phase 2's go entry condition is not met; the full Phase 0-5 plan is preserved.

### Phase 1 review — October 21, 2026

Reviewed 1A–1D against the design and acceptance criteria. Added the missing per-level parsing/completeness counts and official cell/valid-grid summaries from existing data, with three focused tests. All 189 tests pass. Original trajectory/profile data, frozen protocol/partitions, and all prior decision/cost results are unchanged. [Review and commands](docs/phase1_review.md); [current evidence](results/phase1/review_validation.json).

Phase 1 remains complete with no-go. Phase 2's entry requirement is not met; no online work or new inference was performed.

### Research-paper and revised-plan delivery — October 21, 2026

Created [RESEARCH_PAPER.md](RESEARCH_PAPER.md) from the recorded baseline, trajectories, profiles, uncertainty, correctness evidence, and limitations. Added [NEXT_STEPS.md](NEXT_STEPS.md) with proposed R1–R3 diagnosis/screening/audit milestones and preserved all original phases. R0 is documentation-complete. No new inference, profiling, training, online implementation, or holdout access occurred.

### R1A completion — October 22, 2026

Completed the predeclared saved-data diagnosis: 1,000 exploration inputs, 12,000 board states, and 11,000 adjacent transitions. Development JSONL rows were skipped before deserialization. Original exploration primary counts were reproduced exactly, with no new inference, timed requests, downloads, or holdout materialization.

Level 11 averages 14.821 wrong reference cells, including 4.964 at given clues; 999/1,000 boards violate at least one clue. Level 12 preserves every clue and has no blanks, but 146 boards still fail primary validity. At 10→11 every puzzle loses at least one previously correct cell despite aggregate improvement. These are descriptive findings; tokenizer/generator attribution remains open.

[Report](results/followup/sudoku_prefix_diagnosis/summary.md), [pre-analysis plan](docs/studies/sudoku-prefix-diagnosis-plan.md), [provenance](results/followup/sudoku_prefix_diagnosis/provenance.json), and [completion record](results/followup/sudoku_prefix_diagnosis/completion.json). All 218 tests pass, including 29 R1A tests. The previous current Phase 1 source/JUnit review is archived byte-for-byte under results/phase1/reviews/2026-10-21/ before refreshing compatibility evidence. Original empirical/Phase 1D completion artifacts are unchanged. At R1A completion, R1B was proposed next; its subsequent completion is recorded below.

### R1B completion — October 22, 2026

Completed the predeclared target-encoding diagnostic on exactly exploration indices 0–31. Forward counts: 32 normal upstream reference encodings, 384 prefix decodes, and 32 separately declared latent-only final-reconstruction parity checks. No generator was instantiated/called, no timing study or training occurred, and no development/final-holdout rows were materialized. Every final latent matched upstream bitwise; tokenizer state fingerprints were unchanged.

Neither target-encoded nor cached generated prefixes produced an early valid solution. All 32 target references round-tripped exactly at level 12; the cached generated path finished 24/32 valid. This narrows the diagnosis but does not prove a tokenizer-only cause or impossibility for other codes/decoders. Original hard-Sudoku no-go remains unchanged.

[Protocol](docs/studies/sudoku-target-encoding-protocol.md), [report](results/followup/sudoku_target_encoding/summary.md), [raw target records](results/followup/sudoku_target_encoding/targets.jsonl), [provenance](results/followup/sudoku_target_encoding/provenance.json), and [completion record](results/followup/sudoku_target_encoding/completion.json). R1B completed with 244 passing tests, including 26 new R1B tests. At that point R2 was recommended next; its subsequent completion is recorded below.


### R2 completion — October 22, 2026

R1A/R1B warranted the bounded difficulty/checkpoint screen; neither exposed an unresolved correctness failure requiring a change to the original hard-Sudoku evidence. The separately [frozen protocol](docs/studies/sudoku-checkpoint-screen-protocol.md) screened easy first, then medium after a complete negative easy result. Each used exactly 32 official comparator and 32 adapter generations (128 full-depth input-evaluations across both candidates), with no warmups, retries, extra seeds, profiling, or training.

Easy produced 0/32 early valid and 32/32 final valid outputs; medium produced 0/32 early valid and 31/32 final valid outputs. Every paired final token/text comparison passed. Independent full-resolution reconstruction, final latent parity, storage/finiteness checks and model-state integrity passed for all inputs.

Because all released difficulties share identical solution files, R2 inherited the original row-index partitions before selecting inputs. Identity-only hashing traversed all 2,000 candidate puzzle rows, including reserved operands, while only the 32 exploration puzzle/reference rows per candidate were materialized. No development/final boards, references, or outputs were materialized. These related difficulty views are not independent datasets.

**Exit:** Close the released-Sudoku first-valid path at this budget. Neither candidate qualified for R3; no new Phase 2 go or population impossibility claim follows. [Report](results/followup/sudoku_checkpoint_screen/summary.md), [release inventory](configs/r2_sources.json), and [completion evidence](results/followup/sudoku_checkpoint_screen/completion.json). All 282 tests pass, including 38 new R2 tests. The previous current compatibility review is archived byte-for-byte under results/phase1/reviews/2026-10-22-r1b/. Original Phase 1/R1A/R1B empirical and completion artifacts remain unchanged. At R2 completion R3 and task-change work had not started. The subsequently requested R3 extension is recorded below.


### R3 easy extension completion — October 22, 2026

R3 easy-Sudoku extension is complete with **no-go**: no early valid solution among 1,000 exploration and 400 development inputs. Final primary validity was 994/1,000 and 396/400. Development component-sum estimates were 104.22 ms full depth versus 145.20 ms every-level verified, an estimated 39.31% cost increase (paired 95% interval 38.96%–39.68%). These are not measured online latencies. All 310 tests pass, including 28 new R3/resumption tests.

The user explicitly requested R3 after negative R2 screens. Easy was selected as the first candidate in the declared order, under a [separate entry-exception protocol](docs/studies/sudoku-easy-r3-protocol.md). This does not retroactively qualify R2 or confirm a positive pilot. Exactly 32 screened trajectories were reused within the 1,400 total; all 1,000 timed repeats matched their collected outputs. Independent primary checks and false accepts both had zero disagreements/errors. Fixed depth 12 was the development-selected quality-feasible comparator.

The official easy aggregate baseline solved 1,988/2,000. R3 completed exactly 4,378 new generations and 31,536 decoder forwards. A filesystem metadata interruption after 499 saved rows was retained and resumed for only the 901 unrun inputs under a [dated amendment](docs/studies/sudoku-easy-r3-resumption-amendment.md). Original byte prefixes and failure receipts are preserved, with no repeated model evaluation.

[Report](results/followup/sudoku_easy_r3/summary.md), [completion](results/followup/sudoku_easy_r3/completion.json). The previous compatibility review is archived under results/phase1/reviews/2026-10-22-r2/. Original Phase 1/R1A/R1B/R2 empirical and completion artifacts remain unchanged. Phase 2 and new task work have not started.


### Phase 2A completion — October 22, 2026

Implemented an isolated completed-level hook against the pinned upstream generate body, with a recorded patch and clean unchanged vendored checkout. All 192 real-checkpoint requests over the original 32 exploration inputs passed code/token/text and offline/online exit-output checks. Forced depths 1 and 6 execute exactly those transformer levels. Synthetic tests cover causality, future-code isolation, min/max bounds, independent incremental reconstruction and never-valid fallback. All 353 tests pass, including 43 new Phase 2 tests.

[Protocol](docs/studies/phase2-easy-online-protocol.md), [2A receipt](results/phase2/2a.json), [completion](results/phase2/2a_completion.json), [unified patch](results/phase2/upstream_level_hook.patch.txt). A report-only diff newline-marker correction retained the initial artifact and passed git apply --check with zero additional model calls. No development benchmark or final per-input access has occurred. Next: 2B, then locked 2C; prior negative gates remain unchanged.


### Phase 2B completion — October 22, 2026

Completed all seven frozen development methods: 100 development identities x three repeats x seven methods = 2,100 timed requests, plus 70 exploration-only warmups. All outputs matched their saved offline policy exits. Development-selected fixed depth is 12; the selected verifier checks only level 12, and no method exited early or falsely accepted an early board. This is an overhead-minimizing degenerate verifier, not evidence of early-exit headroom.

[2B completion](results/phase2/2b_completion.json), [development analysis](results/phase2/development_analysis.json), [policy lock](results/phase2/policy_lock.json). Source/model-state and 2A parity checks remain passed; the 353-test engine/policy suite is unchanged. Commit/push the lock before releasing the 300 Phase 2 final rows. Phase 3 remains reserved.


### Phase 2C and whole Phase 2 completion — October 22, 2026

Completed all 4,500 final timed requests (300 phase2_final identities × three repeats × five methods) and 50 exploration warmups. Every method solved 299/300 inputs; no early exits or false early accepts occurred. Full depth averaged 100.98 ms, the selected verifier 101.84 ms, and every-level verification 116.03 ms. Primary reduction was −0.85% (paired 95% interval −1.34% to −0.39%); every-level checking cost 14.91% more. The 5% practical gate and matched fixed-depth frontier comparison both fail. These are actual request measurements, not component sums.

The selected verifier checks only level 12. Incremental reconstruction and development-selected deferred schedules reduced monitoring overhead but did not create early valid outputs. All 353 tests pass. Phase 2 consumed 6,912 input-generations, 82,382 generator level evaluations, 25,906 decoder forwards and zero encodings within its frozen caps. No model-work retries or extra samples were used. Report-only fixes and the retained 2A diff-format correction added no model evaluations.

[Report](results/phase2/summary.md), [analysis](results/phase2/analysis.json), [2C receipt](results/phase2/2c.json), [2C completion](results/phase2/2c_completion.json), [whole-phase completion](results/phase2/completion.json), [tests](results/phase2/2c_tests.xml). 2A was committed/pushed as a0af5cb; 2B as 2687a46. The [lock release](results/phase2/policy_lock_release.json) proves local/GitHub equality before final access. Stage source snapshots preserve execution versions; report-only analysis sources are separately hashed. The previous compatibility review is archived under results/phase1/reviews/2026-10-22-phase2b/.

The Phase 2 final subset had prior aggregate official-baseline exposure and related-mask shared identities, both disclosed. Integrity hashing traverses reserved identity operands without retaining boards; the restricted inference/scoring reader leaves Phase 3 rows unmaterialized. No per-input Phase 3 board/reference/prediction was inspected. Phase 3 stays deferred: there is no observed early-valid headroom in this setting. Stop here; a task/objective change or learned-controller study needs separate justification and a work order.
