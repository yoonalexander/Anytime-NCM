# Quality-tolerant early translation: next research roadmap

October 25, 2026. **Q0 and its multiplicity extension are complete. The alternative method passed validation, but feasibility remains statistically blocked. Q1-Q4 remain unstarted; Q1 is not ready.** The user authorized Q0 on October 25; this roadmap grants no later-phase execution or changes to earlier gates.

**Question:** Can a frozen NCM produce earlier translations that differ from its final text yet retain acceptable quality and deliver useful actual latency savings?

The [completed cycle](evidence-gaps/continuous-closure.md) found sparse, late exact-text matches and insufficient savings for that rule. Earlier approximate-output searches suggested possibilities but failed to establish quality and latency together. This direction tests that unresolved question; it does not erase those results.

## Success contract

Keep the existing full-relative tolerances: corpus BLEU loss <=0.5, chrF loss <=1.0, numeric-reference F1 loss <=0.02 where defined, and negation-mismatch increase <=0.02. Require appropriate uncertainty bounds, >=5% actual mean ready-output savings versus full with a positive paired lower bound, and positive bounded improvement over potentially feasible fixed depths. Exclude a fixed depth only when adjusted quality bounds rule it out; lock the strong comparator before confirmation. Metrics and literal cues do not certify semantic correctness or safety.

## Conditional sequence

| Phase | Work | Gate to advance |
| --- | --- | --- |
| Q0: statistical feasibility | **Original Q0 complete, statistically blocked; subsequent multiplicity audit below.** [Protocol](quality-tolerant/q0-protocol.md), [methods/feasibility](quality-tolerant/q0-methods-and-feasibility.md), [synthetic validation](../../results/quality_tolerant/q0/README.md), [decision](../../results/quality_tolerant/q0/decision.json). 26 tests/137 deterministic checks; 96,000 trials/140,000 draws. | **Did not pass.** Primary cue floor 385 covered groups versus at most 240 in the 448-group consumed union; planned 80% power first needs 1,038 covered groups. E4 has 1,024 total, unknown coverage and remains sealed. Stop before Q1. |
| Q1: saved-data opportunity | **Not ready; unstarted after failed Q0 gate.** Under a new bounded protocol, inspect already released S1/E2 trajectories for quality-tolerant assignments and candidate inspection schedules. Reuse is exploratory; disclose search selection and estimated costs. | Enough exploratory headroom after plausible observation costs to justify measurement. A found assignment is not a certified optimum. |
| Q2: sparse-observation costs | Freeze a small inspection schedule and measure assigned exits against full and all relevant fixed-depth controls, charging reconstruction, decoding, transfers and observation work. | Matched-quality measured headroom meets the success contract. Clairvoyant assigned-exit timing remains a diagnostic, not an online selector. |
| Q3: causal controller | Freeze current/past-only features and continuation-value labels; use separately allocated development data, bounded fits and actual online timing. | One locked policy passes development quality/cost gates against full and a strong fixed baseline. |
| Q4: reserved confirmation | Evaluate that policy and locked comparators once on separately reserved confirmation inputs; no refitting or comparator replacement. | Report one go/no-go/inconclusive result, preserve failures, and update the manuscript. |

## Q0 multiplicity extension

October 25: the user authorized a bounded audit of the statistical design. [Prospective protocol](quality-tolerant/q0-multiplicity-protocol.md), [numeric lock](quality-tolerant/q0-multiplicity-lock.json), [source lock](quality-tolerant/q0-multiplicity-source-lock.json). **Complete:** [methods/feasibility](quality-tolerant/q0-multiplicity-methods-and-feasibility.md), [synthetic evidence](../../results/quality_tolerant/q0_multiplicity/README.md), [decision](../../results/quality_tolerant/q0_multiplicity/decision.json). The protected-exclusion joint design passed64 tests and610,000 synthetic trials; necessary covered count385->183 and first80%-power count1038->436 at adverse p=.005. **Feasibility still blocked:** released numeric coverage is at most240, half-margin zero-event precision needs368, and separate population coverage/dependence is unresolved. Original Q0 results/margins and all reservations are unchanged. Stop before Q1.

## Boundaries and stopping

Before each executed phase, freeze identities/access releases and numeric sample, search, fit, request, warmup, retry, time, memory, storage and dollar caps. Existing E3/E4 reservations remain sealed until their new prerequisites and explicit releases are satisfied. Historical finals and E2 are consumed data; unknown document/training overlap remains disclosed.

References, future outputs and identities may support offline diagnostics/labels, never online features. Stop on inadequate statistics, absent headroom, parity failure or exhausted budgets. Preserve original protocols/artifacts, commit/push each completed phase and verify remote equality. Do not enlarge samples, relax margins or add rules to pursue a positive result. Target encoding, model training, paid compute, external contact and submission are outside this roadmap.
