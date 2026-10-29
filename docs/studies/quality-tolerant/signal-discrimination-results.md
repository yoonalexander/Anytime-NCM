# Phase03 signal discrimination: completed, development gate passed

October29,2026. **Selected-token raw logits and literal source/current cues improved the fixed level8 joint-risk probe on consumed calibration data.** This supports the next bounded controller-selection study. It does not establish quality preservation, actual controller savings or independent confirmation. Level10 remains weak; rare-cue supervision remains inadequate.

[Prospective protocol](signal-discrimination-protocol.md), [numeric lock](signal-discrimination-lock.json), [source lock](signal-discrimination-source-lock.json). Lock1229f7b910ca5ad23f5b473e9142850c9bda160f was pushed with live remote equality before tests, outcome reads, inference or fitting. [Analysis](../../../results/quality_tolerant/campaign_20261029/signal_discrimination/analysis.json), [decision](../../../results/quality_tolerant/campaign_20261029/signal_discrimination/decision.json), [execution](../../../results/quality_tolerant/campaign_20261029/signal_discrimination/execution.json), [completion review](../../../results/quality_tolerant/campaign_20261029/signal_discrimination/completion-review.json).

## Fixed comparison and observed ranking

260fit/101calibration inputs are the same consumed document/alias split used previously,66/33components. No former87evaluation bodies or reserved outputs were opened. Four fixed ridge binary-label probes: cheap19features versus selected27features, separately at8and10. The joint-adverse label is max defined normalized sentence loss>4; equality is nonadverse and undefined numeric labels are omitted only for this proxy. This differs from the earlier diagnostic's threshold1AUC; those earlier numbers are not a matched comparison. Threshold4 was prospectively fixed using disclosed earlier development diagnostics, not selected on fresh outcomes. Corpus margins remain unchanged.

| Level | Calibration adverse/nonadverse | Cheap AUC | Rich AUC | Rich-minus-cheap | Rich component-deletion AUC range |
| --- | --- | --- | --- | --- | --- |
| 8 | 67/34 | .622915 | .663301 | .040386 | .609971–.683607 |
| 10 | 42/59 | .520178 | .564165 | .043987 | .544288–.577511 |

The frozen richer-gain heuristic requires at least10calibration examples/class, rich AUC>=.60 and gain>=.02 at one level. Level8passed; neither level10probe qualified. Component deletions are sensitivity checks on dependent observations, not confidence intervals or new samples. There are no p-values, significance/multiplicity assertions or bootstrap draws. The result cannot distinguish the contribution of logit summaries from the simultaneously added literal cues; a separate ablation would require another declared experiment.

Negative selected-logit mean raw-score AUCs were .595259/.573043 at8/10; raw p10/min, cue-disagreement and token-change baselines are retained in the analysis. No sign was flipped after access. All scores are development diagnostics; raw logits are not probabilities.

## Calibration and supervision limits

Rich clipped-score squared errors were .208638/.255519 versus fit-prevalence baselines .223763/.247647 at8/10. Level8improves this descriptive error; level10does not. Five fixed reliability bins and clipping counts (5at8,0at10) are saved. Clipped least-squares scores are not calibrated probabilities; squared error combines calibration and discrimination, and these bins cannot establish risk control. See the [primary implementation documentation](https://scikit-learn.org/stable/modules/calibration.html).

Numeric-reference labels are defined for58/260fit and20/101calibration inputs. Fit adverse counts12at8/5at10; calibration9/3. Fit negation-change labels remain exactly0/260at both levels while calibration has4/2adverse changes. No endpoint-specific head was fitted, and the joint probe cannot be described as learned protection for a cue with no adverse fit supervision. Source/current cue agreement is a heuristic, not the reference-defined endpoint or semantic correctness.

## Execution, verification and next branch

9focused synthetic tests passed before data/model work: missing numeric/boundary proxies, rare/absent classes, training-only standardization, constant features, shifted validation, tied/null/reverse AUC, component dependence, clipping/bin boundaries, all gate branches, allocation rejection and penalized normal equations.3toyfits,0synthetic model requests/checkpoint loads. Four real models consume family1and4of32campaign fits. No broader historical full suite was rerun.

366real requests (361collection+5warmups),4026generated levels,1098decoders,0encoders/targets.727prefix calls,361source strings/references/old trajectory bodies,1083sentence-label pairs,732each cheap/logit/cue calls. Every generated8/10/11prefix and decoded observation/final output matched the old cache. Released generator/tokenizer states were unchanged. One local CUDA process; actual model orchestration82.927sec; total102.235sec. Execution CPU charge78.773sec plus300reporting credit, parentRSS135467008bytes, workerRSS2807537664bytes, artifact credit64MiB, actual pre-report tree~2.84MB,$0. These collection timings are not an adaptive-controller benchmark.

Saved verifier passed. An independent pure-Python completion check verified1103protected historical files,1098current-prefix receipts, all four101-input predictions, training-only feature means, pairwise AUCs and9test cases without new inference/fitting. [Accounting03](../../../results/quality_tolerant/campaign_20261029/accounting/phase-03-signal-discrimination.json) is append-only. Cumulative charges1323model attempts,339.540model seconds,1209.398CPU seconds,4real fits,1family,192MiBartifact credit,$0. Earlier failed pilot gates and failed Q0 remain unchanged.

Next authorized branch: prospectively lock a bounded joint-risk controller calibration/selection using these fixed models, unchanged corpus point margins and fully charged online timing. Push the selected policy/comparator before allocated evaluation access. Do not infer quality or5%speedup from AUC. Rare-cue data extension remains conditional; confirmation remains statistically blocked unless separate prerequisites can actually be met.

Verification from repository root:

~~~powershell
.\scripts\wsl_python.ps1 -PythonArguments @('scripts/run_signal_discrimination.py','verify')
~~~
