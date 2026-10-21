# Experiment protocol

**Revision 1 — frozen October 20, 2026, before baseline inference.**

This protocol fixes the partitions, design gate, and measurement rules. Section 7 performs official baseline reproduction only. Later phases remain unimplemented.

## Sources and partitions

- Upstream commit: `c70274273f489abc73832b2b98584a8483b6b203`.
- Dataset: `hazyresearch/ncm-datasets`, revision `6580ba41a4b0a976dde876fbe84d25327617b0e6`.
- Model: `hazyresearch/ncm-checkpoints`, revision `d342ce8aaea58830eef3b8ad473664673e41f692`.
- Manifest: [partitions/sudoku-hard.json](partitions/sudoku-hard.json).
- Manifest SHA-256: `ed7a6b3c102fe4713a3f80f8f02b53afe37a44b53da80964936467617799bdb7`.
- Identity: SHA-256 of compact JSON containing the complete integer input-token list. Solutions are not read by the partition generator. Duplicate identities stay in one split.
- Seed: `20261020`; allocate 1,000 puzzles to exploration/training, 400 to development, 300 to `phase2_final`, and 300 to `phase3_final`. The first 32 official inputs belong to exploration. The released set contains 2,000 unique puzzle identities.

Official full-set reproduction is descriptive: its evaluator reads and scores all examples internally. Keep its per-input predictions/references out of policy selection; inspect only aggregate reproduction metrics. Record access in the reproduction log. Future adaptive-policy final evaluations use the reserved phase-specific holdouts. Phase 2 results cannot justify relabeling its exposed holdout as an untouched Phase 3 test set. Evaluate all later comparison methods on the same appropriate holdout after freezing their settings.

## Baseline execution

Use the unchanged official evaluator, one GPU (`0`), float32/default precision, no autocast or compilation override, and the original batch size of 128. Retain temperature 0.0, top-k 0, top-p 1.0, and guidance scale 0.0. Run 32 inputs first, then all 2,000 in separate output directories. Set CPU thread counts to four and record this execution setting. Record any failed attempt and batch-size override explicitly. Whole evaluation process duration includes loading/scoring and is not inference latency.

## Future trajectory and profiling budget

These limits authorize no trajectory work during Section 7. In the later trajectory phase, use at most all 1,000 exploration and 400 development inputs; keep adaptive-policy holdouts unavailable. For diagnostic cost profiling, use the first 100 indices from each of exploration and development, ten exploration-only warmup requests, and five timed repeats per profiled input. If these measurements cannot resolve the gate, report inconclusive rather than inspect a final holdout or expand the budget retrospectively. A larger study requires a dated protocol amendment.

Validate full-resolution partial reconstructions, independent snapshot storage, prefix isolation, Sudoku correctness, and final-output parity before interpreting trajectories. Select fixed depths, thresholds, inspection schedules, and any later learned-policy settings using exploration/training and development data only. Freeze selected settings before final evaluation.

## Primary gate and statistics

- Minimum worthwhile relative reduction in mean end-to-end latency: 5%.
- Maximum empirical solve-rate loss for verified stopping: zero percentage points.
- Maximum false verifier accepts: zero.
- Paired 95% bootstrap interval: 10,000 puzzle-identity resamples, seed `20261020`; preserve all repeated timings for each selected puzzle. Report quality differences and uncertainty separately, plus median and p95 latency.
- Go: estimated reduction is at least 5%, its interval lower bound exceeds zero, and correctness/parity checks pass.
- No-go: interval upper bound is below 5%, or correctness/parity remains unresolved; distinguish limited opportunity from an unresolved correctness blocker.
- Inconclusive: other cases, including unavailable cost measurements.

Offline estimates must include generation through the exit and every reconstruction, decode, transfer, verifier, feature, and policy cost through that exit. Never-valid trajectories incur full work and every scheduled check. Compare with full generation plus its final reconstruction/decode. Offline component profiles cannot establish real online speedup.

## Measurement boundaries

Profile components separately using CUDA events or isolated synchronized timings, documenting instrumentation overhead. For headline online timing, synchronize only at request boundaries in addition to synchronization required by the actual algorithm; include input preparation through usable output and actual monitoring. Exclude loading, warmup, offline reference scoring, and serialization from warm inference latency. Use matched boundaries and hardware for all methods. Section 9 of the design governs later actual-speedup claims.

## Amendments and access history

Do not revise thresholds or choose policies based on final-holdout outcomes. Log dated amendments and any holdout access. At protocol creation, no baseline inference, trajectory inspection, or adaptive-policy final evaluation has been performed. Subsequent descriptive baseline access is recorded in `reproduction_log.md`.
