# Final mathematical feasibility review: tighter bounds do not clear the current gate

October28,2026. **The final bounded review is complete. Close the current all-zero/marginal confirmation route under its declared statistical model.** Using every document weight materially tightens the earlier inequality, but the sharp all-zero endpoints still exceed the unchanged0.02 margins. Exact admissible outside-margin distributions demonstrate why this is more than numerical conservatism. No model quality or actual speedup was evaluated.

[Protocol/proof](final-math-review-protocol.md), [numeric lock](final-math-review-lock.json), [source lock](final-math-review-source-lock.json), [decision](../../../results/quality_tolerant/final_math_review/decision.json), [exact rational results](../../../results/quality_tolerant/final_math_review/exact-results.json), [execution](../../../results/quality_tolerant/final_math_review/execution.json). Lock7245cda93740631928e8bb4325b30171b5c9e510 was pushed before tests, numerical evaluation or profile decoding; clean local/live main was verified again at execution.

## Result using the complete weight distribution

These are bounds for a **hypothetical all-zero paired-loss observation**, not measured model losses. Denominators and signed endpoints are unchanged. The model conditions on the known applicable document counts, permits arbitrary dependence inside a component, and permits independent but heterogeneous risks across components.

| Fixed profile | Applicable components | Applicable inputs | Prior largest-cap zero upper bound, alpha.025 | Sharp full-weight zero endpoint, alpha.025 |
| --- | ---: | ---: | ---: | ---: |
| Development numeric |269|1,229|0.053659|0.041805|
| Development all-input negation |297|5,487|0.075499|0.047023|
| Confirmation numeric |391|1,778|0.059884|**0.034389**|
| Confirmation all-input negation |447|7,700|0.040554|**0.025542**|

The full-weight calculation removes real slack in the earlier largest-weight approximation. It does not lower either confirmation endpoint to0.02, nor to the retained0.01 half-margin precision target. Even the isolated alpha.05 sensitivity gives confirmation endpoints0.029169 and0.021561, still above0.02. That sensitivity does not replace the registered alpha.025 or its protected exclusion family.

Each endpoint is recorded as a64-step exact rational bracket of width2^-64; displayed decimals are rounded. The sharp endpoint is for the all-zero observation only. This review neither implements nor validates a general confidence interval for arbitrary positive/signed observations.

## Exact information constraint at the all-zero observation

For applicable counts c_j, total C and weights w_j=c_j/C, take independent Bernoulli document flags B_j with probabilities p_j. Every applicable paired loss within a flagged document is1; otherwise it is0. This mathematical subfamily is allowed by the existing bounded-loss/independent-component model. It is not a claim about the checkpoint's real errors. Expected signed input-weighted loss is sum w_j p_j; the complete observed loss vector is all zero with probability product(1-p_j).

