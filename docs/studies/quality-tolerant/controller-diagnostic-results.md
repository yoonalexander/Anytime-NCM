# Controller failure diagnosis: completed

October29 UTC / October28 Toronto,2026. **The evidence points to weak fitted ranking and sparse cue supervision, rather than observation cost alone.** All nine original calibration candidates reproduced exactly. No weights were fitted, no model library/checkpoint/GPU was loaded, and the former 87-input evaluation outcome bodies were not reopened.

The predeclared recommendation is `richer_causal_signal_study`: investigate richer current-state signals before another controller fit. A concrete [signal-pilot proposal](causal-signal-pilot-proposal.md) is prepared, with parity/cost checks before training. It is planning only; the present diagnostic stops here. The diagnosis does not prove that the raw features contain no signal or establish that a richer model will succeed.

[Prospective protocol](controller-diagnostic-protocol.md), [numeric lock](controller-diagnostic-lock.json), [source lock](controller-diagnostic-source-lock.json). Lock `118e0408f4533783b0b8b1f243174ac095a7485f` was pushed and live remote equality verified before synthetic tests or outcome access. All historical protocols, models, receipts and failed gates remain unchanged. Q0 remains failed; Q4 is not ready or released.

## Observed prediction and supervision limits

Exactly 260 old fit inputs and 101 old calibration inputs, in 66/33 disjoint source-document/alias components, were revisited. Numeric coverage is 58 fit/20 calibration; no new quality samples were acquired. Every statistic is descriptive on consumed development data, with no p-values, inference or multiplicity-adjusted significance claim.

| Calibration diagnostic | Level 8 | Level 10 |
| --- | ---: | ---: |
| Joint adverse-loss ranking AUC | 0.274510 | 0.509426 |
| Proxy-safe / proxy-unsafe inputs | 17 / 84 | 40 / 61 |
| Inputs rejected at the largest original threshold 4 | 101 /101 | 84 /101 |
| Dominant BLEU / numeric prediction among rejections | 60 /41 | 71 /13 |
| Constant training features out of 19 | 7 | 3 |
| Fit negation-change labels with nonzero value | 0 /260 | 0 /260 |
| Adverse calibration negation-change labels | 4 /101 | 2 /101 |

AUC uses higher predicted benefit-of-continuing as the positive/adverse direction; ties count half. AUC 0.5 is the descriptive random-order reference, not a significance threshold. 0.2745 at 8 and 0.5094 at 10 show that these particular combined predictions did not rank low-loss exits effectively on this calibration split. Small class counts, prior consumption, model/target choice and document composition limit interpretation. Post hoc sign flipping would be a new tuned policy; no such policy was created.

Individual BLEU/chrF adverse-ranking AUCs were 0.527/0.487 at 8 and 0.504/0.467 at 10. Numeric AUCs were 0.495/0.353on 20 covered calibration references. The retained [prediction diagnostics](../../../results/quality_tolerant/controller_diagnostic/run/prediction-diagnostics.json) include all target quantiles, bias/MAE/MSE, comparison with the training marginal mean, and feature-shift counts. Several regressions did not improve squared error over that simple descriptive mean reference; prediction error and ranking are different diagnostics, neither a confidence bound.

All 260 fit negation-change targets were exactly 0 at both levels. The resulting head had no varying supervision for that particular endpoint, while calibration contained 4 and 2 adverse changes. Better features alone cannot add missing training examples. This does not imply absolute translations had no negation errors; the labels are differences between early and full reference-mismatch outcomes.

At level 8 the BLEU/numeric predictions rejected all 101 inputs at threshold 4. At 10, numeric predictions alone vetoed 5 of 81 reference-uncovered rows. This is an offline domain-use diagnostic: the numeric regressor was fitted on reference-covered inputs but used in a joint gate everywhere. Reference coverage was never an online feature. Dropping a guard or replacing the reference-defined endpoint with source-number coverage would not be justified. All four endpoint-omission controls failed the unchanged corpus point-quality screen; none produced an exit at 8.

## Opportunity remains when future labels are supplied

The five frozen perfect-label controls substitute known future/reference proxy outcomes for fitted predictions. They are clairvoyant, nondeployable controls, not trained controllers, certified optima or measured speedups. All five meet the unchanged calibration CORPUS point margins; estimated costs use the prior fixed-depth profiles and observation proxy.

| Perfect-label threshold | Exit 8 /10 /11 | BLEU loss | chrF loss | Numeric /negation loss | Estimated saving at original observation cost |
| --- | ---: | ---: | ---: | ---: | ---: |
| 0.0 | 11 /17 /73 | -0.197052 | -0.412492 | 0.000000 /0.000000 | 1.739% |
| 0.5 | 12 /26 /63 | -0.188568 | -0.392039 | 0.000000 /0.000000 | 2.917% |
| 1.0 | 17 /26 /58 | -0.179742 | -0.344922 | 0.000000 /0.000000 | 4.337% |
| 2.0 | 23 /31 /47 | -0.152441 | -0.154166 | 0.000000 /0.000000 | 6.538% |
| 4.0 | 34 /27 /40 | -0.008781 | 0.263251 | 0.000000 /0.000000 | 9.266% |

Threshold 2 meets the point margins with 6.538% estimated saving; threshold 4 with 9.266%. Thus this narrow perfect-label family can retain point quality and exceed 5% under the declared cost model on the same 101 calibration inputs where the learned candidates failed. It is a diagnostic separation between available quality-tolerant opportunities and the current fitted scores; it does not show that current/past-only information can identify those opportunities.

