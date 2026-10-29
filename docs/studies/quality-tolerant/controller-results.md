# Q3 exploratory causal controller: completed negative screen

October28 Toronto / October29 UTC,2026. **The bounded controller family did not yield a selected early-stopping policy.** Calibration selected native full depth. The locked choice reached 11 on all 87 test inputs, with 0 early exits. Decision: `controller_no_early_exits`. This completes the authorized experiment; Q4 is not ready or released.

Selected-policy ready-output mean was 143.693ms versus 143.670ms for the native full control: saving -0.016%, conditional nominal paired interval [-1.386%, 1.047%]. Both methods execute full depth; small timing differences are not adaptive benefit. The 5% goal was not met.

## Prospective separation and completed work

[Protocol](controller-protocol.md), [numeric lock](controller-lock.json), [source lock](controller-source-lock.json), [document/alias split](controller-split.json). Protocol/source commit `3ab82760e02746192bc1adda5ac3d546ca0c45c4` was pushed and live-main equality verified before tests, outcome access or fitting. Selected policy/development evidence commit `31f41d949d2091f307cc3b7bac88bbcf18e500e4` was pushed and verified before this study decoded test outcomes or references. All earlier exposure remains disclosed.

Exactly 448 already consumed inputs were divided by 132 source-document/alias components: fit 260/66 components, calibration 101/33 components, evaluation 87/33 components. Numeric-covered counts were 58/20/14. No identities or components cross roles. These are newly separated roles within previously studied data, not independent confirmation or a fresh test set. Unknown checkpoint-training overlap persists.

13 synthetic tests passed before real data access. Eight fixed-lambda linear regressions were then fitted on 260 fit inputs using current/past-only features and offline full-minus-current quality-proxy labels. Four targets at each of 8 and 10: sentence BLEU, sentence chrF, covered numeric F1 and negation mismatch. Labels use future/reference outcomes only offline in fitting. Corpus endpoints remain exact corpus scores. No Q1 oracle assignments were used as labels. Training label counts per level were 260/260/58/260. The learned models are refinement-benefit proxies, not a certified continuation-value function, calibrated uncertainty estimator or optimal policy.

Calibration compared three stability candidates, five thresholds on the shared ridge models, and native-full fallback. The coefficients were never refitted on calibration or evaluation. Calibration used exact corpus point margins and a predeclared estimated-cost ranking; no test metrics or timings chose the policy or comparator. Native full was also the locked fixed comparator. All 11 fixed depths were retained in actual evaluation, with no adjusted quality exclusions.

## Why calibration selected full depth

| Candidate | Early exits /101 | BLEU loss | chrF loss | Numeric F1 loss | Negation increase | Point screen | Estimated mean ms |
| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| full | 0 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | pass | 139.613 |
| stability:0.0 | 1 | 0.049995 | 0.041731 | 0.000000 | 0.000000 | pass | 143.765 |
| stability:0.03125 | 9 | 0.183175 | 0.248064 | 0.050000 | 0.000000 | fail | 142.656 |
| stability:0.0625 | 16 | 0.469748 | 0.577975 | 0.050000 | 0.000000 | fail | 141.686 |
| ridge:0.0 | 0 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | pass | 143.904 |
| ridge:0.5 | 0 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | pass | 143.904 |
| ridge:1.0 | 0 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | pass | 143.904 |
| ridge:2.0 | 2 | 0.111950 | 0.142341 | 0.000000 | 0.000000 | pass | 143.627 |
| ridge:4.0 | 17 | 0.462288 | 0.544378 | 0.100000 | 0.009901 | fail | 141.547 |

Allowed losses remain BLEU 0.5, chrF 1.0, numeric F1 0.02 and negation increase 0.02. No candidate exited at 8. The most permissive quality-passing learned candidate exited at 10 on only 2/101 inputs; exact stability exited early on 1/101. Those sparse exits did not overcome the estimated observation costs. More permissive stability/learned candidates exited 9,16 or 17 times but lost 0.05 or 0.10 numeric F1, exceeding 0.02.

