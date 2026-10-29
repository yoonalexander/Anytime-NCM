# Actual sparse assigned-exit latency diagnostic

Completed October28,2026 on256 consumed E2 inputs under the prospectively pushed `9f1841a` lock. This is an exploratory entry exception; Q0 remains failed and no controller/confirmation release follows.

- [Results and limitations](../../../docs/studies/quality-tolerant/latency-diagnostic-results.md)
- [Prospective protocol](../../../docs/studies/quality-tolerant/latency-diagnostic-protocol.md)
- `started.json`, `execution-sources.zip`: pushed source commit and exact execution snapshot.
- `synthetic-tests.log`, `synthetic-tests.xml`: 19 CPU-only validation tests before released checkpoint loading.
- `asset-preflight.json`, `access-release.json`: pinned local assets, consumed identity release, zero reference/new-input access.
- `timing-schedule.json`, `parity-hashes.json`, `document-components.json`: frozen paired order, old-output hashes and source-only cluster linkage.
- `0/1-starts.jsonl`, `0/1-requests.jsonl`, `0/1-execution.json`: all warmups/timed requests, charged forwards, parity and unchanged-state receipts.
- `saved-quality-summary.json`: reused Q1 point scores; no fresh quality inference.
- `analysis.json`, `decision.json`, `execution.json`: one20,000draw paired analysis, bounded decision, actual resource/artifact receipt.
- `completion-review.json`, `completion-manifest.json`: additional scripted request/hash checks and final report/artifact digests.

Verify saved receipts without new model calls or bootstrap:

```powershell
.\scripts\wsl_python.ps1 -PythonArguments @('scripts/run_latency_diagnostic.py','verify')
```

Do not rerun `run`: the directory is once-only, and the consumed inference budget is complete. No paid compute, fitting, target encoding or E3/E4 model-output access occurred.
