# E1: measured forced-exit costs

Completed October 24, 2026 under the [prospective protocol](../../../docs/studies/evidence-gaps/e1-protocol.md), [lock](../../../docs/studies/evidence-gaps/e1-lock.json) and [exact schedule](../../../docs/studies/evidence-gaps/e1-schedule.json), committed/pushed at `c8633ad45e2ef0220f2c1b516b6241595258e7b0` before inference, with remote equality checked.

**A cheaper forced path exists in this finite engineering pilot. Practical quality-matched adaptive speedup is still unestablished.** All 1,000 allocated requests completed with exact cached-prefix parity and expected work; model weight/buffer fingerprints were unchanged in both independently started model processes. No failed or replacement requests, extra parity requests, encodings, fits, reference reads or new input identities. E2/E3/E4 outcome roles remain sealed.

## Measured ready-output latency

Sixteen previously exposed exploration inputs, three repeats, two process blocks; 96 timed requests per cell. Timing starts before source preprocessing/context transfer and ends after CPU text is ready and pending device work is synchronized. Terminal depth 11 uses the unmodified released generator as the full-depth control. All other paths use the isolated stopping hook; every-level paths reconstruct/decode every visited level. See [raw records and execution receipt](execution.json) and [paired analysis](analysis.json).

| Forced depth | Terminal-only mean ms | Every-level mean ms | Terminal reduction vs full | Every-level reduction vs full |
| --- | ---: | ---: | ---: | ---: |
| 1 | 14.881 | 15.065 | 88.316% | 88.172% |
| 4 | 49.570 | 55.999 | 61.079% | 56.031% |
| 7 | 83.794 | 96.338 | 34.207% | 24.358% |
| 10 | 117.523 | 135.763 | **7.723%** | **-6.598%** |
| 11 | **127.360** | 148.507 | 0% | **-16.604%** |

Negative reduction means overhead. These forced outputs were checked against their saved **same-level** outputs, not against reference translation quality. A fast shallow request may return inadequate text. These values do not describe an adaptive selector, actual S1 oracle execution, throughput, decoder-only cost, or all possible inspection schedules.

Terminal depth 10 saves 7.723%, nominal paired 95% interval [6.701%,8.608%], compared with full depth. Inspecting all levels through 10 instead adds 6.598% relative to full, nominal interval [5.843%,7.334%]. At equal exit depth 10, the every-level path costs 18.240 ms more than terminal-only, a 15.520% overhead relative to that terminal path. It includes observation reconstruction, decoding, transfers, callback and related path costs; it is not a separately instrumented decoder component estimate.

Every-level depth 11 costs 21.147 ms more than the full control: 16.604% overhead, nominal interval [15.367%,17.510%]. Depth 7 remains cheaper even with dense observation, but its translation quality was deliberately not scored. There was no controller training or threshold/assignment optimization.

## Process and uncertainty scope

Full-control means were 126.702 ms and 128.018 ms in the two process blocks. Terminal depth 10 means were 118.072 ms and 116.975 ms; every-level depth 10 means 135.545 ms and 135.982 ms. Full mean/median/p95 and separate-process comparisons for every cell are retained in `analysis.json`; raw timers, CUDA stream spans and allocator peaks remain in each request row.

The primary summaries give identities equal weight and average three repeats within each identity/process. All contrasts reuse the frozen 10,000 PCG64 identity-resample vectors. Intervals are **nominal descriptive intervals**, conditional on these 16 reused inputs and two fixed process blocks, with no multiplicity correction or process-population coverage guarantee. Repeats are not new independent quality inputs. Known/unknown news-document dependence, prior aggregate baseline exposure and unknown checkpoint-training overlap remain limitations. Do not interpret the narrow conditional intervals as broad deployment or cross-hardware certainty.

The visible pattern narrows a cost question: under these paths, forcing a stop before the last level saves real request time, and dense observation can consume that saving near full depth. It does not identify a unique architectural bottleneck or rule out cheaper sparse/latent observation policies. No decomposition or interpolation was fitted. Do not substitute these 16-input measurements into the earlier 64-input S1 surrogate and call the result measured oracle latency.

## Integrity, work and resources

- Actual released-checkpoint work: 1,000 requests = 40 warmups + 960 timed; 6,600 sample-level generator evaluations; 3,800 decoder forwards;zero encoder forwards, target encodings or fits. Each request's counters prove its hard stop omitted later generator levels.
- Exact source prefix/generated-code prefix/64-ID/text parity passed on every allocated request, including every intermediate observation in every-level paths. Parity reused the allocated requests and added no model calls. These are current-to-cached checks; the historical official-comparator parity remains separate evidence.
- Two fresh model processes (PIDs 390 and 413), one checkpoint load each; loading took 9.523 s and 9.077 s outside request clocks. Model state fingerprints before/after each block match. Both blocks used pinned float32/eval, four CPU threads, Torch 2.10.0+cu128/CUDA 12.8 and RTX 5060. Backend/driver/free-memory details are in process receipts.
- Orchestration, preflight hashing, model loads, measurement and saved-record analysis took 137.368 s, within the 30-minute orchestration subcap. The frozen budget conservatively charges 90 setup/reporting minutes in addition; no two-hour resource cap was enlarged. Host peak RSS was 2,812,735,488 bytes across the process receipts. Original pre-report artifacts were 1,793,924 bytes, below 256 MiB; $0 paid compute. CUDA virtual addressing was not artificially capped.
- [87 synthetic/compatibility checks](../../../docs/studies/evidence-gaps/e1-lock-validation.json) passed before inference. They use tiny untrained CPU models or synthetic records and do not supply released-checkpoint empirical parity. No historical full-suite count is presented as freshly rerun.
- A [separate checker](../../../scripts/verify_evidence_e1.py) verified all 1,000 actual rows/start ledgers, cached output/observation hashes, state/source/artifact hashes, and 45 pooled/process contrast summaries with the same resample vectors: [receipt](independent-checks.json). It imports no model libraries, adds zero model calls/inputs/references and is same-assistant verification, not independent human review.

The original empirical files, submodule, E0 role manifest and frozen protocols remain intact. The byte-exact executed-source archive handles Windows newline normalization separately from Git canonical text. Successful request logs retain hashes, not duplicate translation text.

## Gate and next work

**E1 engineering screen passed:** cheaper genuinely stopped paths were observed under valid parity/work/state checks. The quality-latency research claim remains unresolved. This completes E1 within its allocation; no further timing requests are permitted under this run.

The next useful proposal is a **separately preregistered exact-final-text opportunity audit**, with fresh-data access rules, all relevant fixed-depth comparators and measured assignment execution. Exact-final-text equality defines a retrospective diagnostic; the online policy cannot see its future final output. Do not relabel it a causal rule.

E0's finding still blocks automatic execution of the planned nonidentical-output E2 gate: its conservative cue-bound coverage floor 405 exceeds the 256-input allocation. Do not loosen tolerances, silently remove endpoints or expand the population because forced exits were fast. E4 numeric coverage and missing document grouping also remain unresolved. E3 controller fitting, E4 confirmation, target encoding, model intervention and submission/contact remain unexecuted. All reserved outcome/reference roles are still sealed.
