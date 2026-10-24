# S2A prospective saved-data diagnosis

Frozen October 24, 2026 after S1 commit ebf85f6667bb36fae8ebef500c3329988ad4902c, before the new diagnosis calculations. The user requested the full roadmap subject to scientific gates. S1 found point-feasible WMT mixed exits but failed quality noninferiority bounds and cannot identify actual early-exit latency. S2A asks which failure explanations the saved evidence can distinguish, and whether more model work would change the decision.

## Population and access

Exactly the same 128 exploration and 64 development effective-prefix identities frozen in the S0A inventory. Reuse S1's header-filtered reader, identity/level schema checks and restricted selected-reference-string reader. No final/reserved data, model/decoder/encoder calls, target encoding, source retokenization, fit, external judge or new search. R1A/R1B are reused through their saved aggregate analyses/receipts; do not repeat their target-encoding pilot. Unknown training overlap, related Sudoku solutions and reused development status remain explicit.

## Frozen calculations

Compute once, by split, at each of 11 levels and 10 adjacent transitions (2,112 saved states /1,920 transitions total):

1. **Content emergence:** macro reference-word recall using sets from Python Unicode regex `\b\w+\b` after casefolding, intersection size divided by reference-set size. Empty reference sets are unavailable with coverage. This lexical similarity is not semantic completeness or truth.
2. **Revisions:** sentence chrF using sacreBLEU 2.6.0, beta 2 and the same character-order defaults. Classify adjacent changes as improvement >1e-12, deterioration <-1e-12, or unchanged. Report the macro change, count and denominator; never label this corpus chrF or factual damage.
3. **Visible/final agreement:** counts of exact saved text equality to that input's level-11 output, and independently exact 64-ID equality. Report first early text match and any match before 11 per input; these use future outputs retrospectively, not causal policy inputs. Match to full depth is not match to reference or semantic correctness.
4. **Cue persistence:** reuse exact numeric/negation cue extraction. Count references with digit numbers, references with a numeric token missing from every prefix including final, references whose required negation cue is absent at every level, and final cue mismatch. Empty coverage is unavailable. Do not expand cues or treat a lexical mismatch as a proven error.
5. **Search limitation:** for retained O1 vectors, report exit histogram, number changed from full, mean levels/codes, and mean sentence-chrF change relative to full. No new candidates or oracle fitting. The same 10,000-slot budget at different split sizes permits different optimization progress; this confounds interpreting exploration/development differences as generalization.

Only use S1's already selected exploration examples (at most five; first three canonical plus predeclared gain/damage extremes); do not select more examples or use development examples. Report absent categories as absent. Corpus quality remains the S1 corpus result; sentence diagnostics cannot replace it.

## Competing explanations and decision

For representation/decoder limitations, generated-code errors, decoder sensitivity, stopping-signal weakness and measurement/protocol constraints, record support, counterevidence, unresolved confounds and a falsifiable next check. No mechanism is established from these summaries. Give a reasoned decision on S2B: run new target encoding only if a specific unresolved localization question would change an actionable scientific decision under the existing gate. A justified decision not to collect more data completes S2A. S3 remains blocked unless S1's practical-headroom entry is met; S4 requires a specifically supported intervention, not dissatisfaction with a result.

## Numeric resources, failure and outputs

One deterministic pass, no restarts. CPU <=4 threads, analysis RSS <=2 GiB, <=256 MiB new artifacts, <=2 cumulative wall hours including implementation/validation/failed attempts, $0. At most 192 trajectories, 2,112 states, 1,920 transitions, 22 level summaries and five reused exploration examples. Model counters (encodings, requests, sample-level evaluations, decoder forwards, warmups, parity/repeats/retries), fits and new-final access all zero. Missing/provenance failures stop the analysis; no replacements or model regeneration. Save failed attempts before any amendment.

Outputs under results/stronger_research/s2a/: protocol/source/input digests, numeric diagnostics, per-identity diagnosis rows, limitations, competing-explanation table and branch decisions. Code/aggregation checks use synthetic fixtures before real data. Preserve historical protocols/artifacts. Commit/push this protocol before diagnosis, then commit/push the completed S2A report and verify remote equality. Subsequent S5 synthesis can proceed with appropriately deferred branches; no submission/contact is authorized.
