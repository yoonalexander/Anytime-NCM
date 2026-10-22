# R1B: target-encoded Sudoku prefix diagnostic

**Declared:** October 22, 2026 (America/Toronto), before reference encoding or inspection of target-encoded outputs.
**Study:** R1B / sudoku_target_encoding, revision 1.
**Base repository:** `ee043228ede0a95a82bf6033211a2168d7ec3add`.
**Role:** A reference-based, exploration-only diagnostic. Encoded references are unavailable to a deployed stopping policy. No online speedup, final-holdout result, causal attribution, or new Phase 2 go is claimed by this pilot.

## Frozen selection and sources

Select exactly the first 32 exploration identities by original dataset index from the unchanged manifest: indices 0–31. Do not choose examples based on R1A errors. Use the existing selective reader with exactly `{"exploration": 32}`; materialize only their puzzles and valid references. No development or final-holdout token rows may enter this study.

The generated comparison is the corresponding first 32 records of the original complete Phase 1 JSONL. Verify the complete file checksum, manifest/order, and collection metadata before parsing those 32 records. Do not deserialize later trajectories or generate replacements. The original batch-up-to-128 generated outputs and the batch-one target reconstruction have different production paths; differences cannot by themselves isolate a causal component.

| Source | Frozen revision or SHA-256 |
| --- | --- |
| Upstream | `c70274273f489abc73832b2b98584a8483b6b203` |
| Model revision | `d342ce8aaea58830eef3b8ad473664673e41f692` |
| Dataset revision | `6580ba41a4b0a976dde876fbe84d25327617b0e6` |
| Original trajectories | `2baf2948df953d7f379f9b359091c9a40d31fe9ecafe29f99305ff8bb3e0f5d9` |
| Original collection metadata | `c873d0f584173cbdf17e0b19f787a41a512a8db2170e45a0a01fe4a6543df342` |
| Original protocol | `557cf1377fe49b6c8515f506856ff0a395f8aaabe32adc79c25a8f2d9a3929ef` |
| Original manifest | `ed7a6b3c102fe4713a3f80f8f02b53afe37a44b53da80964936467617799bdb7` |

Validate the exact pinned tokenizer checkpoint/config and dataset hashes, a clean unchanged upstream checkout, float32 parameters, evaluation mode, deterministic nearest-code selection, and the released 12-level schedule. Do not change original sources or sampling behavior.

## Encoding, reconstruction, and fixed execution budget

Use the normal upstream `VQVAE.encode(reference_ids)` entry point, which includes the official pre-quantization normalization/dropout path followed by `vq.z_to_idx`. Do not bypass normalization or use puzzle/context tokens as the target. Targets have shape [1, 89], legal complete Sudoku target tokens, and no BOS/padding. Encoding is deterministic in eval mode; stochastic encoding must be disabled.

Run batch size 1, one existing RTX 5060 GPU, four CPU threads, float32/no autocast/no compilation, without generator construction, generator checkpoint loading, generator calls, stochastic samples, warmups, timing instrumentation, or model training.

Fixed released-checkpoint work:

- Exactly 32 reference encodings, once per selected identity.
- Exactly 384 cumulative full-resolution monitored prefix reconstructions and decoder evaluations: 12 per encoded reference.
- Additionally, exactly 32 **latent-only** upstream `vq.idx_to_z_q` final-reconstruction parity checks, one per input. These verification reconstructions are declared here before execution; they add no encoder, decoder, or generator evaluation.
- Parameter/buffer fingerprints before and after the pilot, tensor shape/finiteness/code-range checks, and independent snapshot-storage checks. These do not add model forward passes.
- Synthetic prefix/future-code-isolation and encoding-contract tests precede pilot inference; synthetic fixtures are separate from released-checkpoint study inputs.

Reconstruct monitored prefixes with the existing source-pinned, independently tested full-resolution cumulative helper. Clone snapshots inside the accumulation loop. Require distinct storage for all 12 snapshots and exact final-latent equality against the additional upstream reconstruction. Decode each prefix exactly once using the actual pinned decoder and evaluator token-selection/text helpers. At the final level the parity-checked official latent may be used for that same single decoder evaluation; do not perform a second full-depth decode.

