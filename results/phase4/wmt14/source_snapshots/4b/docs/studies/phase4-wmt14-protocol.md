# Phase 4: bounded WMT14 German-to-English generalization

Declared October 23, 2026, before Phase 4 model calls, baseline outputs or trajectory inspection. Base commit 8de2ad8e841a534df18654ec457cae39bc420e97. User requested completing Phase 4 and committing/pushing; Phase 5 is outside this work order.

## Task, resources and provenance

Select released WMT14 De-En, not XSum. Preserve upstream c70274273f489abc73832b2b98584a8483b6b203, checkpoints d342ce8aaea58830eef3b8ad473664673e41f692 and data 6580ba41a4b0a976dde876fbe84d25327617b0e6. Pin Qwen/Qwen3-0.6B tokenizer c1899de289a04d12100db370d81485cdf75e47ca; download tokenizer/config files only, no Qwen language-model weights. Exact sizes/digests/URLs are recorded in configs/phase4_wmt_sources.json and preflight. Approximately 1.13 GB checkpoint download plus small tokenizer/data files fits existing disk/GPU estimates; actual peak memory is measured.

Existing RTX 5060 / WSL2, float32/eval, four CPU threads, no compilation/autocast/KV cache. Official temperature 1 / top-k 1 / top-p 0 / CFG 0 remains unchanged. Reset seed 20261023 before each batch-one request outside timing for paired reproducibility; top-p zero leaves one sorted candidate. No paid compute, training or checkpoint changes. The source prefix uses the pinned tokenizer, first 96 IDs padded to 96; target decoder emits 64 IDs with official EOS truncation/special-token filtering. All 11 levels use full-resolution reconstruction, preserving learned L1 cascade, intermediate GroupNorm and residual transforms.

## Partitions and access

Before outputs, hash effective padded source prefixes, group all duplicate/truncation-identical inputs, and keep each group in one split. Force the first 32 official rows/groups to exploration, then deterministic seed-20261023 group allocation: 512 exploration groups, 256 development groups, 256 phase4_final groups, remaining groups reserved/unused. Use one canonical minimum index per group for study inference. Source strings may be tokenized for identity construction; no references are used for splitting. Record source/truncation/duplicate coverage.

Audit first 128 exploration and first 64 development canonical indices. Development benchmark uses those same 64 development groups. Final benchmark uses all 256 preassigned phase4_final groups. Warmups: first eight exploration canonical inputs per active method. Official full-set reproduction scores all 3,003 rows internally and exposes only aggregate metrics; disclose that prior aggregate exposure and unknown base-model overlap. It cannot establish untouched official-test performance. Restricted non-executing string readers materialize references only for selected study rows; later final access requires a committed/pushed source-matched released policy lock.

## Metrics, losses and safeguards frozen before outputs

Use pinned sacreBLEU defaults matching upstream: corpus cased BLEU (13a, mixed case, exp smoothing, effective_order false), lowercase BLEU secondary, corpus chrF (character order 6, word order 0, beta 2). Record library versions/signatures. Quality tolerances versus matched full depth: at most 0.5 absolute BLEU points and 1.0 absolute chrF points, both on 0-100 scales. These are task-specific empirical tolerances, not Sudoku's exact zero-loss contract.

