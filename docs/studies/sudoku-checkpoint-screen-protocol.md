# R2: bounded released Sudoku checkpoint screen

**Declared:** October 22, 2026 (America/Toronto), before any candidate model evaluation.
**Base:** ff8adb713b668ee03a7bff916f2b42c9d2d5113c. R1A/R1B complete; original hard-Sudoku no-go unchanged.
**Purpose:** Detect at least one early exact, clue-preserving solution in a fixed exploration screen. This is not an online latency study or a Phase 2 gate.

## Rationale, candidates, and release preflight

R1A found inaccurate and unstable late generated prefixes. R1B found no early valid target-encoded solution among 32 references, despite exact final reconstruction for all 32. Neither diagnoses a universal tokenizer-only cause. A bounded difficulty/checkpoint change is warranted before implementing online stopping.

Order: **easy, then medium only if easy has zero early valid outputs**. Stop immediately when a candidate qualifies for R3. At most two candidates; never search seeds or replace inputs. A compatibility/parity failure blocks scientific interpretation: preserve the failed attempt, investigate without new inference, and do not silently rerun or proceed past the failure.

Pin upstream c70274273f489abc73832b2b98584a8483b6b203, model d342ce8aaea58830eef3b8ad473664673e41f692, dataset 6580ba41a4b0a976dde876fbe84d25327617b0e6. Read release metadata/config/license before downloading model weights. Save metadata and exact file sizes/hashes in configs/r2_sources.json. Official source and both Hugging Face cards declare MIT. No training or paid/cloud compute.

Inspected official easy/medium architectures use 8 generator blocks, width 512, 4 tokenizer encoder layers, width 256, a one-layer decoder, raw 91-token Sudoku prefixes, 89-token targets, twelve 16-entry codebooks, and levels 1,2,4,6,9,13,18,26,37,50,67,89 (322 codes). Check actual configs independently; do not assume interchangeability. Generator dropout differs but is disabled in eval. Each pair occupies 162,376,412 checkpoint bytes, plus config and 736,126 dataset bytes. Available C-drive free space exceeded 374 GB at preflight. Model dimensions and batch 1 match the validated local float32 CUDA pathway; enforce a 6 GiB peak allocated-memory ceiling as a fit check, not a benchmark. Download only the active candidate's five declared files. Medium model/data downloads wait for a completed negative easy screen.

## Identity partitions and shared-reference protection

Release metadata establishes that easy/medium/hard solutions.pickle files have identical SHA-256 b52de75f5e4642adca58b18967bcd4bbcafa699c61b21ac33ee0fd7389e0d576. They are aligned shared solutions, so merely checking masked-puzzle hashes is insufficient.

Inherit every original hard-manifest row's partition at its dataset index **before any candidate row is materialized**. Thus the same reference row remains exploration/development/Phase 2 final/Phase 3 final across difficulty masks. Preserve the original manifest/protocol hashes. Never promote any original reserved row into exploration.

A non-executing protocol-4 token-list scanner may traverse the candidate puzzle file for identity-only hashing, emitting SHA-256 per index without retaining token rows/boards. This is an explicit identity audit, including reserved puzzle operands; it is not zero byte access. Check all candidate puzzle hashes against the original manifest and candidate duplicates: any cross-partition collision makes the candidate ineligible. Solutions are not opened for partition construction. Reserve all four partitions and write a new immutable candidate manifest before opening selected solution operands or inspecting any outputs. Record identity-only access separately from materialized rows. Do not claim a new independent dataset: shared solutions and prior hard exploration exposure are known; base-model training overlap remains unknown.

Select exactly the first 32 unique exploration identities by dataset index (duplicate groups never split). The released first 32 rows must be exploration and unique; otherwise stop before inference rather than substitute examples. Use the existing non-executing selective reader for only these 32 puzzle/reference rows. No development/final board/reference rows or outputs are materialized by this screen. Reference format and clue consistency must pass before inference.

## Fixed execution and failure budget

