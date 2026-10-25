# Q0 multiplicity audit: method improved, feasibility remains blocked

October 25, 2026. **The prospective multiplicity alternative passes its method audit. Research feasibility remains blocked; Q1 is not ready and was not started.** This extension fixes avoidable statistical conservatism while retaining the original endpoints and every potentially feasible fixed comparator. It does not establish adequate eligible data, actual early-output quality, latency savings or a continuation-value model.

## What changed and what the new guarantee means

Original Q0 asked for 59 simultaneous two-sided intervals. That is a defensible, conservative guarantee, but stronger than needed for the single scientific claim that **all** required quality and latency conditions hold. The user authorized a separate prospective audit of that distinction after the original Q0 findings. No real outcomes were rescored and no method was chosen because it rescued a known assignment.

The [frozen alternative](q0-multiplicity-protocol.md) reserves .025 for one all-required decision and .025 for simultaneous protection against falsely excluding any quality-feasible fixed depth. All candidate quality conditions and all retained cost-superiority conditions must pass one-sided .025 bounds. For ten early fixed depths x four endpoints, exclusion lower bounds use .025/40=.000625 each. No alpha is recycled from redundant, unavailable or unhelpful endpoints. Full depth11 always remains required. A strong comparator is locked prospectively without dropping other potentially feasible depths. Missing numeric coverage, an absent comparator, incomplete paired timings, a zero superiority lower bound or <5% point savings cannot pass.

Proof: with probability at most .025, any truly feasible fixed control is erroneously excluded (union bound over40). If the overall claim is false, choose one population-level false candidate/full condition or one truly feasible non-improved fixed depth. Outside the erroneous-exclusion event, global go requires that fixed false component to pass its .025 test. Therefore probability of **false global go or any false exclusion** is at most .05. Component tests may be dependent. This is the usual all-required intersection-union principle plus an explicit exclusion-family allowance, conditional on valid marginal tests. The .001 numerical bootstrap allowance is additional; approximate corpus-bootstrap sampling error is not proved away.

This is **not** a new promise that all displayed component intervals simultaneously cover their parameters. Component passes are not independent standalone confirmatory discoveries. Multiple candidate winners, outcome-selected comparator removals, or unadjusted “any exclusion endpoint or faster” routes invalidate the proof. The locked simulator includes those shortcuts only as negative controls.

Keep the original margins: corpus BLEU loss<=.5, corpus chrF loss<=1., mean numeric-reference F1 loss<=.02 on reference-covered groups, negation-mismatch increase<=.02 on all groups. Keep corpus aggregation and metric signatures. The actual savings contract is still >=5% **point mean** ready-output savings versus full plus a positive paired lower bound, and positive bounded improvement versus all retained controls. It does not require a lower bound above5%, and has not been weakened to a latency proxy. A future benchmark must charge all actual request work through CPU-ready output.

## Lock, source preservation and validation

Actual root `C:\Users\Admin\Documents\Projects\Anytime-NCM`, branch main, origin `https://github.com/yoonalexander/Anytime-NCM.git`, starting clean local/live main `21608e17c1e4da1f2b9aff2d46ba89ae56524260` were verified. [Protocol](q0-multiplicity-protocol.md), [numeric lock](q0-multiplicity-lock.json), [source lock](q0-multiplicity-source-lock.json), implementation and fixtures were committed/pushed as **`9dad432739b081efe9b2e7ab2c311a624154084e`** before any tests or simulations. The runner again verified a clean checkout and matching live main.

One run passed **64 focused tests** (38 extension fixtures and26 original Q0 regressions), **17 gate cases x20,000 trials** and **54 cue cases x5,000 trials**: **610,000 trials total**. Zero bootstrap draws, real-body reads, model loads, requests, warmups, fits, encodings or training. Execution including tests and analysis took **5.374 seconds**, peak RSS **126,164,992 bytes**, $0. The cap was1800 measured seconds/1200 CPU seconds per process/one thread/2GiB/16MiB;7200 seconds were conservatively charged for preparation/reporting. The verified executed-source/artifact/preservation set contains48 byte-hash checks. No original Q0/E0/E2 protocol, result, receipt, partition or reservation changed.

[Execution](../../../results/quality_tolerant/q0_multiplicity/execution.json), [exact source archive](../../../results/quality_tolerant/q0_multiplicity/execution-sources.zip), [64-test JUnit](../../../results/quality_tolerant/q0_multiplicity/focused-tests.xml), [pre-work ledger](../../../results/quality_tolerant/q0_multiplicity/ledger.jsonl), [decision receipt](../../../results/quality_tolerant/q0_multiplicity/decision.json).

## Actual sample and power improvements

[Exact binomial calculations](../../../results/quality_tolerant/q0_multiplicity/statistical-feasibility.json) retain the original conservative paired cue envelope. Only its prospective alpha allocation changes:

| Candidate cue requirement | Original Q0 | Protected-exclusion IUT alternative |
| --- | ---: | ---: |
| One-sided tail | .05/118 | .025 |
| Minimum covered n with zero adverse events and .02 margin | 385 | **183** |
| First covered n with >=80% noninferiority power at adverse p=.005 | 1,038 | **436** |
| First covered n with >=80% noninferiority power at adverse p=.01 | 2,704 | **1,233** |

The new floor183 is now justified for the **whole protected-exclusion design**, not merely the optimistic one-endpoint benchmark. The .05 single-endpoint floor149 remains a benchmark, not the adopted design. Sample-power discreteness remains: the first qualifying n does not guarantee every larger n also meets80% until a suitable subsequent range is checked. We scanned through10,000 without collecting examples.

Original half-margin planning precision is still required. Even with zero adverse events, a one-sided .025 cue bound needs **368 covered groups** to be <=.01 above a zero sample loss. Additional nonzero events and joint requirements can demand more.

