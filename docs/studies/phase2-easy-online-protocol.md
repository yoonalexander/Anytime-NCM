# Phase 2 easy Sudoku: online stopping, bounded unblocking, and held-out comparison

**Declared:** October 22, 2026 (America/Toronto), before Phase 2 model calls or per-input Phase 2 final access.
**Base:** 77b959a39d9f0a4913f684479addac4f0f2e7588.
**Work order:** User explicitly requested unblocking and finishing Phase 2, with commit/push after each subphase.

## Entry exception and claim boundaries

Phase 1 hard and R3 easy remain no-go; R2 screens remain negative. No reconstruction bug explains away the lack of early valid outputs. This request authorizes a separately documented **online engineering and measurement experiment despite the failed opportunity gate**. It does not turn those gates into go, promise a speedup, or authorize relaxing Sudoku quality, training a checkpoint, changing tasks, or consuming Phase 3 finals.

Bounded unblocking: implement a true level hook, reuse an incremental full-resolution monitoring accumulator, and compare four frozen verifier inspection schedules on development. These can reduce monitoring overhead; they cannot manufacture an early valid output. Complete and report Phase 2 even if actual costs remain negative. Original scientific thresholds remain unchanged.

Setting: pinned easy checkpoint, same upstream/model/dataset revisions and artifact hashes as R2/R3. RTX 5060/WSL2, float32/eval, batch 1, four CPU threads, official greedy sampling (temperature 0, top_k 0, top_p 1, cfg 0), no KV cache, autocast or compilation. No new downloads, paid compute, model training, stochastic samples or seeds.

## 2A: minimal isolated hook and parity

Preserve the vendored upstream checkout. Extract the exact pinned generate function and insert only two completed-level boundaries: after generated_idx initialization and after each append. Record a unified function patch, base revision and source hashes. The disabled hook follows the same generation body with no stops. Reject unsupported batch/sampling/cache configurations. A current-level callback may see only the generated prefix; its public immutable observation contains current/past decoded IDs and level counts, never references or future codes. Enforce min/max boundaries, Boolean decisions, safe level-12 fallback and cleanup on errors.

Monitoring accumulates each codebook contribution at full length exactly once, lazily up to the inspected depth, including learned upsampling and residual convolutions. Snapshot before decoding. Test against independent arithmetic and saved offline outputs; later codes must not affect earlier observations. Reference-free clue verification uses the known input puzzle.

Before released-checkpoint inference, pass synthetic tests for source patch boundaries, disabled parity, forced skip counts, invalid boundaries, callback isolation, storage, full-resolution reconstruction, stability state and fallback.

Exactly 32 existing exploration identities (indices 0–31), six requests each: original full depth, patched disabled, forced depth 1, forced depth 6, every-level verified, and stability (minimum 2, one unchanged transition). **192 generations maximum**, at most **1,760 generator first-block level evaluations and 864 decoder forwards**. Zero warmups/timed requests. Compare original and disabled codes/tokens/text bitwise; compare fixed and adaptive exit output against the already saved R3 trajectory and policy simulator, including never-valid fallback. Enforce actual work caps and record model state fingerprints. No extra parity generations.

Commit/push 2A and verify remote equality before benchmarks.

## 2B: development policy selection and real request costs

Only original exploration/development partitions, inherited across difficulty masks with identical solution rows. R3's 1,400 trajectories remain unchanged and may supply offline development labels and the retrospective first-valid oracle. The oracle is analysis-only.

Fixed-depth family: all 12 depths, zero empirical primary solve loss relative to full depth on all 400 development trajectories; choose minimum saved R3 estimated fixed-depth cost among feasible depths, disclosing this selection on development.

Available causal heuristic: exact decoded-ID stability, with minimum levels {2,6,10} and unchanged-transition patience {1,2}. Evaluate all six on the 400 development trajectories. Exclude any candidate with an invalid early exit or primary solve-rate loss. Among feasible candidates choose fewest mean decoded inspections, then highest minimum level, then lowest patience. If none qualifies, retain min10/patience1 as an explicitly infeasible descriptive comparator, never as the primary method. Decoder-logit uncertainty was not retained in the frozen trajectories; no unvalidated entropy feature, additional calibration family or learned controller is introduced.

