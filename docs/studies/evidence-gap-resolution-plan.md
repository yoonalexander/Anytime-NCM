# Evidence-gap resolution plan

Planning revision 1, October 24, 2026. Prepared against clean `main` at `fe0c931cc751b76b32860ada2c3fab2d59299cb3`, with local HEAD and GitHub main verified equal. This is a new prospective extension, not a revision of the completed S0-S5 experiments or their consumed budgets.

**Status: planning only. No experiment, fit, new input outcome, target encoding, contact or submission is authorized or performed by this document.** Stage-specific protocols, implementation checks and an execution request are required before real-data work. Numeric allocations below are proposed ceilings; unused allocations do not transfer between stages. A failed scientific gate cannot be waived by renaming the next stage.

Sources of truth: [roadmap](../../RESEARCH_ROADMAP.md), [current synthesis](../../RESEARCH_SYNTHESIS.md), [S1 protocol](stronger-research-protocol.md), [S1 results](../../results/stronger_research/s1/summary.md), [S2A diagnosis and timing proposal](../../results/stronger_research/s2a/summary.md), [identity/exposure inventory](stronger-research-inventory.md), and [submission issues](../../paper/stronger-research-v3/NOT_SUBMISSION_READY.md). Historical protocols and artifacts remain intact.

## 1. Questions and priority

The next cycle should determine whether an available early answer is economical to return, whether this opportunity survives a prospectively fixed diagnostic on additional inputs, and only then whether an online rule can recognize it. A negative or inconclusive answer is useful. More checkpoints/tasks, deeper search, target encoding and training are not default ways to rescue the hypothesis.

| Gap | Present evidence | Proposed resolution | Limit even after resolution |
| --- | --- | --- | --- |
| Arbitrary-exit cost | Full-depth historical timings; dimensionless savings estimate | E1 forced exits, then E2 measured assignment execution | Clairvoyant assignment timing is not deployed adaptive latency |
| Quality uncertainty and selection | Reused 64-input development assignment; failed conditional bounds | Lock a small pointwise retrospective rule family before new E2 outcomes; evaluate unchanged with multiplicity accounting | Confirms a diagnostic procedure, not a causal selector |
| Fresh confirmation | Original final data consumed; reserved data have aggregate-baseline exposure | E0 identity/exposure audit; separately reserve E2 audit, E3 development and E4 confirmation groups | Unknown model-training overlap and news-document dependence remain disclosed |
| Causal recognition / continuation value | Some early text matches its future final text; no continuation estimator | E3 only after opportunity and observable-signal gates; E4 locked online evaluation | Proxy quality labels do not certify semantics |
| Search optimum | Six truncated heuristic searches | Retain best-feasible terminology; avoid another optimization on confirmation | Global optimum remains unknown unless a separate valid certificate is produced |
| Mechanism | Several compatible explanations | Optional M1 only if one localization result would change a named decision | Target-vs-generated comparison alone is not causal attribution |
| Paper readiness | Checked internal manuscript | P1 human scientific review, authorship and rights decisions | No guarantee of novelty, venue acceptance or scientific success |

## 2. E0: freeze access and statistical feasibility before new outcomes

E0 is the next implementation prerequisite. It uses input-only metadata, existing evidence and synthetic statistical simulations; it permits zero new references, outputs or model work. Produce a new exposure ledger, disjoint input manifest, source/config lock, executable budget definitions and a stage-specific analysis protocol. Commit/push and verify remote equality before E1 or any new outcome access.

Proposed population: only the existing 1,979 WMT `reserved` effective-prefix groups from the [historical input manifest](../partitions/wmt14-phase4.json). Do not reclaim consumed final groups or the unused historical exploration/development groups as fresh confirmation. Check all later uses, caches, viewer bundles and analyst exposure against the ledger; a historical reservation alone does not establish eligibility.

Proposed allocation, after input-only eligibility/grouping checks:

| Role | Groups | Access release |
| --- | ---: | --- |
| E2 additional opportunity audit | 256 | After E1 engineering acceptance and the E2 source/protocol lock |
| E3 policy development | 128 | After E2 headroom and signal gates, and E3 protocol lock |
| E4 final policy confirmation | 1,024 | After E3 policy/config/source lock is committed, pushed and verified |
| Unallocated | 571 | Remains closed; no automatic replacement or expansion |

