# Final timing diagnostic: actual speedup, but the selected rule fails quality

October 29, 2026. **The frozen controller saves 5.076% actual mean ready-output time against full depth on the 1,188 evaluation inputs. It still fails the original BLEU point tolerance: 0.664892 loss versus 0.5 allowed.** This campaign has a negative combined quality-and-speed result for its selected policy.

[Prospective protocol](first-timing-diagnostic-protocol.md), [numeric lock](first-timing-diagnostic-lock.json), [source lock](first-timing-diagnostic-source-lock.json), [analysis](../../../results/quality_tolerant/campaign_20261029/first_timing_diagnostic/analysis.json), [decision](../../../results/quality_tolerant/campaign_20261029/first_timing_diagnostic/decision.json), [execution](../../../results/quality_tolerant/campaign_20261029/first_timing_diagnostic/execution.json), [separate arithmetic review](../../../results/quality_tolerant/campaign_20261029/first_timing_diagnostic/completion-review.json), [quality and original failure detail](development-evaluation-results.md).

## Actual measured performance

The same cheap19-feature ridge rule observes level 8 and exits at score <=0.6; otherwise it continues directly to 11. Policy/comparator were pushed at 993180f before evaluation access and were not changed afterward. Diagnostic lock f19effd was pushed before its three pure synthetic tests or real requests. All 1,188 inputs / 60 document-alias components are retained, with 315 early exits and 873 full fallbacks per timed process.

| Ready-output timing | Controller | Native full |
| --- | ---: | ---: |
| Mean, ms |127.872|134.710|
| Median, ms |133.271|134.059|
| p95, ms |149.954|149.016|
| Session 0 mean, ms |126.843|133.984|
| Session 1 mean, ms |128.902|135.436|

Mean saving is 5.076%; session savings are 5.330% and 4.825%. The retained conditional nominal paired interval is [3.377%, 6.861%]. The predeclared timing screen passes: mean >=5%, both sessions positive and paired lower bound >0. This does not require the lower bound itself to exceed 5%, nor each session individually to reach 5%. p95 is slightly worse for the controller; no tail-latency improvement is claimed.

The complete wall timer includes source tokenization/context, actual generation, current-prefix reconstruction/decoding/transfers, 19 cheap features, scalar prediction and final synchronization. CUDA stream spans remain separate records. Two distinct processes, one timed repeat per input/method/session, 20 warmups, 4,772 real requests. All actual exits/visits, skipped forwards, current generated level-8 codes, feature values, every observed/final output and unchanged generator/tokenizer state hashes passed. Workers read sources only, no references. No target encodings, training, new features or score recomputation.

## What the result does not establish

Saved corpus points on the SAME outputs are BLEU loss .664892 (fails .5), chrF .994323, numeric-reference mean F1 .011534, negation increase .003367; the latter three pass their point tolerances. Numeric coverage is 289 references. Points are not independent quality confidence bounds. The development selection/generalization limitations and failed Q0 remain.

The original phase09 twelve-method/two-repeat matrix was interrupted after native-cache collection by a TorchVersion reporting failure. Its full conservative reservation remains charged and its missing terminal state/resource receipt is not reconstructed. The separately declared reporting repair bound every saved trace and reported quality. This FIRST timing diagnostic uses two methods/one repeat to fit the remaining budget; it is not completion of that original matrix. Fixed depths 1-10 retain quality POINTscores but no current-policy actual timing or adjusted quality exclusions. Thus supported improvement over all potentially feasible fixed alternatives is unestablished.

The 20,000 whole-component paired draws use the original conservative nominal tail .05/22, Monte Carlo family 11 and rank-error allowance .001, despite only one observed contrast. Input totals are summed before ratios. Intervals condition on the two observed sessions and need suitable independent/exchangeable components; they do not resolve temporal/device dependence, cross-hardware variability, within-session repeat variance or population quality assurance. Primary methodology sources remain in the frozen protocol.

## Validation, accounting and decision

Three pure tests passed before models: full paired schedules/year routing/work caps; unequal-weight component ratios/null/5% boundary/invalid inputs using fixed arrays; normalized complete/failure environment receipt before requests. No synthetic model APIs or repeated model tests. The original five runtime tests and four actual TorchVersion tests remain preserved. The durable initial environment/state receipts were saved successfully before real requests, and both final worker receipts exist with unchanged states.

Saved verification passed. A separate standard-library review checked all 4,772 records / 4,752 timed cells, current cheap features, prefix/output hashes, exact counters, positive finite times, means/medians/p95/session ratios and 1,326 protected files. It did not resample, rescore references or run models, and is not independent human scientific review. No fresh whole-suite claim is made.

Actual model orchestration 768.948 seconds; CPU 701.902 seconds charged plus 50 reporting/verification credit; public artifact allowance 32 MiB; $0. Cumulative charges: 73,724 attempts, 16,906.930 model seconds, 13,343.441 CPU seconds, 16 real fits / 2 families, 784 MiB artifact credit, 0 downloads/confirmation/paid dollars. Known actual model attempts are 16,571; failed reservations explain the larger charge and are not refunded. The original phase07 missing parent resource receipt and phase09 missing cache terminal receipt remain explicit limitations.

**Decision:** no further controller fitting, threshold changes, new development collection or confirmation. Finish the existing-evidence readiness audit and bounded negative campaign closeout. Actual speed saving has been measured; acceptable quality under the original contract has not.

~~~powershell
.\scripts\wsl_python.ps1 -PythonArguments @('scripts/run_first_timing_diagnostic.py','verify')
~~~
