# Phase07 development collection: data verified; reporting repaired

October29,2026. **The fixed development extension adds actual, varying refinement-loss supervision.**3408fit inputs and891calibration inputs are collected;1188development-evaluation and7700proposed-confirmation outcomes remain closed. Fit negation-change adverse counts are34at8/11at10, compared with0/260in the original fit pool. Both the general joint-class and minimal5adverse/5nonadverse cue-label floors pass. These are development sanity checks, not quality power, calibrated protection or a Q0pass.

[Original collection protocol](development-collection-protocol.md), [numeric lock](development-collection-lock.json), [source lock](development-collection-source-lock.json), pushed e26967e7bc8e457fd48f22aec84e886f724bd81c before tests/corpus/models. The native collection completed but its report serialization failed. The failed attempt was preserved/pushed f2771d2475e49bcba3719ac9fa957001bef9e550. [Reporting-only repair protocol](development-reporting-protocol.md), [repair lock](development-reporting-lock.json), [repair source lock](development-reporting-source-lock.json), pushed6d11e1a3b1417b441a139683faaeff4e93404645before tests/saved-data replay. No generation or reference scoring was repeated.

[Repaired support](../../../results/quality_tolerant/campaign_20261029/development_collection_reporting/label-support.json), [decision](../../../results/quality_tolerant/campaign_20261029/development_collection_reporting/decision.json), [combined completion](../../../results/quality_tolerant/campaign_20261029/development_collection_reporting/completion.json), [repair execution](../../../results/quality_tolerant/campaign_20261029/development_collection_reporting/execution.json), [review](../../../results/quality_tolerant/campaign_20261029/development_collection_reporting/completion-review.json). [Original failure](../../../results/quality_tolerant/campaign_20261029/development_collection/failure.json), [worker completion](../../../results/quality_tolerant/campaign_20261029/development_collection/worker-execution.json) and its partial label-support.json remain byte-identical.

## What the new labels establish

All label counts are per-input differences against the same frozen full output. Sentence BLEU/chrF losses are proxies, not decompositions of corpus metrics. Missing numeric labels stay missing; no source-number replacement of the reference-defined endpoint occurs. Normalized joint adverse=max(0,defined endpoint losses)>4as previously frozen.

| Role /level | Joint adverse/nonadverse | Numeric defined | Numeric adverse/nonadverse | Negation adverse/nonadverse |
| --- | --- | --- | --- | --- |
| Fit /8 | 2383/1025 | 714/3408 | 253/461 | 34/3374 |
| Fit /10 | 1562/1846 | 714/3408 | 114/600 | 11/3397 |
| Calibration /8 | 647/244 | 226/891 | 85/141 | 13/878 |
| Calibration /10 | 408/483 | 226/891 | 35/191 | 7/884 |

Fit has178document/alias components and calibration59, fixed prospectively. Counts do not imply independent adverse examples; endpoint-specific component concentration/generalization remains to be assessed in the fitting study. Every previously all-zero fit negation head was unsupported; the new data now contains both adverse and nonadverse labels, but does not itself train or validate any head. Operational floors(20/10joint examples/class and100/40numeric-covered references;5each-fit-cue class)pass at both levels. All missing/nonzero/improvement/range counts remain in the full report.

This adds new DEVELOPMENT model outcomes; it is distinct from phase06's outcome-free metadata audit. It supplies no new independent confirmation, corpus uncertainty bounds or adaptive timing claim. Unknown checkpoint overlap, unresolved story dependence, aggregate reference exposure and failed Q0proofs remain disclosed. No evaluation data is used for these labels.

## Acquisition, current-state isolation and verification

Selective byte-header parsing inspected13955source/refheaders each, decoded exactly4299source and4299reference payloads, and skipped unallocated payloads before UTF8decode. All source/reference document/segment headers aligned. Exact prior-audit payload text/whitespace/entities were preserved; all4299actual native96-token source prefixes matched audited identities before generation.0GETs/downloads;71,147,520decompressed bytes from checksum-pinned cached archives. Corpus text and complete generated traces remain ignored private data with public digests; no full logits/activations/checkpoints entered Git.

