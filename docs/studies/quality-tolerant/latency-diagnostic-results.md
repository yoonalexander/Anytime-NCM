# Sparse assigned-exit actual latency: completed exploratory diagnostic

October 28, 2026 (Toronto). **The frozen Q1 E2 assignment saved 9.165% actual mean ready-output time.** Assigned sparse exits averaged 126.818ms versus 139.613ms for native full depth. The conditional paired nominal interval is [5.982%, 12.558%]; observed session savings are 9.243% and 9.083%.

Decision: `measured_assigned_exit_headroom`. This meets the predeclared exploratory timing screen on these consumed inputs. It establishes measured assigned-exit headroom under the executed sparse schedule, with no predicted controller costs. It does not pass Q0, demonstrate an online selector, certify quality for unseen inputs, or satisfy the whole project's confirmation contract.

## Locked execution and interpretation

[Protocol](latency-diagnostic-protocol.md), [numeric lock](latency-diagnostic-lock.json), [source lock](latency-diagnostic-source-lock.json). Commit `9f1841af30d5e9a49f0172f95ae90d9348731ef6` was pushed with verified live remote equality before synthetic checks, saved assignment/trajectory body access or checkpoint loading. The final mathematical Q0 no-go and all historical gates remain intact; this was an explicitly authorized exploratory entry exception.

Exactly 256 consumed E2 representatives; the previously selected `[8,10,11]` assignment has 94 exits at 8,60 at 10 and102 at 11. No assignment search or fitting occurred. Observations are [8], [8,10] or [8,10,11] according to the forced exit. Each executed observation includes learned cumulative reconstruction, decoding, ID transfer and text rendering. Every generated prefix and every observed output matched the saved E2 counterpart. Saved Q1 quality point scores can therefore be reused without reference decoding.

Two separate processes, two timed repeats per input/method/process, 12 methods, five fully charged warmups per method/process. Every method has 1,024 timed requests;12,288 timed requests plus 120 warmups yield12,408 total. Native full uses the upstream generator; fixed 1-10 decode once at their terminal depth. Sparse paths skip unused observations and generation after the assigned exit. The timer includes source tokenization, reconstruction, all scheduled decoding/transfers, Python observation work and final synchronization. Parity hashing, identity prechecks, model loading and fingerprints are outside request timing. CUDA span is reported separately.

## Actual ready-output measurements

All values below are milliseconds. Median/p95 pool the balanced timed requests; session means are recorded separately in the [analysis](../../../results/quality_tolerant/latency_diagnostic/analysis.json).

| Method | Mean | Median | p95 | Saved point-quality screen |
| --- | ---: | ---: | ---: | --- |
| assigned_sparse | 126.818 | 129.832 | 157.054 | pass |
| fixed:1 | 16.222 | 15.662 | 19.440 | fail |
| fixed:2 | 29.214 | 28.404 | 33.951 | fail |
| fixed:3 | 41.495 | 40.376 | 48.011 | fail |
| fixed:4 | 54.087 | 52.659 | 63.030 | fail |
| fixed:5 | 67.170 | 65.121 | 77.870 | fail |
| fixed:6 | 79.290 | 77.475 | 90.458 | fail |
| fixed:7 | 91.548 | 89.231 | 105.001 | fail |
| fixed:8 | 103.846 | 101.104 | 119.905 | fail |
| fixed:9 | 115.872 | 113.066 | 132.858 | fail |
| fixed:10 | 127.757 | 124.804 | 144.843 | fail |
| fixed:11 | 139.613 | 136.212 | 160.595 | pass |

All 11 fixed-depth contrasts were retained; no fixed depth was statistically excluded. Full depth is the only fixed control passing the saved Q1 point screen. A point-screen failure is not an adjusted quality exclusion for the eventual confirmation comparison.

| Control | Sparse saving relative to control | Conditional nominal interval |
| --- | ---: | ---: |
| fixed:1 | -681.765% | [-709.337%, -653.376%] |
| fixed:2 | -334.102% | [-349.734%, -317.905%] |
| fixed:3 | -205.618% | [-216.160%, -194.515%] |
| fixed:4 | -134.470% | [-142.670%, -125.762%] |
| fixed:5 | -88.802% | [-95.450%, -81.807%] |
| fixed:6 | -59.941% | [-65.705%, -54.042%] |
| fixed:7 | -38.526% | [-43.258%, -33.388%] |
| fixed:8 | -22.121% | [-26.402%, -17.610%] |
| fixed:9 | -9.447% | [-13.274%, -5.498%] |
| fixed:10 | 0.735% | [-2.805%, 4.422%] |
| fixed:11 | 9.165% | [5.982%, 12.558%] |

Intervals use exactly 20,000 paired whole-document/alias-component bootstrap draws across 116 represented components. Repeats and the two observed sessions are averaged within input and held fixed. Component totals preserve input weighting; shared resampling indices pair all 12 methods. The nominal two-sided family uses 11 contrasts and tail .05/22; conservative rank 22 adds the declared .001 aggregate Monte Carlo rank-error allowance. These are approximate, conditional exploratory intervals under the declared independent/exchangeable component assumption. They do not capture cross-hardware/process-population uncertainty, all temporal timing dependence, or selection uncertainty from Q1. No quality bootstrap or fresh quality inference was run.