The BLEU/chrF targets are per-input proxies, not exact decompositions of the corpus contract:

| Fixed level / endpoint | Mean sentence proxy loss | Actual preserved corpus loss |
| --- | ---: | ---: |
| 8 /bleu | 6.698700 | 8.764958 |
| 8 /chrf | 7.910091 | 8.595475 |
| 10 /bleu | 3.340808 | 4.071685 |
| 10 /chrf | 3.412365 | 3.542952 |

The synthetic metric check also demonstrates nonadditivity. [BLEU's original corpus formulation](https://aclanthology.org/P02-1040/) and [chrF's original definition](https://aclanthology.org/W15-3049/) provide primary background. This mismatch is a design limitation, but the perfect-label controls show that it does not by itself prevent every useful assignment in the tested family. It does not establish why the linear predictions failed.

## Cost estimate is imperfect, but not a sufficient explanation

None of the ORIGINAL quality-passing candidates reaches 5% estimated saving even when additional observation/decision cost is set to 0 in the frozen fixed-profile scenario. That scenario is an optimistic approximation, not a proven upper bound on actual per-input execution. It nevertheless shows that simply reducing the observation surcharge does not rescue the original estimates. No new GPU benchmark of an unselected candidate was run.

The prior Q2 paired timing audit used 195 permitted fit/calibration E2 inputs, 780 paired input/session/repeat cells and 9,452 timing bodies including 92 warmups. Other inputs' bodies were skipped after metadata-header inspection. The residual sparse_ms - [terminal_ms + (observations - 1)*proxy_ms] had bias 1.127 ms and MAE 4.897 ms. By-depth mean residuals were -0.039 ms at 8, 1.215 ms at 10, 2.105 ms at 11. Positive means the approximation underestimated actual sparse execution on that reused subset. Those are noisy old paired measurements, not an isolated decoder-cost measurement, a new confidence interval or controller-cost validation.

## Completed bounded work and checks

13 synthetic deterministic tests passed before real-data access: rare/absent classes and ties, ranking direction/null, missing numeric labels, threshold boundaries, sparse fallback costs, order-independent header filtering with poisoned bodies, duplicate/missing timing cells, all recommendation branches, constant/outlier features and corpus nonadditivity. No real model or fit was used by these tests. No broader historical test suite was rerun.

| Work/resource | Actual | Cap |
| --- | ---: | ---: |
| Source/reference/trajectory materializations, each | 361 | 361 |
| Sentence-label pairs | 1,083 | 1,083 |
| Feature /decision calls | 924 /808 | 1,000 /808 |
| Original scalar policy-input replays | 404 | 404 |
| Diagnostic assignments /corpus calls | 18 /18 | 18 /18 |
| Frozen cost-grid evaluations | 72 | 72 |
| Timing headers /selected bodies | 12,408 /9,452 | 12,408 /12,408 |
| Wall /parent CPU seconds | 23.951 /5.647 | 1,800 /900 |
| Parent peak RSS bytes | 172,314,624 | 2,147,483,648 |
| Artifacts before reporting bytes | 1,908,135 | 134,217,728 |
| New fits /model loads /GPU requests /target encodings | 0 /0 /0 /0 | 0 /0 /0 /0 |
| Bootstrap /permutation draws /retries /paid dollars | 0 /0 /0 /0 | 0 /0 /0 /0 |

The receipt verifier passed all source, 1,014 historical-file and artifact  hashes and caps without data-analysis replay. An additional [completion review](../../../results/quality_tolerant/controller_diagnostic/completion-review.json) checked 1,102 hashes and output/coverage/accounting consistency, with 0 new fits/model calls/original body reads. This is scripted verification, not independent replication. All nine original calibration exit histograms, losses, point decisions and costs reproduced within the frozen tolerance. The former 87evaluation outcome bodies and all reservations remain closed in this subphase; prior exposure is still disclosed. Reporting has a separate conservative 7,200-second allowance, not analysis time.

## Recommended next unit and limits

The prospective decision tree selected a richer causal-signal study because a point-quality-feasible perfect-label control exceeds 5% estimated saving while level 8 joint-ranking AUC is below the declared 0.65 development heuristic. This is a practical routing rule, not inferential evidence that the next approach will work.

The prepared [pilot proposal](causal-signal-pilot-proposal.md) focuses on current decoder confidence/logit information and literal source/current number preservation, with a small parity/overhead pilot before another fit. Any future supervised rare-cue head must explicitly handle absent adverse examples; a constant-zero regressor is not learned rare-event protection. Model calibration, corpus-objective alignment and the conditional numeric population also remain design questions. We cannot yet identify whether richer features, another learner, additional eligible development examples or a different objective is the necessary fix.

No new controller was selected, no guard/tolerance was weakened, and no weight was retrained. Existing 9.165% Q2 actual assigned-exit headroom remains unchanged; the 9.266% perfect-label figure here is an ESTIMATE on a different development subset. No real adaptive speedup or independent quality confirmation is added by this audit. Q0 remains failed and Q4 is not ready. Stop before revised fits, new profiling or reserved-output access, as prospectively declared.

[Execution](../../../results/quality_tolerant/controller_diagnostic/run/execution.json), [decision](../../../results/quality_tolerant/controller_diagnostic/run/decision.json), [all diagnostic controls](../../../results/quality_tolerant/controller_diagnostic/run/diagnostic-assignments.json), [prediction diagnostics](../../../results/quality_tolerant/controller_diagnostic/run/prediction-diagnostics.json), [cost audit](../../../results/quality_tolerant/controller_diagnostic/run/cost-proxy-diagnostics.json).
