# What Comes Next: Revised Research Roadmap After the Phase 1 No-Go

**Updated:** October 22, 2026 (America/Toronto)

**Status:** R0, R1A, and R1B complete. R1B used its separately frozen diagnostic protocol; R2 and later studies remain proposed.

**Read first:** [Research paper](RESEARCH_PAPER.md). [Original Phase 0–5 checklist](ROADMAP.md) remains the implementation record. The [frozen Phase 1 protocol](docs/experiment_protocol.md) and its completed no-go remain unchanged.

## 1. Recommendation

The next research question should be: **Does another frozen Sudoku setting offer useful exact solutions before its final hierarchy level?**

R1A characterized the saved errors. R1B then encoded the 32 preselected valid references: all 32 round-tripped exactly at level 12, but none produced a valid earlier prefix. This does not prove that every alternative code sequence or decoder would fail early. The next recommended branch is the bounded R2 easy-Sudoku screen, followed by medium only if needed, after artifact/resource inspection and a new screen protocol. Keep exact verification and change one major setting at a time.

Do not prioritize an online stopping hook, controller training, or a viewer as the next efficiency experiment. None can, on its own, make an invalid existing prefix into a valid early answer. This is a research sequencing choice, not a claim that the software would be impossible to implement.

If bounded Sudoku follow-ups remain negative, choose explicitly between closing the Sudoku line as a documented negative result and designing a separate natural-language study. Do not keep expanding samples or relaxing quality requirements until a favorable result appears.

## 2. What the existing evidence establishes

| Finding | Consequence |
| --- | --- |
| No valid board before level 12 on 1,400 exploration/development inputs | The studied first-valid rule has no observed generation savings. |
| Development estimated time is 151.02 ms full depth versus 217.74 ms with every-level checking | Monitoring adds an estimated 66.71 ms; this is computation time, not money. |
| Estimated reduction is −44.18%, with 95% interval [−45.02%, −43.45%] | The original 5% improvement gate fails. |
| Cell accuracy reaches 81.70% exploration / 82.09% development at level 11, while valid-grid rate remains zero | Partial information exists, but the mechanism preventing exact early solutions is undiagnosed. |
| Correctness/parity checks pass; all 244 current tests pass | The completed no-go is not an unresolved implementation-correctness failure. |

An optimized implementation might reduce reconstruction/transfer overhead. It would still need earlier acceptable outputs to skip generation under the current verified rule. There is no measured online slowdown or speedup yet.

## 3. Revised sequence and decision points

| ID | Work package | Status | Required outcome before proceeding |
| --- | --- | --- | --- |
| R0 | Package the completed study as a paper and revise the research plan | Complete with these documents | Claims, sources, limitations, and conditional next work are explicit. |
| R1A | Diagnose errors in saved exploration trajectories | Complete — October 22; [report](results/followup/sudoku_prefix_diagnosis/summary.md) | A reproducible error taxonomy and specific hypotheses, without new inference. |
| R1B | Test target-encoded prefixes on a small exploration-only set | Complete — [report](results/followup/sudoku_target_encoding/summary.md) | Evidence separating limited target reconstruction from generated-prefix failure, without claiming a causal proof. |
| R2 | Screen alternative frozen Sudoku checkpoints | Proposed next work; not started | At least one actual early valid output admits a candidate to a larger audit; no screen result alone authorizes online work. |
| R3 | Run a confirmatory opportunity/cost audit for one selected setting | Conditional; separate frozen study | A new documented go/no-go/inconclusive decision using matched quality and total estimated time. |
| Phase 2 | Implement and benchmark actual online verified stopping | Blocked for the original setting | A justified setting-specific go and a separate implementation work order. |
| Phase 3 | Learn a stopping controller | Deferred | Remaining headroom beyond strong simpler policies and an appropriate reserved final set. |
| Phase 4 | Translation/summarization generalization | Alternative branch, not started | Task-specific quality tolerances, signals, protocol, artifacts, and resource feasibility. |
| Phase 5 | Viewer / optional Concept Firewall bridge | Optional, not started | A separate scope grounded in recorded results. |

