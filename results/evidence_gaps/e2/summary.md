# E2 exact-final-text diagnostic: bounded no-go

October 24, 2026. **Early exact-final-text outputs exist on 43/256 assigned WMT audit inputs, but the frozen every-level oracle execution is slower than full depth.** This closes E2 with a bounded negative result. It does not establish absence of useful approximate early translations, absence of cheaper inspection schedules, or failure of every possible controller. E3 controller development and E4 confirmation remain sealed and unexecuted.

## Frozen question and access

The [prospective protocol](../../../docs/studies/evidence-gaps/e2-protocol.md), [numeric lock](../../../docs/studies/evidence-gaps/e2-lock.json), implementation and 96-test receipt were committed/pushed at `d88b7c495df37635b3497661e3e9b56169c1576f` before access. Local and live GitHub main equality was checked. E1 had observed cheaper forced paths, while E0 blocked the proposed nonidentical-output rules under its sparse-cue method. E2 therefore **prospectively** retained only O-exact and all 11 fixed-depth controls, reducing the planned comparison family from 89 to 59 intervals without relaxing any quality margin or increasing n.

The [access receipt](access-release.json) releases exactly the 256 `E2_audit` groups from [E0's immutable allocation](../e0/input-manifest.json). Its copied entry-level `outcome_access_released=false` values describe the original allocation; the E2 receipt's explicit trajectory/reference release supersedes access only for that role. The old manifest was not rewritten. These groups already had official aggregate-baseline exposure and E0 source-only hashing; unknown document and checkpoint-training overlap remain. This is new per-input **audit evidence**, not fresh policy confirmation. Only the 16 already exposed E1 identities supplied warmups. No E3/E4, consumed-final or other reserved output/reference bodies were accessed.

O-exact chooses the earliest level whose rendered string exactly equals the same input's level-11 string, otherwise 11. No normalization, reference-based choice, threshold search, fitting or subset selection occurred. Its timing receives the clairvoyantly assigned depth outside the clock and charges reconstruction/decoding at every visited level. This is actual request execution cost for the locked assignment, **not** online recognition or end-to-end search latency. Earliest exact depth is neither a certified minimum-latency assignment nor a global opportunity bound.

## Results

| Method | Mean ready-output latency, ms | Median, ms | p95, ms | Corpus BLEU | Corpus chrF | Quality versus full |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Exact assignment, every-level observations | 146.557 | 150.148 | 158.928 | 23.018 | 50.903 | Structurally identical text |
| Terminal fixed 10 | 118.469 | 118.714 | 125.582 | 19.277 | 47.013 | Fails adjusted BLEU/chrF bounds |
| Native terminal fixed 11 | 129.230 | 129.577 | 137.266 | 23.018 | 50.903 | Full-depth control |

All 12 methods and all intervals are in [analysis.json](analysis.json). The oracle's relative mean reduction versus full is **-13.407%**, with adjusted interval **[-15.208%, -11.310%]**; equivalently, **13.407% overhead**, interval [11.310%, 15.208%]. This interval's upper reduction bound is below the locked +5% practical target, giving `bounded_exact_no_go`. The two process-specific point reductions are -13.443% and -13.372%. These are measurements on this GPU/environment and assigned audit population, with limited two-process uncertainty information.

| Earliest exact-final-text level | Inputs |
| --- | ---: |
| 1–5 | 0 |
| 6 | 1 |
| 7 | 3 |
| 8 | 6 |
| 9 | 13 |
| 10 | 20 |
| 11 | 213 |

Early equality occurs on 16.797% of inputs, mostly near full depth; mean assigned depth is 10.683594. Level counts are work descriptors, not measured latency savings. Exact outputs preserve all deterministic text metrics relative to the full output by construction, conditional on verified execution parity. This does not establish the full output's correctness or safety.

All fixed depths 1–10 fail an adjusted corpus-quality endpoint, so full depth alone remains potentially feasible under the locked rule. For example, fixed 10 has BLEU difference -3.7411 with interval [-5.3757, -2.2709], and chrF difference -3.8906 with interval [-5.0439, -2.7786], wholly outside the allowed losses of 0.5 and 1.0. Fixed 10's lower latency therefore does not establish a matched-quality improvement. No comparator was dropped merely for uncertainty or sparse cue coverage.

Numeric-reference coverage is only 48/256. Under the narrowed family's conservative cue envelope, even zero adverse events require 385 covered examples to certify the 0.02 margin for a nonidentical rule; E0's obstruction remains. The exact rule's structural equality is a different mathematical statement from a finite sample with no observed errors. No nonidentical-output oracle was run or rescued with degenerate intervals.

## Statistics and verification

The frozen family includes 48 quality intervals and 11 cost intervals, with two-sided Bonferroni tail `0.05/(2*59)`. Exactly 100,000 shared PCG64 identity vectors and crossed process vectors, seed20261026, retained all methods together and nested repeats. E0's Monte Carlo guard used one-based tail rank 18, with its separately reported 0.001 numerical allowance. Corpus metrics sum sufficient statistics and match direct corpus scoring; they are not sentence-score averages. Cue intervals use the locked signed Clopper-Pearson envelope. Sampling-model/bootstrap limitations and unknown document dependence remain; adjusted intervals are not an exact population-coverage or hardware-generalization guarantee.

- [Execution receipt](execution.json): all 12,664 requests completed, with zero failures, replacements or retries; actual work 82,110 generator evaluations, 25,240 decoder forwards, zero encoder forwards. Counts are below the frozen maxima of 82,434 and 25,564.
- One collection process and two fresh timing processes (PIDs 381/404/688), three WMT model loads. The native full control and every scheduled intermediate observation matched collected code prefixes, IDs and text; warmups matched their existing cached trajectories. All three before/after model-state fingerprints match.
- [Pre-inference synthetic tests](../../../docs/studies/evidence-gaps/e2-lock-tests.xml): **96 passed** in 12.95 seconds. These were tiny untrained CPU/compatibility tests, not uncounted released-checkpoint calls. The historical 451-test full suite was not rerun.
- [Separate saved-record checker](independent-checks.json): all 12,664 request/start rows, actual work, source/archive hashes, parity/inspection hashes, 24 direct corpus scores, sparse-cue envelopes, quality classifications and all 11 crossed timing intervals passed. It reused the same locked draw vectors, made zero model calls and accessed no new identities. This is separate arithmetic by the same assistant, not independent human scientific review or an independently reimplemented corpus-bootstrap engine.
- [Byte-exact executed sources](execution-sources.zip), [asset preflight](preflight.json), [trajectory record](trajectories.jsonl), [derived timing schedule](timing-schedule.json) and three process receipts preserve what ran. All historical tracked protocols and evidence remained unchanged.

Model orchestration took **1,129.041 seconds**; analysis took **32.116 seconds**. Charge the full three-hour preparation/reporting allowance conservatively, for 11,961.157 seconds total, within the separate four-hour model and four-hour CPU budgets. Analysis peak RSS was 758,616,064 bytes; the execution artifacts at the receipt were 23,806,383 bytes, below 8GiB/1GiB caps. Final closure artifacts add only small documentation/receipts. Process/GPU peaks and per-request CUDA stream spans are in the ledgers; CUDA span is not kernel busy time. Paid compute $0. There were 256 distinct new audit references, materialized once in execution and once for verification; neither the extra read nor timing repeats create new quality examples. Zero fits, target encodings, weight updates or new final outcomes.

## Interpretation and stopping decision

**Established:** this population has some early prefixes that render exactly the full answer; lack of all such prefixes is not the explanation here. With the locked every-level schedule, those late/sparse exits do not offset charged observation work, even when the exit assignment is provided clairvoyantly. The practical headroom/fixed-frontier gate fails before recognition is attempted.

**Still unresolved:** the usefulness of tolerated nonidentical outputs under adequately supported quality bounds; cheaper sparse observation schedules; a causal current/past signal for continuation value; document dependence and training overlap. This study does not isolate a decoder-only causal cost component or explain why the hierarchy produces particular intermediate texts.

**Stop:** no E3 controller fitting, E4 confirmation, target encoding, model intervention or submission/contact follows. An alternative schedule would require a specific hypothesis and a separate prospective gate/resource design, disclosing E2 as consumed audit/development data. Do not expand samples, margins or rules just to obtain a positive result. Human authorship/rights decisions and independent researcher review for the existing manuscript remain unresolved; this diagnostic report does not update or submit that historical manuscript automatically.
