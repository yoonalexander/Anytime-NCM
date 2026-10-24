# E1 artifact guide

[Summary](summary.md) reports measured forced-path costs and their limits. The [prospective protocol](../../../docs/studies/evidence-gaps/e1-protocol.md), [schedule/lock](../../../docs/studies/evidence-gaps/e1-lock.json) and [87-test preparation receipt](../../../docs/studies/evidence-gaps/e1-lock-validation.json) predate all released-checkpoint requests.

- `started.json`, `preflight.json`, `execution-sources.zip`: source commit/digests, pinned asset verification and byte-exact executed files. The ZIP's internal manifest matches the started receipt; Git text normalization may differ from execution bytes.
- `block-*-starts.jsonl`: pre-request charges and expected identity/order, written before inference.
- `block-*-requests.jsonl`: measured warmup/timed wall and CUDA stream-span times, actual forwards, allocator peaks, output/observation hashes and parity checks. Warmups are retained but excluded from latency estimates.
- `block-*-started.json`, `block-*-execution.json`: distinct process IDs, environment, load/runtime/RSS, model-state fingerprints and exact process counters.
- `analysis.json`: frozen paired descriptive summaries, nominal intervals, shared-resample comparisons and engineering gate.
- `execution.json`: actual total allocation, source version, time/resources and original artifact digests. Subsequent reporting/check files are additional artifacts; the original receipt is not rewritten.
- `independent-checks.json`: separate same-assistant arithmetic/ledger/hash verification, including resample index digest. No independent researcher review is claimed.

No raw dataset/reference strings, reserved outcomes or weights are included. Cached Phase4 first 16 exploration records supply expected values for hash/parity verification. Reproduction requires a separately budgeted study in an isolated checkout; the runner refuses overwriting this consumed allocation. The pure verifier also preserves its existing receipt rather than silently replacing it.

E1 used its entire 1,000-request allocation. It did not release E2/E3/E4 data, assess translation quality, fit a controller or demonstrate quality-matched adaptive speedup.