Verifier schedules: every level 1–12; levels 6–12; levels 10–12; level 12 only. All include final fallback. Level-12-only is a degenerate verifier schedule without possible early generation savings, not evidence of adaptive advantage.

Development online comparisons: original full depth, selected strong fixed depth, all four verifier schedules, selected stability = seven methods. First 100 original development indices, three paired repeats per identity. Ten exploration-only warmup inputs per method (70 warmup requests). Maximum **2,170 generations / 26,040 generator level evaluations / 11,160 decoder forwards**. These include warmups and all candidates; no reruns. Select primary verifier schedule using lowest actual mean development wall latency among zero-loss/zero-false-accept candidates, requiring agreement with offline policy simulation. Tie break by method ID. Retain every-level verification as a separately reported comparator.

Use balanced cyclic method order by identity and repeat; rotate warmup order by input. Do not change sampling. No profiler or per-component synchronization in headline runs. Keep one non-mutating first-block and decoder counter per model to prove real work; counter/marker overhead is included consistently. Request wall timing: synchronize, start host timer, record CUDA start event, prepare input, generate/monitor/decode/transfer/text/features/policy, record end event, synchronize, stop timer. Events are allocated outside requests. GPU event duration is stream elapsed time (including host-driven gaps), not kernel-busy time. Exclude model loading, warmup, offline reference scoring, diagnostic code transfer and serialization. Include synchronization/transfer inherently required by the algorithm. Reset/read peak allocated memory outside timing. Report warm batch-1 latency and requests/s reciprocal latency; do not infer batched throughput.

Freeze methods, selected specs, source/config/protocol/manifest hashes, method ordering, statistics and budget in a policy-lock artifact. Commit/push 2B before opening final token operands or outputs.

## 2C: final comparison and report

Require 2A complete, 2B complete and its source-matched policy lock. Open only the preassigned **300 easy phase2_final identities**. Existing official full baselines internally scored these rows with only aggregate inspection; disclose this history. Do not call this an entirely unseen official test set. Phase3_final (300 aligned solution rows) remains unavailable: selective readers traverse structural bytes but never materialize those token operands, references or outputs. Record final access before opening selected rows.

Final methods: full, selected fixed, every-level verified, development-selected verifier schedule, selected stability; deduplicate an identical selected schedule while retaining its alias in analysis. At most five methods. Three paired repeats per final identity, ten exploration warmups per active method. Maximum **4,550 generations / 54,600 generator level evaluations / 33,670 decoder forwards**, including warmups. Maximum total Phase 2 allocation: **6,912 generations, 82,400 first-block level evaluations, 45,694 decoder forwards**. Zero encoder forwards. No sample replacement, extra seeds, policy changes, profiling or extra model-evaluation retries. All invalid and never-valid outcomes remain results.

Freeze primary metric relative reduction in actual mean wall latency, paired 95% identity bootstrap with 10,000 resamples, seed 20261022, retaining all three repeats and paired methods. Also report means/medians/p95, GPU event elapsed, memory, generated levels/codes, inspection counts, quality differences/intervals and false early accepts. Recompute primary validity independently from Sudoku units and clues. Primary claim gate: >=5% actual mean reduction, interval lower bound >0, zero empirical solve-rate loss, zero false accepts and passed correctness/parity. Upper interval bound <5% is no-go; other uncertain cases are inconclusive. Compare primary to full and selected fixed; beating full alone does not establish an adaptive-frontier advantage. A negative result completes the experiment.

## Evidence, failure handling and delivery

New files under results/phase2/. Each stage has pre-execution source/input hash receipts, reserved input slots, bounded atomic metadata writes, raw request records, work counts, failures and completion. Metadata I/O retries add no model calls and occur outside timed regions. A partial model-work failure requires a dated amendment before any continuation; do not silently replay completed work. Debug/synthetic fixtures are separate from released input budgets.

Model-free verification recomputes selection, labels, paired costs/intervals/gates and checks raw output/exit consistency, budgets, source/input/output hashes, policy lock and final access history. It does not replay GPU parity or treat timestamps as proof of hardware execution. Preserve all historical source, data, profiles, negative gates and completion records; archive current compatibility review before refreshing it.

For each of 2A, 2B and 2C: tests, evidence, roadmap status, commit to main, push and verify local/GitHub equality. Stop after Phase 2; no Phase 3 training or final access.