R1–R3 are new follow-up study identifiers, not retroactive additions to Phase 1's frozen budget. Original phases retain their numbering and completion history. R0 documented the existing study; R1A added a saved-data diagnosis; R1B completed the reference-encoding pilot. None changes the original gate or starts R2.

## 4. R1A — Diagnose the saved failures before collecting more data

**Question:** What distinguishes increasingly accurate but invalid intermediate boards from their final outputs?

**Scope:** Use only the existing 1,000 exploration trajectories and their already-permitted puzzle/reference inputs. Keep development out of exploratory diagnosis to avoid accumulating additional selection on the gate set. Reuse the existing validator and independent checks. No model calls, profiling, new downloads, final-holdout materialization, or changes to historical artifacts.

- [x] Produce per-level distributions of wrong reference cells, blank cells, clue violations, and row/column/box constraint violations. Label whether zeros/blanks participate in each statistic.
- [x] Separate errors at given clues from errors at originally empty cells; report denominators and overlapping error categories explicitly.
- [x] Compare levels 10, 11, and 12 for final-success and final-failure groups. Label these groups as retrospective analysis, never inference-time features.
- [x] Measure how many cells change, are corrected, or become incorrect between adjacent levels. Keep reference-based labels outside causal features.
- [x] Select representative examples by a declared rule and report absent categories rather than inventing them.
- [x] Reconfirm the original primary counts; a discrepancy triggers a correctness investigation before interpreting any new analysis.

**Completed deliverables:** `docs/studies/sudoku-prefix-diagnosis-plan.md`, `results/followup/sudoku_prefix_diagnosis/summary.md`, machine-readable counts, source hashes, and focused tests of error-count definitions.

**Acceptance:** Another developer can regenerate the summary from saved evidence. The report separates observed error patterns from hypotheses. No new outcome is attributed to tokenization or generation solely because errors cluster near the last level.

**Stopping rule:** Complete this analysis once; use its synthesis to specify R1B. It cannot overturn the original gate because it introduces no earlier valid outputs.

**Evidence and findings:** [Report](results/followup/sudoku_prefix_diagnosis/summary.md), [analysis](results/followup/sudoku_prefix_diagnosis/analysis.json), [provenance](results/followup/sudoku_prefix_diagnosis/provenance.json), and [completion record](results/followup/sudoku_prefix_diagnosis/completion.json). At level 11, 999/1,000 exploration boards violate a clue; mean reference errors are 14.821, including 4.964 at supplied clues. The final level restores all supplied clues, but 146 boards remain invalid. All 1,000 puzzles lose at least one previously reference-correct cell at 10→11 despite net improvement. These patterns motivate the target-encoding comparison and do not establish its cause.

## 5. R1B — Compare target-encoded and generated prefixes

**Question:** When the frozen tokenizer encodes an already valid reference solution, can its early cumulative prefixes decode back to a valid clue-preserving board?

This diagnostic was not performed in Phase 1. It is a new reference-based analysis, not an inference policy and not a speedup result.

**Executed fixed pilot, frozen before encoding in the [R1B protocol](docs/studies/sudoku-target-encoding-protocol.md):**

- Use exactly the first 32 exploration identities already assigned by the manifest; do not choose inputs from observed error severity.
- Encode each reference once through the official target encoder/quantizer path and decode its 12 cumulative full-resolution prefixes: 32 encodings and 384 prefix reconstructions/decodes. No new generator runs and no timing study.
- Compare against the corresponding generated-prefix outputs already saved in Phase 1. Keep all outcomes, including unsuccessful final reference round trips. Carry R1A's given/empty-position split and clue/unit metrics into the pilot, with special attention to levels 10–12; retain all 12 levels and the same 384-decode budget.
- The protocol additionally declared 32 latent-only upstream final-reconstruction checks, with no extra decoder evaluations. Actual forward counters were exactly 32 encodings and 384 decodes; tokenizer state was unchanged and every final latent matched upstream bitwise.
- First validate the target-encoding contract, token format, final reconstruction, and storage/future-code isolation. A failed final round trip is a finding requiring investigation, not a reason to remove that input.
- Record any failed attempt; do not silently increase the pilot size. Any additional operation needed beyond the declared budget must be documented before execution.

