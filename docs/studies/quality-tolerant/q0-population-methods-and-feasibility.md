# Q0 population/coverage audit: actual coverage and document overlap established

October25,2026. **Audit complete; Q1 remains statistically blocked and was not started.** Actual counts replace the earlier unknown-coverage/upper-bound assumptions. The consumed448-group pool has **92 numeric-covered groups**, and E4 has **191 of1,024**. E4 clears the new183 zero-adverse-event floor, but does not meet the unchanged power/precision planning criteria. Official document metadata is now validated:988 E4 inputs share documents with already consumed groups. Model outputs remained sealed; reference access was machine-only coverage counting, explicitly released and disclosed.

## Prospective lock, access and source provenance

Actual clean root `C:\Users\Admin\Documents\Projects\Anytime-NCM`, main, origin `https://github.com/yoonalexander/Anytime-NCM.git`, matched live main `d3f1cf1914c024c967ab0f39e2aaa871c3864a2f` before preparation. The [protocol](q0-population-protocol.md), [numeric lock](q0-population-lock.json), [source lock](q0-population-source-lock.json), implementation and tests were pushed as **`22d57ab7b23d197b1a4c7f9a7d5a9df6b96a756f`** before any real reference/source materialization or archive download. The runner verified clean local/live equality again.

[Access release](../../../results/quality_tolerant/q0_population/coverage-access-release.json) permitted exactly2,171 distinct reference materializations:128 S1 exploration,64 S1 development and1,979 E0 reserved-role groups. One machine-only pass tested the unchanged numeric regex. No reference text, number-cue lists, positive input IDs or per-input coverage flags were exported. No model output, F1 loss, BLEU/chrF quality, request timing, trajectory, fit, checkpoint or target encoding was accessed/generated. Original256 consumed-final references and576 other historical references were excluded; the parser scanned their uninterpreted serialization only.

This **does add aggregate reference-derived exposure** for E3/E4/unallocated roles. Their model outputs remain sealed, but future reports must not call their references wholly uninspected. Old manifests/protocols remain byte-identical with their original access flags; the new append-only receipt supersedes restrictions solely for this coverage audit. It does not authorize policy features, example enrichment, outcome evaluation, refitting or confirmation.

One public official WMT archive download used3,255,445 bytes. Its expected SacreBLEU MD5 matched; SHA256 is `f298b2435218a563268da99a66b21c03d925895c5f26fac82706e12b40b63619`. Only `test-full/newstest2014-deen-src.de.sgm` was opened/decoded. Other archive members were transported/decompressed as uninterpreted bytes, with zero body decodes. The archive remains under ignored `data/wmt14/q0_population/`; no corpus text was added to Git.

All **3,003 source rows matched exactly even before normalization**, and also matched the predeclared normalized comparison. Zero normalized source alias/cross-role alias groups were found. The validated [source-only document map](../../../results/quality_tolerant/q0_population/document-map.json) retains index, hashed official document label and segment ID, without text or cue flags. [Provenance](../../../results/quality_tolerant/q0_population/document-provenance.json) records hashes, sizes and exact alignment. The complete pinned corpus contains **164 official document labels**. This establishes grouping and cross-role overlap, not actual within-document outcome correlations or checkpoint-training independence.

## Actual numeric coverage

[Aggregate evidence](../../../results/quality_tolerant/q0_population/population-coverage.json):

| Fixed population | Groups | Numeric-covered groups | Official documents | Documents with numeric coverage |
| --- | ---: | ---: | ---: | ---: |
| S1 exploration, consumed |128|31|24|17|
| S1 development, consumed |64|13|31|11|
| E2 audit, consumed |256|48|116|38|
| Consumed S1/E2 union |448|**92**|132|53|
| E3 development, model outputs sealed |128|30|73|27|
| E4 confirmation, model outputs sealed |1,024|**191**|160|91|
| Closed unallocated, model outputs sealed |571|90|150|64|

The consumed union is31+13+48=92; it is no longer described only by its previous240 upper bound. E2's prior48/256 aggregate reproduces exactly. Counts do not score how well any model preserves numbers. Negation's denominator remains all groups; no reference-negative subpopulation endpoint was substituted.

## Consequences under the unchanged design

With the frozen split-error IUT design, .025 one-sided claim alpha and .02 cue margin:

- Consumed n=92: even the hypothetical zero-adverse upper bound is **.0393033**, above.02. It cannot certify the original numeric margin under this conservative envelope, regardless of re-reading references or adding timing repeats.
- E4 n=191: the zero-adverse upper bound is **.0191282**, so a zero-adverse sample could certify noninferiority. That alone does not establish a reliably powered design.
- At the prespecified Bernoulli adverse probability p=.005, exact E4 numeric NI power is **.383891**; at p=.01 it is **.146664**. These calculations optimistically assume independent covered groups and are planning examples, not observed model loss rates.
- The first covered count reaching80% NI power at p=.005 remains436. Even with zero adverse events, the retained half-margin precision target needs368 covered groups. At n191, exact probability of simultaneously meeting NI and that precision criterion is0 in the Bernoulli planning model.