Before selecting rows, group effective-prefix aliases and any known document/duplicate links across old and new roles. Where document IDs are unavailable, record that limitation rather than claiming independent document sampling. Use input-only exact full-source duplicate checks when permitted by E0; no reference or model-output inspection for deduplication. Hashing entire files is not permission to deserialize forbidden rows. Shared Sudoku solutions remain excluded from this WMT-only extension.

Order eligible groups by SHA-256 of UTF-8 `anytime-ncm-evidence-gap-v1|` followed by the existing identity string, with canonical source index as tie break. Assign the next whole groups to roles in table order. The table assumes one effective-prefix identity per eligible group, as in the historical manifest. If newly discovered cross-role links or exposures change eligibility, stop before outcome release and amend counts/allocation prospectively; do not silently replenish or split clusters. No exact allowlist is created in this planning task.

All additional groups remain public-checkpoint evaluation data with disclosed prior aggregate baseline exposure. Call E4 fresh **policy confirmation relative to recorded analyst access**, not a new external test set or contamination-free evaluation. New domain/checkpoint generalization would be a separate study.

Statistical preflight: at most 24 synthetic scenarios, 1,000 simulated trials each, sample sizes 256/512/1,024, and 10,000 bootstrap draws for at most 12 representative synthetic datasets; zero real-outcome rescoring or new assignment optimization. Freeze scenarios before simulation, including zero/rare numeric coverage, correlated input groups, 0/2.5/5/10% latency changes, and quality at/inside/outside the declared margins. This checks implementation and precision sensitivity; it cannot establish real-data power. Do not select an enlarged final sample after viewing E2/E3 outcomes. If the available population cannot credibly resolve the declared margins, retain an explicitly exploratory study or stop; any different data acquisition needs a separate scoped plan.

E0 ceilings: four CPU threads, 8 GiB RSS, four cumulative wall hours, 256 MiB new artifacts, $0. No model loads, encodings, generator/decoder calls, fits or final outcomes. Freeze actual statistical formulas, interval directions, failure rules and random seeds before execution; unresolved method choices make the affected stage **not execution-ready**.

## 3. E1: bounded forced-exit timing pilot

Question: can the unchanged released checkpoint genuinely omit generator work and return a parity-checked output at lower ready-output latency, and how much does observing intermediate outputs cost?

Keep the previously priced S2A proposal unchanged:

- First 16 canonical identities in the already exposed 128-input exploration allowlist; never choose by output quality or timing.
- Forced depths `{1,4,7,10,11}`; terminal-only decoding and decoding at every visited level.
- Batch one, three paired repeats, two separately started model processes. Each process has 20 warmups, one for each of ten depth/schedule cells repeated twice; deterministic order recorded before running.
- Timed requests: `16 x 5 x 2 x 3 x 2 = 960`; warmups: `40`; total `1,000` generator requests. Sum of depths is 33, so total sample-level generator evaluations `6,600`. Terminal schedule needs `500` decodes; every-level schedule `3,300`; total decoder forwards `3,800`. No extra parity or model warmup requests outside these counts.
- Exact cached-prefix code/token/text parity is checked within those requests. Any mismatch closes inference before further scheduled work; no replacement examples or automatic retries. Successful early requests must show the intended generator evaluation count and no future suffix access.

Use the historical environment and local assets, with fresh integrity/environment receipts. Do not upgrade dependencies or patch upstream. Stop on missing assets or material drift requiring repair; price any repair/parity allocation before proceeding.