Encoding and decoder prehooks enforce hard per-input and total forward budgets. Preserve a started/completed/failed attempt record, actual counts, every completed input record, and the reason for a failure. Do not silently retry, drop an input, substitute an example, or add a seed. If execution fails after model calls, retain their counts and require a dated explicit amendment before additional released-checkpoint evaluations.

## Checks before interpreting target quality

1. Validate reference/puzzle contracts and target token shape/format.
2. Pass synthetic tests for upstream encoding delegation, normalization, eval/stochastic rejection, code shape/ranges, full-resolution prefix decoding, storage isolation, and suffix-code isolation.
3. Require real final latent parity and recorded storage/shape checks. A contract/parity failure blocks scientific interpretation until resolved within a documented scope.
4. Retain final decoded mismatches as **data**, not infrastructure failures. Report all indices for:
   - primary-invalid final reconstructions;
   - final parsed-board reference disagreement;
   - final decoded-token inequality to the original target.
5. Require unchanged tokenizer parameters/buffers and actual forward counts equal to the frozen budget before marking the pilot complete.

Final reference round-trip success is measured at the token, parsed-board, and primary-validity levels. Primary validity requires parseability, completeness, row/column/box validity, and clue preservation; reference equality remains separate.

## Predeclared analysis

For both target-encoded and saved-generated paths, retain all 12 levels, raw selected token IDs/text, parsed boards, primary/secondary flags, and R1A reference/clue/blank/unit error counts. Store full per-level distributions with defined/undefined coverage and given/empty position denominators. Retain the existing distinction that official cell scoring can reward truncated strings.

Summarize first-valid levels, ever/early/final validity, exact and board-level final round trips, and paired per-level differences. Track all 11 adjacent boundaries with R1A corrected/corrupted/wrong-to-different-wrong definitions and identities. There are 384 newly decoded target states, 384 cached generated states, and 352 transitions per path. There is no new timing analysis or sample-size expansion.

Show levels 10–12, clue preservation, and final failure lists prominently. Choose the lowest selected dataset index independently for each case: target early-valid with no generated early validity; target with no early validity; target final primary failure; target final token mismatch. Mark absent categories explicitly. Representatives may overlap; preserve every final failure outside the representative selection.

## Interpretation and next branch

- Early valid target prefixes would establish that an early acceptable decoded solution is reachable by this target-encoding path for those examples. They would not make references deployable or prove that fixing only the generator is sufficient.
- If neither path solves early but final target round trips succeed, the tested target prefixes also fail exact validity. Treat tokenizer/decoder limitations as a hypothesis, not a proof that no alternative code combination or decoder can work.
- Final target mismatches require diagnosing reconstruction quality or compatibility; they do not automatically show that the original generated-prefix adapter was wrong.
- Keep structural contract failures separate from ordinary quality failures. Pilot outcomes are descriptive, development is not used, and no population absence claim follows from 32 inputs.
- Close with one explicit recommendation: R2 bounded checkpoint screening, a separately scoped tokenizer/generator intervention, or closure. Do not start that branch, change the original hard-Sudoku no-go, train a controller, or open either final holdout.

## Artifacts, verification, and delivery

Write a fresh `results/followup/sudoku_target_encoding/` directory with raw target records, call-count/attempt metadata, analysis JSON, paired board/transition CSVs, a Markdown diagnosis memo, figures, source/input/output hashes, tests, and completion evidence. Existing evidence is preserved. Provide model-free verification that selectively reloads only 32 references and cached comparison records, recomputes all labels/statistics, and checks budget, source/artifact integrity, storage/parity declarations, and failure coverage. Do not claim that a model-free verifier reruns latent parity.

Run the appropriate full tests, inspect figures, update the roadmap, commit, push to main, and verify remote equality. Historical empirical artifacts and completed R1A evidence remain unchanged. Archive the current compatibility review before refreshing repository navigation/source audit metadata if necessary.
