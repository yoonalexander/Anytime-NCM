# What Comes Next: Revised Research Roadmap After the Phase 1 No-Go

**Updated:** October 22, 2026 (America/Toronto)

**Status:** R0, R1A, R1B, R2, and the separately requested R3 easy extension are complete. R2 stayed negative; R3 also returned no-go. Phase 2 remains unstarted.

**Read first:** [Research paper](RESEARCH_PAPER.md). [Original Phase 0–5 checklist](ROADMAP.md) remains the implementation record. The [frozen Phase 1 protocol](docs/experiment_protocol.md) and its completed no-go remain unchanged.

## 1. Recommendation

**Close the released-Sudoku first-valid path at the completed budget.** After negative R2 screens, the user explicitly requested R3. The separately frozen easy extension found no early valid outputs on 1,400 exploration/development inputs and a negative estimated-cost gate. A new task/objective requires a separate request. [R3 report](results/followup/sudoku_easy_r3/summary.md).

R1A characterized the saved errors. R1B then encoded the 32 preselected valid references: all 32 round-tripped exactly at level 12, but none produced a valid earlier prefix. This does not prove that every alternative code sequence or decoder would fail early. Those findings warranted R2, which executed easy first and then medium under a new frozen protocol. Neither produced a valid solution before level 12. Final validity was 32/32 easy and 31/32 medium; all 64 matched official/adapter final outputs passed exact token/text parity. [R2 report](results/followup/sudoku_checkpoint_screen/summary.md).

Do not prioritize an online stopping hook, controller training, or a viewer as the next efficiency experiment. None can, on its own, make an invalid existing prefix into a valid early answer. This is a research sequencing choice, not a claim that the software would be impossible to implement.

The bounded Sudoku follow-ups are now negative, so closure at this budget is the recorded decision. If the project continues, the recommended next work is a separately requested WMT14 resource/protocol audit before any model evaluation. Do not expand Sudoku samples or relax quality requirements until a favorable result appears.

## 2. What the existing evidence establishes

| Finding | Consequence |
| --- | --- |
| No valid board before level 12 on 1,400 exploration/development inputs | The studied first-valid rule has no observed generation savings. |
| Development estimated time is 151.02 ms full depth versus 217.74 ms with every-level checking | Monitoring adds an estimated 66.71 ms; this is computation time, not money. |
| Estimated reduction is −44.18%, with 95% interval [−45.02%, −43.45%] | The original 5% improvement gate fails. |
| Cell accuracy reaches 81.70% exploration / 82.09% development at level 11, while valid-grid rate remains zero | Partial information exists, but the mechanism preventing exact early solutions is undiagnosed. |
| Correctness/parity checks pass; all 310 current tests pass | The completed no-go is not an unresolved implementation-correctness failure. |

An optimized implementation might reduce reconstruction/transfer overhead. It would still need earlier acceptable outputs to skip generation under the current verified rule. There is no measured online slowdown or speedup yet.

## 3. Revised sequence and decision points

| ID | Work package | Status | Required outcome before proceeding |
| --- | --- | --- | --- |
| R0 | Package the completed study as a paper and revise the research plan | Complete with these documents | Claims, sources, limitations, and conditional next work are explicit. |
| R1A | Diagnose errors in saved exploration trajectories | Complete — October 22; [report](results/followup/sudoku_prefix_diagnosis/summary.md) | A reproducible error taxonomy and specific hypotheses, without new inference. |
| R1B | Test target-encoded prefixes on a small exploration-only set | Complete — [report](results/followup/sudoku_target_encoding/summary.md) | Evidence separating limited target reconstruction from generated-prefix failure, without claiming a causal proof. |
| R2 | Screen alternative frozen Sudoku checkpoints | Complete — [report](results/followup/sudoku_checkpoint_screen/summary.md); both negative | No candidate met the early-valid screen gate; close this path at the declared budget. |
| R3 | Extended opportunity/cost audit of easy under an explicit entry exception | Complete — [report](results/followup/sudoku_easy_r3/summary.md); no-go | User requested extension after negative R2; it does not retroactively qualify R2. |
| Phase 2 | Implement and benchmark actual online verified stopping | Blocked for the original setting | A justified setting-specific go and a separate implementation work order. |
| Phase 3 | Learn a stopping controller | Deferred | Remaining headroom beyond strong simpler policies and an appropriate reserved final set. |
| Phase 4 | Translation/summarization generalization | Alternative branch, not started | Task-specific quality tolerances, signals, protocol, artifacts, and resource feasibility. |
| Phase 5 | Viewer / optional Concept Firewall bridge | Optional, not started | A separate scope grounded in recorded results. |

