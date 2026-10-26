# Q1 exploratory results: approximate exits show headroom; confirmation remains blocked

October25,2026. The user-authorized exploratory Q1 exception is complete. Two sparse E2 oracle assignments meet the unchanged **point** quality tolerances and exceed the frozen projected5% screen after estimated observation costs. This is a positive exploratory result, not demonstrated online speedup or a passed Q0 gate. Q2 remains unstarted and unauthorized. No reserved model outputs were read.

The [protocol](q1-exploratory-protocol.md), [numeric lock](q1-exploratory-lock.json), [source lock](q1-exploratory-source-lock.json), implementation and tests were pushed in commit `be48446c928e07ab2f979a6f5468732a1b8dcab9`; execution independently verified matching clean local/live main before access. [Decision](../../../results/quality_tolerant/q1/decision.json), [full results](../../../results/quality_tolerant/q1/results.json), [execution receipt](../../../results/quality_tolerant/q1/execution.json), [independent saved-result verification](../../../results/quality_tolerant/q1/report-verification.json).

## Main E2 result

All256 E2 inputs are already consumed;48 references contain numeric cues. Full terminal depth11 averaged129.230309ms. Only fixed11 meets all four point quality margins in each of the three consumed cohorts; **no fixed depth is statistically excluded**. All11 controls remain potentially relevant to future inference.

| E2 offline assignment | Early inputs (differing from final) | BLEU loss | chrF loss | Numeric F1 loss | Negation increase | Primary projected savings | Savings across frozen cost grid |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Terminal oracle, depths1..11 |118 (96)|0.423336|0.993812|0|-0.003906|14.018%|14.018% (no monitor charged)|
| Sparse[8,10,11] |154 (130)|0.496317|0.999449|0|0.007813|**9.670%**|7.722–11.461%|
| Sparse[9,10,11] |156 (123)|0.498609|0.994907|0|0.003906|**7.733%**|6.007–9.311%|
| Sparse[10,11] |161 (119)|0.477965|0.999887|0|0.003906|4.568%|3.792–5.237%|

Margins are <=0.5 BLEU,<=1.0 chrF,<=0.02 numeric-reference F1 and<=0.02 negation mismatch increase. Negative loss denotes an improvement. Corpus scores use aggregated sufficient statistics, checked against direct corpus scoring. The selected assignments lie close to the BLEU/chrF boundaries; search reuse and saturation preclude interpreting these point passes as quality noninferiority evidence.

Sparse[8,10,11] exits94 inputs at8,60 at10,102 at11; it charges1/2/3 observations respectively. Sparse[9,10,11] exits124/32/100 inputs at9/10/11. References and future trajectories determine these assignments. **No rule deciding which input should exit was constructed or evaluated.**

The earliest exact-text baseline reproduces43/256 early matches, zero quality losses and2.670% selected-terminal assembly savings. Approximate-output searches therefore find more point headroom than this exact-only diagnostic; that observation does not identify a causal online selector.

## What the cost numbers mean

The common E2 terminal depth profile is measured from all saved fixed-depth requests, with equal input weighting and two blocks/two repeats per input. The extra-observation proxy is2.145616ms per additional observation, derived from dense-exact versus matched terminal-exact records; it includes implementation/path differences and is not an isolated component measurement. Primary sparse costs also charge0.05ms per observation for decision work. Sensitivity freezes the assignment and crosses h factors0/0.5/1/2 with decision costs0/0.05/0.2ms. It does not reoptimize or span all plausible real costs.

| E2 assignment | Selected terminal assembly mean | Assembly means in blocks0/1 | Assembly savings | Primary projected mean including observation/decision costs |
| --- | --- | --- | --- | --- |
| Sparse[8,10,11] |114.524669ms|113.828436/115.220902ms|11.379%|116.734004ms|
| Sparse[9,10,11] |117.247564ms|116.466643/118.028485ms|9.272%|119.237179ms|
| Sparse[10,11] |122.358039ms|121.630586/123.085493ms|5.318%|123.327420ms|

The primary modeled mean uses the common depth profile; the assembly uses each input's own selected terminal cells, explaining their small difference beyond monitor charges. Recorded constituent timings are real, but their post hoc assembly is **not an integrated sparse-observation request or online policy benchmark**. Block variation is descriptive; repeats are not new independent inputs. No confidence interval or positive paired lower bound is claimed.

## Other consumed cohorts and finite-search limits

Using the transferred E2 cost profile (uncalibrated on S1), projected savings for exploration128/development64 are17.930%/15.902% for terminal oracle,10.567%/10.814% for[8,10,11],8.696%/8.843% for[9,10,11], and4.842%/5.782% for[10,11]. All reported final assignments pass point margins. These are separate consumed cohorts, not held-out replication or measured S1 latency.

Twelve deterministic single-start searches used8,003 total baseline/search attempts of24,036 allowed, including failed and cached attempts;36 attempts were baselines. Exploration and E2 terminal-oracle searches stopped at their2,000-attempt caps. Other searches stopped at two passes or a complete pass without an improving coordinate. None certifies an optimum, complete frontier or global upper bound. No extra search, restart, bootstrap, fit, model request or retry occurred.

## Statistical obstruction and next decision

Q0 remains statistically blocked. The consumed union has only92 numeric-covered references, below even the183 zero-adverse floor of the protected-exclusion joint design; first80%-power count is436 under the illustrative independent adverse-rate0.005 scenario and half-margin zero-event precision needs368. These are necessary scenario-specific counts, not guarantees under document dependence. E4 has191 covered references and heavy overlap with consumed documents; the prior audit found only36 E4 inputs/12 covered references in document-disjoint remainder. Q1 cannot retroactively repair those counts, dependence or consumed selection. E3/E4 model outputs remain sealed; earlier aggregate reference-derived coverage exposure remains disclosed.

**Recommendation:** retain[8,10,11] and[9,10,11] as hypotheses for a separate population and document-cluster-aware design. First determine whether an eligible, separately reserved population and feasible bounded measurement plan can support unchanged endpoints, quality precision and actual latency comparisons. New acquisition/inference, a continuation-value controller, Q2 measurement and confirmation each need their own authorization and prospective lock. Do not release current reservations or train a model on this result. Stop here.

## Verification and resources

42 focused synthetic tests passed before real-body access, including strict quality boundaries, unavailable numeric coverage, direct corpus metric parity, schedule observation counts, deterministic capped search, forbidden header rejection and timing parity/work/duplicate/missing/invalid-cell failures.48 direct real-assignment corpus parity checks passed. Independent saved-result/ledger/source-archive arithmetic checks reopen no historical outcomes and rerun no search; hash verification checks693 locked sources/protected artifacts. All668 protected historical files/assets are unchanged, including failed gates and upstream controls.

Exactly448 references and448 trajectory bodies (4,928 saved states) were materialized;12,408 timing records include120 consumed warmups. The execution took208.721s, peak RSS114,098,176bytes; conservative preparation/reporting charge7,200s gives7,408.721s, below9,000s. Dollar cost0; downloads0; new model requests0; fits0; new encodings0; bootstrap draws0; reserved-output bodies0. [Access receipt](../../../results/quality_tolerant/q1/access-receipt.json), [cost calibration](../../../results/quality_tolerant/q1/cost-calibration.json), [test output](../../../results/quality_tolerant/q1/test-output.txt), [source snapshot](../../../results/quality_tolerant/q1/execution-sources.zip). Original evidence and manifests remain unchanged.