Session 0 sparse/full means: 129.848/143.071ms; session 1: 123.788/136.154ms. Absolute timings changed between sessions, while the saving remained positive. Both sessions use RTX 5060, driver 610.88, Python 3.12.3, torch 2.10.0+cu128/CUDA12.8, transformers 4.57.6, float32/eval,4 CPU threads, matmul TF32 off/cudnn TF32 on. Background system load is uncontrolled. The new full-depth mean is a contemporaneous control; historical E2 latency is not substituted into this comparison.

The arithmetic budget remaining before savings fall below 5%, at this identical assignment and observed means, is 5.814ms per input. A controller must still choose suitable exits and pay its own measured feature/decision costs. This number is not a measured controller latency or a guaranteed allowance for a different exit distribution.

## Reused quality point estimates

| Full-relative loss | Frozen assignment | Original allowed margin |
| --- | ---: | ---: |
| Corpus BLEU | 0.496316700 | 0.5 |
| Corpus chrF | 0.999449059 | 1.0 |
| Numeric-reference mean F1 | 0.000000000 | 0.02 |
| Negation-mismatch increase | 0.007812500 | 0.02 |

The numeric endpoint covers 48/256 references. BLEU and chrF losses are close to the allowed margins. These are the already consumed, search-selected Q1 corpus scores, preserved exactly through output parity. They give no new independent quality evidence or semantic correctness guarantee. The original quality uncertainty problem remains unresolved; the final bounded math review's no-go is unchanged. No E3/E4 model outputs were opened. Previously disclosed aggregate reference/metadata exposure remains disclosed.

## Validation, actual resources and delivery

19 focused synthetic tests passed before checkpoint loading. They check independent intermediate reconstruction, skipped generator/decoder work, causal current-prefix callbacks, full/partial parity, invalid/training-mode rejection, enforced forward limits, complete paired scheduling, unequal document weights, alias transitivity, null/5%-boundary/negative contrasts, missing data and inadequate coverage. Toy charged work was 6 requests, 59 generator levels, 19 decoders, 0 encoders; expected rejected calls are retained in the test log. No whole historical test suite was rerun, and no released checkpoint was used by the synthetic tests.

| Resource | Actual | Frozen cap |
| --- | ---: | ---: |
| Model requests including warmups | 12,408 | 12,408 |
| Generator levels | 78,228 | 79,618 |
| Decoder examples | 13,469 | 14,476 |
| Encoder examples / target encodings / fits | 0 / 0 / 0 | 0 / 0 / 0 |
| Source-prefix calls including prechecks | 12,920 | 12,920 |
| Selected source materializations | 512 | 512 |
| Old E2 trajectory bodies decoded | 256 | 256 |
| Reference bodies decoded / new inputs | 0 / 0 | 0 / 0 |
| Model orchestration seconds | 1122.491 | 7,200 |
| Total execution seconds | 1151.228 | 9,600 |
| Parent peak RSS bytes | 406,237,184 | 8,589,934,592 |
| Worker peak RSS bytes | 2,819,457,024 | 17,179,869,184 |
| Peak GPU reserved bytes | 1,279,262,720 | 8,589,934,592 |
| Execution artifact bytes before reporting | 18,829,261 | 1,073,741,824 |
| Bootstrap draws / automatic retries / paid dollars | 20,000 / 0 / 0 | 20,000 / 0 / 0 |

Model states were unchanged in both processes. The frozen verifier passed 20 artifact and 935 protected-history hash checks, all 12,408 request/work receipts, source hashes and state checks without replaying outcomes or inference. An additional [completion review](../../../results/quality_tolerant/latency_diagnostic/completion-review.json) cross-checks every recorded generated-prefix/observed-output hash against the derived parity cache and confirms budgets. This is scripted verification, not an independent replication. Reporting has a separately declared conservative 21,600-second allowance; it is not request latency. No failures or retries occurred.

## What this changes and what comes next

The project now has actual latency evidence that one previously selected quality-tolerant offline assignment can exceed the 5% time target after charging its sparse observations. This closes the estimated-versus-measured-cost question for this assignment, consumed population and hardware setup. It does not establish a deployable policy or generalization.

The next possible engineering study is a separately bounded causal controller feasibility experiment: learn or specify when to stop using current/past-only information, then measure that complete controller against the same full/fixed controls. It requires its own authorization, data allocation, prospective protocol and costs. Independent quality confirmation also requires a defensible new population/statistical route; it cannot reuse this consumed assignment as confirmation or treat the failed Q0 route as passed. This milestone ends here, with no fitting or reserved-output release.

[Execution receipt](../../../results/quality_tolerant/latency_diagnostic/execution.json), [decision](../../../results/quality_tolerant/latency_diagnostic/decision.json), [artifact guide](../../../results/quality_tolerant/latency_diagnostic/README.md). Primary measurement/bootstrap references and their limitations are recorded in the prospective protocol. Historical evidence, protocols, artifacts and failed gates remain intact.
