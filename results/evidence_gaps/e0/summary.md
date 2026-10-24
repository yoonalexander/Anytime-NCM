# E0: input reservations and statistical feasibility

Completed October 24, 2026. **Input audit and fixed synthetic preflight complete; no checkpoint inference, model fitting, target encoding, new references or new per-input model outcomes. E1 was not started.**

The main finding is a limitation of the proposed statistical design: with the frozen conservative sparse-cue interval, the 256-input E2 audit cannot establish the 0.02 cue noninferiority margins for nonidentical-output methods. This does not establish poor model quality or absence of early-exit opportunity. Do not collect those outcomes under the assumption that the statistical gate is feasible.

## Frozen execution and access

The [protocol](../../../docs/studies/evidence-gaps/e0-protocol.md), [machine lock](../../../docs/studies/evidence-gaps/e0-lock.json) and source/tests were committed/pushed at `08a85cd709359f1e104471181374de92a9e2d18d` before input-audit/simulation work. A clean-checkout guard then failed **before** any audit/trial because WSL did not inherit Windows Git's submodule CRLF normalization. The [failure receipt](../e0-preexecution-failure-1.json) and [prospective recovery amendment](../../../docs/studies/evidence-gaps/e0-recovery-amendment.md) preserve this incident. Command-local Git normalization was corrected; no upstream files/global settings, budgets, scenarios or statistical methods changed. Corrected source and amendment were pushed at `4f13c5d9d271557358925445601ba97beb3f075e`, with local/remote equality checked before one successful run.

The [execution receipt](execution.json) records the actual source/protocol digests and environment. Historical empirical artifacts were not rewritten. The source-string parser is non-executing; output JSON bodies, including consumed final records and viewer content, were never decoded. Only leading output identity/index/partition headers and byte hashes were used.

## Input eligibility and sealed allocation

The [exposure audit](exposure-audit.json) verified 3,003 unique historical effective-prefix groups and read their source strings solely for exact-source duplicate hashing. It found zero exact full-source duplicate groups. All 192 audit trajectory headers, 768 development request headers over 64 identities and 3,072 consumed-final request headers over 256 identities exactly match their historical populations; none overlap the 1,979 reserved identities. S1 access ledgers match 128/64 historical groups. Viewer artifacts match their recorded build, whose reviewed source selects those same 192 WMT audit identities. The audit inventories 483 prior result files and 17 local cache/render paths; no unclassified plausible WMT output location was found by the declared path rule.

The [new input manifest](input-manifest.json) freezes the unchanged hash-order proposal:

| Role | Effective-prefix groups | Outcome access |
| --- | ---: | --- |
| E2 audit | 256 | Sealed |
| E3 development | 128 | Sealed |
| E4 confirmation | 1,024 | Sealed |
| Unallocated | 571 | Sealed |

The manifest also freezes the 16 already exposed E1 exploration identities. All new role records retain parent identity/index and source-text digest; no source/reference/output text is copied. Original partitions remain unchanged.

**Limits:** this is eligibility relative to recorded local access. All groups had official aggregate baseline exposure; source strings were inspected by E0's deterministic hashing routine. Unknown checkpoint-training overlap, undocumented external/human access and news-document relationships remain unresolved. No document IDs are available. Exact-source/effective-prefix grouping does not establish independent document sampling or contamination-free evaluation. A later report must retain these qualifications.

## Statistical results and interpretation

The [fixed trial grid](synthetic-trials.json) contains 24 scenarios x 1,000 trials = 24,000 synthetic trials. The [bootstrap checks](synthetic-bootstrap.json) contain 12 fixed synthetic corpora x 10,000 shared draws = 120,000 draws, including paired corpus sufficient-statistics/direct-score parity. Normal-difference trial proxies are not corpus-BLEU power calculations. The 12 representative corpora do not establish confidence-interval coverage. No real outcome was rescored, no optimizer was rerun and no data-dependent case was substituted.

The [feasibility record](statistical-feasibility.json) gives the exact zero-adverse-event coverage floors under the frozen signed-loss envelope:

| Stage | Required tail alpha | Minimum covered groups for a 0.02 bound | Zero-event upper bound at relevant coverage |
| --- | ---: | ---: | --- |
| E2, 89 simultaneous two-sided intervals | 0.05/(2 x 89) | **405** | n=256: **0.0314386** |
| E4, 10 one-sided tests | 0.005 | **263** | n=205: **0.0255143**; n=256: 0.0204838 |

