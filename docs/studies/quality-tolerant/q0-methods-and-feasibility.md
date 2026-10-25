# Q0 methods and statistical feasibility: complete, statistically blocked

October 25, 2026. **Q0 is complete; its feasibility gate did not pass. Q1 is not ready and was not started.** The unchanged tolerances have a defensible prospective procedure, but the eligible consumed population cannot meet its numeric coverage floor; a sufficiently powered and adequately clustered confirmation population is not established. This is a limitation of this declared study design and available evidence, not proof that approximate early translations cannot work or that no better valid design exists.

## Prospective lock and execution

The [protocol](q0-protocol.md), [numeric caps](q0-lock.json), [source lock](q0-source-lock.json), numerical implementation, runner and deterministic fixtures were committed/pushed at **`96dc9a0be7ec551b9ae7f7f8b07e5ac35631bfac`**. Local/live main equality and a clean actual checkout were verified before any tests or simulations. Starting main was the requested `e63896481a4d98317828276ef381fbc5c83dc095`, in `C:\Users\Admin\Documents\Projects\Anytime-NCM`, branch main, remote `https://github.com/yoonalexander/Anytime-NCM.git`; the OneDrive chat directory was a different repository and was not used for research files.

One capped CPU run completed: **26 tests passed**, **96,000 synthetic trials**, **40,000 synthetic corpus draws**, **100,000 shared timing draws**, five datasets, **13.115 seconds** measured tests/analysis/initial verification and **128,802,816 bytes** peak RSS. Additional deterministic CDF/result checks took 0.100 seconds inside the remaining verification allowance; no new random draws. The 7,200-second conservative preparation/reporting charge is separate. Caps were 1,800 measured seconds, 1,200 CPU seconds per process, one thread, 2 GiB memory, 16 MiB durable artifacts, total charged wall <=9,000 seconds, $0. All allocations, source bytes, receipts and tests are new; original protocols/artifacts and reserved manifests retain their hashes. No full historical test-suite refresh is claimed.

See [execution](../../../results/quality_tolerant/q0/execution.json), [exact source archive](../../../results/quality_tolerant/q0/execution-sources.zip), [test receipt](../../../results/quality_tolerant/q0/focused-tests.xml), [137 deterministic checks](../../../results/quality_tolerant/q0/independent-checks.json) and [decision](../../../results/quality_tolerant/q0/decision.json). The additional checker uses binomial CDF arithmetic to check beta-inverse endpoints; it is same-assistant validation, not independent human scientific review.

## Contract and prospective inference

All losses are oriented adverse-positive. Keep corpus BLEU loss <=0.5, corpus chrF loss <=1.0, paired mean numeric-reference F1 loss <=0.02 **only among reference-number-covered groups**, and literal negation-mismatch increase <=0.02 **across all groups**. SacreBLEU 2.6.0 defaults and existing cue definitions are preserved. These proxies do not certify factuality, general semantic equivalence or safety.

The future single-candidate template retains all terminal depths 1..11: 12 methods x four quality intervals plus 11 candidate-versus-fixed timing intervals = 59 simultaneous two-sided intervals. Each tail has `a=.05/118=0.000423728813559322`. The union bound needs no independence between endpoints; input sampling assumptions still matter. Redundant slots keep their alpha. No winning interval method, candidate-dependent alpha recycling or outcome-driven family reduction occurred.

For paired cue losses D in [-1,1], the primary interval is `[-U(k_negative,n,a), U(k_positive,n,a)]`, with U the Clopper-Pearson upper event-probability bound. The inequality `-P(D<0)<=E[D]<=P(D>0)` makes this a conservative bound on the **original mean endpoint**, not a replacement Bernoulli endpoint. It loses magnitude and beneficial-offset information deliberately. Undefined numeric coverage is unresolved; finite empirical equality is not a structural guarantee. No bootstrap-degenerate cue interval can certify rare errors away.

Corpus quality uses paired input/cluster resampling of **summed sufficient statistics**, with direct corpus-score parity. Timing uses the ratio of equal-weight identity means, repeats averaged within process first, and shared crossed input/process indices across methods. Require actual mean ready-output savings >=5% versus full, positive adjusted paired lower bound, and positive adjusted lower improvement over every potentially quality-feasible fixed depth. An adjusted quality lower loss bound strictly above a margin can exclude that fixed depth; failure to establish its quality cannot. Lock a strong comparator before separate confirmation and retain other still-plausible controls. All request work through CPU-ready text must be charged; offline oracle selection and code/level counts do not establish deployed savings.

