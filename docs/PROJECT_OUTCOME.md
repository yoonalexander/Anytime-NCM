# Final project outcome

## Original question

Can a frozen Next-Concept Modeling checkpoint choose a stopping level per input, return an acceptable answer earlier, and improve the measured quality/latency tradeoff after paying every monitoring cost?

The project tested hard/easy Sudoku and German-to-English translation. The original ambition was not merely fewer generated codes: it required appropriate quality assurance, at least 5% actual mean ready-output saving with a positive paired lower bound, and supported improvement over potentially feasible fixed-depth controls.

## Implemented engineering

- Full-resolution reconstruction of cumulative latent prefixes with released learned transformations, independent snapshots, intermediate/final parity and suffix isolation.
- A causal online callback that actually skips later generator levels, with per-forward accounting and current/past-only features.
- Exact Sudoku acceptance; corpus BLEU/chrF and separately labeled numeric/negation translation diagnostics.
- Fixed policies, learned current-validity and joint-adverse proxies, feature ablations, paired timing, whole-component data roles, source locks, budgets and retained failures.
- A portable historical trajectory viewer and saved Concept Firewall forecast bridge. The bridge performs no new forecasts or interventions.
- A dependency-free aggregate snapshot inspector and versioned source/wheel distributions. These are research inspection tools, not a production translation system.

Engineering validation supports these implementations. It does not establish the research advantage.

## Findings supported by retained evidence

Original Sudoku audits found no early exact valid solution in their tested settings. The selected Phase 2/3/4 final policies reached full depth and paid monitoring overhead. These are bounded negative comparisons, not proof of no useful policy for every model or task.

E2 found early exact-final-text matches on 43/256 inputs, but its charged every-level assignment was 13.41% slower than full depth. The 2.67% terminal-only assembly was post hoc and below the practical target. Approximate-output searches and the later clairvoyant sparse diagnostic showed headroom under their stated conditions; they were not deployable causal selectors or independent quality confirmation.

The final campaign used two controller families, 16 real fits and one eligible development extension. A cheap 19-feature, level-8 ridge rule was selected and pushed before evaluation. On 1,188 allocated development inputs it exited early on 315 and measured 127.872 ms versus 134.710 ms full: **5.076% mean savings**, conditional paired interval **[3.377%, 6.861%]**. Its **0.664892 BLEU loss exceeded 0.5 allowed**. chrF, numeric F1 and negation points were within their margins; independent noninferiority bounds were not established. Thus the intended combined result was not achieved.

[Detailed final campaign report](studies/quality-tolerant/campaign-20261029-final-report.md) · [Timing analysis](../results/quality_tolerant/campaign_20261029/first_timing_diagnostic/analysis.json) · [Quality points](../results/quality_tolerant/campaign_20261029/development_evaluation_reporting/quality-points.json).

## Unproven and unavailable

- No independently confirmed quality-preserving adaptive advantage, semantic correctness guarantee or feasible-fixed-depth frontier.
- The final smaller timing diagnostic omitted fixed depths 1-10 and used one repeat per process. The original full matrix remains incomplete.
- Original phase07 parent final resource values and phase09 native-cache terminal state/resource values were not durably recorded. Their failure evidence and full conservative charges remain; they are not fabricated later.
- Q0 and its bounded population/method reviews remain failed. The existing all-zero marginal route is closed under its declared model, not a universal impossibility result. E3/E4/unallocated and 7,700 proposed-confirmation outcomes remain sealed.
- Checkpoint-training overlap and broader story dependence remain uncertain. A true continuation-value estimator, XSum, generator/tokenizer training and a live Concept Firewall intervention were not performed.
- The historical hard-Sudoku baseline is 86.25% versus the upstream paper's 86.1%; the cause remains unresolved.
- Independent human scientific review, rights/authorship decisions for manuscript submission, and publication are separate and unperformed.

## Final delivery decision

Close the declared studies with their negative/inconclusive findings. Preserve deferred work as deferred, not as promised next milestones. Ship **research-v0.1.0** as a presentable research snapshot and inspection package. The useful deliverable is the code/evidence/inspection workflow, not an assertion that adaptive translation now meets the original contract.

No consumed experiment was rerun for repository delivery. New checks are software, installation, visual and saved-artifact checks recorded under `results/delivery/20261029/`; original research ledgers are not reset or extended.
