# S1B: cost, uncertainty and decision

Completed October 24, 2026. **Practical headroom: inconclusive. S3 entry gate not met.** The finite search finds point-feasible saved-output opportunity, but does not establish reliable matched quality or actual latency benefit.

## Frozen scenarios

| Split / point | Early inputs | Surrogate reduction vs full | Conditional 95% interval |
| --- | ---: | ---: | --- |
| exploration / O0 | 9/128 | 4.553% | [1.762%, 7.817%] |
| exploration / O1 | 9/128 | -1.167% | [-4.193%, 2.373%] |
| exploration / O2 | 9/128 | -18.328% | [-22.057%, -13.958%] |
| development / O0 | 18/64 | 14.085% | [8.315%, 20.377%] |
| development / O1 | 18/64 | 9.016% | [2.799%, 15.778%] |
| development / O2 | 18/64 | -6.190% | [-13.714%, 2.022%] |

Surrogate units are dimensionless. O0 assumes zero monitoring, O1 charges 0.005 per extra reconstruction/transfer plus 0.001 per observation for features/controller, and O2 charges 0.02 plus 0.004. f=0.25 and tau=0.5 are uncalibrated. The all-level surrogate schedule is distinct from the historical selected rules with two observations. These intervals keep exits and comparator fixed and ignore selection uncertainty.

## Why the gate does not pass

Development primary O1 point losses are 0.370429 BLEU /0.984773 chrF. The one-sided 95% lower quality bounds are -1.163781 BLEU and -1.905485 chrF, below allowed -0.5/-1.0. Two-sided intervals are [-1.351043,+0.572822] and [-2.136699,-0.201402]. This is unresolved noninferiority, not a demonstrated population violation and not confirmation on new data.

The O1 estimated reduction is 9.016214%, conditional 95% [2.798767%,15.778496%], versus both full and feasible fixed depth 11. O2 estimates 6.190036% overhead. The result depends materially on cost assumptions. The primary assignment breaks even at h about 0.01389; retaining at least 5% reduction requires h about 0.00896 or below under the frozen f/tau/controller-ratio model.

Historical development requests measure full 132.567596 ms and selected guarded adaptive 135.645510 ms: 2.321769% overhead, paired interval [1.533713%,3.110171%]. Those are retained full-depth requests, not a new benchmark. The primary scenario would predict only 0.7% overhead for a final-depth two-observation schedule; O2 predicts 2.8%. This comparison does not identify arbitrary per-level generator/decoder costs or a transferable h. No existing evidence calibrates f/tau. Actual latency for the oracle assignments stays unavailable.

All 45 f/tau/h scenarios for each of three found assignments are in `cost-sensitivity.csv` (270 rows across splits); no additional searches were run. The feasible fixed depth is 11 across these positive monotone cost models.

## Search and uncertainty limits

All six searches exhausted the cap mid-sweep; optimum/gap unavailable. Exploration and development have different n under the same candidate cap, so their different progress/headroom is not a clean generalization comparison. Oracle references/future levels are unavailable to a deployed controller. Bootstrap resampling is descriptive conditional uncertainty, not correction for assignment selection. Number-cue coverage is 13/64 development references; all cue metrics are heuristics.

## Branch decisions

- S2A: proceed with a frozen saved-data diagnosis of content emergence, harmful revisions and alternatives; zero model work.
- S3: do not fit or benchmark a continuation controller because practical-headroom and quality evidence do not meet entry.
- S4: no intervention justified from S1 alone; changing checkpoints/objectives to obtain a positive result would be outside this evidence.
- S5: a bounded mixed/inconclusive result plus S2A synthesis may be packaged honestly.

A specifically priced next-measurement proposal is included in the S2 closure record. It is not automatically executed; the failed/inconclusive gate does not permit expanding the consumed S1 search.