**Interpretation guide:**

| Observation | Supported interpretation | Not established |
| --- | --- | --- |
| Target-encoded prefixes solve early, generated prefixes do not | A usable early decoded solution can exist for those examples under the target-encoding path; generated codes do not recover it. | That a generator fix is easy, or that it alone causes every failure. |
| Neither path solves early, while target final round trips succeed | The tested early target prefixes also fail exact validity; tokenizer/decoder limitations deserve attention. | That no alternative early code combination or decoder could work. |
| Target final round trips fail | Reconstruction/encoding compatibility or tokenizer reconstruction quality needs investigation. | That the generation-stage no-go was necessarily an adapter bug. |

**Deliverables:** A separately versioned protocol and report under `docs/studies/` and `results/followup/`; prefix-level primary/secondary metrics; all round-trip failures; exact code/artifact hashes; a diagnosis memo. References used to construct these targets must never become deployed stopping inputs.

**Completed outcome:** Both paths had zero early valid outputs. Target final exact-token, parsed-board, and primary-valid round trips were 32/32; the cached generated path finished 24/32 valid. Final target failure lists are empty. The selected recommendation is R2 bounded checkpoint screening; R2 has not started. These 32 exploration observations do not establish a causal mechanism, population absence, deployable policy, or speedup. [Report](results/followup/sudoku_target_encoding/summary.md), [provenance](results/followup/sudoku_target_encoding/provenance.json), [completion evidence](results/followup/sudoku_target_encoding/completion.json). All 244 tests pass, including 26 new R1B tests.

**Exit:** Record a diagnosis and choose one explicit next branch: R2, a separately scoped tokenizer/generator intervention, or closure. A modified/trained checkpoint would start a different method study; it would not silently replace the frozen-checkpoint result.

## 6. R2 — Screen other released Sudoku settings with a bounded budget

