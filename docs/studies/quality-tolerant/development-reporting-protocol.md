# Phase07R: preserved-development reporting repair only

Prospectively frozen October29,2026. The [original phase07protocol](development-collection-protocol.md) produced4304native traces with complete generator/tokenizer state/work/native-final checks and12897sentence-label pairs. It saved valid proxy-labels.json and parity-hashes.json, then failed writing label-support.json because its support arithmetic retained a NumPy bool scalar. json.dumpcannot serialize that scalar; the partial76byteJSON and failure are preserved. The failed attempt was pushed atf2771d2475e49bcba3719ac9fa957001bef9e550 before this repair. [Numeric lock](development-reporting-lock.json), [source lock](development-reporting-source-lock.json).

## Allowed repair and unchanged arithmetic

Do not edit or rerun scripts/run_development_collection.py, original support()or any original artifact. Do not regenerate, tokenize, extract corpus payloads, rescore references, refit, allocate data, change endpoints/thresholds or release evaluation/confirmation. Write all new outputs under campaign_20261029/development_collection_reporting/. Source/private failed data are byte-frozen before repair; preserve the partial JSON without parsing or replacing it.

The new plain()helper recursively converts NumPy scalar.item()values to ordinary bool/int/float and validates finite floats/string keys, preserving exact existing scalar values and None. Reuse UNCHANGED original support()on the already saved normalized label table and fixed4299fit/calibration entries, then normalize its report. This changes serialization types only, not statistical arithmetic, support floors, margins or any policy. Four invented cases must reproduce the NumPy failure, demonstrate equal NumPy/native statistics, preserve nested values/missing labels without mutation and reject nonfinite/unsupported values before saved data replay.

## Verification and provenance

Verify all4304saved public request records against the original plan, original worker counts(47344generator levels/51648decoders/0encoders), all8608feature calls/type,8603source-prefix checks and unchanged worker fingerprints. Stream exactly4304private generated traces, compare complete11decoded-state/native-final/work metadata, exact all-level prefix/output cache hashes and27features8/10to committed public records. Verify4299unique nonwarm keys/5warmups and alloriginalfit/calibration component/role/identity bindings. Replay ZEROmodel operations. Read only4299saved normalized label rows; validate exactly8/10,4coordinates and Noneallowed only for numeric-reference F1. Do not open source/reference cache as text or call sentence_targets again. Source/reference caches are hashed as bytes solely for preservation. Check recorded GPU/worker wall/RSS and combined original public/private storage caps.

Original extraction/label ledger must show4299source/refpayloads,13955source/refheaders,4304trace reads,12897label pairs. No development_evaluation1188, proposedconfirmation7700, old87/E3/E4/unallocated outcome is released. All old failed scientific gates, Q0and unknown overlap/dependence remain unchanged. The successful new report can support only a separately locked fitting/selection study if the ORIGINAL label-support criteria pass; it does not establish quality, speedup or confirmation.

The old parent final resource-check/execution receipt was never reached. Do not invent exact parent CPU/wall usage or relabel that failed run complete. Worker CPU771.204sec/wall837.808sec/RSS2778546176bytes are recorded. Original accounting07charges its FULL4312attempt/3720model-sec/2400CPU-sec/128MiBreservation, while4307actual model attempts are known(4304real+3toy). Preserve that conservative charge without refund or double-charging model work in this repair. The new combined completion receipt distinguishes successful saved-data verification/reporting from the original failed attempt and its missing parent final CPU receipt.

## Current repair caps and delivery

4synthetic cases,<=1000invented scalar values,0toy models/fits/Monte Carlo. Current real model requests/checkpoint loads/tokenizations/corpus payload decodes/reference scores/fits/new families/targets/downloads/dollars/confirmation all0. Saved public/private trace records4304each; normalized label rows4299; source-only allocation metadata5487. Wall1200sec, tests120sec, executionCPU600sec+300reporting/verification credit, parentRSS2GiB, new artifacts16MiB, retries0. SHA checks may stream only the fixed source/failed/private files; no data mutation or additional collection is allowed. Record original work as provenance, not new model charges. Shared campaign ceilings remain binding.

Freeze/push before tests or saved-label replay. Archive repair source, bind old failure/private/public hashes, append accounting07Rusing ONLYnewCPU/artifactcharges, write a new support/decision/completion receipt and report/roadmap. On another failure preserve it and do not silently retry or alter the original run. The two unvalidated future fitting prototype files are safely hash-preserved under ignored data/.../unvalidated_planning; they are not imported/executed by this repair and await their own future lock/tests.

~~~powershell
.\scripts\wsl_python.ps1 -PythonArguments @('scripts/repair_development_reporting.py','run','--commit','PUSHED_REPAIR_LOCK')
.\scripts\wsl_python.ps1 -PythonArguments @('scripts/repair_development_reporting.py','verify')
~~~

Saved verification checks bound files/receipts without re-decoding corpus text, repeating reference scoring or running model inference. No new methodological claim or Q0method is introduced; unchanged primary metric/statistical sources remain in earlier protocols.
