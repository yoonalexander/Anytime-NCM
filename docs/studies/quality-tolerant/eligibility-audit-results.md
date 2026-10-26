# Eligibility and statistical-method audit: complete; current route does not clear the gate

October26,2026. The user-authorized bounded audit is complete. **We now have actual candidate-population coverage and document-group counts, plus a validated conditional cue-bound implementation. The current population/method combination still cannot certify the unchanged quality margins; Q2 is not ready.** No model checkpoint, model output, controller fit, target encoding or actual-latency experiment was used. This adds evidence about feasibility, not model benefit.

[Combined decision](../../../results/quality_tolerant/eligibility_audit/completion-decision.json), [protocol](eligibility-audit-protocol.md), [numeric lock](eligibility-audit-lock.json), [original source lock](eligibility-audit-source-lock.json), [metadata completion](../../../results/quality_tolerant/eligibility_audit/metadata_correction/decision.json). The lock was pushed as5c15db347bf188cbc9a31388a35ff07dcbc8a443 before tests, simulation, download or tokenization. Both execution entry points verified clean local/live main.

## What was measured about the candidate data

Six official de-en source/reference SGML pairs, with pinned MD5 and recorded SHA256, supplied13,955 rows and751 official documents. Every source/reference document/segment sequence aligned. Bare source tokenization reproduced all3,003 historical WMT14 effective-prefix identities before any new tokenization. No model framework was imported.

| Official test set | Audited source/reference pairs |
| --- | ---: |
| newstest2015 |2,169|
| newstest2016 |2,999|
| newstest2017 |3,004|
| newstest2018 |2,998|
| newstest2019 |2,000|
| newstest2020 |785|
| Total |13,955|

The frozen source-hash/normalization/effective-prefix alias rules removed14 duplicate representatives. Complete components above128 canonical inputs excluded754 further inputs. No historical-overlap exclusion was found by these declared source/prefix/document-label checks; this does not establish absence of semantic near duplicates or checkpoint training overlap. The retained population has13,187 canonical inputs in744 document/alias components. No numeric enrichment or quality filtering occurred.

The one frozen component-hash allocation produced:

| Outcome-free allocation | Development | Proposed confirmation |
| --- | ---: | ---: |
| Canonical inputs |5,487|7,700|
| Document/alias components |297|447|
| Numeric-covered references |1,229|1,778|
| Components with numeric coverage |269|391|
| Largest component input share |2.059%|**1.104%**|
| Largest component numeric share |1.465%|1.631%|
| Input weight concentration proxy n_eff |175.66|286.31|
| Numeric weight concentration proxy n_eff |157.78|227.43|

[Aggregate inventory](../../../results/quality_tolerant/eligibility_audit/metadata_correction/population-summary.json), [source-only split manifest](../../../results/quality_tolerant/eligibility_audit/metadata_correction/split-manifest.json), [acquisition/header receipt](../../../results/quality_tolerant/eligibility_audit/metadata_correction/acquisition.json). The concentration proxies are descriptions of weights, not independent-sample counts or power certificates.

The count floors pass, but the predeclared confirmation maximum input share<=1% fails: the largest component contributes85/7,700 inputs. Do not silently drop that component, change the128 size restriction or reseed the split. Confirmation numeric share meets its separate<=2% operational screen, yet the statistical bound below still fails. Component-disjoint allocation is established under the declared rules; independent news stories, training-cleanliness and representativeness of future news are not established.

Reference inspection was machine-only cue-presence/alignment. Private metadata includes coverage flags and hashed source fields, with no source/reference text export. New source/reference archives and private flags remain ignored under data/. Public manifests contain no per-input numeric flags. This creates disclosed aggregate reference-derived exposure for the proposed new confirmation pool. Existing E3/E4/unallocated model outputs and all historical reference bodies stayed unread. No corpus text is added to Git. Official benchmark research-use context was recorded; an unrestricted redistribution license is not asserted.

## What the statistical audit establishes

The prospective candidate upper-bounds the original paired signed numeric/negation loss using positive paired-loss contributions and known document weights. It allows arbitrary dependence within a component, while requiring independence between components conditional on their sizes/coverage. The [protocol](eligibility-audit-protocol.md) gives the convexity/Markov/KL derivation and conservative root inversion. The point endpoint remains the original input-weighted mean; no unweighted-document or reference-negative-only metric is substituted.

**Scope matters:** this is a conditional known-count expected-loss bound. It is not automatically a bound for a ratio of unconditional expected document totals, nor proof that actual news components satisfy the independence assumption. The earlier fixed-M128 empirical-Bernstein reference is preserved rather than retroactively repaired. No real outcomes were read to choose a method or to infer a loss rate.

All48,000 prospective synthetic datasets completed exactly once:24 cases of2,000, with J128/512/1024, balanced or uneven sizes, risks0/.005/.02/.03 and perfectly shared losses within each document. Both cue endpoints share simulated flags. All frozen boundary/outside sanity checks passed. The source-header continuation reused these results, with **zero additional simulations**.

