# Anytime NCM: bounded campaign complete, selected controller fails quality screen

October 29, 2026. **This campaign did not establish the intended quality-and-latency advantage.** The final frozen controller stops early on 315 of 1,188 development-evaluation inputs, but its corpus BLEU loss is 0.664892, above 0.5 allowed. Actual mean ready-output time is 127.872 ms versus 134.710 ms native full (5.076% saving). This is a bounded negative development result for this selected rule; it does not prove every adaptive translation approach fails.

[Final decision](../../../results/quality_tolerant/campaign_20261029/closeout/decision.json), [objective-by-objective audit](../../../results/quality_tolerant/campaign_20261029/closeout/requirements.json), [phase/test/provenance audit](../../../results/quality_tolerant/campaign_20261029/closeout/phase-audit.json), [confirmation readiness](../../../results/quality_tolerant/campaign_20261029/closeout/confirmation-readiness.json), [verification runbook](campaign-20261029-verification.md), [live roadmap](../quality-tolerant-translation-roadmap.md), [original campaign objective](campaign-20261029-objective.md).

## What the final rule actually did

The 19-feature ridge rule was pushed at 993180f before evaluation outcomes. It observes level 8, exits at score <=0.6, otherwise goes directly to level 11. It uses no level-10 inspection, extra raw-logit summary or literal guard. Thresholds/coefficients/comparator were unchanged after evaluation. Evaluation uses 1,188 inputs in 60 whole document-alias components, including 289 references with numeric cues. Unknown checkpoint-training overlap and broad prior development exposure remain.

| Full-relative endpoint | Evaluation point | Requirement | Result |
| --- | ---: | ---: | --- |
| Corpus BLEU loss |0.664892|<=0.5|Fail|
| Corpus chrF loss |0.994323|<=1.0|Pass point only|
| Reference-defined mean numeric F1 loss |0.011534|<=0.02|Pass point only|
| Negation mismatch increase |0.003367|<=0.02|Pass point only|
| Actual mean ready-output saving vs full |5.076%|>=5%|Timing screen passed|

Actual per-session savings: 5.330%, 4.825%; retained conditional nominal paired interval [3.377%,6.861%]. Two processes, one timed repeat per input/method/session, 20 warmups and 4,772 requests, all causal exit/current-prefix/feature/output/work checks and unchanged model states verified. The timer includes tokenization, generation, observations, reconstruction, decoding/transfers, features, scalar decisions and final synchronization. CUDA stream spans are separate records.

Intervals resample 60 whole components 20,000 times, condition on the two observed sessions, and retain original nominal tail .05/22 and Monte Carlo family 11 despite only one observed contrast. Their approximate interpretation requires suitable independent/exchangeable components; no hardware/session-population or finite-sample guarantee follows. No quality confidence bounds were established. Corpus metrics/literal cues do not certify semantics.

All 11 fixed depths have corpus point scores; depths 1-10 fail them, but no adjusted quality exclusion was established. Their actual timings were omitted from the final smaller diagnostic. Consequently improvement over all potentially feasible fixed alternatives remains unproved. Historical all-fixed timings for a different policy/population cannot fill that gap. This report does not claim the original success contract was met.

## What the campaign learned

The original 16-input rich confidence pilot failed its whole-request cost gate. A separately frozen lighter pilot qualified selected-token raw-logit extraction; these scores are not calibrated probabilities. Initial richer probes modestly improved level8ranking on consumed calibration data, without demonstrating useful controller performance.

The first rich controller's actual calibration saving was 4.161%, below 5%. A metadata-first whole-component development extension added 3,408 fit, 891 calibration and 1,188 evaluation inputs while leaving 7,700 proposed confirmation inputs reserved. Numeric supervision grew to 714 fit and 226 calibration covered references, and fit negation-change labels became variable (34 adverse examples at level 8; 11 at level 10) rather than all zero. These are development support counts, not protection or power guarantees.

Final matched ridge ablations and shallow trees used 16 total real fits across 2 families. Richer features improved ranking modestly, but the frozen cost/quality selection chose cheap features. Selected calibration BLEU loss of .446092 and projected 5.325% saving did not transfer to the evaluation BLEU tolerance. Changed sample/population/model/target choices prevent attributing improvement or failure to a single cause. No true continuation-value estimator, generator/tokenizer training or target encoding was performed.

## Preserved failures and scope limits

The original phase07 collection completed 4,304 native requests but failed NumPy-boolean support-report serialization. A reporting-only repair recovered saved labels; original partial JSON/full reservation and missing original parent final CPUgate remain preserved.

The original phase09 evaluation completed 1,193 native-cache requests but failed terminal JSON serialization of TorchVersion. Its final state hashes/environment/resource values were not durably saved. Reporting-only repair verified every saved trace/public binding and computed the above corpus points without new inference. Missing process-state/resource observations remain unavailable. The version field was explicitly normalized and a durable initial receipt added before the final timing diagnostic.

**The original 12-method/two-repeat evaluation matrix remains incomplete.** Full conservative failure charges left insufficient CPU for it. A prospectively frozen first controller/native-full timing diagnostic retained all 1,188 inputs but used 2 methods and one repeat; its quality failure was already known and could not be rescued. This is a separate bounded diagnostic, not retrospective completion of the failed matrix. No policy was retuned or sample replaced.

## Confirmation and stopping decision

Confirmation is not ready and was not released. The selected controller fails its development BLEU point gate. Independently, the prior final-math review's declared heterogeneous independent-component all-zero marginal route remains closed: sharp endpoints .034389 for numeric loss and .025542 for negation increase exceed .02, and the largest confirmation component (85/7,700) exceeds the frozen 1% operational screen. These are limitations of that model/population/observation route, not universal impossibility for every signed-data method or population. No new method was chosen to rescue this result.

Q0 remains failed; 7,700 proposed confirmation inputs and historical E3/E4/unallocated outcomes stay sealed. No further model families, fits, development extension, retuning or confirmation follows this campaign. A materially different scientific hypothesis would be a new study with new justification; it is not remaining work in this completed negative campaign. Human rights/authorship/independent scientific review and external submission remain separate and unperformed.

## Evidence, resources and delivery

There are 73 recorded passing focused test cases across prospectively locked stages; no fresh whole-suite run is claimed. [Phase09quality/repair detail](development-evaluation-results.md), [original phase09protocol](development-evaluation-protocol.md), [first timing protocol](first-timing-diagnostic-protocol.md), [phase08comparison](development-controller-results.md), [final mathematical review](final-math-review-results.md) preserve the primary evidence and methodological sources. Separate same-assistant arithmetic reviews are not independent human scientific review.

Charged before this reporting phase: 73724 attempts, 16906.930 model seconds, 13343.441 CPU seconds, 16 fits / 2 families, $0; known actual attempts 16571. Conservative failed reservations are charges, not claims all reserved calls ran. Closeout accounting adds its measured CPU/reporting allowance without refunds. Public/private artifacts, models/data kept outside Git, missing historical resource receipts and unknown checkpoint overlap remain explicit. All source locks, archived execution bytes, failures and pinned upstream are preserved.

The final saved verifier and Git live-equality check complete delivery. This negative closeout answers the bounded campaign objective without asserting that the project has achieved its intended useful adaptive stopping advantage.