| Covered n | Exact NI power at p=.005 | Exact probability of NI **and** half-margin cue precision |
| --- | ---: | ---: |
| 48 | 0 | 0 |
| 183 | .399598 | 0 |
| 192 | .381972 | 0 |
| 240 | .300289 | 0 |
| 384 | .698373 | .145903 |
| 512 | .883519 | .274431 |
| 1,024 | .993623 | .993623 |

These are Bernoulli adverse-loss planning examples. They are not actual F1 outcomes, guarantees for arbitrary signed/fractional distributions, full joint-study power, or a new larger data allocation. Paired F1 still has its original conditional mean estimand; the unchanged event envelope discards beneficial offsets and loss magnitude. Its lower bound is nonpositive, so it cannot itself exclude a fixed depth through a positive cue loss. Those exclusion slots are retained; corpus BLEU/chrF can rule out depths.

## What the simulations and exact checks show

The [gate grid](../../../results/quality_tolerant/q0_multiplicity/gate-trials.json) tests each candidate quality endpoint as the sole null, a full-cost null, one or ten shared comparator nulls, independent/shared/disjoint exclusion dependence, all-true requirements and missing-data/point-threshold guards. Every predeclared Monte Carlo sanity check passed. At least-favorable individual quality nulls, observed false-go rates are2.415%--2.580%, around the allocated2.5%. A comparator-null construction has exact false-go probability2.75%; the shared-ten sample observed2.965%, within its frozen binomial fluctuation range. This is a finite-sample realization, not a different alpha guarantee.

Negative controls demonstrate why exclusions and candidate locking matter: an unadjusted union of quality-exclusion/cost routes gives **24.96%** false acceptance (exact25%); choosing among four independently tested candidate winners gives **9.62%** (exact1-.975^4). Neither shortcut is used. P-value simulations validate only composition conditional on valid marginal p-values, not real BLEU/chrF confidence coverage or model quality.

The [cue grid](../../../results/quality_tolerant/q0_multiplicity/cue-trials.json) compares old/new tails on the same frozen invented counts, including rare, boundary, outside-margin and fractional cases. At n512,p=.005 the new observed NI rate is87.98%, versus exact88.3519%; requiring the original half-margin precision reduces the observed rate to27.76%. At n1024 the observed new NI/precision rate is99.46%, exact99.3623%. Better NI power alone does not meet the whole precision contract.

Perfect eight-copy clusters break naive independent-input inference. At192 nominal rows, the new naive procedure falsely certifies the .02 boundary in61.06% of trials (exact61.578%); the correct24 independent-cluster analysis does not certify. This is a deliberate assumption stress test, not measured dependence in WMT. Exact binomial-CDF inversion independently checks beta inverse bounds;240 Bernoulli coverage/power cases span the declared alpha/n/p grid, without additional random trials.

For a future100,000-draw bootstrap, numerical one-sided ranks are2299 at tail.025 and33 at tail.000625 under the .001/55 numerical allocation. At10,000 draws the exclusion rank is0, unresolved. No new corpus/timing resampling was run; original Q0 aggregation/parity evidence is retained. Neither these ranks nor generic uniform-p tests establish actual population coverage of the approximate corpus bootstrap.

## Feasibility after the improvement

The method-dependent statement “E4 has fewer than1,038 total inputs” is no longer, by itself, an obstruction under this alternative. With1,024 genuinely independent numeric-covered examples, its illustrative cue requirement could have high power and precision. **E4 actually has1,024 total groups, not1,024 verified covered independent groups.** Its coverage and document clustering remain unknown, and it stays sealed.

The released consumed union has448 groups but at most240 numeric-covered examples (48 known E2 + at most192 other consumed groups). This is below the first436 covered examples reaching the frozen80% planning power and below the zero-event368 half-margin precision floor. At n240 specifically, exact NI power is30.03% and NI-plus-precision probability is zero in the planning submodel. Unknown actual union coverage cannot be substituted with that optimistic bound; consumed data would also not become fresh confirmation.

At the **hypothetical** .1875 numeric prevalence observed in consumed E2, a1024-group population would average192 covered groups, have77.55% probability of reaching the necessary183 floor, and only28.95% mixture NI power at adverse p=.005. This differs from treating the expected count as a known fixed count because of discreteness. At assumed .40 prevalence mixture power is67.34%; at1.0 it is99.36%. These are sensitivity calculations, not E4 predictions or authorization to inspect, enrich or combine reservations.

Full joint power across numeric/negation/corpus quality and all required costs remains unestablished; even80% for each of two independent components gives only64% joint power. Adequate document/group sampling and separate confirmation are still required. Source/effective-prefix uniqueness does not establish document independence or absence of checkpoint-training overlap.

**Decision:** keep this prospectively justified alternative as a validated template for a future study, preserve original Q0's historical result, and mark overall Q0 feasibility **still statistically blocked**. No Q1 searches, reservation releases, trajectories or causal controller development occurred. A future step would need a prospective eligible population/coverage and clustering plan that meets power/precision across all endpoints; this audit does not authorize collecting it. Any later Q1 on consumed data could explore finite-sample assignments only, not certify quality or actual speedup.

Primary sources: [FDA2022 sectionIII.C.1](https://www.hhs.gov/guidance/sites/default/files/hhs-guidance-documents/FDA/MultipleEndpoints_FinalGuidance.pdf) for the all-required-endpoint principle; [SciPy exact binomial implementation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats._result_classes.BinomTestResult.proportion_ci.html) and [binomial CDF/quantiles](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.binom.html) for the marginal calculations. The exclusion/error-control proof is explicit above. No source is represented as proving this application has independent data, adequate joint power, exact corpus-bootstrap coverage or practical adaptive speedup.