**Recommendation:** Screen easy Sudoku first, then medium only if needed. This retains the exact Sudoku verifier and changes difficulty/checkpoint before changing task and quality criteria. Their release availability is documented in the [official source repository](https://github.com/HazyResearch/ncm); compatibility, resource fit, and early-exit behavior remain untested locally.

Before any screen, inspect the actual checkpoint/config/data layout, license, file sizes, tokenization, hierarchy, and resource requirements. Download only selected artifacts, pin exact revisions/hashes, and verify compatibility with the adapter. Do not assume that the hard-Sudoku artifact paths or hierarchy are interchangeable. No paid cloud compute is part of this plan.

**Proposed screen protocol:**

- Predeclare a maximum of two candidates in the order easy, then medium. Stop screening once one qualifies for R3; do not pick a winner based on unrecorded trials.
- Freeze each candidate's input-identity partitions before its baseline outputs or trajectories are inspected. Reserve final sets at that time. Do not use the original hard-Sudoku holdouts for candidate selection; check available input identities against the inherited reservation manifest before materializing a candidate row.
- Use exactly 32 exploration identities per candidate. Run one unchanged official comparator generation and one adapter trajectory generation per identity: at most 64 full-depth input-evaluations per candidate, or 128 across both. These are input-evaluations, not a claim about the number of batched calls. There is no profiling budget in this screen.
- Freeze how failed attempts and any required warmups count before execution; retain every attempt. Do not replace difficult examples or add seeds after seeing results.
- Require full-depth comparator parity, correct independent prefix reconstruction, valid input/reference contracts, and complete records before interpreting opportunity.
- Report all per-level primary-valid counts, first-valid levels, never-valid cases, and reference diagnostics. The budget is intentionally a screening budget, not a powered absence test.

**Screen gate:** At least one independently verified valid output before the final level qualifies a setting for R3. That is a necessary opportunity signal, not evidence of a worthwhile speedup or acceptable population error. Zero early solutions in 32 inputs closes that screen at its fixed budget; it does not prove that none exist in the population.

**If both screens are negative:** Close the frozen-Sudoku first-valid path at this budget and publish the follow-up outcomes. Choose a new objective or task explicitly; do not expand screening indefinitely.

## 7. R3 — Confirm opportunity and total estimated savings before Phase 2

Choose at most one setting from the exploration screen. Before exposing its development outputs, freeze the complete study: artifacts, input partitions, policy, quality definition, budgets, instrumentation, bootstrap, and gates. Previously screened exploration identities stay exploration and count toward its total; they are not new independent confirmation examples.

For a released Sudoku set with at least 2,000 usable unique identities, the recommended starting design mirrors the original allocation: 1,000 exploration, 400 development, 300 Phase 2 final, and 300 Phase 3 final. If its actual data cannot support that allocation, declare a suitable design and its limitations before output inspection. These numbers are proposed defaults for a new study, not permission to reuse an exposed set as untouched confirmation.

- [ ] Reproduce the selected setting's official baseline, with aggregate-only handling of reserved final partitions if the official evaluator scores them internally. Disclose any base-model or cross-study overlap that can be established, and what remains unknown.
- [ ] Audit the full permitted exploration/development trajectories with the same independent reconstruction and validity requirements.
- [ ] Profile the first 100 identities of each permitted partition, five repeats each, after ten exploration-only warmups, at batch size 1. This is a new allocation of 1,000 timed requests under its own protocol; the original Phase 1 allocation stays exhausted.
- [ ] Start with every-level first-valid checking to isolate the changed setting. If another inspection schedule is to be selected, declare its candidate family and selection procedure before development evaluation and report selection explicitly.
- [ ] Compare full depth, all fixed depths, and the verified candidate. Include every scheduled reconstruction/decode/transfer/verifier/policy cost, including full work on never-valid inputs. Charge feature costs only to methods that use them.
- [ ] Document whether monitoring reconstructs from scratch or reuses an accumulator; validate the exact strategy whose time is estimated. Keep generation feedback and monitoring work from being double-counted.
- [ ] Report quality differences, false accepts, work skipped, mean/median/p95 estimates, and paired 95% identity-bootstrap intervals with 10,000 resamples and retained repeats.

**Sudoku gate:** Retain the substantive original rule: estimated mean reduction at least 5%, interval lower bound above zero, zero empirical solve-rate loss, zero false accepts, and passed parity/correctness. An upper bound below 5% is no-go; missing costs, inadequate evidence, or other cases are inconclusive. Correctness problems must be fixed before opportunity is interpreted. Stop at the frozen budget and retain negative outcomes.

A new setting-specific go can justify that setting's online experiment. It does not relabel the original hard-Sudoku no-go as a success. Beating full depth alone also does not establish an adaptive advantage over a strong fixed-depth baseline.

## 8. Conditional Phase 2 — Measure real online stopping

Proceed only after R3 supplies a justified go and an implementation work order is requested.

Preserve [Phase 2A–2C](ROADMAP.md#phase-2--true-online-verified-stopping): add the smallest isolated hook that actually skips later generator evaluations; prove disabled-stop parity and offline/online exit-output equivalence; test current/past-only inputs and never-valid fallback; then measure full depth, development-selected fixed depth, and verified stopping with matched request boundaries.

Freeze policies, metrics, hardware settings, repetitions, and statistical procedure before opening the selected study's Phase 2 final set. Keep its Phase 3 set reserved. Include actual monitoring costs and required synchronization; exclude loading/warmup/reference scoring consistently. Report actual quality and mean/median/p95 request latency, GPU time, memory, and any throughput claim under its own batch conditions.

A positive speedup claim requires the declared actual 5% improvement and uncertainty/quality criteria. A quality-versus-compute frontier claim additionally requires comparison with strong fixed-depth methods. A valid negative online result is still a completed experiment; it must not trigger an automatic controller-training project.

## 9. Other branches and deferred work

### Natural-language study — original Phase 4

If bounded Sudoku diagnosis/screens remain unpromising, begin with a source/resource/protocol audit for WMT14 German-to-English translation; consider XSum as a separate subsequent study. This ordering is a research preference, not evidence that either has useful early exits or fits the current GPU. The [official release inventory](https://github.com/HazyResearch/ncm) lists both tasks.

Translation permits examining graded quality, but lacks Sudoku's cheap exact verifier. Before collecting task trajectories, choose quality metrics, numerical acceptable losses, targeted error checks, inspection signals, budgets, and final-set rules. For example, BLEU/chrF and checks on numbers/negation can be considered; their acceptable numerical tolerances still need to be fixed in that task's protocol. Reference-based scores are offline labels, never online stopping inputs. Do not quietly substitute approximate text quality for the completed Sudoku zero-loss objective.

A task-change study starts with baseline reproduction and an offline opportunity audit, not with an assumption that an online controller will help.

### Learned stopping — original Phase 3

A first-valid controller has no positive early-exit targets in the current hard-Sudoku trajectories. Defer fitting one until a setting supplies useful early outputs and a credible advantage over simpler policies. Any later controller uses only current/past features at inference; final holdout selection remains prohibited. Future outcomes may supply training labels only within the allowed training split.

Predicting that a request will ultimately fail and abandoning it is a different possible objective. It could save work on failures without producing an early valid answer, but can also discard requests that would have succeeded. It requires a separately declared abstention/quality-risk protocol and evidence; the existing first-valid no-go neither validates nor rules out that method. It is not the recommended immediate branch.

### Viewer / Concept Firewall — original Phase 5

Useful for communication after the next research decision, but optional and separate from efficiency validation. Use recorded artifacts and label estimates versus measurements. No Sudoku result establishes a safety benefit or validates an unavailable external integration.

## 10. Research controls and delivery rules

- Preserve original study artifacts, pinned source, frozen protocol/manifest, negative decision, and access history. Follow-ups use new directories, study IDs, and dated protocols; this planning document is not an amendment.
- Record candidate ordering, selected inputs, failed attempts, missing measurements, and stop decisions. Never remove unfavorable observations or use reserved final outputs to choose a method.
- Treat target-encoded reconstructions, reference-based errors, retrospective grouping, and oracle exits as diagnostic labels rather than inference inputs.
- Carry the unexplained 0.15-percentage-point paper-baseline discrepancy and unknown base-model overlap into subsequent reports. Reproduce or investigate them when relevant; do not invent an explanation.
- Keep checkpoint/data downloads narrow and record storage/resource requirements before execution. Additional training, paid compute, and a change of quality objective are not included in this documentation task.
- End each requested phase/subphase with appropriate verification, evidence and roadmap updates, a commit to `main`, a push, and verification that local and GitHub commit IDs match. Work only through the requested boundary.

## 11. Immediate handoff

**Recommended next work order:** “Complete R2: inspect the released easy-Sudoku artifacts and resource requirements, freeze the bounded screen protocol/partitions, run the first eligible 32-input screen with parity checks, and screen medium only if needed within the declared cap; report, commit, and push.”

R1B is complete: 32 reference encodings, 384 prefix decodes, and 32 declared latent-only parity checks, with no generator calls or holdout access. R2 remains unstarted; no additional checkpoint download/screen, online stopping, controller training, or final-holdout evaluation occurred.
