# Stronger research S0A: evidence and access inventory

Completed October 23, 2026. Documentation and provenance inspection only; no S1 opportunity search or new scientific outcomes. Starting checkout verified as `C:/Users/Admin/Documents/Projects/Anytime-NCM`, clean `main`, origin `https://github.com/yoonalexander/Anytime-NCM.git`; local and remote main both `06c7b3ddb22e798e4302cf4d816053172f701bd4`. The roadmap's `a9d79c4...` starting snapshot describes its creation context, not the current checkout.

## Provenance and availability

The accompanying [inventory manifest](stronger-research-inventory.json) records current byte digests of the selected evidence, all 192 S1-eligible identity/group records, and local presence/size of pinned external assets. It contains no new quality calculations or exit assignments. Identity selection is derived exclusively from the historical input manifest. Hashing a saved trajectory file does not interpret its outputs. Checkpoint/data digests below are recorded historical values; heavy files were not rehashed, unpickled, loaded into models or downloaded in S0. Presence/size is not integrity verification.

| Item | Revision / evidence |
| --- | --- |
| Upstream NCM | `c70274273f489abc73832b2b98584a8483b6b203`; current submodule at that commit, unchanged by S0 |
| Released generator/tokenizer repository | `hazyresearch/ncm-checkpoints`, `d342ce8aaea58830eef3b8ad473664673e41f692` |
| Released evaluation data | `hazyresearch/ncm-datasets`, `6580ba41a4b0a976dde876fbe84d25327617b0e6` |
| Hard Sudoku file digests | [setup inventory](../../results/setup/artifacts.json), [setup sources](../../configs/setup_sources.json) |
| Easy/medium file digests and pinned URLs | [R2 sources](../../configs/r2_sources.json); all difficulty solution files share digest `b52de75f5e4642adca58b18967bcd4bbcafa699c61b21ac33ee0fd7389e0d576` |
| WMT files and pinned URLs | [WMT sources](../../configs/phase4_wmt_sources.json); generator `ae580cbbb400a27b30c616634745d4c9cfa8b66806f936c6c26041e5b9640d4f`, tokenizer `74f04176a3cd985e4142761bd7464ea6edb44dc0025c40302b5e45ea0d865702` |
| WMT text tokenizer | Qwen/Qwen3-0.6B revision `c1899de289a04d12100db370d81485cdf75e47ca`; tokenizer files only, no Qwen LM weights |
| Executed source versions | [4A receipt](../../results/phase4/wmt14/4a.json), [4B receipt](../../results/phase4/wmt14/4b.json), and their `source_sha256` / byte-exact `source_snapshots`; historical receipts take precedence over assuming today's reporting code ran then |
| Recorded inference environment | RTX 5060, WSL2 Ubuntu 24.04, Python 3.12.3, Torch 2.10.0+cu128 / CUDA 12.8, float32/eval, four CPU threads; [4A record](../../results/phase4/wmt14/4a.json). Not newly revalidated in S0 |

Sudoku uses 12 levels, widths `1,2,4,6,9,13,18,26,37,50,67,89`, 322 cumulative codes, full-resolution 89-ID decode / 81 cells. WMT uses 11 levels, widths `1,4,8,14,20,26,32,40,48,56,64`, 313 cumulative codes, 96-ID effective source prefix and 64 target IDs before EOS/filtering. The WMT learned reconstruction cascade includes GroupNorm and differs from Sudoku. [Reconstruction contract](../phase1b_partial_decoding.md), [WMT protocol](phase4-wmt14-protocol.md), [4A checks](../../results/phase4/wmt14/4a_completion.json).

## Identity, reservations and previous exposure

These categories describe recorded access, not a claim to reconstruct every analyst's memory. Prior summaries, plots and the viewer exposed exploration/development results. Official aggregate baseline evaluation also scored released final/reserved examples internally. Checkpoint-training overlap and WMT news-document clustering are unknown. None of the public data can be advertised as contamination-free.

| Population | Exact identity authority and recorded use | Current classification / S0-S1 access |
| --- | --- | --- |
| Hard Sudoku exploration | [hard manifest](../partitions/sudoku-hard.json), 1,000 input-token SHA-256 identities, seed 20261020 | Explored; all 1,000 audited. R1A reuses these; R1B indices 0–31 reuse their references. Historical evidence only in S0 |
| Hard Sudoku development | Same manifest, 400 | Used for audit, selection and profiling; development, not confirmation |
| Hard Sudoku phase2_final / phase3_final | Same manifest, 300 / 300 | Original reservations; hard full baseline scored them aggregate-only. Later *easy* final studies consume aligned solution groups. Do not reclaim related hard boards as fresh confirmation |
| Easy Sudoku exploration / development | [easy manifest](../partitions/sudoku-easy-r2.json), inherited hard row/solution partitions, 1,000 / 400 | R2 indices 0–31 reused in R3; all 1,400 audited; Phase 3 fitting and policy selection also reuse these |
| Easy phase2_final / phase3_final | Same manifest, 300 / 300 | Consumed by corresponding frozen online studies; no new final access in S0/S1 |
| Medium Sudoku | [medium manifest](../partitions/sudoku-medium-r2.json), same 1,000/400/300/300 allocation | Only indices 0–31 screened per R2. Other boards unused by that adaptive screen, but aligned solutions and other difficulties have exposure. Not independent or newly authorized |
| WMT exploration | [WMT manifest](../partitions/wmt14-phase4.json), 512 effective-prefix groups | First 128 canonical indices audited; these alone eligible for S1 exploration. Remaining 384 not audited by Phase 4 adaptive study; aggregate baseline exposure only, excluding any separately documented use |
| WMT development | Same manifest, 256 groups | First 64 canonical indices audited and benchmarked; these alone eligible for S1 development. Remaining 192 aggregate-baseline-exposed only under the recorded protocol |
| WMT phase4_final | Same manifest, 256 groups | Consumed frozen final comparison; excluded from S1, including raw final request records |
| WMT reserved | Same manifest, 1,979 groups | Not used for adaptive analysis under Phase 4; aggregate-baseline-exposed only. Not authorized for S0/S1 or automatically fresh confirmation |

