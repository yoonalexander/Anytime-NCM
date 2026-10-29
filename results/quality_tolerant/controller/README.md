# Bounded consumed-data causal controller experiment

Complete: calibration selected native-full fallback; evaluation has0/87early exits. Decision controller_no_early_exits. Q0 remains failed; no Q4 or reserved-output release.

- [Results and limits](../../../docs/studies/quality-tolerant/controller-results.md)
- [Prospective protocol](../../../docs/studies/quality-tolerant/controller-protocol.md), [split](../../../docs/studies/quality-tolerant/controller-split.json), [numeric lock](../../../docs/studies/quality-tolerant/controller-lock.json), [source lock](../../../docs/studies/quality-tolerant/controller-source-lock.json).
- development/: source snapshot,13synthetic tests, fit/calibration access release and coverage, work ledger, eight fitted proxy models, all9candidate scores, locked policy and immutable execution receipt.
- evaluation/: post-policy access release, coverage, saved-output parity hashes, causal replay checks, timing schedule, all4,296request/start ledgers, two process receipts, one paired analysis, decision and execution hashes.
- completion-review.json: scripted request/hash/data-separation/budget audit; no independent replication or new model work.
- completion-manifest.json: final report and result digests without rewriting either execution receipt.

Verify saved evidence with no new fitting, inference or bootstrap:

```powershell
.\scripts\wsl_python.ps1 -PythonArguments @('scripts/run_quality_controller.py','verify')
```

Do not rerun develop/evaluate: both once-only stages and their consumed access are complete. Synthetic malformed-JSON fixture bytes are retained under development/pytest-tmp/; only WSL's current-directory alias is ignored. No real corpus/reference text or model checkpoints are bundled here.
