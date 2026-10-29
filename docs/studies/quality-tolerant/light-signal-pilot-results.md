# Campaign phase02: lighter current-logit measurement

October29,2026. **Selected-token raw-logit summaries qualified for bounded signal collection; top-two margins did not.** This is a collection-cost/variation result, not evidence of predictive value, a calibrated confidence probability, controller speedup or quality confirmation. The original phase01 whole-request cost screen remains failed.

[Protocol](light-signal-pilot-protocol.md), [numeric lock](light-signal-pilot-lock.json), [source lock](light-signal-pilot-source-lock.json), [campaign goal](campaign-20261029-objective.md). Lock `744789ca304c30566a39a4a042cb00c285f196f8` was pushed and live main verified before execution. This phase was a prospectively specified alternative feature bundle and measurement endpoint; no earlier failure, threshold or receipt was edited.

## Measurement and result

Same 16 consumed fit representatives; cheap control, margin-only and selected-logit summaries; two independent workers, eight repeats and five warmups/method/session.798 real requests:768 timed and30 warmups;128 timed observations per method/session. Method positions were balanced across each input's repeats. At 8/10 all arms computed 19 cheap current/past features; each extra arm added 3 logit summaries and 5 literal source/current cue features. All arms observed 8/10/11 and forced 11. No references or old 87 evaluation outcome bodies were opened, and no learned stopping occurred.

Selected logits were gathered at the frozen picker's already selected current token IDs, then summarized by mean/p10/min through the current EOS inclusive. They are raw model scores, sensitive to additive logit shifts; neither their scale nor ordering is assumed calibrated. Margin is a shift-invariant relative score, but its vocabulary-wide top-two operation was more expensive here. Source/current cue comparisons retain their literal heuristic meaning and do not replace any endpoint.

Every current code prefix at 8/10/11 and every observed token/text matched saved fit outputs, including final full codes. Model states were unchanged before/after and across workers. All features were finite/repeatable, cheap prefixes matched exactly across arms and both logit groups varied across inputs. No raw logits/activations or new full trajectories were persisted.

The new engineering screen required, in EACH session: extra synchronous extraction mean<=1 ms and p95<=3 ms, plus paired whole-request mean penalty<=5 ms as a large-penalty guard. The synchronous block includes its GPU work, compact transfer and cue/host summaries inside request timing. It does not capture every possible downstream scheduling/clock interaction. Whole ready-output timing remains separately reported.

| Signal /session | Extra-block mean ms | Extra-block p95 ms | Paired ready-output mean added ms | Paired ready-output p95 added ms | New collection screen |
| --- | ---: | ---: | ---: | ---: | --- |
| margin /0 | 1.491 | 2.048 | 1.778 | 17.753 | fail |
| margin /1 | 1.549 | 2.145 | 2.084 | 17.278 | fail |
| selected_logit /0 | 0.836 | 1.116 | 0.221 | 15.746 | pass |
| selected_logit /1 | 0.873 | 1.111 | 1.265 | 18.932 | pass |

Only selected_logit qualified. The margin-first priority was frozen before execution; selected_logit was chosen because margin failed the component-mean criterion, not because of quality labels. Pairwise whole-request p95s remain large: this phase has NOT passed the old 1 ms/3 ms paired whole-request screen. A later actual controller must still pay every cost and demonstrate >=5% mean ready-output saving with a positive paired lower bound and all unchanged quality requirements. These engineering thresholds are provisional development heuristics, not inferential guarantees from 16 inputs. No timing resampling or statistical significance test was run.

## Work and campaign accounting

Six synthetic tests passed before real model/data work, validating raw-score versus margin semantics, EOS isolation/nonmutation, exact independent prefix/observation parity, work counters, explicit component-only qualification/large whole-path guard, invalid cells and balanced order. Tiny CPU work:6 model API attempts including 2 expected rejections,44 generator levels,20 decodes,0 encoders/fits. Those attempts were charged.

Real work:798 requests,8,778 generator levels,2,394 decodes,0 encoders,830 prefix calls including 32 prechecks;1,596cheap/532margin/532selected-logit/1,064cue feature calls. Two checkpoint loads,32source-string materializations,16old trajectory bodies,0reference bodies/new inputs/target encodings/fits/families/downloads/dollars. Model orchestration171.347seconds; execution wall194.199seconds. All stage/campaign resource caps passed.

The cumulative append-only campaign charge after phase02 is 957 model attempts (including 11 synthetic),256.613 model seconds,830.624 CPU seconds (including two 300-second reporting allowances),128MiB conservative artifact credit,0 real fits/controller families/downloads/confirmation/dollars. Actual result bytes are much smaller than the artifact credits. See [phase02 accounting](../../../results/quality_tolerant/campaign_20261029/accounting/phase-02-light-signal-pilot.json); ceilings are not reset for the next phase.

Scripted completion checked 1171 hashes, all 798 request receipts and 2,394 current-prefix hashes without new model work or old-body replay. This is not independent replication. No full historical suite was rerun. [Execution](../../../results/quality_tolerant/campaign_20261029/light_signal_pilot/execution.json), [analysis](../../../results/quality_tolerant/campaign_20261029/light_signal_pilot/analysis.json), [decision](../../../results/quality_tolerant/campaign_20261029/light_signal_pilot/decision.json), [completion review](../../../results/quality_tolerant/campaign_20261029/light_signal_pilot/completion-review.json). Saved verifier: `scripts/run_light_signal_pilot.py verify` through WSL, with no new inference/analysis.

## Conditional next phase

The active goal now authorizes a separately frozen predictive-signal study on allocated development data, comparing selected-logit/cue signals with cheap features and simple baselines. It must report prior consumption, document allocation, missing/rare labels, calibration/ranking limitations and actual work. It must not infer predictive value merely from feature variation or the collection-cost pass. The constant-zero fit negation labels remain a supervision limit, not learned protection.

Proceed to that justified conditional stage after this result is committed/pushed; do not ask for another routine confirmation. Q0 remains failed; no original tolerance, scientific gate or reservation changes. A real controller and independent confirmation remain conditional on their own evidence.