One local CUDA worker,4304native full requests(4299inputs+5warmups),47344generated levels,51648decoder calls,0encoders/targets/fits/new families. Native full generation produced every code sequence;11prefix-isolated reconstructions plus independent direct final decoding checked every final state.8608each cheap/logit/cue feature calls,8603source-prefix calls. Features at8/10use exact current prefixes, current raw logits and actual8-only history at10. These offline traces do not save generation or measure controller speed. Parameter-state fingerprints were unchanged, and every native-final/work check passed.

7original synthetic cases validated selective-poison skipping, literal text preservation, alignment before reference decode, schema boundaries, native/final/prefix equivalence, poisoned future suffixes, exact work, history and unchanged states.3toyattempts including a rejected training-mode call;22toy generator levels/15decodes. Four additional reporting-only cases reproduced NumPy JSON failure, exact NumPy/native statistical parity, nested scalar/missing-value preservation and nonfinite/type rejection. No broader full suite was rerun.

## Preserved failure and bounded repair

The parent completed12897sentence-label pairs and saved valid proxy labels/all-level hash cache, then json.dumprejected a NumPy bool in its support dictionary. The partial76byteJSON and failure are retained. Frozen original code was not modified. The repair losslessly converts NumPy scalar values to native JSON types, calls the UNCHANGED support arithmetic on the saved labels and writes a NEWreport directory.

The pushed repair verified4304private traces against committed public all-level prefix/output/feature hashes,4299nonwarm identities/roles,5warmups, original forward/feature ledgers and recorded GPU/worker/storage limits. It read no corpus source/reference payload and performed0newtokenizations/modelcalls/reference scores/fits/bootstrap. Saved verifier passed; independent review checked typed support identities,7+4test cases and1234protected historical files. Original private/public data binding is preserved; no failed artifact was replaced to make a verifier green.

Original worker wall837.808sec, CPU771.204sec, RSS2778546176bytes. Original combined public/private storage79,973,571bytes<128MiB. The parent's final execution/resource gate was never reached and its exact final CPU/wall receipt remains unavailable; do not claim those checks passed. Original accounting07retains the FULL4312attempt/3720model-sec/2400CPU-sec/128MiBreservation, while4307actual attempts are known. That is a conservative allocation charge, not a claim all reserved work ran, and was not refunded. The separate reporting repair added0model work, wall17.837sec/CPU6.246sec+300reporting credit/RSS252919808bytes/16MiBartifact credit.

Cumulative campaign charges10607model attempts(including5conservative unused slots),5157.982model seconds(including explicit allowances/reservations),5307.228CPU seconds,4real fits/1family,480MiBartifact credit,$0. Actual-known attempts10602. Shared ceilings remain binding; no confirmation was released.

## Next conditional stage

General development support and minimal cue variation pass, so prospectively lock bounded controller fitting/feature ablations/selection using ONLY3408fit/891calibration inputs. Report rare-adverse component support and calibration/ranking limitations. Keep all generator/tokenizer weights frozen; do not describe raw scores or literal cues as semantic guarantees. Select/push ONEpolicy and fixed comparator before opening1188development-evaluation outcomes. The remaining campaign budget permits at most one additional family; every actual refit/ablation counts against32. Do not repeat this extension, enrich outcomes or tune against evaluation to rescue a result.

Q0remains failed. Its independent-population/statistical prerequisites are distinct from improved development supervision. The original .5BLEU/1chrF/.02numeric/.02negation margins and>=5%actual mean saving with positive paired lower bound/fixed-depth improvement remain unchanged.

Saved-data verification:

~~~powershell
.\scripts\wsl_python.ps1 -PythonArguments @('scripts/repair_development_reporting.py','verify')
~~~

The original run command must not be repeated. Private corpus/trace assets are intentionally required locally for full hash verification and future development; their digests and official archive provenance are retained without claiming redistribution rights.
