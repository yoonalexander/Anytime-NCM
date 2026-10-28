# Final bounded mathematical review

Complete: full document weights tighten the old bound, but exact outside-margin counterexamples still block all-zero certification on the current confirmation population. No model-benefit evidence or Q2 release.

- [Results and exact scope](../../../docs/studies/quality-tolerant/final-math-review-results.md), [protocol/proof](../../../docs/studies/quality-tolerant/final-math-review-protocol.md).
- [Decision](decision.json), [exact certificates](exact-results.json), [anonymous weight histograms](weight-distributions.json).
- [27 invented tests](test-output.txt), [deterministic validation](deterministic-validation.json), [execution](execution.json), [budget ledger](ledger.jsonl), [source snapshot](execution-sources.zip).

Local hash/receipt verification, with no profile decode or calculation replay:

```powershell
.\scripts\wsl_python.ps1 -PythonArguments @('scripts/run_final_math_review.py','verify')
```

Do not rerun `run`. Existing raw/private inputs remain ignored; source/reference strings and per-input flags are not exposed. Preserve all original evidence and stop before Q2.

Independent fixed-certificate verification (no private profile decode, root optimization or grid replay):

```powershell
python results/quality_tolerant/final_math_review/verify_certificates.py
```
