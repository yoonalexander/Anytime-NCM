# S1 exploration lock

Completed October 24, 2026. Exactly 128 saved exploration trajectories; no development bodies/references materialized for new S1 analysis. The frozen algorithm/source is unchanged.

Selected feasible fixed depth: 11. All 11 fixed-depth scores match historical exploration corpus results within 1e-10.

| Point | Evaluations | Early inputs | Mean levels | Mean codes | Surrogate reduction vs full |
| --- | ---: | ---: | ---: | ---: | ---: |
| O0 | 10000 | 9 | 10.3672 | 293.0000 | 4.553% |
| O1 | 10000 | 9 | 10.3672 | 293.0000 | -1.167% |
| O2 | 10000 | 9 | 10.3672 | 293.0000 | -18.328% |

Every point hit the 10,000-assignment cap during a sweep. These are best feasible assignments found, not certified optima. No extra search, alternative initialization or budget extension will be used on development.

Practical headroom remains inconclusive: arbitrary-exit WMT latency is unidentified by retained full-depth measurements. Surrogate costs are uncalibrated assumptions, not milliseconds. Bootstrap intervals condition on selected assignments and do not account for selection uncertainty.

The source, population, protocol, metrics, quality thresholds and cost scenarios are locked for development. See `result.json`, append-only search/acceptance ledgers, and `execution.json`. Exactly 30,000 complete assignments were charged; zero model calls, fits or new final outcomes.