Cost ranking used the prior measured terminal-depth means plus the previously frozen observation-step proxy. Those are estimates for selection. Unselected non-full candidates were NOT run in the new actual GPU benchmark. Consequently, this study does not measure their actual decision costs or prove that every quality-passing non-full candidate is actually slower. It shows that the declared family and selector chose full; it cannot rule out better features, models, thresholds, cost estimates or stopping policies. No extra candidate, refit or threshold was added to rescue the result.

## Once-only actual evaluation

The selected native-full policy and all 11 fixed terminal controls were run on 87 evaluation representatives, in two separate processes, with two repeats per input/method/process. Each method has 348 timed requests. Total 4,176 timed +120 charged warmups =4,296 requests. All expected exits, generated code prefixes, every observed token/text output and actual generator/decoder counts matched the old-output causal replay. The online API received only source and the selected controller; replayed depths/identities were for checks, not features or forced stopping. The selected full fallback does not run learned decisions/features; its actual decision and feature call counts are 0.

| Method | Mean ms | Median ms | p95 ms | Test point-quality screen | Selected-policy saving versus this control |
| --- | ---: | ---: | ---: | --- | ---: |
| controller | 143.693 | 143.248 | 155.381 | pass | - |
| fixed:1 | 16.829 | 16.434 | 19.926 | fail | -753.846% |
| fixed:2 | 30.058 | 29.611 | 33.762 | fail | -378.051% |
| fixed:3 | 42.949 | 42.598 | 48.562 | fail | -234.569% |
| fixed:4 | 55.679 | 55.208 | 62.477 | fail | -158.076% |
| fixed:5 | 68.587 | 67.767 | 77.450 | fail | -109.504% |
| fixed:6 | 82.046 | 81.131 | 92.780 | fail | -75.138% |
| fixed:7 | 94.913 | 93.956 | 105.307 | fail | -51.395% |
| fixed:8 | 106.685 | 106.655 | 115.575 | fail | -34.690% |
| fixed:9 | 119.163 | 118.628 | 130.521 | fail | -20.586% |
| fixed:10 | 131.228 | 130.786 | 144.420 | fail | -9.499% |
| fixed:11 | 143.670 | 143.497 | 154.712 | pass | -0.016% |

The selected full policy has exactly 0 full-relative losses for all four quality endpoints because its text is identical to full. Its test corpus scores are BLEU 20.414358, chrF 49.668660; covered numeric-reference mean F1 0.700000on 14 references, negation mismatch 0.057471. These consumed-data points do not validate a nonidentical early-output policy.

Session 0 selected/full means: 142.940/143.422ms, saving 0.336%. Session 1: 144.446/143.918ms, saving -0.367%. The approximately zero difference changes sign across sessions. Do not compare these absolute times against Q2 as if the input populations or timing conditions were identical.

Ready-output timing includes source tokenization, generation, reconstruction, decoding/transfers/rendering, any executed feature/decision work and final synchronization. CUDA span is separate. State/identity/hash checks are outside the request timer. Native-full fallback has no sparse observations or learned online decisions; this is explicitly not a measurement of an unselected ridge controller's overhead.

Exactly 20,000 paired whole-component bootstrap draws, 33 components, 11 nominal two-sided contrasts, tail .05/22, conservative rank 22 and aggregate Monte Carlo rank-error allowance .001. Component totals preserve input weighting; repeats and the two observed sessions are held fixed. Intervals are approximate and conditional under declared independent/exchangeable component assumptions; no cross-device/process-population inference, exact coverage claim, quality bootstrap or independent confirmation. All fixed contrasts/point metrics remain in [analysis.json](../../../results/quality_tolerant/controller/evaluation/analysis.json); the comparator was not replaced based on test outcomes.

## Actual work and verification

