# Stronger research S0B: prospective saved-WMT opportunity protocol

Version 1, October 23, 2026. Frozen after S0A commit `62397eaac9e2d28e62beacd818b99faa17153286`, before any S1 search, additional outcome analysis or model work. [Roadmap](../../RESEARCH_ROADMAP.md), [inventory/claim map](stronger-research-inventory.md), [exact identities and input digests](stronger-research-inventory.json), [related work](stronger-research-related-work.md).

This freezes S1 procedures; it does not execute or authorize S1 in this work order. Stop after committing/pushing S0B and verifying remote equality. A later S1 request is required. No outcome-dependent pilot, dry run on real trajectories or exploratory assignment scoring is allowed in S0. Prior Phase 4 aggregate curves, selected policies and published examples were already exposed; this is prospective about the new search, not blind to the old study.

## 1. Questions, estimands and scope

Primary question: among the saved 64 development WMT trajectories, does a bounded reference-informed search find a corpus-quality-feasible mixed exit assignment with at least 5% estimated mean savings versus full depth after declared monitoring assumptions, and positive estimated improvement over the strongest feasible fixed depth? The 128 exploration trajectories are analyzed first under the same frozen algorithm. They are not pooled with development to improve the gate.

Secondary questions: how much generated work could such an assignment avoid; how sensitive is estimated benefit to monitoring and non-generator cost; how far are the historical selected policies from the found assignment? No deployable controller is fitted. The assignments use references, later outputs and identity keys offline. Their cost/quality is a diagnostic attainable point in a relaxed, reference-informed problem, not a causal policy's measured performance.

This is the released WMT checkpoint only, 11 levels, 313 cumulative generated codes. Do not change checkpoint, decoder, sampling, tokenization, data, tolerances, search family or budgets to seek a positive result. Sudoku/R1B findings supply context, not a new experiment. S2 diagnosis, WMT target encoding, S3 controllers, intervention and manuscript submission are outside S1 and this work order.

## 2. Allowed population and enforceable access procedure

Population authority: [WMT input manifest](../partitions/wmt14-phase4.json), SHA-256 `9cbd6503cb440b72f14296dc35d2c1054060f8c2ceebc26ae3349c348768dacb`. Exact selected records are frozen in [S0A JSON](stronger-research-inventory.json): first 128 exploration and first 64 development groups sorted by canonical minimum source index. There are 192 distinct effective-prefix identities. Do not regenerate a split, substitute rows or add the other 384 exploration /192 development /1,979 reserved groups.

Permitted S1 reads:

- Saved `results/phase4/wmt14/trajectories.jsonl` (SHA-256 `bcbb399d427e31f740b0a9916686c47e8b8c2d7978e6ee7a022d9705272e7c28`), containing the preselected exploration/development trajectories; metadata, 4A/4B receipts, source snapshots, audit/policy-lock records and input-only manifests from the inventory.
- Existing `results/phase4/wmt14/4b_requests.jsonl`, only timed development rows for the 64 selected groups, three repeats, four historical methods. Exploration warmups are identified and excluded from latency estimands. No final `4c_requests.jsonl`, raw final outputs/references or additional baseline predictions.
- Reference strings for those same 192 rows only, using the existing restricted non-executing selected-string reader in [wmt_data.py](../../src/anytime_ncm/wmt_data.py). Do not call unrestricted pickle loading or execute pickle instructions. Prefer retained selected references if present, and verify matching values. Source token rows outside the identity manifest are unnecessary; no retokenization/model load.
- Historical aggregate reports, including consumed-final aggregate results, for provenance/context only. No final per-input data is needed to choose a search, cost model, examples or gate.

Materialize/read outcomes and references only for the active split; development content remains closed to new S1 analysis until the exploration implementation/results lock is committed, pushed and remote-verified. Before any scoring, S1 implementation must fail closed unless allowlisted identity/index pairs exactly equal the 128/64 lists; reject extras, duplicate identities, split collisions, missing/duplicate levels, invalid level numbers or inconsistent saved source/metric hashes. Streaming readers must filter by split/index before exposing row content to analysis. Log references materialized and records accepted/rejected; never open a broader viewer bundle to work around access limits. Synthetic fixtures may test that final/reserved sentinels are rejected before use. Whole-file byte hashing is permitted; it is not permission to deserialize forbidden rows.

