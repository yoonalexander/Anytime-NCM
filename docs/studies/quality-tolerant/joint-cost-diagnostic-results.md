# Phase05 actual causal-controller timing: 4.16%, below target

October29,2026. **The unchanged richer-feature controller saved4.161%actual mean ready-output time on its101consumed calibration inputs, below the5%target.** Both observed sessions were faster and the conditional nominal paired interval was positive. This demonstrates a limited causal-controller timing gain on selected development inputs, not independent quality preservation or completion of the original success contract.

[Prospective protocol](joint-cost-diagnostic-protocol.md), [numeric lock](joint-cost-diagnostic-lock.json), [source lock](joint-cost-diagnostic-source-lock.json). Lock915ea2e076e56bf30b6c9d036f1e93f077cbe688 pushed with live equality before tests/model work. Exact [policy](../../../results/quality_tolerant/campaign_20261029/joint_controller_selection/policy.json) was already pushed in phase04. Its failed4.289%estimated-saving gate is unchanged; this separately locked calibration-only diagnostic resolved cost without opening87evaluation inputs or changing thresholds. [Analysis](../../../results/quality_tolerant/campaign_20261029/joint_cost_diagnostic/analysis.json), [decision](../../../results/quality_tolerant/campaign_20261029/joint_cost_diagnostic/decision.json), [execution](../../../results/quality_tolerant/campaign_20261029/joint_cost_diagnostic/execution.json), [review](../../../results/quality_tolerant/campaign_20261029/joint_cost_diagnostic/completion-review.json).

## Actual cost and retained quality points

| Method | Mean ready-output ms | Median ms | p95 ms | Session0/1 mean ms |
| --- | --- | --- | --- | --- |
| Causal rich8-only guarded policy | 138.790975 | 144.970220 | 159.309893 | 138.642994/138.938955 |
| Native full/fixed11 | 144.817283 | 143.487633 | 157.182478 | 144.021451/145.613114 |
| Fixed8 | 107.039238 | 106.153901 | 117.685597 | 106.325414/107.753063 |
| Fixed10 | 132.232721 | 131.714232 | 144.224185 | 131.042773/133.422668 |

Saving versus full4.161318%; session savings3.734483%/4.583487%. Eleven-contrast Bonferroni nominal conditional interval[0.651905%,7.886619%]from20,000paired whole-component draws,33document/alias components, observed sessions/repeats held fixed. Existing conservative binomial rank22/20000with Monte Carlo rank-error allowance.001was used. These approximate intervals require appropriate independent/exchangeable component assumptions and do not resolve temporal dependence, process-population stability or prior selection. They are not independent quality bounds. All11fixed-depth timing contrasts are retained, including faster controls; no adjusted quality exclusion is claimed for them. The original requirement to outperform all potentially feasible fixed depths has not been established.

Exactly23/101inputs exit at8,78fallback directly to11without10inspection. Actual generation/reconstruction/decoding/transfers/current features and scalar decisions are inside the ready-output timer. Original selected calibration corpus point losses remain .484309734BLEU/.644695808chrF/0numeric-reference F1/0negation; no new reference was read or metric rescored. Numeric coverage20/101, fit negation-change targets all0in the prior260fit inputs. Literal guards and raw-logit scores are not semantic guarantees, calibrated probabilities or learned rare-cue protection. The same calibration data selected the policy, so these quality points are development evidence.

## Work and independent verification

Two distinct local CUDA processes, two timed repeats per input/method/session, five warmups per method/session.4968real requests(4848timed+120warmups),31596generated levels,5288decoders,0encoders/target encodings/fits/new families.414each current feature/logit/cue/decision calls,5170source-prefix calls,202source strings,0new old-trajectory/reference bodies.366prior feature records were used to select101current vectors for post-timer validation; future/reference data never enter the online adapter. All observed outputs/final prefixes and414actual current8prefixes/features match the prior cache; actual skipped work and released states verified. Model checkpoint states match across processes.

4focused synthetic cases passed first: actual8stopping/full fallback, exact prefix/final text, unchanged states/cleanup and work counters; complete paired8-only schedule; unequal-cluster totals/null/5%boundary; missing/duplicate/inadequate-component rejection before resampling.4toyAPIattempts including one rejected training-mode call,30toy generated levels/4decodes,0real checkpoint loads by tests. No historical full suite was rerun.

Saved verifier passed. An independent pure-Python review checked1154protected historical files, all4968requests/4848timed cells,414current-feature/prefix receipts,5288observations, all12mean/session summaries and4test cases without model calls, original outcome rereads or a second bootstrap. The frozen interval computation and rank receipt remain bound to execution source; no new resampling was performed.

Real model orchestration492.600sec; total515.856sec; phase CPU charge477.740sec plus300reporting credit. Model-wall charge1098.442sec additionally includes the whole5.842sec synthetic-test process and an explicit600sec conservative allowance for earlier phases01/02synthetic ceilings. That allowance is not a claim600sec actually ran; earlier immutable receipts are preserved. Cumulative campaign charges6295model attempts,1437.982model seconds,2297.526CPU seconds,4real fits/1family,320MiBartifact credit,$0. Real artifacts remain far below credits/2GiBceiling. No retries, paid resources, evaluation87or reservation release.

## Decision and remaining branch

`controller_insufficient_savings`: the actual mean misses5%despite a positive conditional lower bound. Preserve this negative target result and the earlier estimated-cost failure. Do not tune this selected policy against the measured timing, open evaluation87under the failed branch, or interpret consumed point quality as confirmation. Q0 remains failed.

The next bounded branch should first assess the available eligible DEVELOPMENT population and sparse-cue supervision before spending the remaining controller family. A new official/free development allocation is authorized only with prospective eligibility/document/exposure/access caps; confirmation allocations stay separate and sealed. That audit does not itself add quality evidence. If a defensible development extension is unavailable, consider a prospectively justified family2study using existing data or close out the campaign. Do not run indefinitely or claim all controllers impossible.

Saved verification:

~~~powershell
.\scripts\wsl_python.ps1 -PythonArguments @('scripts/run_joint_cost_diagnostic.py','verify')
~~~