Ready-output time starts before source preprocessing/device transfer and ends after the returned CPU text is ready and pending device work is synchronized. Exclude checkpoint loading from per-request latency but report it separately. Include reconstruction, decoder work, transfers, feature preparation and schedule dispatch. Keep queueing, CUDA-event elapsed, instrumentation costs and process setup separate. Every method uses the same instrumentation. Capture raw times, output hashes, inspected levels, generator/decoder counters, failures and process identifiers. See [PyTorch 2.10 CUDA semantics](https://docs.pytorch.org/docs/2.10/notes/cuda.html) for asynchronous execution and synchronization; this does not authorize changing the pinned environment.

Freeze paired balanced method order with seed `20261025`. Give each identity equal weight; summarize repeats within identity/process before forming mean/median/p95 and depth/schedule contrasts. Report process-specific results alongside identity-paired intervals; two process starts cannot establish robust process-population or cross-hardware uncertainty. Use 10,000 shared identity resamples, no method selection in resamples. Treat pilot contrasts as descriptive engineering evidence, not confirmatory multiple-depth significance claims.

E1 caps: two cumulative wall hours including setup, execution, failed attempts and reporting; 256 MiB artifacts, existing hardware and $0; 0 encodings, 0 fits, 0 newly released input outcomes. E1 reuses already exposed inputs, so it supplies no fresh quality evidence.

Exit: parity/integrity failure -> stop and report engineering failure. Valid forced exits -> publish measured costs, including negative results. E2 can be considered if some genuinely skipped-work paths are cheaper and no unresolved measurement defect prevents interpretation. If none are cheaper, close this bounded route unless a separately justified cost-bottleneck amendment is accepted. Sixteen inputs cannot prove global absence of headroom. Never interpolate this pilot into a claimed actual speedup for the old 64-input assignment.

## 4. E2: fresh diagnostic rules, without a new corpus optimizer

E2 addresses selection uncertainty by fixing the **procedure** before seeing its inputs, rather than optimizing a new corpus assignment and bootstrapping it as if unselected. Its three retrospective rules use future output/reference information offline and are expressly not deployable policies.

Collect all 11 cumulative-prefix reconstructions once on the 256 E2 groups. Before any outcome access, lock these three rules, exact text normalization (saved decoded string equality, no extra normalization), sentence chrF implementation and the existing literal numeric/negation definitions:

| Rule | Earliest eligible level from 1 through 10; otherwise level 11 |
| --- | --- |
| O-exact | Decoded text is exactly equal to this input's level-11 decoded text |
| O-chrf0 | Sentence chrF is at least its level-11 sentence chrF; numeric F1 is no worse where defined; negation mismatch indicator is no worse |
| O-chrf05 | Same guards, with sentence chrF at least level-11 chrF minus 0.5 absolute points |

Sentence chrF is a selection feature for an offline diagnostic only. Recompute **corpus** BLEU/chrF for every retained rule; none of these local conditions guarantees corpus BLEU noninferiority. O-exact preserves the paired visible output and therefore all deterministic text quality metrics exactly, conditional on verified execution parity. It need not provide sufficient savings.

Do not tune thresholds, add rules, run coordinate descent, or select examples after E2 outcomes. Compute and time all 11 fixed depths alongside the three oracle rules. Full depth anchors quality tolerances; all potentially feasible fixed depths enter the cost gate under simultaneous uncertainty accounting. A later deployable frontier claim requires one fixed comparator selected on E3 development and locked before E4.

Execute each rule's preassigned exit with the **every-level observation schedule**, measuring real request latency. The assignment itself is clairvoyant: reference/future information used to choose a depth is available outside the timed request. Describe the result as measured execution cost of reference-informed assignments with charged observation work, never an online policy or end-to-end oracle-search latency. Offline collection, reference scoring and selection costs are recorded separately. This can establish diagnostic opportunity while leaving causal recognition unresolved.

E2 allocation: 256 trajectory-collection requests plus 14 timed methods (three assignments with every-level observation and 11 terminal-only fixed depths), two repeats in two process blocks: `256 + 256 x 14 x 2 x 2 + 140 = 14,732` total requests, including five warmups per method/process on already exposed E1 identities. Upper sample-level generator evaluations are `256 x 11 + (256 x 4 + 10) x (3 x 11 + 66) = 105,182`, where 66 is the sum of fixed depths 1 through 11. Upper decoder forwards are `256 x 11 + (256 x 4 + 10) x (3 x 11 + 11) = 48,312`: one terminal decode per fixed-depth request, at most 11 for each assignment request. Record lower actual counts too. No extra official-parity generation is available: use pinned historical official parity plus matched cached outputs within allocated requests. If additional official work is necessary, stop for a prospective budget amendment. All processes, including collection, count toward time/resource totals.

Gate statistics: use paired corpus differences and equal-weight identity latency ratios of means, keeping repeats nested within identity/process. Proposed 100,000 shared bootstrap draws, seed `20261026`; no reoptimization or changes to the three rules within resamples. Account prospectively for up to 89 primary intervals: 14 methods x four quality endpoints versus full = 56, plus three oracle rules x 11 fixed depths for latency = 33. Use conservative Bonferroni two-sided intervals with tail alpha `0.05/(2 x 89)`, since both feasibility and exclusion use interval directions. Include full-versus-itself redundancies without reallocating their alpha. Because the rules were fixed before these outcomes, this tests the fixed retrospective procedures; it does not correct the old S1 optimization or validate a causal policy. Bootstrap validity/precision, including these extreme quantiles, must pass E0's synthetic implementation checks; it is not an exact finite-sample guarantee. Unknown document clustering remains a limitation.

Keep the original tolerances: BLEU lower difference bound >= -0.5, chrF >= -1.0, numeric F1 >= -0.02 where defined, negation mismatch upper difference bound <= +0.02. Require point mean latency reduction >=5% with a positive adjusted lower bound. Sparse/undefined numeric coverage or degenerate resampling cannot silently count as a population noninferiority pass. E0 must freeze a conservative sparse-cue interval/fallback and minimum coverage; absent an adequate method/coverage, the nonidentical-output rule's gate is inconclusive. Exact paired text equality is distinguished from estimating a rare error rate.

E2 ceilings: four cumulative model-execution hours, four CPU analysis/reporting hours, 1 GiB artifacts, 8 GiB analysis RSS, four CPU threads, $0. Zero target encodings or fits. Failures consume slots, with no repeats beyond the schedule and no replacements. Any timeout closes the study as incomplete/inconclusive.

Exit: at least one rule must meet all applicable adjusted quality bounds, achieve >=5% point savings versus full with positive adjusted lower bound, and have positive adjusted cost-improvement lower bounds versus every potentially feasible fixed depth. A fixed depth can be excluded from this comparator set only when an adjusted interval places a quality endpoint wholly outside its tolerance (quality upper bound below the allowed loss, or negation lower bound above its allowed increase); otherwise include it. This avoids choosing the easiest fixed comparator after seeing outcomes. Sparse-cue or other comparator uncertainty remains conservative, rather than being treated as proof of infeasibility. Report whether only O-exact passes or tolerated changes contribute. No passing rule -> no-go for this rule family or inconclusive if uncertainty dominates; do not claim no possible assignment exists. A passing rule supports only bounded additional controller research. It is not a speedup claim, a global oracle optimum, or automatic satisfaction of S3's observable-signal requirement.

## 5. E3: conditional causal signal and controller development

Entry requires E2 headroom with no unresolved strong-fixed-comparator gap, an explicitly justified observable signal, a new E3 execution request and a frozen S3 amendment. Preserve the old failed/inconclusive gate and explain exactly which new evidence addresses it. No fits merely because E2 was completed.

The first E3 deliverable is a signal argument using only released exploration/E2 data: which available current/past feature could predict incremental benefit, what counterexamples it faces, and the cost of observing it. A prefix matching its future final text is a label, never a feature. If no testable causal feature family follows, stop here.

Proposed bounded controller study:

- Training: previously exposed 192 groups plus released E2 groups, grouped with any known aliases; E2 is now training/development evidence, not final policy confirmation.
- New E3 development: 128 reserved-role groups. All 11 prefixes may be collected only after feature/label/calibration definitions and source lock are frozen.
- Predict stop/continue incremental quality benefit and remaining cost under the actual inspection history, rather than current validity or eventual failure. A sentence-chrF utility target is a proxy for training; held-out corpus quality remains the decision criterion. Specify action horizon, utility scaling and cost coefficient before fitting.
- Primary schedule proposal `{4,7,10}`, with level 11 fallback. First observation has no prior stability comparison. Code-only features and any decoded-text features must be costed separately. Do not use references, future levels, final output, input identity or split membership as online features.
- At most six CPU fits and twelve complete candidate policies. Lock exact model family, feature transformations, regularization/seeds, calibration and candidate thresholds in the E3 protocol before fits; no hidden cross-validation/refits. Start with an interpretable small model. A neural NCM update is outside scope.
- Replay the twelve candidates on development once, then choose one using fixed quality/cost criteria and deterministic ties. Synthetic tests must cover history mismatch, future/reference/identity sentinels, real skipped work, exact budget exhaustion and forced-boundary parity.
- Compare full depth, a strong feasible fixed depth, one simple causal stability rule and the selected continuation controller. Select the fixed/stability comparators on E3 development and freeze them; do not replace them on E4.

E3 model-work ceiling: 128 full-trajectory requests, then four methods x 128 groups x 2 repeats x 2 process blocks, plus 40 warmups on exposed E1 identities = `2,216` requests; at most `24,376` sample-level generator evaluations/decoder forwards. Timed testing of extra candidates is excluded; candidate replay uses saved development outputs and labeled measured-cost estimates. Budget six CPU fits, four model-execution hours, four CPU implementation/analysis hours, 1 GiB artifacts, four CPU threads/8 GiB analysis RSS, zero target encodings and $0. These ceilings include parity, failed attempts and interruptions; no additional retries.

Development may use estimated costs to shortlist a policy, but the selected policy's online timing must be measured within the allocated requests. If it is structurally final-only, quality fails, or observation/controller costs erase the improvement, close E3 and keep E4 sealed. Passing development does not constitute fresh confirmation.

Exit lock must contain exactly one controller, three comparator specifications, source/protocol/weights hashes, feature and inspection histories, data identities, statistical code/seeds, missing/failure rules, all costs and the E4 access release. Commit/push and verify remote equality before any E4 outcome/reference read. No refitting after the lock.

## 6. E4: one fresh actual online comparison

Use the 1,024 reserved confirmation groups only if E0 establishes eligibility and E3 passes. Four methods: full depth, locked strong fixed depth, locked simple stability, locked controller. Use four separately started model-process blocks, two paired repeats and five warmups per method/block; `1,024 x 4 x 4 x 2 + 80 = 32,848` generator requests, with upper caps `361,328` sample-level generator evaluations/decoder forwards. All warmups use the already exposed E1 identities, never extra final inputs. There are zero target encodings, fits, extra trajectories or replacement samples. Each confirmation reference is materialized once under the release allowlist.

Freeze balanced paired ordering with seed `20261027`; quality uses one parity-checked output per method/identity. Repeats measure timing variation, not extra quality samples. Disagreement across repeats is an execution fault requiring retained failure evidence, not selection of the best repeat. No intermediate outcome-driven analysis, stopping for favorable significance or retuning. Operational failures may stop execution under the locked failure rule.

Require point ready-output mean reduction >=5% versus full, positive paired lower confidence bound, original quality margins with appropriate bounds, and a positive improvement over the strong feasible fixed comparator for an adaptive-frontier claim. If the selected fixed comparator fails its own final quality contract, report that result and withhold the frontier claim rather than select a new fixed depth on final data. The stable baseline remains a reported comparator even if it performs poorly.

Proposed final inference: 50,000 paired group resamples for corpus quality and crossed group/process-block resamples for timing, with process-specific sensitivity results and explicit limited four-block precision. Average repeats within each identity/block first. Two prespecified primary contrasts (controller versus full/fixed), five endpoints each; conservative one-sided alpha `0.05/10`. Numerical definitions, sparse-cue handling, interval construction and approximate-coverage limitations must be finalized in E0/E3 before E4 access. A simultaneous pass across the locked endpoints is required; unadjusted 95% summaries can accompany it, clearly labeled. If fixed/full are identical, keep the planned conservative correction; do not spend the freed comparison elsewhere.

Ceilings: six cumulative model-execution hours, four CPU reporting hours, 2 GiB artifacts, 8 GiB analysis RSS, four CPU threads and $0. Include feature extraction/reconstruction/controller runtime, device synchronization, memory, failures and all actual counts. Report mean/median/p95; primary estimand remains the ratio of equal-weight input means. Measure model memory consistently and separate optional instrumentation that would alter latency.

Record exactly one go/no-go/inconclusive decision. If uncertainty or rare-cue coverage is inadequate at 1,024, report it; do not open the remaining 571, add repeats or collect another test set until the hypothesis passes. No causal mechanism, broad task generalization or factual-safety claim follows from a positive WMT comparison.

## 7. Optional M1 mechanism localization and historical discrepancy

Keep S2B and S4 deferred unless a specific mechanism question changes a decision. Before M1, state competing predictions, the control and the actionable interpretation of each outcome. If all outcomes merely suggest more experiments, do not run it.

An eligible target-encoding M1 would use the first 32 already exposed exploration identities, 32 full target encodings, 352 prefix decoder forwards and at most 32 matched final-path parity decodes: maximum 384 decoder forwards, 32 encoder sample evaluations, zero generator requests/fits/new-final access. Cap two model-execution hours, two CPU reporting hours, 256 MiB artifacts and $0. Count parity/warmups within those ceilings; no extra warmups are allocated. Freeze preprocessing, batch/path matching, lossy-reference fidelity criteria and code-state isolation before execution. This localizes representation/decoder versus generated-code differences; it cannot alone establish a cause or justify a training intervention.

A later S4 intervention requires its own request and prospective compute/data/control budget; **zero training allocation is proposed here**. Do not bundle decoder changes with generator training.

The hard-Sudoku 86.25% versus published 86.1% discrepancy can receive one saved-metadata/protocol/aggregation review, capped at two CPU hours/64 MiB/$0, with zero raw new outcomes or model work. Compare documented denominator, rounding, acceptance and source versions. If no explanation follows, preserve the discrepancy. No rerun or tuning to reproduce the published aggregate is necessary for the WMT decision.

## 8. P1: independent review and publication decisions

This can proceed alongside E0/E1 without new experiments. Prepare a local review packet with the manuscript, claim-to-evidence table, frozen protocols, analysis verification limits, failure/attempt ledgers and a short list of questions: Does the oracle interpretation hold? Are quality uncertainty and data exposure represented correctly? Is the contribution sufficiently focused? Which causal claims are unsupported?

A human author must identify/authorize any reviewer contact, confirm authors/affiliations and responsibility, resolve project/data/model redistribution rights, and select a license. Do not infer these from a GitHub account. External review is genuinely independent only if another researcher performs it; another same-assistant calculation pass is not a substitute. Reviewer availability/timing cannot be guaranteed. No contacts, uploads, endorsement requests or submission are included in this plan.

Revise the manuscript when a stage closes, retaining prior versions and source receipts. If the cycle closes negative/inconclusive, center the contribution on the bounded evidence and limitations; do not automatically enlarge the experiment. Recheck venue requirements only when an authorized submission is concrete.

## 9. Execution records, budgets and readiness

For each future stage, create new paths under `docs/studies/evidence-gaps/` and `results/evidence_gaps/<stage>/`: frozen protocol/input/source lock, append-only request/fit ledger, environment/provenance receipt, raw records, independent calculation checks, gate decision and concise summary. Refuse overwrites. Every attempted/failed/warmup/parity request consumes its slot. No automatic restart or resume; any recovery plan shares the original cap and must be recorded before continuation. Time caps include failed attempts; coding tests use synthetic fixtures before model access. Preserve upstream and original empirical artifacts.

Proposed model-work maximum within the listed E1-E4 allocations, if every gate passes: `1,000 + 14,732 + 2,216 + 32,848 = 50,796` generator requests; `6,600 + 105,182 + 24,376 + 361,328 = 497,486` sample-level generator evaluations; `3,800 + 48,312 + 24,376 + 361,328 = 437,816` decoder forwards; at most six CPU fits; zero target encodings/training. Optional M1 separately adds 32 encodings and 384 decodes, not generator work. These are ceilings, not predicted runtime or permission to consume every stage. No paid compute, downloads or environment rebuilds are budgeted.

Stop on missing identity eligibility, incompatible model/source/config hashes, parity failure, insufficient resource/statistical feasibility, a failed entry gate or a consumed cap. Record whether the result is engineering failure, bounded no-go or scientific inconclusive. Commit/push each completed stage and verify local/remote equality before releasing the next role.

**Ready now:** this planning document and its documentation checks. **Next requestable work:** E0 protocol/access/statistical preflight, followed by E1 only under its accepted execution protocol. **Not execution-ready today:** E2-E4 (eligibility, detailed statistical/sparse-cue procedures, feature/model specifics and stage locks outstanding). M1/S4 remain deferred; P1 requires human decisions. This plan deliberately does not promise that every evidence gap can be resolved within the available data or that all gates will pass.

## Primary methodological references

- [PyTorch 2.10 CUDA semantics](https://docs.pytorch.org/docs/2.10/notes/cuda.html): device execution is asynchronous; synchronization is essential to distinguish ready-output wall time from enqueue time. Checked October 24, 2026; use the pinned environment, not a documentation-driven upgrade.
- [SacreBLEU upstream documentation](https://github.com/mjpost/sacrebleu#paired-significance-tests-for-multi-system-evaluation): metric signatures and paired multi-system comparisons. Keep the recorded 2.6.0 implementation; proposed multiplicity/access rules above are this study's design, not guarantees supplied by the package.
- [Koehn 2004, Statistical Significance Tests for Machine Translation Evaluation](https://aclanthology.org/W04-3250/): primary motivation for paired corpus bootstrap in MT. It does not validate an outcome-optimized oracle, guarantee power at the proposed sample sizes, or solve unknown document dependence.