Validate all 11 levels, saved token/text schema, full-resolution reconstruction evidence and task source/checkpoint/tokenizer revisions against the 4A receipt. Verify source-snapshot hashes, not an assumption that current reporting files are identical to executed versions. Raw WMT source/reference asset files may be byte-hashed for integrity without unpickling. Stop on provenance or identity mismatch; retain a failure record. Do not regenerate trajectories or rerun Phase 4 model stages.

Analyze exploration completely first. Commit its implementation, provenance and termination ledger, with development access still closed for **new S1 analysis**, and push/verify before development. The development sample was already used for historical selection; this procedural separation does not erase exposure. Any outcome-dependent change requires a dated amendment and invalidates the original prospective development decision; do not quietly restart this protocol.

## 3. Quality, signatures and constraints

Use sacreBLEU **2.6.0**, matching the historical WMT metric implementation and tokenizer defaults. Record actual Python/NumPy/sacreBLEU versions; no dependency upgrades or environment rebuilds. If unavailable in the existing environment, stop and report the missing dependency instead of selecting a different metric implementation.

| Quantity | Frozen contract |
| --- | --- |
| Primary corpus BLEU | cased, one reference, 13a tokenization, exponential smoothing, effective_order false; signature `nrefs:1|case:mixed|eff:no|tok:13a|smooth:exp|version:2.6.0` |
| Primary corpus chrF | character order 6, word order 0, beta 2, spaces excluded; signature `nrefs:1|case:mixed|eff:yes|nc:6|nw:0|space:no|version:2.6.0` |
| Secondary | Lowercase corpus BLEU, reported only; cannot replace primary criteria |
| BLEU feasibility | mixed assignment minus matched level-11 corpus score >= -0.5 absolute points, on 0–100 scale |
| chrF feasibility | difference >= -1.0 absolute points, on 0–100 scale |
| Numeric-reference F1 | candidate minus full >= -0.02, where reference digit-number coverage is nonzero |
| Negation-cue mismatch | candidate rate minus full rate <= +0.02 |