The prespecified magnitude-sensitive empirical Bernstein interval is **diagnostic only**. It never replaces the primary procedure. Its transformed range-2 bound has a zero-variance, mean-zero coverage floor of **1,975** at the same alpha; range-2 Hoeffding needs **38,833** for a zero sample mean. Those particular methods do not solve the obstruction. This is not a claim that every variance-sensitive, paired or specialized method fails.

## The prior obstruction remains, and coverage alone understates it

[Exact calculations](../../../results/quality_tolerant/q0/statistical-feasibility.json) reproduce the historical 405/385 floors without reading real outcomes:

| Inference family | Tail alpha | Necessary covered n with zero adverse events | Zero-event upper bound with n=48 |
| --- | ---: | ---: | ---: |
| Historical original 89 intervals | .05/178 | 405 | .156643 |
| Historical narrowed E2 / Q0 primary 59 intervals | .05/118 | 385 | .149389 |
| Optimistic unadjusted single one-sided endpoint | .05 | 149 | .060503 |

Derivation: U(0,n,a)=1-a^(1/n); require it <=.02. Nonzero adverse counts only worsen this primary upper bound. Thus no paired observations whatsoever on 48 covered examples can satisfy this construction's margin; even n=256 covered is insufficient. The favorable signed mean need not equal the conservative event envelope, so this is not a theorem about all possible mean estimators.

There is also a narrower method-independent warning: consider the permitted adverse Bernoulli subclass D in {0,1}. At a true mean arbitrarily above .02, 48 all-zero observations have probability approaching `.98^48=.379185`. Any deterministic uniformly valid one-sided level-.05 procedure that always certifies on that all-zero sample would exceed its allowable false-certification probability. Mere sharper treatment of a zero empirical variance at n=48 cannot fix this without extra assumptions or changing the inferential claim. This statement concerns that sample and unrestricted subclass, not every possible observed signed dataset.

The frozen power requirement was >=80% for a .005 adverse-event alternative under the .02 margin. Exact CP test inversion gives:

| Covered independent groups | Largest accepted adverse count | Power at p=.005 | Power at p=.01 |
| --- | ---: | ---: | ---: |
| 48 / 192 / 256 / 384 | none | 0 | 0 |
| 385 | 0 | .145173 | .020871 |
| 512 | 1 | .274431 | .035944 |
| 1,024 | 6 | .744765 | .114504 |

The first scanned count achieving 80% power is **1,038 covered independent groups** at p=.005, and **2,704** at p=.01. Counts were enumerated through 10,000; discreteness means power can dip when n increases without increasing the accepted count. These are the first qualifying counts, not a guarantee at every larger n. Even with all 1,024 references covered, E4 misses the prespecified .005-alternative planning requirement. A truly zero-loss candidate could still certify at sufficient coverage: this power criterion is a prospective design requirement, not a universal impossibility claim or observed E4 result. Full joint power for BLEU/chrF, cues and latency remains unknown.

## Eligible populations: verified counts versus unknown coverage

Aggregate-only evidence gives 128 consumed S1 exploration +64 consumed S1 development +256 consumed E2 audit = **448 released groups**. E2 has **48 numeric-covered references**. Even granting numeric coverage to every one of the other 192 groups, this released union has at most **240 numeric-covered groups**, below 385. This bound uses no fresh reference reads and cannot be repaired by re-reading outcomes or adding timing repeats. Reusing those groups for search also prevents fresh confirmation regardless of coverage.

E3's 128 groups, E4's 1,024 and the 571 unallocated remain sealed. Their numeric coverage is unknown; neither a reservation nor official aggregate-baseline exposure establishes power or document independence. The actual unknown E4 count could in principle exceed 385, but Q0 cannot count it as verified feasibility. At the **sensitivity assumption**, not an estimate of E4, of E2's .1875 coverage prevalence, E4's expected covered count would be 192 and the binomial probability of reaching 385 about `3.40e-45`. At prevalence .40 it would be 409.6 with probability .9457 of reaching 385, still distinct from the stronger power/precision requirement. Hypothetical pooling of E4 and unallocated roles is not authorized; its table is arithmetic sensitivity only and grants no access or replenishment.

