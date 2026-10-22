# Phase 3: bounded learned stopping on easy Sudoku

Declared October 22, 2026 before fitting Phase 3 controllers or opening per-input phase3_final data. Base commit: d6bd23fe9afcc7d0f952b76e0e353ff5d1918dca.

## Entry exception and unchanged objective

The user explicitly requested "finish phase 3 regardless". Phase 1, R2, R3 and Phase 2 negative results and the unmet remaining-headroom condition are preserved. This separately requested, negative-capable study tests interpretable learned policies despite no demonstrated early-valid opportunity. It cannot promise a speedup or justify more checkpoint training, quality relaxation or a task change.

Frozen easy checkpoint, original row-index reservations across related difficulty masks, RTX 5060 / WSL2, float32/eval, batch 1, four CPU threads, greedy official sampling; no compilation/autocast/KV cache. Existing data and dependencies only. Base-model training overlap is unknown. Full official baselines previously scored reserved rows internally with aggregate-only analyst inspection; identity hashing traversed reserved operands. This is a reserved policy-evaluation subset with disclosed prior exposure, not untouched official test data.

## 3A: causal features, target, fitting and offline development

Reuse unchanged R3 trajectories: all 1,000 exploration identities for fitting and 400 development identities for selection. Neither phase2_final nor phase3_final supplies fitting, normalization, calibration or selection examples. Phase 2 aggregate findings motivate this design, never refitting on its final records.

Binary target: the CURRENT decoded prefix is a complete grid-valid, clue-consistent solution. References/future states may establish offline labels, never inference features. Sufficiency estimates when refinement can safely cease; it does not model failure-abandonment utility or relax valid-output requirements. There are no positive pre-final labels in these saved data, a limitation retained explicitly.

Base features: normalized level and cumulative code count, input clue density, histogram of 12 current decoded token IDs, change fraction from the prior INSPECTED output, and previous-observation availability. No Sudoku unit/clue validator, solution, reference, correctness flag, sample identity or future token enters the model. Input clue density is Sudoku-specific; no cross-task generalization claim.

Internal ablation adds the CURRENT codebook's 16-bin code histogram, entropy/log(16), maximum frequency, distinct-code fraction and adjacent-code-change fraction. Code IDs are local discrete categories; these are code statistics, not transformer activations/logits. No claim about all possible internal features or H3 in other settings.

Train two feature families x C in {0.1,1,10}, standardized using exploration-only mean/std. scikit-learn LogisticRegression, lbfgs, max_iter 2000, tol 1e-8, no class weighting, seed 20261022, deterministic float64 CPU fits. Six fits maximum; no neural checkpoint fitting, extra seeds or calibration fits. Require convergence. Select C per family by lowest development unweighted log loss over 4,800 level states (ties lower C).

Then evaluate thresholds {0.5,0.9,0.99,0.999,1.0} and inspection minimum levels {1,6,10}; inspect every level from that minimum through 12. Choose candidates with zero invalid early exits and no empirical solve loss relative to final depth on all 400 development trajectories. Minimize mean decoded inspections, then prefer lower minimum level, then lower threshold. If no candidate qualifies, threshold 1.0/minimum 10 is mandatory no-early fallback, reported as such. Do not omit favorable/unfavorable candidate results. Selected controller remains a learned classifier even if it never exits early. Record coefficients, normalization, candidate metrics and reliability bins/Brier/log loss with identity-level uncertainty.

The training feature tracker uses the actual candidate inspection history; C selection uses consecutive all-level observations. Report this schedule-dependent feature distribution explicitly. Model diagnostics always name their inspection coverage.

Commit/push 3A after tests and fitting evidence, before any Phase 3 model inference.

## 3B: development online parity, timing and lock

Methods: original full depth; Phase 2 development-selected strong fixed depth, selected verifier schedule, every-level verifier and stability; learned base; learned internal. Seven methods, no final-driven removal or deduplication. First 100 original development indices x three paired repeats = 2,100 timed requests. Ten original exploration warmup inputs per method = 70 untimed warmups.

Caps: 2,170 input-generations, 26,040 first-block level evaluations, 16,120 decoder forwards, zero encodings. At most 12 decodes each for every-level verifier, stability, base and internal, plus one each full/fixed/selected verifier: 51 per complete method set. The conservative stated decoder cap allows 52 per set and all warmups; actual counted work must remain within it. No additional real-checkpoint parity requests. Every development request must match its saved R3 prefix codes/decoded IDs and the offline policy simulation; compare scores/features at all inspected levels. Synthetic small-generator fixtures separately test forced learned exits, causality, no-reference inputs, fallback and disabled baseline parity.

Same ready-output wall boundaries as Phase 2; balanced cyclic method order, two CUDA events allocated outside requests, first-block/decoder counters, synchronization at request boundaries and transfers actually needed by each algorithm. Includes learned code transfers, feature extraction, scalar CPU scoring, policy checks and callback overhead. No per-component synchronization. Keep reference labels, diagnostic transfers and serialization outside timing. Record CPU feature+score milliseconds inside learned callbacks as an included descriptive submeasurement, not a component-sum substitute for actual latency. CUDA event elapsed includes host gaps; requests/s is serial warm batch-1 reciprocal mean latency, not batched throughput.

Do not use development online timings to expand model/threshold families. Freeze all seven policies, model hashes, execution sources, metrics, counts and statistical procedure. Commit/push the lock and verify GitHub/local equality before per-input Phase 3 final access.

## 3C: reserved comparison and final report

Open only original 300 easy phase3_final rows after the source-matched released lock. No phase2_final rows are needed. Record access before reading selected token operands; do not claim this set remains reserved after use.

Seven frozen methods x 300 identities x three repeats = 6,300 timed requests, plus 70 exploration warmups. Caps: 6,370 input-generations / 76,440 generator level evaluations / 47,320 decoder forwards / zero encodings. Total Phase 3 caps: 8,540 generations / 102,480 level evaluations / 63,440 decoder forwards. No extra samples, seeds, stochastic retries, replacement inputs, warmups or model evaluations. Preserve every failed/invalid request; a partial failure needs a dated amendment before continuation.

Primary learned method: internal-feature model (base is the predeclared ablation). Practical claim: >=5% actual mean wall-latency reduction, paired 95% lower bound >0, zero empirical primary solve loss and zero invalid early exits, with parity/correctness passed. Evaluate against both full depth and strong fixed depth; both must pass for an adaptive-frontier claim. Upper interval below 5% is no-go; other uncertain cases are inconclusive. Bootstrap 10,000 paired identity resamples, seed 20261022, keeping all three repeats. Report separate quality intervals, mean/median/p95 wall, CUDA elapsed, peak allocation, levels/codes/inspections and serial requests/s for all methods.

Calibration: raw deployed model probabilities at inspected states, Brier/log loss and ten equal-width reliability bins, repeated-output consistency; identity bootstrap intervals with seed 20261022. Compare base versus internal on the SAME matched inspected states if schedules agree; otherwise report per-model coverage and avoid an unpaired incremental-value claim. No extra final trajectory generation to obtain missing levels. Descriptive subgroups: 27 input clues or fewer versus more than 27, fixed before access, report counts/validity/latency without selecting policy.

A finite sample with zero errors does not guarantee population correctness. No headroom / no speedup remains a valid complete Phase 3 result. No automatic Phase 4 work. Preserve original protocols, study artifacts and execution snapshots; new source snapshots and source/input/output hashes under results/phase3/. Archive the current compatibility review before refreshing. Complete tests, report, roadmap, commit/push main and verify remote equality after EACH of 3A, 3B and 3C.