| Synthetic independent-component scenario, adverse risk.005 | Two-cue NI rate | Two-cue NI + retained half-margin precision | Lower99% bound on latter |
| --- | ---: | ---: | ---: |
|128 balanced components|0%|0%|0%|
|512 balanced components|51.85%|7.90%|6.42%|
|1,024 balanced components|96.10%|**92.10%**|**90.42%**|
|128/512/1,024 uneven components|0% in each case|0% in each case|0%|

Only the1,024-balanced scenario clears the frozen>=80% lower-confidence power/precision screen. These are invented cue-loss distributions, not translations, whole-study power or a guarantee for the real metadata distribution. The fixed EB reference does not become feasible. The deterministic cross-component-dependence negative control has exact false-NI probability.98 under one shared Bernoulli(.02) flag, showing why changing sentences to document labels alone does not validate independence.

[Full synthetic results](../../../results/quality_tolerant/eligibility_audit/method-results.json). There are no bootstrap draws. BLEU/chrF cluster-bootstrap coverage, actual request-time uncertainty, all fixed-depth contrasts and full joint-gate power remain unvalidated by this cue-only audit. Keep the original alpha_claim=.025, alpha_exclusions=.025/40, unchanged margins and all fixed controls. No fixed depth is statistically excluded here.

## What the real counts imply under the audited bound

No translation losses were measured. The following are **hypothetical best-case zero-positive-loss upper bounds**, computed from source/reference count metadata alone:

| Fixed split | Numeric-reference loss upper bound | Negation-mismatch increase upper bound | Required margin |
| --- | ---: | ---: | ---: |
| Development |0.053659|0.075499|<=0.02|
| Proposed confirmation |**0.059884**|**0.040554**|<=0.02|

The conditional bound cannot pass either confirmation cue endpoint even with zero observed adverse losses. Raw numeric coverage1,778 therefore does not fix the obstruction: a few larger components can carry much of the input-weighted risk. This is an identified limitation of this frame plus this conservative bound, not proof that all cluster methods fail, not an observation of actual cue degradation, and not a universal75,000-example requirement. No synthetic risk is assigned to the actual checkpoint.

## Preserved parser failure and prospective correction

The first metadata attempt rejected the official language header as `Wrong source language`. All six official files in fact use srclang="any"; the paired reference has trglang="en". The original parser incorrectly accepted only explicit de/deu/ger labels. The checksum-pinned member names establish the intended de-en direction. The stop occurred before creation of any new segment records or inspection of reference rows; the first allowed source member was UTF-8 decoded for the failed header check.

That attempt, its36 passing tests,48,000 synthetic results, receipts and original source were preserved unchanged. A [prospective correction protocol](eligibility-audit-metadata-correction-protocol.md), [numeric lock](eligibility-audit-metadata-correction-lock.json), [source lock](eligibility-audit-metadata-correction-source-lock.json) and12 invented header tests were pushed asdd4fd66e67405c994fa06a68b68025f0c23608bb before continuation. The wrapper records original attributes, accepts standard labels/any only with the pinned member pair, rejects contradictory languages, and changes no segment bytes.

The correction reused the2015 archive without another GET. Because the interrupted process had not persisted its historical duplicate-hash sets, it re-materialized3,003 historical **source** strings; that extra source-only pass was explicitly budgeted before continuation. It reused the original3,003-prefix parity and did not repeat historical tokenization, any simulation or any model operation. No further correction/retry is authorized. The parser issue is resolved; the remaining no-go is statistical/eligibility, not that parser error.

## Work, preservation and stopping decision

36 original deterministic tests plus12 header tests passed; this is48 focused tests across the two preserved executions, not a full-suite rerun. Tests cover root inversion/zero formulas, invalid coverage, weighting, fractional losses, exact heterogeneous finite-support checks, parser boundaries, aliases, complete historical/oversize component exclusion, deterministic splits and private flags.

Cumulative work:13,955 new source segment records;13,955 new reference cue-presence records;6,006 historical source materializations including the declared correction;16,958 source tokenizations;48,000 synthetic datasets;6 GETs;23,674,436 transport bytes;77,301,760 decompressed bytes. No historical reference, model outcome, model load/request, learned encoder/decoder, target tokenization, fit/training, Q1 search or bootstrap. First execution13.555s and correction23.313s, about36.87s cumulative; peak RSS265,699,328bytes;$0. A14,400-second conservative preparation/reporting charge remains below the18,000-second total allowance. Data/body storage and execution counters stay within the amended caps.

The original lock/failed metadata attempt and correction source snapshots are retained. Hash verification checks898 first-attempt and914 continuation source/artifact/protection entries, without replaying simulations or re-parsing data. [First execution](../../../results/quality_tolerant/eligibility_audit/execution.json), [continuation execution](../../../results/quality_tolerant/eligibility_audit/metadata_correction/execution.json), [preserved failure](../../../results/quality_tolerant/eligibility_audit/metadata-failure.json), [combined decision](../../../results/quality_tolerant/eligibility_audit/completion-decision.json).

**Decision:** close this bounded audit as complete and no-go for launching Q2 under the current population/method combination. Do not spend model compute, relax the margins, remove inconvenient documents or reallocate reservations. Q1's9.67%/7.73% projected oracle headroom remains an exploratory hypothesis. A materially different prospectively justified method and matching inference population could be considered separately, but its success must not be assumed and no further execution follows this audit. The original Q0 failed gate remains failed.
