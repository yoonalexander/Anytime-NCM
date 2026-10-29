# Phase09 evaluation reporting: unchanged controller fails the BLEU point margin

October29,2026. **The locked rule exits315/1188inputs early but loses0.664892corpus BLEU against0.5allowed.** The original four-endpoint development point screen fails. This is a negative result for the selected policy on its allocated evaluation data; no threshold, feature or model was changed afterward. There is no independent quality assurance or full-contract success.

[Original protocol](development-evaluation-protocol.md), [preserved failure](../../../results/quality_tolerant/campaign_20261029/development_evaluation/failure.json), [failure preservation](../../../results/quality_tolerant/campaign_20261029/development_evaluation/failure-preservation.json), [repair protocol](evaluation-reporting-protocol.md), [points](../../../results/quality_tolerant/campaign_20261029/development_evaluation_reporting/quality-points.json), [decision](../../../results/quality_tolerant/campaign_20261029/development_evaluation_reporting/decision.json), [execution](../../../results/quality_tolerant/campaign_20261029/development_evaluation_reporting/execution.json), [separate arithmetic review](../../../results/quality_tolerant/campaign_20261029/development_evaluation_reporting/completion-review.json).

## Frozen evaluation points

Policy ridge:cheap:8:guard0:0.6and fixed11 were pushed993180fbefore1188allocated evaluation outcomes. The rule observes8, stops when score<=.6, otherwise continues11, using19cheap features only. Population1188inputs/60document-alias components,289numeric-reference-covered inputs. No confirmation claims follow from this internal development allocation or the operational100coverage floor.

| Full-relative loss | Evaluation | Allowed | Point screen |
| --- | ---: | ---: | --- |
| Corpus BLEU |0.664892|0.5|Fail|
| Corpus chrF |0.994323|1.0|Pass, near margin|
| Mean reference-defined numeric F1 |0.011534|0.02|Pass|
| Negation mismatch increase |0.003367|0.02|Pass|

Full BLEU24.138878, chrF50.536913; controller BLEU23.473986, chrF49.542591.315/1188early exits(26.515%),873full fallback. Calibration's selected0.446092BLEU loss did not transfer below0.5here; different realized loss alone does not establish a mechanism or universal impossibility. All fixed1-10also fail the original corpus POINTscreen; fixed11passes. No adjusted quality exclusions were established, so faster fixed alternatives cannot be declared statistically ruled out.

## Original technical failure and bounded repair

Original lockde2bc20was pushed before5synthetic tests and evaluation access. All5tests passed. All1193native-cache requests(including5warmups) completed per-request parity/work checks:13123generator levels,14316decodes,0encoders. Receipt serialization then rejected torch.__version__, a TorchVersion string subclass, because strict plain() accepts native str. The error handler rejected it too. Parent stopped before trace replay, corpus scoring or any timing request. Full phase09reservation remains charged:58345attempts/10980model seconds/6800CPU seconds/192MiB, despite far fewer actual attempts. No refund or inference retry occurred.

The terminal traceback reached serialization after completion/state/work checks, but the actual final worker hashes/environment/CPU/RSS values were not durably written. They remain unavailable. Saved traces do not repair that missing process-state receipt. Original phase07reporting failure/full charge/missing original parent CPUgate also remain preserved.

Repair lock4c0c26dwas pushed before4focused reporting tests or saved-body replay. It explicitly converts only the version field to plain str, preserving strict rejection elsewhere. Tests cover actual TorchVersion complete/failure writes, source immutability, invalid/unrelated/nonfinite/key rejection and incomplete population rejection before body iteration. No toy/model/checkpoint initialization or request; test subprocess imports torch for its version type, parent imports no model framework.

All1193private traces bind to pushed plans/public features and every prefix/output hash; original native work totals and1188nonwarm population verified. Exactly1188already-released reference-cache bodies and12corpus score sets were used; no new SGML payload decode, tokenization, reference allocation, generation, encoding, feature extraction, fit or bootstrap. Saved verifier passed. Separate same-assistant arithmetic checked1188scalar decisions and12point differences/screens,1305protected files/3private digests. It is not independent human review or fresh corpus rescoring. No historical full-suite rerun claimed.

Repair wall36.365sec, CPU18.448sec charged plus50reporting credit, RSS278937600bytes,16MiBcredit,$0. Cumulative charges68952attempts,16137.982model seconds,12591.539CPU seconds,16fits/2families,752MiBartifact credit,0downloads/confirmation/paid dollars. Actual-known NNattempts are far below charged reservations; neither quantity may be silently substituted for the other.

**Next:** the original full timing matrix remains incomplete and cannot fit the remaining CPUbudget after full failure charge. A separately justified FIRST timing diagnostic may compare THISunchanged rule/nativefull on all1188inputs under a smaller frozen schedule to characterize actual speed despite failed quality. Omitted fixed-depth timing/reduced repeats must stay explicit; it cannot rescue the quality failure or establish the original contract. No refitting, new development population, or confirmation follows; finish with readiness audit and bounded closeout.

~~~powershell
.\scripts\wsl_python.ps1 -PythonArguments @('scripts/repair_evaluation_reporting.py','verify')
~~~