Targeted diagnostics are explicitly HEURISTICS, not semantic truth labels: English digit-number token sets and English lexical negation-cue presence (no/not/never/neither/without/n't), reference mismatches and changes versus previous/full output. Numeric reference F1 is reported only for references containing digit numbers, with coverage; empty coverage is unavailable. Negation cue mismatch is not a proof of polarity error (e.g. not-only constructions, paraphrases, written-out numbers and source/reference differences). No LLM judge, factual-consistency guarantee or cheap exact translation verifier is claimed.

Development feasibility: point BLEU loss <=0.5, chrF loss <=1.0, numeric-reference F1 loss <=0.02 where defined, and negation-cue mismatch-rate increase <=0.02 versus full depth. Select policies only on development. Final practical claim requires >=5% mean ready-output wall-latency reduction with paired 95% lower bound >0 AND one-sided quality lower interval bounds >=-0.5 BLEU and >=-1.0 chrF. Heuristic diagnostics remain disclosed guardrails; violating their point tolerances defeats a positive claim. A frontier claim additionally requires beating the selected strong fixed-depth comparator at matched quality. If speedup upper interval <5% or a quality interval lies wholly beyond its tolerance, no-go; other unresolved quality/latency cases are inconclusive. A bounded negative/inconclusive result completes Phase 4.

Paired identity bootstrap: 10,000 resamples, seed 20261023, retaining all three timing repeats. Recompute corpus metrics using summed per-segment sufficient statistics, validated against sacreBLEU direct corpus scoring. Report quality differences/intervals separately from timing. No sentence-BLEU average masquerades as corpus BLEU. Calibration/false verifier acceptance does not transfer automatically to translation.

## 4A: prepare, official baseline, full-resolution audit

Freeze protocol/identity manifest before inference. Reproduce verbatim official prefix/pick_tokens/dec/run bodies with the pinned tokenizer and released model. Official smoke: 32 first rows; full: all 3,003. Predeclare batch 8 instead of release batch 64 for memory headroom, recording this override and not claiming exact paper-number/batch parity. Retain smoke outputs only; full-set per-input outputs/references remain inside the scorer process and are not published or used for policy selection. Record aggregate BLEU/lowercase BLEU/chrF, work/memory/environment and model state. Process duration is not warm latency.

Collect 192 batch-one trajectories, 11 full-resolution decodes each. First 32 exploration trajectories use patched-disabled generation and compare exact codes/tokens/text with 32 fresh official batch-one comparator requests. All remaining trajectories use unchanged original full generation. Validate independent functional reconstruction including learned ConvTranspose1d/GroupNorm/residual arithmetic, snapshot storage and future-code isolation. Synthetic pinned small-model tests prove forced boundaries skip real transformer calls, including WMT's predict-level-zero branch. No additional real-checkpoint parity calls.

4A caps: 3,259 input-generations, 35,849 sample-weighted first-block level evaluations, 5,179 sample-weighted decoder forwards, zero full encoder forwards (raw-prefix embedding lookup is still used). Counter forward-call counts and sample-weighted work are distinct; batch 8 reproduction does not imply batch-one latency. Commit/push 4A with its evidence before benchmarking.

## 4B: development policies and measured comparison

Fixed-depth family: depths 1-11; choose smallest depth satisfying all development feasibility constraints, falling back to depth 11. Retrospective best-prefix quality is an offline oracle only, never an online signal.

Two adaptive families: decoded-ID stability and guarded stability. Grid: inspection minimum {5,8,10}, consecutive-small-change patience {1,2}, token-ID change fraction epsilon {0,0.02,0.05}; inspect every level from minimum through 11. First observation cannot stop; final level is unconditional fallback. Guarded stability additionally requires current/previous digit-number sets and negation-cue presence unchanged at every accepted transition. No references, BLEU/chrF, future outputs, oracle labels or input IDs enter online decisions. These checks do not verify correctness.

Evaluate all 36 candidates offline on 64 development trajectories; choose each family's feasible candidate with fewest mean inspected decodes, then fewer mean generated levels, then higher minimum, lower patience, lower epsilon. If none is feasible, min10/patience2/epsilon0 is a declared final-only fallback. No outcome-driven expansion or learned controller.

Benchmark full, selected fixed, selected stability, selected guarded adaptive (primary): 64 identities x three repeats x four methods =768 timed requests, plus 32 exploration warmups. Caps:800 generations /8,800 sample-level evaluations /4,800 decoder forwards. Require each output/code prefix/exit to match saved offline simulation. Headline timing synchronizes only at ready-output request boundaries plus algorithm-required transfers, includes source tokenization, context preparation, generation, reconstruction, decoder, transfers, text and features/policy. Loading/warmup/reference metrics/diagnostic code transfer/serialization excluded. Balanced cyclic method order; two CUDA events outside request allocation, included non-mutating counters, record peak allocated bytes. CUDA stream elapsed includes host gaps, not kernel busy; reciprocal serial batch-one latency is not batched throughput.

Freeze methods, thresholds, checkpoint/tokenizer/input/source hashes, quality tolerances, ordering and statistics; commit/push lock and verify GitHub/local equality before final access.

## 4C: frozen final comparison and generalization report

256 phase4_final groups x three repeats x four methods =3,072 timed requests, plus32 exploration warmups. Caps:3,104 generations /34,144 sample-level evaluations /18,624 decoder forwards /zero full encoder forwards. Total Phase 4 caps:7,163 generations /78,793 sample-level evaluations /28,603 decoder forwards. No additional samples/seeds/replacement inputs/model-call retries or profiling runs. Preserve failures; partial model-work continuation needs a dated amendment, never replay completed inputs silently.

Freeze final access before materializing selected references. Evaluate all methods together, including degenerate full-depth fixed/adaptive fallbacks. Report actual quality/latency, mean/median/p95, work, peak allocation, serial requests/s, paired uncertainty, quality-by-level and improve/damage transitions, targeted heuristic coverage/issues, deterministic representative cases and unavailable values. Do not conflate BLEU/chrF with Sudoku validity or semantic equivalence; quantify what does and does not transfer.

Preserve prior empirical/completion evidence, original protocols and unchanged upstream checkout. New evidence under results/phase4/wmt14/ with byte-exact per-stage execution snapshots, source/input/output hashes, state fingerprints, failures and completion. Archive current compatibility review before refresh. Tests, documentation and verified commit/push after each of 4A/4B/4C. Stop after Phase 4; do not begin Phase 5.

Deterministic examples: first three exploration canonical indices, plus the largest exploration adjacent sentence-chrF improvement and damage (ties by index, then level). Examples are diagnostic labels, never policy inputs. Explicit empty/reference-number coverage is retained.