No feasible eligible population is established under this primary design and the frozen power/precision rules. Unknown news-document clusters, unknown checkpoint-training overlap and previous aggregate exposure remain material limits. A future fresh allocation, different defensible inferential design, document grouping or carefully justified sampling design would require new information and prospective authorization. No reference-based enrichment, denominator change, invented independent examples or automatic sample expansion is proposed as a Q0 pass.

## What synthetic validation establishes

The [48-case trial grid](../../../results/quality_tolerant/q0/synthetic-trials.json) covers rare .005 events, null/boundary .02 and outside .03 loss, fractional losses, beneficial offsets, exact zero loss and perfect eight-copy dependence, at six sample sizes, 2,000 trials each. The EB diagnostic does not certify the zero/nonnegative scenarios at any n<=1,024. In the independent rare-event case at n=1,024, primary simulated power is .745, agreeing with exact .744765; it fails the >=80% criterion, including the required lower Monte Carlo bound. Primary floors reject inadequate coverage without treating absent observed events as absence of risk.

Naively treating eight copies as independent is unsafe: at n=512 it falsely certifies the boundary in 27.9% of trials, exact probability .274454, versus the nominal per-tail .000424. At n=1,024 this is 7.2%, exact .075325. Using the actual independent cluster count (64 or 128) does not certify these scenarios. This is an intentionally broken assumption stress test; no actual news-document correlation is measured. The [deterministic audit](../../../results/quality_tolerant/q0/independent-checks.json) additionally checks 35 exact Bernoulli distributions at p=0,.005,.01,.02,.03, plus binomial-tail endpoint inversion. Finite Monte Carlo trials cannot validate errors as small as the adjusted tail; the exact/proven inequality supplies that guarantee under its assumptions.

The [invented text checks](../../../results/quality_tolerant/q0/synthetic-corpus.json) verify all eight direct BLEU/chrF point/statistics comparisons, identical-text zeros and positive modified-text losses. At 10,000 bootstrap draws their extreme rank is zero: adjusted intervals are correctly unavailable. Increasing draws was forbidden and did not occur. The prospective 100,000-draw template resolves rank 18, but numerical resolution does not prove bootstrap sampling coverage. Four invented corpora cannot establish real BLEU/chrF power; the half-margin precision criteria remain unverified on an eligible population.

The [synthetic timing check](../../../results/quality_tolerant/q0/synthetic-timing.json) verifies pairing, ratio-of-means, nested repeats, shared process indices and 0/2.5/5/10% effects. The null interval contains zero; shifted effects reproduce shifted paired bounds. All are invented timings, with only two process blocks; they measure no checkpoint latency, process-population variation, controller overhead or real-world speedup.

## Q1 and separate confirmation

A separately requested, bounded Q1 could search already released consumed development trajectories for point-feasible approximate assignments, describe where quality tradeoffs occur, and propose inspection schedules using explicitly estimated costs. It could establish existence of a found finite-sample assignment under those point tolerances. It could not certify population quality, an optimum/global opportunity bound, causal recognition, actual saved request latency or an adaptive advantage. Search selection invalidates a naive confirmatory reading of intervals conditional on the selected assignment.

Separate adequately covered eligible confirmation with a locked causal policy, locked comparators, unchanged margins, no refitting and actual paired ready-output timing is required for a scientific success claim. Q2 measures assigned exits; Q3 develops a causal continuation-value selector; Q4 confirms it. No true continuation-value estimator was trained here or retroactively attributed to historical controllers.

**Decision: stop before Q1.** Q0's implementation checks pass; the statistical feasibility gate is blocked by verified coverage/power limits and unresolved population/dependence/precision. This does not alter the completed studies' practical no-go results. No reserved outcome access, trajectories, real checkpoints, fits, encoding, training, paid compute, contact or submission occurred.

Primary methodological support and explicit derivations are recorded in the [frozen protocol](q0-protocol.md): [official SciPy exact binomial implementation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats._result_classes.BinomTestResult.proportion_ci.html), [Maurer-Pontil 2009 Theorem 4](https://arxiv.org/pdf/0907.3740), [Koehn 2004](https://aclanthology.org/W04-3250/). These sources motivate the individual procedures; they do not establish this application's power, corpus bootstrap coverage, document independence or scientific success.
