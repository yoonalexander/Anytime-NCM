# S1A: saved WMT opportunity audit

Completed October 24, 2026 under the frozen S0B protocol. Exactly 128 exploration then 64 development trajectories. Source/result lock was committed and pushed before development; the release records remote equality. Development is reused selection data, not fresh confirmation.

## Main observation

The bounded reference-informed search finds corpus-point-feasible mixed exits on development. This rejects the narrow assertion that the tested saved translation prefixes offer no mixed-assignment quality/work opportunity. It does not establish a deployable rule, statistically secure quality noninferiority, or an actual speedup.

| Development setting | Corpus BLEU | Corpus chrF | Early inputs | Mean levels | Mean codes |
| --- | ---: | ---: | ---: | ---: | ---: |
| Full / feasible fixed depth 11 | 19.965679 | 48.219904 | 0/64 | 11 | 313 |
| Best feasible found, primary O1 | 19.595250 | 47.235131 | 18/64 | 9.28125 | 244.34375 |

Point losses: 0.370429 BLEU and 0.984773 chrF; numeric-reference F1 unchanged over 13 covered references; negation mismatch +0.015625. These meet the point tolerances. Number/negation cues are heuristics, not factuality or safety labels.

All 11 fixed-depth corpus points reproduce the historical values within 1e-10; smallest feasible fixed depth is 11 in both splits. Saved selected stability and guarded-stability exits replay at full depth. Saved development online outputs match their trajectory exits for all 768 retained timed rows.

## Search and evidence boundary

Each of O0/O1/O2 used all 10,000 complete assignment slots on each split: 60,000 total. All six searches stopped during an incomplete sweep. No restarts, alternative algorithms, new trajectories, fits, model calls, or final outcomes. The three points happen to retain identical exit vectors within each split; this is a result, not a search reduction.

These are best feasible assignments found by one decreasing-coordinate search. They are not certified optima, global headroom bounds or causal policies. Limitations include single start, no compensating swaps/upward moves, finite cap, oracle references/future outputs, reused development data and unknown training overlap.

The 128-input exploration results were committed/pushed at dd2124e before development. Its cost/quality result did not trigger changes to development code, data, thresholds or budget. A WSL safe-directory check failed before development access; a command-scoped repository exception resolved it with no experiment source change.

S1B interprets costs and conditional uncertainty separately. See [development results](development/result.json), [exploration lock](exploration/summary.md), [release](exploration_release.json), and [frozen protocol](../../../docs/studies/stronger-research-protocol.md).
