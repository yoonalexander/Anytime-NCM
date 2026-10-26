# Bounded eligibility and cluster-method audit

Complete: actual six-year metadata and conditional cue-method validation; current frame/method remains a no-go for Q2. No model-benefit evidence was collected.

- [Results and limitations](../../../docs/studies/quality-tolerant/eligibility-audit-results.md), [combined decision](completion-decision.json).
- [Original prospective protocol](../../../docs/studies/quality-tolerant/eligibility-audit-protocol.md), [source-header correction](../../../docs/studies/quality-tolerant/eligibility-audit-metadata-correction-protocol.md).
- [48,000 synthetic datasets](method-results.json), [36 original deterministic tests](test-output.txt), [12 correction tests](metadata_correction/test-output.txt).
- [Actual population/coverage](metadata_correction/population-summary.json), [source-only split manifest](metadata_correction/split-manifest.json), [acquisitions and original headers](metadata_correction/acquisition.json).
- [Original failure retained](metadata-failure.json), [original execution](execution.json), [metadata continuation](metadata_correction/execution.json).

Verification only, without dataset-body parsing or simulation replay:

```powershell
.\scripts\wsl_python.ps1 -PythonArguments @('scripts/run_eligibility_audit.py','verify')
.\scripts\wsl_python.ps1 -PythonArguments @('scripts/run_eligibility_metadata_correction.py','verify')
```

Do not rerun either execution command. Raw archives/private reference flags remain ignored under data/. Old protocols, failed gates and reserved model outputs are preserved.