For zero observed adverse cases the upper probability bound is `1-alpha**(1/n)`. Even if every E2 reference had a numeric cue, n could be only 256, below 405. Negation uses all 256 groups and has the same limit. Nonzero adverse counts can only worsen this conservative bound. Therefore O-chrf0/O-chrf05 cannot pass the frozen full E2 cue contract with this allocation. This is a proof about this confidence construction and budget, not an impossibility result about better statistical procedures or stopping policies.

**O-exact is different:** it defines its retrospective exit by exact equality to its future full-depth decoded text for every input. Conditional on execution parity, deterministic text metrics are identically preserved by construction. Merely observing no output changes in a finite sample from a causal controller or fixed early depth does not justify that exception. O-exact still needs measured cost, all fixed comparators and a causal recognition study before any deployable benefit can be claimed.

For E4 the 263-covered-reference floor is a conditional warning, not a measured coverage estimate for the sealed 1,024 inputs. At the predeclared synthetic 20% coverage, the positive n=1,024 scenario averaged 204.93 covered groups and none of 1,000 trials passed the full conservative cue gate. Actual new reference coverage remains unknown. Do not view final references early or increase the sample after seeing a disappointing count.

The clustered synthetic n=256 scenario illustrates the grouping limitation: E4-tail naive identity intervals covered the stipulated true latency mean in 69.8% of trials, versus 98.6% using the known artificial clusters. These are synthetic rates, not measured WMT coverage or nominal 95% calibration results. Missing document grouping can materially affect inference; a larger bootstrap alone cannot repair it.

Monte Carlo tail precision was also checked. At the E2 tail, 10,000 draws leave an expected 2.809 observations and a 6.02% chance of none, so the conservative order-statistic check refuses that extreme quantile. The planned 100,000 E2 draws have expected 28.09 tail observations and conservative one-based rank 8; the planned 50,000 E4 draws have 250 and rank 191. This resolves the predeclared rank-availability check, not sampling-validity or real-data power. Preserve the extreme-quantile and approximate-coverage limitations.

## Gate decisions and next work

1. **E0 complete with explicit statistical limitations.** Input reservations and statistical procedures are locked; all outcome roles remain closed.
2. **E1 remains the next useful measurement.** It can proceed only under its separate frozen execution protocol and an execution request, with asset/environment checks, 1,000 requests and the existing two-hour cap. E0 did not validate current CUDA behavior or measure any early-exit latency.
3. **Do not automatically execute the full nonidentical-output E2 study.** Its cue gate is not resolvable under this frozen fallback at n=256. After E1, a separately declared O-exact-focused diagnostic may be useful; its primary scope/resource budget must be fixed before new E2 outcomes. Do not quietly drop cue endpoints, loosen tolerances or enlarge the population.
4. **E3/E4 stay blocked.** No controller fit, new development outcome, final outcome or reference access is released by E0. E4 additionally needs enough numeric coverage and a defensible grouping/statistical interpretation; 1,024 inputs are not a promise of a conclusive result.
5. Mechanism/target encoding, NCM training and publication/contact remain deferred. The original S1 result is still inconclusive and its oracle is still best-feasible, not certified optimal.

## Work, tests and resources

The one successful audit/computation took 23.899 seconds, peak RSS 173,404,160 bytes (165.37 MiB). Execution charges the original two full setup/reporting hours conservatively in addition to measured runtime; no resource cap was enlarged. The pre-execution guard failure remains charged to preparation. Scientific counters: zero model loads/generator requests/decoder forwards/target encodings/fits/new references/new input outcomes/real assignment searches; $0 paid compute. The ledger records all 24,000 trials/120,000 draws/12 datasets before work starts.

Focused tests cover poisoned output bodies, split and source duplicate rejection, deterministic sealed allocation, exact interval endpoints via an independent SciPy interface, minimal coverage, structural-versus-observed equality, paired/crossed resampling, extreme tails, overwrite refusal and budget exhaustion. The [32-test receipt](focused-tests.xml) and [separate consistency checks](validation.json) accompany this report. No full 451-test suite or historical saved-outcome verifier was rerun in E0.
