# Campaign phase01: confidence instrumentation pilot

October29,2026. **Instrumentation/parity/variation passed; the original engineering cost screen failed.** This is a completed negative pilot, not a failed implementation or evidence that confidence cannot predict useful exits. No predictive-quality evaluation or fitting was performed.

[User goal](campaign-20261029-objective.md), [campaign ceilings](campaign-20261029-lock.json), [prospective pilot protocol](confidence-pilot-protocol.md), [numeric lock](confidence-pilot-lock.json), [source lock](confidence-pilot-source-lock.json). Lock `1607113e693d1642727f4cc1e593e119b9680568` was pushed with verified live-main equality before tests or outcome execution. The campaign remains active; this result selects a bounded alternative, not confirmation or closeout by itself.

## What ran

Sixteen canonical fit-role inputs; two separate processes, two timed repeats, five warmups per method/process.148 real requests (128 timed,20 warmups), plus five charged synthetic model API attempts. Both methods forced generation through 11 and observed 8/10/11. At 8/10 the control extracted 19 old cheap features. Rich extracted the same 19 plus margin/entropy summaries and five literal source/current cue comparisons,30 total. Entropy/margin summaries used only current token positions through first predicted EOS inclusive. References and former 87 evaluation bodies were not opened. No target encodings, weights fitted, generator/tokenizer changes, new inputs or reservations released.

Every generated code and observed token/text hash matched the old fit trajectories. Model fingerprints were unchanged before/after both sessions and identical across sessions. Cheap features matched the rich vector's first 19 fields exactly; rich repeats were consistent. Margin and entropy summaries varied across the 16 inputs at 8 and 10. Variation is not evidence of useful prediction. Full logits/activations were not saved.

## Actual cost screen

All numbers are milliseconds; paired added time is rich minus cheap for the same input/session/repeat. The screen required mean<=1 and p95<=3 in EACH session.

| Session | Cheap ready-output mean | Rich ready-output mean | Paired mean added | Paired p95 added | Synchronously measured extra-feature component mean |
| --- | ---: | ---: | ---: | ---: | ---: |
| 0 | 163.004 | 162.550 | -0.454 | 21.794 | 2.354 |
| 1 | 172.694 | 179.959 | 7.266 | 28.368 | 2.703 |

The paired whole-request contrasts have substantial variation and disagree in mean sign. Negative observed overhead is timing noise, not physically free feature extraction. Background load/clock/scheduling effects were uncontrolled; these data do not establish their cause. The component clocks include the actual confidence GPU work, compact transfer and host summaries inside the ready-output timer; they are supplementary diagnostics, not replacements for the original failed screen.

The full entropy/margin bundle is therefore not advanced unchanged into broad collection or fitting. The failed pilot and its exact thresholds remain intact. It also does not fail the ultimate translation success contract: no controller was fitted or early-stopping policy evaluated here. Q0 remains failed and its statistical prerequisites are unchanged.

## Justified bounded alternative

Source inspection gives a concrete lower-cost alternative: drop full-distribution entropy, retain current top-two margins and literal cue comparisons, and keep current/past cheap features. Full-vocabulary log_softmax/exp/product/reduction requires extra work beyond top-two reduction. That is a complexity rationale, not a measured speedup of the untested bundle.

The next phase must prospectively lock a margin-only engineering measurement before execution. Use direct synchronous extraction timing as its own measurement endpoint, retaining whole ready-output timing as a separately reported check with more pairs. This changes the measurement question and feature bundle; it does NOT turn the original end-to-end gate green, establish predictive utility or waive the final >=5% actual whole-controller requirement. If the alternative is correct, varying and cheap under its own declared screen, continue to prospectively locked signal discrimination. If not, justify only a bounded remaining branch or honest campaign closeout. No threshold loosening or retry-until-pass.

## Work and delivery evidence

8 focused synthetic tests passed before released model loading. Tiny-model attempts 5 include two expected rejections,33 generator levels,17 decodes,0 encoders; all are charged. Real work 148 requests,1,628 generator levels,444 decodes,0 encoders;296cheap/148confidence/148cue feature extractions;180 prefix calls including 32 prechecks. Parent selectively decoded 16 old fit trajectories; workers decoded 32 source strings;0 reference bodies. Two checkpoint loads. No fits or controller families consumed.

Actual model orchestration 85.265seconds, execution wall112.065seconds. Campaign charge:153 model requests, 85.265 model seconds, 368.639CPU seconds including 300 prepaid reporting/verification seconds,64MiB conservative artifact credit,0 dollars/fits/families/downloads/confirmation. The physical artifact tree remains far below that credit. Exact cumulative charges are bound by [append-only phase accounting](../../../results/quality_tolerant/campaign_20261029/accounting/phase-01-signal-pilot.json); future phases do not reset the ceilings.

[Execution](../../../results/quality_tolerant/campaign_20261029/signal_pilot/execution.json), [analysis](../../../results/quality_tolerant/campaign_20261029/signal_pilot/analysis.json), [decision](../../../results/quality_tolerant/campaign_20261029/signal_pilot/decision.json), [completion checks](../../../results/quality_tolerant/campaign_20261029/signal_pilot/completion-review.json). Scripted review checked 1135 hashes, all 148 request receipts and unchanged states, without new inference or old-body replay. This is not an independent replication. No full historical test suite was rerun.

Saved verification command: `scripts/run_confidence_pilot.py verify` through the existing WSL wrapper. The once-only run must not be restarted. The campaign continues under the user's conditional authorization with a new prospective stage lock.