R1–R3 are new follow-up study identifiers, not retroactive additions to Phase 1's frozen budget. Original phases retain their numbering and completion history. R0 documented the existing study; R1A added a saved-data diagnosis; R1B completed the reference-encoding pilot. R2 subsequently completed its separately scoped screen; none changes the original hard-Sudoku gate.

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

**Completed outcome:** Both paths had zero early valid outputs. Target final exact-token, parsed-board, and primary-valid round trips were 32/32; the cached generated path finished 24/32 valid. Final target failure lists are empty. The selected branch was R2 bounded checkpoint screening, subsequently completed below. These 32 exploration observations do not establish a causal mechanism, population absence, deployable policy, or speedup. [Report](results/followup/sudoku_target_encoding/summary.md), [provenance](results/followup/sudoku_target_encoding/provenance.json), [completion evidence](results/followup/sudoku_target_encoding/completion.json). R1B completed with 244 passing tests, including 26 new R1B tests.

**Exit:** Record a diagnosis and choose one explicit next branch: R2, a separately scoped tokenizer/generator intervention, or closure. A modified/trained checkpoint would start a different method study; it would not silently replace the frozen-checkpoint result.

## 6. R2 — Screen other released Sudoku settings with a bounded budget

**Recommendation:** Screen easy Sudoku first, then medium only if needed. This retains the exact Sudoku verifier and changes difficulty/checkpoint before changing task and quality criteria. Their release availability is documented in the [official source repository](https://github.com/HazyResearch/ncm). Compatibility, resource fit, and prefix behavior are now checked on both frozen 32-input screens; this is not a full-set reproduction or a new online benchmark.

Before any screen, inspect the actual checkpoint/config/data layout, license, file sizes, tokenization, hierarchy, and resource requirements. Download only selected artifacts, pin exact revisions/hashes, and verify compatibility with the adapter. Do not assume that the hard-Sudoku artifact paths or hierarchy are interchangeable. No paid cloud compute is part of this plan.

**Executed screen protocol:** [Frozen R2 protocol](docs/studies/sudoku-checkpoint-screen-protocol.md), declared before candidate inference. The unchanged rules below define the completed allocation.

- Predeclare a maximum of two candidates in the order easy, then medium. Stop screening once one qualifies for R3; do not pick a winner based on unrecorded trials.
- Freeze each candidate's input-identity partitions before its baseline outputs or trajectories are inspected. Reserve final sets at that time. Do not use the original hard-Sudoku holdouts for candidate selection; check available input identities against the inherited reservation manifest before materializing a candidate row.
- Use exactly 32 exploration identities per candidate. Run one unchanged official comparator generation and one adapter trajectory generation per identity: at most 64 full-depth input-evaluations per candidate, or 128 across both. These are input-evaluations, not a claim about the number of batched calls. There is no profiling budget in this screen.
- Freeze how failed attempts and any required warmups count before execution; retain every attempt. Do not replace difficult examples or add seeds after seeing results.
- Require full-depth comparator parity, correct independent prefix reconstruction, valid input/reference contracts, and complete records before interpreting opportunity.
- Report all per-level primary-valid counts, first-valid levels, never-valid cases, and reference diagnostics. The budget is intentionally a screening budget, not a powered absence test.

**Screen gate:** At least one independently verified valid output before the final level qualifies a setting for R3. That is a necessary opportunity signal, not evidence of a worthwhile speedup or acceptable population error. Zero early solutions in 32 inputs closes that screen at its fixed budget; it does not prove that none exist in the population.

**If both screens are negative:** Close the frozen-Sudoku first-valid path at this budget and publish the follow-up outcomes. Choose a new objective or task explicitly; do not expand screening indefinitely.

**Completed — October 22, 2026:** Easy had 0/32 early valid inputs and 32/32 final valid; medium had 0/32 early valid and 31/32 final valid (index 6 never valid). Both used exactly 32 official comparator plus 32 adapter input-generations, 768 generator level evaluations and 416 decoder forwards per candidate. All 64 paired final outputs match exactly. Every candidate prefix matched independent reconstruction; model state was unchanged. No profiling, warmups, retries, additional seeds, training, development/final board/reference materialization, or R3 execution occurred.

The identical released solution files require shared row-index reservations across difficulty masks. R2 inherited all original partitions, performed an explicitly disclosed identity-only hash traversal of 2,000 puzzle rows per candidate, and materialized only the 32 exploration puzzle/reference rows per candidate. These are related difficulty views, not independent datasets.

**Recorded exit:** Both negative; close this released-Sudoku first-valid path at its declared budget. No R2 candidate qualified for R3; the later explicit R3 extension is documented below. No new Phase 2 go exists. Zero in 32 per candidate is not a population impossibility result. [Report](results/followup/sudoku_checkpoint_screen/summary.md), [completion evidence](results/followup/sudoku_checkpoint_screen/completion.json). All 282 tests pass, including 38 new R2 tests.

## 7. R3 — Confirm opportunity and total estimated savings before Phase 2

**Completed under a separately requested entry exception:** The user requested “Do R3” after the negative R2 result. Easy was chosen by the existing candidate order. The [new frozen protocol](docs/studies/sudoku-easy-r3-protocol.md) explicitly authorizes a larger audit without claiming R2 qualification or a positive pilot. Original R2 evidence remains unchanged.

R3 easy-Sudoku extension is complete with **no-go**: no early valid solution among 1,000 exploration and 400 development inputs. Final primary validity was 994/1,000 and 396/400. Development component-sum estimates were 104.22 ms full depth versus 145.20 ms every-level verified, an estimated 39.31% cost increase (paired 95% interval 38.96%–39.68%). These are not measured online latencies. All 310 tests pass, including 28 new R3/resumption tests.

A metadata-write interruption after 499 saved trajectories was preserved and resolved under a [dated amendment](docs/studies/sudoku-easy-r3-resumption-amendment.md). The 901 unrun inputs completed without repeating model work or expanding the budget. The interrupted process has no measured end-state fingerprint; the resumed process reloaded the exact starting checkpoint and matched it at completion. [Completion evidence](results/followup/sudoku_easy_r3/completion.json).

Choose at most one setting from the exploration screen. Before exposing its development outputs, freeze the complete study: artifacts, input partitions, policy, quality definition, budgets, instrumentation, bootstrap, and gates. Previously screened exploration identities stay exploration and count toward its total; they are not new independent confirmation examples.

For a released Sudoku set with at least 2,000 usable unique identities, the recommended starting design mirrors the original allocation: 1,000 exploration, 400 development, 300 Phase 2 final, and 300 Phase 3 final. If its actual data cannot support that allocation, declare a suitable design and its limitations before output inspection. These numbers are proposed defaults for a new study, not permission to reuse an exposed set as untouched confirmation.

- [x] Reproduce the selected setting's official baseline, with aggregate-only handling of reserved final partitions if the official evaluator scores them internally. Disclose any base-model or cross-study overlap that can be established, and what remains unknown.
- [x] Audit the full permitted exploration/development trajectories with the same independent reconstruction and validity requirements.
- [x] Profile the first 100 identities of each permitted partition, five repeats each, after ten exploration-only warmups, at batch size 1. This is a new allocation of 1,000 timed requests under its own protocol; the original Phase 1 allocation stays exhausted.
- [x] Start with every-level first-valid checking to isolate the changed setting. If another inspection schedule is to be selected, declare its candidate family and selection procedure before development evaluation and report selection explicitly.
- [x] Compare full depth, all fixed depths, and the verified candidate. Include every scheduled reconstruction/decode/transfer/verifier/policy cost, including full work on never-valid inputs. Charge feature costs only to methods that use them.
- [x] Document whether monitoring reconstructs from scratch or reuses an accumulator; validate the exact strategy whose time is estimated. Keep generation feedback and monitoring work from being double-counted.
- [x] Report quality differences, false accepts, work skipped, mean/median/p95 estimates, and paired 95% identity-bootstrap intervals with 10,000 resamples and retained repeats.

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

**Recorded decision:** R2 remained negative. The subsequently requested R3 easy extension is complete with no-go. Do not proceed to Phase 2 from this evidence.

**Optional next work order, requiring a new request:** “Audit the released WMT14 artifacts, resource fit, task-specific quality tolerances, candidate signals, and a bounded study protocol before any inference.” This task change has not started.

R2 consumed its own two-candidate allocation. R3 then used a separate 4,378-generation / 31,536-decoder-forward allocation, including its official aggregate baseline and profiling validation. No model evaluation was repeated during the documented collection resumption. No online stopping, controller training, natural-language study, or adaptive final-holdout evaluation followed.