The protocol proves the exact maximum of that zero probability at a given expected loss. Its active-set solution uses all weights, with a common count-unit level tau satisfying sum(c_j-tau)_+=d*C. The resulting null distribution reaches the objective exactly; a supporting-hyperplane/KKT argument establishes global optimality. General concave-optimality principles are described in [Boyd-Vandenberghe, section5.5](https://web.stanford.edu/~boyd/cvxbook/bv_cvxbook.pdf). The statistical construction and scope are explicitly derived in our locked protocol.

For strictly outside loss d=0.0201, the optimal null gives:

| Confirmation endpoint | Expected loss in constructed null | Maximum probability of an all-zero observation | Registered one-sided alpha |
| --- | ---: | ---: | ---: |
| Numeric F1 loss |0.0201|**0.152356**|0.025|
| Negation increase |0.0201|**0.064060**|0.025|

A deterministic level.025 marginal test cannot certify NI on that all-zero vector: under the constructed outside-margin distribution it would falsely certify with probability greater than.025. Both counterexamples also exceed.05. This establishes a constraint on this observation and model family, independently of the previous KL approximation.

### Independent simple witnesses

The obstruction does not rely solely on the optimality calculation. A second construction assigns one equal event probability to a few heaviest components and zero risk elsewhere:

- **Numeric:** counts[29,23,21,19,18], total110 of1,778. Give each of those five independent component flags probability178689/550000 (about.324889). Expected input-weighted loss is exactly0.0201; all components are observed zero with probability(371311/550000)^5=0.1402412031, greater than.025 and.05.
- **Negation:** counts[85,77,69,65,60,54], total410 of7,700. Give each of those six independent flags probability15477/41000 (about.377488). Expected loss is exactly0.0201; all-zero probability is(25523/41000)^6=0.0581952023, again above.025 and.05.

These witnesses use anonymous counts, not document IDs, translations or per-input flags. Exact rational mean constraints and probabilities are saved and independently checkable. They demonstrate the obstruction even without trusting the sharper extremal optimizer.

Randomizing the rejection decision cannot give high power at the degenerate zero-loss alternative: the optimal null limits rejection probability at zero to at most.025/.152356=16.41% for numeric and.025/.064060=39.03% for negation. Those are limits for that zero-loss alternative under this broad conditional model, **not** new power estimates at the earlier p=.005 scenario. For deterministic gates monotone in nonnegative losses, failing at zero blocks all nonnegative loss vectors. Arbitrary nonmonotone tests, genuine negative signed improvements, model-specific joint information or additional independently justified restrictions are outside that extension.

## What this does and does not establish

**Established:** the largest-document inequality was conservative, but merely sharpening an all-zero marginal bound cannot make the current weights pass. Under the declared independent heterogeneous bounded-loss model, the all-zero observation itself cannot support the registered deterministic0.02 cue certification. The proof assumes independence already; proving independence more convincingly would not remove this particular counterexample.

**Not established:** all adaptive translation policies fail, actual translations lose quality, every possible signed-data confidence procedure is impossible, every population is too small, or a future model-specific joint analysis could never succeed. No real paired losses were inspected. The argument is about the specified marginal inference family and all-zero evidence, not all possible information in natural-language outputs. Negative paired improvements could supply different observations; a different risk model would need independent justification, not adoption merely because it rescues this sample.

The separate operational concentration failure remains: confirmation's largest input component is85/7,700=1.104%, above the frozen1% screen. No component was removed, split or reassigned, and the old failed gates remain unchanged. Corpus BLEU/chrF inference, whole-study power and actual online latency remain unvalidated. No fixed depth is excluded or comparator weakened.

## Inference target is resolved by keeping the claims distinct

The conditional risk is mu_c=sum c_j E[Dbar_j|counts]/sum c_j for fixed observed counts. A conditional error guarantee can be averaged to control coverage of that random mu_c. It does **not** automatically cover theta=E[sum losses]/E[sum counts] for a wider random-document population. The locked exact examples demonstrate the distinction:

| Invented document distribution | Expected realized input mean | Ratio of expected loss/count totals |
| --- | ---: | ---: |
| Counts1 or9 equally likely; per-input loss1 or0 respectively |1/2|1/10|
| Counts1 with probability.99 and100 with probability.01; losses0 and1 |1/100|100/199|

These are algebraic examples, not fitted descriptions of news. Conditional fixed-count inference, an exact finite-corpus census and wider-population ratio inference are three different claims. A deterministic-quality census could establish metrics on its fully evaluated fixed corpus without a sampling-generalization claim; it would require a newly declared limited objective and actual outputs. It does not retroactively satisfy this roadmap's intended population uncertainty/confirmation contract. A wider-population study needs a justified sampling target and ratio inference. This review does not silently switch to either alternative.

## Validation and bounded work

**27 deterministic invented tests passed** before metadata access: equal-weight closed forms, one-heavy and tied active sets, exact risk constraints, permutation/zero handling, invalid inputs, conservative root endpoints, independent top-k witnesses, selective-decoder isolation using poisoned excluded bytes, malformed profile rejection and target counterexamples. No random tests or Monte Carlo were used.

The predeclared coarse validation grids checked16,093 points and48,279 reused-threshold comparisons; every feasible grid probability stayed below the exact optimum. This grid is a sanity check, not the optimality proof. The real-profile calculations used533 charged water-level evaluations and4,212 top-k evaluations; one selected-profile decode provided4 vectors/1,488 count entries. Source/reference strings, per-input cue flags and IDs were byte-skipped, not JSON decoded. Public weight distributions are anonymous count histograms.

Execution took10.018s, peak RSS41,705,472bytes;$0. With the7,200s conservative preparation/reporting charge, total7,210.018s stays below9,000s. No new data download, corpus/reference/model-outcome decode, tokenization, encoding, model load/request, fit/training, Q1 search, bootstrap or Monte Carlo. All915 protected historical/input files remain unchanged. [Ledger](../../../results/quality_tolerant/final_math_review/ledger.jsonl), [anonymous weights](../../../results/quality_tolerant/final_math_review/weight-distributions.json), [deterministic validation](../../../results/quality_tolerant/final_math_review/deterministic-validation.json), [tests](../../../results/quality_tolerant/final_math_review/test-output.txt), [exact source snapshot](../../../results/quality_tolerant/final_math_review/execution-sources.zip).

## Final decision and stopping point

**End this final review and close the current all-zero/marginal confirmation route under the existing assumptions and population.** Q0 is not passed; Q2-Q4 remain unstarted and unauthorized. No further audit, dataset collection, model evaluation or reservation release follows automatically. A materially different justified population/model or explicitly limited finite-corpus objective would be a new study, retaining every previous failure. The exploratory approximate-exit headroom remains unresolved as a practical model benefit; this mathematical no-go is not a universal NCM impossibility result.