Per candidate, exactly:
- 32 unchanged official comparator input-generations and 32 separate adapter input-generations: **64 full-depth input-evaluations**, maximum 128 across two candidates.
- The comparator is the actual pinned eval_shard.py run function, compiled verbatim with its prefix/pick_tokens/dec definitions and released globals. It uses normal generate and upstream final reconstruction/decode. This is a matched 32-input comparator, not a new 2,000-input official CLI reproduction.
- Batch 1 for both paths, identical float32/eval CUDA settings and official deterministic sampling (temperature 0, top_k 0, top_p 1, cfg 0), default eager/no-cache behavior. Four CPU threads; one validated RTX 5060. Zero warmups, extra seeds, retries, profiling, timed requests, reference encoding, or training.
- 12 generator level evaluations per input-generation, measured by a prehook on the first transformer block: **768 level evaluations per candidate**. Direct generate does not invoke the generator module's forward hook; record this measurement correctly.
- Comparator: 32 final decoder forwards. Adapter: 384 prefix decoder forwards. Total **416 decoder forwards per candidate**.
- Additionally 32 declared latent-only upstream idx_to_zhats final-parity reconstructions and one independent functional full-prefix reconstruction per adapter trajectory. Neither adds generator/encoder/decoder forwards. Validate all 12 prefixes against explicit embedding/convolution/interpolation arithmetic, shapes/finiteness, independent storage, and upstream final equality.
- Encoder forward budget zero; raw token embeddings used by generation are not encoder forward calls. Hooks enforce first-block/decoder/encoder limits; input-generation slots are reserved before each generate call.
- Synthetic tests, including actual pinned learned cascade/residual quantizer arithmetic and future-code isolation, run before released-checkpoint inference and are outside the study-input budget.

Persist a started attempt before model loading, per-input generation allocations and completed comparator/trajectory records, counts and errors on failure. Failed calls consume their reserved input-evaluation slots and actual observed forwards; no replacement run. Any extra evaluation after a partial failure requires a dated explicit protocol amendment before execution, within the two-candidate cap, not a silent retry. Structural failures stop the screen; ordinary invalid model outputs remain results. Require all 32 paired records and unchanged generator/tokenizer state fingerprints before declaring completion. Check peak allocated CUDA memory within the declared fit ceiling.

## Correctness, analysis, and decision

Before interpreting opportunity, require exact comparator/adapter final token IDs and decoded text for every input; actual prefix checks must pass. Preserve all raw comparator outputs, full 12-level adapter records/code IDs, independent validator labels, official diagnostics, and reference/clue/unit errors with parseable coverage. Reference equality is secondary; primary validity is parseability, completeness, row/column/box validity and supplied-clue preservation. Independently recompute acceptance with the R1A metric-based test. Retain malformed/never-valid outcomes. No solution/reference or future label enters generation or an online policy.

Report all per-level primary-valid counts, reference agreement, official solved/cell/valid-grid metrics, mean wrong reference/given/empty cells with undefined coverage, first-valid histogram, all early-valid identities and never-valid identities. Keep each candidate separate; do not pool as independent evidence.

**Gate:** at least one independently verified primary-valid output before level 12 qualifies that candidate for R3. Otherwise close that candidate after 32 inputs. Run medium only after a complete, parity-passing easy result with zero early-valid inputs. If both are negative, close the frozen-Sudoku first-valid line at this budget. Zero in 32 is not a population impossibility result. Screening supplies no latency, cost benefit, new hard-Sudoku go, or Phase 2 authorization. R3 requires a separate work order and a frozen opportunity/cost audit; do not run R3 in R2.

## Deliverables and verification

New candidate manifests, preflight/access metadata, every attempt, raw outputs, per-level analysis/CSV, a Markdown report and scientific comparison figure, source/input/output hashes, tests, and completion evidence under results/followup/sudoku_checkpoint_screen/. Verify labels/counts/parity declarations/hashes/selection/budget and candidate ordering model-free, without importing torch/matplotlib; it does not rerun CUDA parity. Keep original Phase 1/R1A/R1B empirical and completion artifacts unchanged. Archive the current compatibility review before updating it for the new suite/source hashes. Update README/roadmaps/limitations; commit/push R2 to main and verify local/GitHub equality. Stop at R2.
