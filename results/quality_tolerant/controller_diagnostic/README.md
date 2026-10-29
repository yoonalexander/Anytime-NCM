# Bounded controller failure diagnosis

Complete: the nine original calibration policies reproduced; the prospective route is richer_causal_signal_study. No new fits, models, GPU work or former87-input evaluation outcome reads.

- [Results](../../../docs/studies/quality-tolerant/controller-diagnostic-results.md)
- [Prospective protocol](../../../docs/studies/quality-tolerant/controller-diagnostic-protocol.md), [numeric lock](../../../docs/studies/quality-tolerant/controller-diagnostic-lock.json), [source lock](../../../docs/studies/quality-tolerant/controller-diagnostic-source-lock.json).
- [Next-unit proposal, planning only](../../../docs/studies/quality-tolerant/causal-signal-pilot-proposal.md).
- run/: exact execution sources,13synthetic tests, fit/calibration access release, work ledger, prediction/feature/domain diagnostics,18frozen original/oracle/omission assignments,72cost-grid points, aggregation gaps, prior timing audit, decision and immutable execution receipt.
- completion-review.json and completion-manifest.json: scripted checks and final report/artifact hashes; not independent replication.

Verify saved hashes/receipts without new fits, analysis replay or outcome reads:

```powershell
.\scripts\wsl_python.ps1 -PythonArguments @('scripts/run_controller_diagnostic.py','verify')
```

Do not rerun run: this once-only subphase and its access budget are complete. All original margins and failed gates remain intact. No Q4/reserved-output release follows.