| Resource | Actual | Frozen cap |
| --- | ---: | ---: |
| Real ridge fits | 8 | 8 |
| Offline sentence-label pairs | 780 | 780 |
| Development / evaluation corpus-score calls | 19 /12 | 20 /12 |
| Old trajectory bodies / reference materializations | 448 /448 | 448 /448 |
| Source materializations, parent plus workers | 622 | 622 |
| Actual model requests including warmups | 4,296 | 4,296 |
| Generator levels | 27,566 | 27,566 |
| Decoder examples | 4,296 | 5,012 |
| Encoder calls / target encodings / generator updates | 0 /0 /0 | 0 /0 /0 |
| Actual online learned decisions / features | 0 /0 | 716 /716 |
| Source-prefix calls including prechecks | 4,470 | 4,470 |
| Development seconds | 27.876 | 1,800 |
| Model orchestration seconds | 432.105 | 3,600 |
| Evaluation total seconds | 442.449 | 6,600 |
| Parent peak RSS bytes | 209,018,880 | 8,589,934,592 |
| Worker peak RSS bytes | 2,777,931,776 | 17,179,869,184 |
| Peak GPU reserved bytes | 1,272,971,264 | 8,589,934,592 and physical limit |
| Artifacts before final reporting bytes | 8,012,559 | 1,073,741,824 |
| Bootstrap draws / inference retries / paid dollars | 20,000 /0 /0 | 20,000 /0 /0 |

Runtime: existing WSL Python 3.12.3, torch 2.10.0+cu128/CUDA12.8, transformers 4.57.6, RTX 5060/driver 610.88, float32/eval,4 CPU threads, matmul TF32 off/cudnn TF32 on. Both released model states are unchanged before/after each process and identical across processes. The original generator/tokenizer were never trained. The eight CPU fits are only the declared small controller proxies. No new inputs/trajectories, downloads, E3/E4 model-output release, target encoding, paid compute, contact or submission.

The frozen verifier passed all saved source/history/artifact and request/work/state checks. Additional [completion review](../../../results/quality_tolerant/controller/completion-review.json) checked 1075 hashes including all 968 protected historical files, all 4,296 request hash receipts, split separation, policy bytes in its pre-test commit and all resource counts, with 0 new fits/inference/bootstrap or original-body replays. This is scripted verification, not an independent replication. Thirteen focused synthetic tests cover causal exits at 8/10/fallback, independently reconstructed prefixes, first-observation handling, future-suffix isolation, eight-fit budgets, insufficient labels, test-body skipping, corpus-margin boundaries, paired weighting and inadequate coverage. The full historical test suite was not rerun. The WSL pytest directory alias was ignored for Windows Git delivery; its real hashed synthetic fixture was retained.

## Project consequence and stopping point

The previous Q2 observation remains intact: one clairvoyantly selected consumed assignment saved 9.165% actual time. This Q3 experiment did not learn/select a useful way to realize it. It narrows the result to the tested 19 features, linear proxy/threshold family, stability rules, cost-ranking approximation and consumed split; it is not evidence that every causal controller must fail.

Q0's statistical confirmation route remains failed. Q4 is not ready: there is no selected adaptive policy meeting this engineering screen, and independent quality confirmation still requires a defensible separate statistical/population route. Further controller work would need a separately justified and bounded revision of the candidate design, with explicit consideration of why the current selection yielded almost no safe early exits. No revision, further fit, new data acquisition or confirmation is executed here. Original margins, frozen evidence and reservations remain intact.

[Development receipt](../../../results/quality_tolerant/controller/development/execution.json), [locked policy](../../../results/quality_tolerant/controller/development/policy.json), [calibration results](../../../results/quality_tolerant/controller/development/candidate-results.json), [evaluation receipt](../../../results/quality_tolerant/controller/evaluation/execution.json), [decision](../../../results/quality_tolerant/controller/evaluation/decision.json), [artifact guide](../../../results/quality_tolerant/controller/README.md). Primary methodological sources and limitations are in the prospective protocol.
