# Q1 bounded exploratory exception

Complete: two sparse E2 oracle assignments show point-quality projected headroom; Q0 remains statistically blocked. No Q2, reserved-output release or online speedup claim.

- [Prospective protocol](../../../docs/studies/quality-tolerant/q1-exploratory-protocol.md) and [results/limits](../../../docs/studies/quality-tolerant/q1-exploratory-results.md).
- [Decision](decision.json), [all assignments and baselines](results.json), [cost calibration](cost-calibration.json).
- [Started/live-remote receipt](started.json), [access receipt](access-receipt.json), [execution](execution.json).
- [42 synthetic tests](focused-tests.xml), [test output](test-output.txt), [budget ledger](ledger.jsonl).
- [Source snapshot](execution-sources.zip), [independent arithmetic and ledger verification](report-verification.json).

Verification (hashes/receipts only, no outcome reread or search replay):

```powershell
.\scripts\wsl_python.ps1 -PythonArguments @('scripts/run_q1_exploratory.py','verify')
```

One execution only. Re-running `run` refuses the existing started receipt. Preserve original artifacts and failed gates.