The WMT manifest has 3,003 unique effective prefixes, no grouped aliases in this release. Identity is SHA-256 of compact JSON of the official truncated first-96/padded token IDs; group canonical index is the minimum row index. First 32 official groups were forced into exploration before seeded allocation. S1 membership is first 128/64 by ascending canonical index, never by outcome. The JSON companion explicitly lists them and hashes the parent manifest (`9cbd6503cb440b72f14296dc35d2c1054060f8c2ceebc26ae3349c348768dacb`). Sources longer than the cap (24 recorded rows) and effective-prefix equivalence matter for any future evaluation.

Sudoku identity hashes full input-token lists; easy/medium inherit hard row reservations because released solution files are identical. Input hashing for all rows was disclosed separately from board/reference access in [R2](../../results/followup/sudoku_checkpoint_screen/summary.md). Shared solutions must stay grouped in a new study. WMT lacks document clusters, so identity bootstrap cannot recover document-level uncertainty. Unknown overlap is not equivalent to no overlap.

## Evidence inventory and claim-to-evidence map

Each observation below is inherited from completed records, not a new S0 analysis. Historical final aggregate reports may be cited; raw final outputs need not be reopened. No counts from overlapping studies should be summed as independent trials.

| ID / claim | Existing protocol and primary evidence | Status and missing evidence |
| --- | --- | --- |
| C1: tested hard/easy Sudoku prefixes have no early exact valid answer | [initial protocol](../experiment_protocol.md), [hard analysis](../../results/phase1/analysis.json), [hard metadata](../../results/phase1/trajectories.metadata.json); [R3 protocol](sudoku-easy-r3-protocol.md), [easy analysis](../../results/followup/sudoku_easy_r3/analysis.json), [receipt](../../results/followup/sudoku_easy_r3/completion.json) | Established finite observation: 1,400 trajectories per difficulty, zero before level 12. Does not rule out other codes/checkpoints or tasks |
| C2: poor early Sudoku output is not explained solely by erroneous generated target codes | [R1B protocol](sudoku-target-encoding-protocol.md), [analysis](../../results/followup/sudoku_target_encoding/analysis.json), [provenance](../../results/followup/sudoku_target_encoding/provenance.json), [receipt](../../results/followup/sudoku_target_encoding/completion.json) | 32 target encodings /384 decodes: final exact round trips, no early valid target boards. Narrows explanations; target-vs-generated batch/path asymmetry and decoder/training confounds remain. No causal mechanism established |
| C3: simple clue preservation does not suffice | [R1A plan](sudoku-prefix-diagnosis-plan.md), [analysis](../../results/followup/sudoku_prefix_diagnosis/analysis.json), [receipt](../../results/followup/sudoku_prefix_diagnosis/completion.json) | At final level clues/blanks can be correct while Sudoku constraints fail. R1A uses exploration only; descriptive, not mechanistic |
| C4: easy/medium screens also lack early valid boards | [R2 protocol](sudoku-checkpoint-screen-protocol.md), [report](../../results/followup/sudoku_checkpoint_screen/summary.md), [receipt](../../results/followup/sudoku_checkpoint_screen/completion.json) | 32 per difficulty, related solutions, easy final 32/32 and medium 31/32; bounded screen only |
| C5: actual Sudoku stopping did not improve latency | [Phase 2 protocol](phase2-easy-online-protocol.md), [analysis](../../results/phase2/analysis.json), [receipt](../../results/phase2/completion.json) | Selected verifier full depth, 0.85% mean overhead. Entry exception after failed offline gate. Not just a replay estimate |
| C6: learned current-validity stopping did not improve latency | [Phase 3 protocol](phase3-easy-learned-protocol.md), [training](../../results/phase3/training.json), [analysis](../../results/phase3/analysis.json), [receipt](../../results/phase3/completion.json) | Six CPU logistic fits, internal primary full depth, 2.98% overhead. Discrete-code statistics, not all transformer activations; no continuation estimator |
| C7: selected WMT rules cannot exit early under their own schedule | [Phase 4 protocol](phase4-wmt14-protocol.md), [audit selection](../../results/phase4/wmt14/audit_analysis.json), [policy lock](../../results/phase4/wmt14/policy_lock.json), [release](../../results/phase4/wmt14/policy_lock_release.json) | Minimum 10, patience 1, first observation cannot stop, next level 11 fallback; structural full-depth result. Does not characterize all possible assignments |
| C8: measured WMT primary comparison is negative | [final aggregate analysis](../../results/phase4/wmt14/analysis.json), [completion](../../results/phase4/wmt14/completion.json) | 1.95% overhead, identical outputs in selected comparison. Not evidence that all useful WMT early answers are absent |
| C9: useful mixed-exit WMT corpus frontier exists / does not exist | Saved [trajectories](../../results/phase4/wmt14/trajectories.jsonl), [audit](../../results/phase4/wmt14/audit_analysis.json), [development timing summary](../../results/phase4/wmt14/development_analysis.json) | Unresolved. Corpus-constrained assignment search not yet run. Negative heuristic search would not prove impossibility; arbitrary-exit latency unidentified |
| C10: representation/decoder, generator errors or stopping signal causes the bottleneck | C1–C4, [partial-decoding validation](../phase1b_partial_decoding.md), [WMT 4A](../../results/phase4/wmt14/4a.json) | Competing hypotheses, not established causes. Need saved diagnosis first; any target-encoded WMT or intervention separate and prospective |
| C11: continuation-value stopping helps | No trained continuation estimator in completed evidence | Untested. Current correctness and eventual failure are different targets. Opportunity, causal features, fresh evaluation and actual latency all missing |
| C12: viewer / CF bridge establishes safety or speedup | [viewer build](../../results/phase5/build.json), [bridge contract](../phase5_firewall_contract.md), [receipt](../../results/phase5/completion.json) | Unsupported benefit claim. Existing 3,468 matching saved forecasts /289 hard puzzles are display correspondence evidence only |
| C13: exact paper baseline reproduced | [original reproduction log](../reproduction_log.md), [paper Table 3](https://arxiv.org/html/2610.14162v1#S4.SS4) | Unresolved: local hard 86.25% vs published 86.1%, +0.15 percentage points. No causal explanation. No new reproduction/tuning in S0; only pursue a separately justified check if it would change interpretation |

Metric authority: exact Sudoku acceptance requires parsing, all cells, clue preservation and row/column/box constraints; reference equality and official cell accuracy are separate. WMT [metric implementation](../../src/anytime_ncm/wmt_metrics.py) uses corpus sacreBLEU 2.6.0: BLEU `nrefs:1|case:mixed|eff:no|tok:13a|smooth:exp|version:2.6.0`, chrF `nrefs:1|case:mixed|eff:yes|nc:6|nw:0|space:no|version:2.6.0`, beta 2. Numeric-F1 and literal negation mismatch are heuristics with coverage, not truth or safety certificates.

## Cost evidence and unresolved measurements

- [Hard profiles](../../results/phase1/profiles/run.json) and [easy profiles](../../results/followup/sudoku_easy_r3/profiles.json) sum separately instrumented components. They are not WMT timing calibration or actual interleaved request latency.
- WMT [4B requests](../../results/phase4/wmt14/4b_requests.jsonl) cover 64 development identities, four selected methods, three repeats, plus 32 exploration warmups. They measure full-depth output and two-inspection selected adaptive paths, not arbitrary depths. S0 inventories/hashes the file without analyzing its rows; future S1 must select timed development rows only.
- Frozen [4B execution](../../results/phase4/wmt14/4b.json) records 800 generations /8,800 sample-level evaluations /1,200 decodes. Full Phase 4 reports 7,163 /78,793 /11,035. Caps and actuals differ; do not reuse unspent caps as new authorization.
- Actual ready-output latency includes tokenization/preparation, generation, full-resolution reconstruction, decoding, transfers, text and policy. CUDA stream elapsed, level/code counts, component estimates and throughput are separate. No saved WMT per-depth generator/decoder decomposition identifies arbitrary early-exit latency.
- Repeats are not independent inputs; a fixed-assignment bootstrap ignores assignment-selection uncertainty. Single-process historical timing does not establish cross-process/hardware generalization.

R3's interrupted collection and [prospective resumption amendment](sudoku-easy-r3-resumption-amendment.md) remain part of the ledger, including [failed attempt](../../results/followup/sudoku_easy_r3/collection.failed_attempt_1.json). S0 does not refresh compatibility receipts, regenerate reports, rerun verifiers that analyze outcomes, or overwrite any historical artifact. The 433-test Phase 5 record is historical, not a fresh S0 suite.

## Research decision

S0A completes evidence/access mapping and the [bounded primary-source review](stronger-research-related-work.md). Existing evidence supports bounded negative findings and motivates an opportunity-versus-recognition question for saved WMT data. It does not justify a positive result, a causal explanation or immediate model work. S0B must freeze a finite, deterministic S1 protocol before any new assignment search. S1, S2 and all conditional branches remain unexecuted.