Therefore this audit does not pass the Q0 feasibility gate. E4's raw count is enough for the exceptional all-zero NI case but inadequate for the frozen power/precision criteria. Corpus quality, all required latency contrasts and whole-study joint power remain unmeasured. No real data were used to switch interval methods, relax tolerances, redistribute alpha or select a favorable assignment.

## Document overlap: a concrete second limitation

Known consumed outcomes span704 groups:192 S1,256 E2 and256 original final. Their source rows belong to150 of the164 official document labels. No consumed-final references were decoded to establish this; its identity metadata and the source document map suffice.

| Model-output-sealed role | Documents shared with known consumed groups | Groups in shared documents | Numeric-covered groups in shared documents | Groups in disjoint documents | Numeric-covered groups in disjoint documents |
| --- | ---: | ---: | ---: | ---: | ---: |
| E3 development |71 of73|125 of128|29 of30|3|1|
| E4 confirmation |148 of160|**988 of1,024**|179 of191|**36**|**12**|
| Closed unallocated |139 of150|549 of571|83 of90|22|7|

E3 and E4 also share71 document labels with each other. Frozen sentence/prefix-level reservations therefore do not constitute document-disjoint development/confirmation. This is newly established overlap, not proof of measured prediction correlation, outcome leakage during this audit, or base-model training contamination.

The disjoint counts are diagnostics only. We did not remove shared-document rows, create new subsets, pool roles, backfill, move reservations or authorize access to any model output. Dropping988 E4 rows would change the population and leave only12 covered rows; it is not an authorized fix. Equally, treating191 covered sentences as191 independent documents would be incorrect: only91 document labels have any numeric coverage. Replacing the original equal-group endpoint with an unweighted document mean would change the estimand and was not done. A valid cluster-aware analysis with unequal sizes/covered denominators requires its own prospective design and power validation.

## Validation, preservation and resources

**87 focused tests passed**:23 new synthetic coverage/parser/access fixtures plus64 existing Q0/multiplicity regressions. Tests cover selective decoding with poisoned excluded UTF-8, rejection of executable pickle opcodes, forbidden consumed-final reference access, exact/disjoint memberships, aliases, source alignment, malformed document tags, aggregate-only outputs and exact planning arithmetic. Tests used invented strings, not real dataset bodies. No historical full suite or model verifier was run.

One successful audit consumed exactly2,171 references,3,003 pinned source strings,3,003 official German source strings and one3,255,445-byte GET. Execution took6.128 seconds, peak RSS123,604,992 bytes, $0. Caps were1800 measured seconds,1200 CPU seconds per process,one thread,2GiB,32MiB combined durable artifacts/download,8MiB transport,64MiB decompression and2MiB source member. Preparation/reporting is conservatively charged7200 seconds, separate from measured work. Original Q0/multiplicity/E0/E2 evidence/manifests and source/config files match protected hashes. The audit verifier checked68 source/artifact/preservation digests without re-reading any references.

[Execution](../../../results/quality_tolerant/q0_population/execution.json), [87-test JUnit](../../../results/quality_tolerant/q0_population/focused-tests.xml), [exact execution sources](../../../results/quality_tolerant/q0_population/execution-sources.zip), [access/work ledger](../../../results/quality_tolerant/q0_population/ledger.jsonl), [decision](../../../results/quality_tolerant/q0_population/decision.json).

## Decision and remaining step

**Population audit complete; Q1 not ready, not started.** We now have an actual coverage count and validated document provenance rather than uncertainty about those facts. The fixed populations do not satisfy the current power/precision design, and their document overlap requires a defensible grouping plan. Approximate early-translation quality/actual speedup and continuation-value recognition remain unknown.

A future empirical study would need an explicitly frozen, eligible population with enough numeric-covered groups, appropriate document-level reservation/inference and separate confirmation; alternatively, a separately justified design targeting a clearly stated inference population. This audit does not authorize a new corpus, selection/enrichment, reallocation, more inference or a revised gate. Further searches on consumed data could only be exploratory under a separate Q1 exception/protocol; they would not repair these confirmation limitations. All original quality/latency thresholds and historical failures remain intact.

Primary provenance: [WMT2014 official translation-task page](https://www.statmt.org/wmt14/translation-task.html), installed SacreBLEU2.6.0 dataset metadata frozen in the source lock, and the verified official source archive. Statistical calculations reuse the [locked multiplicity design](q0-multiplicity-protocol.md) and [SciPy exact binomial construction](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats._result_classes.BinomTestResult.proportion_ci.html). These sources do not establish document independence, training cleanliness, semantic correctness or model benefit.