Reuse exact literal-cue definitions from [wmt_policy.py](../../src/anytime_ncm/wmt_policy.py) and macro aggregation from [wmt_metrics.py](../../src/anytime_ncm/wmt_metrics.py), pinned by S0A JSON. Numeric tokens are regex matches `(?<!\w)\d+(?:[.,]\d+)*(?:%)?`, compared as distinct sets; per-reference-nonempty F1 is twice intersection size divided by the total set sizes, averaged over covered identities. Negation presence is `no/not/never/neither/without/n't` (including the implementation's curly-apostrophe variant), case insensitive; mismatch rate is averaged over all identities. Do not expand or normalize cues after inspection. Empty numeric coverage is `unavailable`, not zero or success; omit that constraint only where undefined and report coverage, including bootstrap undefined counts. No semantic safety/factuality inference follows from these heuristics.

For every complete assignment, assemble one saved hypothesis per input at its assigned level and recompute corpus metrics against that split's matched references. Never average sentence BLEU/chrF for a corpus claim or use per-sentence best chrF as the constrained solution. Cache per-level sufficient statistics and additive cue contributions for efficiency, but cross-check every retained incumbent and all 11 fixed depths against direct corpus scoring within absolute `1e-10`. Treat differences within `1e-10` as numerical equality only; do not enlarge scientific tolerances.

## 4. Baselines, work and cost scenarios

Reproduce all 11 fixed-depth quality points from saved outputs. Replay the saved locked stability and guarded-stability exits with their actual inspection schedules; verify correspondence with saved development rows. This is offline replay, not new model execution. A first observation cannot satisfy stability/patience. Preserve their historical negative results.

For each complete assignment `a=(a_1,...,a_n)`, report mean levels, cumulative codes, histogram of exits, fraction before 11, hypothetical full-resolution reconstructions/decoder calls, reference-metric gains/damage and cue coverage. Widths are `1,4,8,14,20,26,32,40,48,56,64`; let `P(k)` be their cumulative sum. An oracle choosing an exit from future/reference data has no implementable inspection schedule. Cost it under an explicit surrogate schedule: inspect and decode each level 1 through chosen `k`, so `k` decodes and `k-1` extra inspections beyond one terminal decode. Report this assumption, plus terminal-only oracle lower-cost scenario; do not suggest it is a learned or causally realizable selector. Stability baselines keep their own actual minimum/patience schedule.

Missing WMT per-depth timings cannot be recovered from the saved full-depth requests. Use the following dimensionless **cost surrogate**, never call its value milliseconds or actual latency:

`W(k,tau) = tau*k/11 + (1-tau)*P(k)/313`

`C_fixed(k;f,tau) = f + (1-f)*W(k,tau)`

`C_adaptive(k;f,tau,h) = C_fixed(k;f,tau) + h*(k-1) + 0.2*h*k`

Full depth with one terminal decode costs 1. `f` is assumed unavoidable preparation/terminal reconstruction/decoding/transfer fraction; `tau` mixes level-count and code-count scaling for remaining work; `h` is the normalized cost of **each extra** reconstruction, decode and transfer; `0.2*h` is an additional assumed per-observation feature/controller cost, charged at **all k** decision points, including the terminal point. The ratio 0.2 is frozen, uncalibrated, and varied jointly with h; controller work is never silently free in monitored scenarios. The baseline terminal decode remains in f. Treat the forced-final decision as also incurring this conservative controller charge. These are assumptions, not a fit to timings. Generator work is not known to be linear in either levels or codes. Fixed-depth comparators incur no adaptive monitoring. Oracle assignment full-depth cases still pay monitoring under this schedule. Terminal-only optimistic scenario sets extra monitoring to zero; the zero-cost reference oracle is not deployable.

Exactly three search operating points, in order:

| Point | f | tau | h | Role |
| --- | ---: | ---: | ---: | --- |
| O0 | 0.25 | 0.5 | 0 | Optimistic zero-monitoring search |
| O1 | 0.25 | 0.5 | 0.005 | Primary monitored search (0.5% of full cost per extra inspection) |
| O2 | 0.25 | 0.5 | 0.02 | Higher-monitoring search (2% per extra inspection) |

Sensitivity evaluates the **same three retained assignments**, without further search, at every combination `f in {0,0.25,0.5}`, `tau in {0.25,0.5,0.75}`, `h in {0,0.005,0.01,0.02,0.05}`: 45 scenarios each, 135 assignment/scenario evaluations per split. Show cost/savings, fixed comparison and the break-even `h` for 0% and 5% reduction using mean denominator `mean((k-1)+0.2*k)` (unavailable if that denominator is zero). Sensitivity is not 45 extra operating-point searches. Values are an uncalibrated engineering envelope; no evidence that the entire real system lies in it is presumed.

For each split and scenario, the strong fixed comparator is the minimum-cost depth among all 11 satisfying the **same** point quality/cue constraints; full depth is always a quality fallback. Break ties by fewer generated codes, then smaller depth. Report both full and fixed alongside each adaptive assignment. For the primary frontier diagnostic also report assignment-minus-fixed BLEU/chrF with the same margins and numeric/negation guardrails; do not claim matched quality merely because both passed separately versus full. Level-11 comparator fallback remains valid, not a search failure.

Retained 4B ready-output timings may describe their measured full/selected-method conditions, with identity-paired three-repeat summaries, mean/median/p95 and failures. They do not identify `f`, `tau`, an arbitrary early-exit cost, or a pure per-inspection `h`. Do not divide a full-depth time by 11 to fabricate timings or substitute Sudoku profiles. Report a comparison of the observed selected-method aggregate overhead with scenario predictions as a model-adequacy diagnostic, without refitting assumptions. If no defensible mapping to plausible real execution cost exists, the practical headroom decision is **inconclusive**, even when proxy work savings are large.

Actual speedup, reserved for an authorized future online study, requires synchronized ready-output wall time including preparation, skipped generation, reconstruction/decoding, transfers and policy work. Model loading/warmup/offline reference scoring are separate. CUDA event elapsed, generated levels/codes, process duration and throughput remain separately labeled. An S1 surrogate reduction is not the practical-latency target being met.

## 5. One deterministic bounded search

Algorithm: single-start feasible coordinate descent over complete exit assignments. No training, stochastic restarts, extra solver, sentence-oracle initializer, pair swaps or outcome-dependent schedule changes.

For each split in exploration-then-development order, and each O0/O1/O2 in that order:

1. Sort inputs by ascending canonical index, breaking impossible index ties by identity hash. Evaluate/retain the 11 uniform fixed assignments and two historical locked adaptive assignments. Count these **13 evaluations** in each operating point's cap even when their cached metrics are reused. If the saved policies produce identical exit vectors, still charge their declared slots. Full initialization is the uniform level-11 member, so no additional initialization evaluation.
2. Start with every exit at 11. At each sweep, enumerate input indices ascending and candidate new depths ascending from 1 to current depth minus 1. Each neighbor changes exactly one exit; the unchanged incumbent is not reevaluated. Every requested neighbor metric evaluation, including infeasible, failed or cached duplicate attempts, consumes one complete-assignment slot. No partial sentence-score shortcut defines feasibility.
3. Retain neighbors meeting all point quality/cue constraints with strictly smaller mean scenario cost (improvement greater than `1e-12`). At a completed sweep, choose the lowest-cost feasible neighbor; ties within `1e-12` break by smaller total codes, then lexicographically smaller full exit vector in canonical order. Accept it and repeat. Do not accept infeasible intermediate steps or increase an exit to escape a local trap.
4. Stop when a complete sweep finds no improving feasible neighbor, the 10,000-evaluation cap (including the 13 charged baseline slots) is reached, or a resource/failure limit is reached. If cap interrupts a sweep, retain the best feasible point seen, flag the incomplete sweep and do not claim local optimality. Preserve last valid incumbent even on failure; no new start or replacement input.

Maximum **10,000 complete assignment evaluations per split/point**, **30,000 per split**, **60,000 total**, including initial baselines and unsuccessful attempts. Up to 9,987 neighbor attempts per point. At most one sweep can be incomplete at termination. Cache reuse does not buy additional evaluations. Record sequence number, split/point, assignment digest, candidate change, cost, all corpus/cue scores, feasibility, accepted/rejected status, cache hit, elapsed time and termination. Store full vectors for accepted incumbents and final best feasible vector; the ledger plus changes reconstructs every attempted vector. Append/flush at least once per 100 attempts; checkpoint incumbent and counters at each accepted change.

This search only decreases exits and can miss improvements requiring compensating quality changes, swaps, upward moves or different starts. A negative search is “not found by this search within this budget.” At most `11^128` / `11^64` assignments exist before constraints; this procedure does not enumerate them. Failed search never proves no useful early translation.

A found feasible assignment gives an **upper bound on minimum surrogate cost** and thus a **lower bound on maximum surrogate savings** in this offline relaxed problem. It is not an upper bound on what any causal controller can save. A mathematical optimum requires exhaustive search or a valid lower cost bound meeting the incumbent, with reproducible certificate/gap under the exact objective/constraints. No such solver is budgeted here. Report `certified_optimum=false` and `optimality_gap=unavailable` unless independently valid analytic bounds establish equality. An optional trivial unconstrained relaxation `mean_i min_k C(k)` is a valid lower cost bound under the specified surrogate only; its gap to incumbent may be reported but is not a physical-latency bound. Future-aware perfect-information and causal stopping optima are different problems.

## 6. Uncertainty and reporting comparisons

Use paired identity bootstrap, **10,000 resamples per split**, NumPy `Generator(PCG64(seed))`, exploration seed **20261023**, development seed **20261024**. Draw `n` canonical identities with replacement per resample and use the same draws across all comparisons within a split. Recompute corpus metrics from summed per-segment sufficient statistics, validated against direct scoring; the historical source shows the method. Preserve all three timing repeats per selected identity; use per-identity mean for mean-latency reduction and retain raw repeats for latency quantiles. Repeats never increase `n`. News-document IDs are unavailable, so disclose clustering uncertainty.

For each of the three retained assignments versus full and versus the selected fixed comparator, and the fixed comparator versus full, report point differences and two-sided percentile 95% intervals (2.5%,97.5%). This is **seven paired comparisons per split /14 total**, with shared draws. Bootstrap uncertainty is restricted to the three search operating points and their comparisons; the 45-scenario sensitivity grid reports point estimates only. Report one-sided 95% quality lower bounds (5th percentile) separately. A future practical positive claim requires lower bounds >= -0.5 BLEU and >= -1.0 chrF, empirical numeric/negation margins, at least 5% mean actual ready-output reduction and positive paired 95% reduction lower bound. For a future actual online frontier claim, also require positive mean reduction versus the selected fixed comparator with positive paired 95% lower bound, at matched quality. A speedup interval whose upper bound is below 5%, a quality interval wholly beyond a loss tolerance, or a point diagnostic violation is no-go; other unresolved boundary cases are inconclusive. Use these same quality bounds conservatively for S1 evidential interpretation. Simultaneous family-wise coverage across metrics/points is not claimed; O1 is the single primary point and O0/O2 are sensitivity, never post-hoc rescue choices.

For cost, bootstrap the fixed assignment's per-identity surrogate costs, reporting `1 - mean(C_assignment)/mean(C_comparator)` and its percentile interval. A normalized full-depth comparator is 1 for each identity. For actual retained timing comparisons use the ratio of paired mean times, not the average per-input ratios. Report guardrail point differences, coverage and conditional intervals; count numeric-undefined resamples. Missing data is unavailable, not an imputed success or zero.

**Zero reoptimization within bootstrap resamples**: search budget for resampling is 0. These intervals are conditional on the chosen assignments, fixed comparator and cost assumptions, despite recomputing corpus scores under resampling. Search and fixed-comparator selection uncertainty remain unaccounted for. Oracle assignments optimized on development cannot serve as held-out causal predictions, and these intervals cannot validate a learned selector. Development was consumed in Phase 4 selection; it is reused diagnostic evidence, never fresh confirmation. Unknown pretraining overlap and official aggregate exposure remain disclosed.

For any future fresh confirmation, establish an eligible evaluation manifest before per-input outcomes, excluding consumed/previously inspected identities and effective-prefix/shared-solution groups as applicable; disclose aggregate-only exposure and unknown training overlap. If suitable data cannot be obtained, label results exploratory. No such data are accessed or allocated by this protocol.

## 7. Gate, examples and closure

Report three distinct statements: finite-search quality/work opportunity, scenario-based cost opportunity, and whether existing cost evidence suffices for the roadmap's practical-headroom interpretation.

- **Headroom supported:** Primary O1 development assignment satisfies all point constraints and quality lower bounds, estimated mean savings >=5% versus full with positive paired 95% lower bound, and positive estimated mean improvement versus the strongest feasible fixed comparator at matched quality. A defensible justification of the primary monitoring/cost assumptions from covered evidence is also required; state it explicitly and show all sensitivities. This permits proposing bounded next work, not an actual speedup claim or automatic S3 execution.
- **Headroom unsupported:** Under an interpretable declared cost scenario, the completed predeclared search finds no development assignment meeting the point opportunity thresholds. Say “not found by this search”; a global conclusion needs the certified bound described above. The absence of an assignment in this heuristic search alone does not prove useful early outputs absent. Close controller development for this cycle unless a separately requested bounded amendment addresses a specific limitation.
- **Inconclusive:** Missing/unsupported cost decomposition, relevant search-limit ambiguity, unavailable quality/coverage evidence, or quality/cost intervals spanning decision thresholds prevent a defensible decision. Even if O1 passes points, missing real-cost evidence requires an inconclusive practical-headroom assessment. Preserve a separate conditional scenario result. Price a specific proposed measurement before requesting new work; never acquire it automatically.

In particular, hitting the search cap with no qualifying assignment reports a negative finite search and an unresolved global opportunity, not a proof. Distinguish this from provenance failure or absent cost evidence. O0/O2 positives cannot replace an O1 failure. Negative and inconclusive outcomes complete S1 within budget; they do not authorize more searches until success.

Examples: first three exploration canonical indices, plus largest positive and largest negative sentence-chrF difference between the O1 assignment and matched full-depth output (ties by index, then exit). Deduplicate; maximum five examples. If no positive/negative case exists, report that category absent; no replacements or development/final examples. Sentence metrics are diagnostic labels only. Do not use these examples to change search or infer a causal mechanism. Detailed mechanistic analysis belongs to S2A.

## 8. Numeric resource limits and accounting

| Stage | Numeric cap / boundary |
| --- | --- |
| S0A/S0B actual work | Documentation, literature and metadata/digests only; **0** S1 assignments, **0** encodings, **0** generator requests/sample-level evaluations/decoder forwards, **0** fits, **0** new final outcomes, **$0** paid services |
| Future S1 population | Exactly 128 exploration +64 development saved trajectories; 2,112 saved levels. **0** new trajectories, source retokenizations or model loads |
| Future S1 search | One algorithm, 3 operating points, <=10,000 complete assignments per split/point; <=60,000 total |
| Future S1 uncertainty | 10,000 shared identity resamples per split, 7 comparisons per split; **0** optimizer reruns inside resamples |
| Future S1 cost sensitivity | 45 scenarios x3 retained assignments x2 splits =270 scalar scenario evaluations; no new assignment search |
| Future S1 compute/storage/money | Existing CPU only, at most 4 compute threads, <=8 GiB analysis-process memory, <=512 MiB new durable artifacts, <=8 hours cumulative analysis wall time including failed attempts/resumes; **$0**, no paid compute or large downloads |
| Future S1 time allocation | <=2 hours implementation/integrity setup using synthetic checks, <=2 hours per split for scoring/search/uncertainty, <=2 hours reporting/validation; each subcap and total bind. No automatic transfer of unused subcaps |
| S2A boundary | Separate request needed; saved data only, **0** model calls/fits/new final access. Its quantitative diagnosis measures and CPU/storage budget must be frozen before that analysis; no S2A execution allocated now |
| S2B/S3/S4 boundary | **0** new model-work allocation here. Separate request and stage-specific protocol required before any new encoding/inference/profiling/fitting/training |

S1 model counters must remain zero for full encoder calls, generator requests, sample-weighted generator-level evaluations, decoder forwards, parity requests, inference warmups/repeats/retries and training. Metric scoring on saved text is offline CPU work; count it in search/bootstrap/time/storage, not as a model call. Interrupted scoring evaluations consume their slot and elapsed time. At most one resumed continuation from the last flushed ledger is allowed per split, sharing the original cap; no fresh restart, no replay of completed evaluations, no silent replacement of missing rows. Retain errors and pending assignment IDs so an uncertain interrupted evaluation can be marked consumed and skipped. Resource exhaustion closes the stage as bounded/inconclusive; an amendment is required before additional resources.

Any future S2B/S3/S4 protocol must separately enumerate reference encodings, generator input-requests, batch forward calls and sample-weighted levels, decoder forwards, prefix-embedding operations, warmups, forced-boundary/parity checks, repeats, failed attempts, interruptions/resumes and CPU fits. It must freeze wall time, storage, monetary cost, fresh-data eligibility and retry rules before execution. The roadmap's S2B default (32 encodings/352 decodes/zero generator requests) is a proposed ceiling, not permission or a complete execution protocol; extra parity work must be counted prospectively. Paid compute is excluded without explicit authorization.

## 9. Implementation acceptance and required artifacts

S1 implementation is deferred. Before applying it to real outcomes, use synthetic tests for mixed-corpus aggregation, exact budget exhaustion, deterministic ties, infeasible neighbors, complete/incomplete sweeps, receipt mismatch, no final access and numeric-coverage absence. Use no real-trajectory dry run during S0. Before development access, source-lock and commit/push the unchanged algorithm/metrics/access code and exploration ledger; verify remote equality. No new dependencies or model-based verifier runs are needed for S0 documentation.

Future outputs under new `results/stronger_research/s1/` only: `access.json`, `provenance.json`, `budget.json`, append-only search ledger, accepted/terminal assignment vectors and digests, fixed/policy replay metrics, corpus sufficient-statistic parity checks, cost sensitivity table, bootstrap seed/version/interval records, deterministic examples, termination/failed-attempt records and a summary with explicit gate and limitations. Preserve all original protocols, manifests, policy locks, empirical artifacts and completion/source snapshots. Do not overwrite historical JUnit or mutable compatibility evidence to make checks pass.

S0 completion checks: all new local documentation links resolve; the JSON population equals the exact manifest selections with no overlaps; inventory-protected evidence digests are unchanged; numeric search/sensitivity/bootstrap totals and quality margins agree across this protocol, its [machine-readable lock](stronger-research-protocol.json) and the roadmap; `git diff --check` passes; only authorized S0 files are staged. Record these checks under a new S0B validation receipt. Do not describe the historical 433 tests as rerun.

S0B is complete when these documents and checks are committed/pushed on main with local/remote equality, before outcome-dependent work. S1 is ready to be requested under this frozen protocol; its opportunity, cost adequacy and gate remain unknown.
