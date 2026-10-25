# Quality-tolerant early translation: next research roadmap

October 25, 2026. **Planning only: all phases below are unstarted.** This document authorizes no experiments, fits, new outcome access or changes to earlier gates.

**Question:** Can a frozen NCM produce earlier translations that differ from its final text yet retain acceptable quality and deliver useful actual latency savings?

The [completed cycle](evidence-gaps/continuous-closure.md) found sparse, late exact-text matches and insufficient savings for that rule. Earlier approximate-output searches suggested possibilities but failed to establish quality and latency together. This direction tests that unresolved question; it does not erase those results.

## Success contract

Keep the existing full-relative tolerances: corpus BLEU loss <=0.5, chrF loss <=1.0, numeric-reference F1 loss <=0.02 where defined, and negation-mismatch increase <=0.02. Require appropriate uncertainty bounds, >=5% actual mean ready-output savings versus full with a positive paired lower bound, and positive bounded improvement over potentially feasible fixed depths. Exclude a fixed depth only when adjusted quality bounds rule it out; lock the strong comparator before confirmation. Metrics and literal cues do not certify semantic correctness or safety.

## Conditional sequence

| Phase | Work | Gate to advance |
| --- | --- | --- |
| Q0: statistical feasibility | Freeze endpoints, paired inference, multiplicity, sparse-cue handling, coverage/power checks and numeric resource caps. Validate proposed methods on synthetic data before real-outcome analysis. | Original quality margins can be assessed with an eligible, feasible population. Otherwise stop as statistically blocked. |
| Q1: saved-data opportunity | Under a new bounded protocol, inspect already released S1/E2 trajectories for quality-tolerant assignments and candidate inspection schedules. Reuse is exploratory; disclose search selection and estimated costs. | Enough exploratory headroom after plausible observation costs to justify measurement. A found assignment is not a certified optimum. |
| Q2: sparse-observation costs | Freeze a small inspection schedule and measure assigned exits against full and all relevant fixed-depth controls, charging reconstruction, decoding, transfers and observation work. | Matched-quality measured headroom meets the success contract. Clairvoyant assigned-exit timing remains a diagnostic, not an online selector. |
| Q3: causal controller | Freeze current/past-only features and continuation-value labels; use separately allocated development data, bounded fits and actual online timing. | One locked policy passes development quality/cost gates against full and a strong fixed baseline. |
| Q4: reserved confirmation | Evaluate that policy and locked comparators once on separately reserved confirmation inputs; no refitting or comparator replacement. | Report one go/no-go/inconclusive result, preserve failures, and update the manuscript. |

## Boundaries and stopping

Before each executed phase, freeze identities/access releases and numeric sample, search, fit, request, warmup, retry, time, memory, storage and dollar caps. Existing E3/E4 reservations remain sealed until their new prerequisites and explicit releases are satisfied. Historical finals and E2 are consumed data; unknown document/training overlap remains disclosed.

References, future outputs and identities may support offline diagnostics/labels, never online features. Stop on inadequate statistics, absent headroom, parity failure or exhausted budgets. Preserve original protocols/artifacts, commit/push each completed phase and verify remote equality. Do not enlarge samples, relax margins or add rules to pursue a positive result. Target encoding, model training, paid compute, external contact and submission are outside this roadmap.
