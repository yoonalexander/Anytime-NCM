# E0 retained artifacts

[Summary and decisions](summary.md) explain the completed input-only/synthetic study. [Protocol](../../../docs/studies/evidence-gaps/e0-protocol.md) and [lock](../../../docs/studies/evidence-gaps/e0-lock.json) were published before execution; the bounded [pre-execution recovery](../../../docs/studies/evidence-gaps/e0-recovery-amendment.md) changed Git metadata normalization only.

- `input-manifest.json`: exact sealed identity roles and the already exposed E1 pilot identities; no source/reference/output text.
- `exposure-audit.json`: header-only prior-access checks, exact-source grouping, result/cache path inventory, config/revision pins and limitations.
- `started.json`, `ledger.jsonl`, `execution.json`: consumed budgets, environment, executed digests and completion receipt. No model work occurred.
- `synthetic-trials.json`, `synthetic-bootstrap.json`, `statistical-feasibility.json`: fixed synthetic results, conservative cue coverage floors and Monte Carlo tail precision; no actual model-quality/latency observations.
- `focused-tests.xml`, `validation.json`: focused test receipt and separate same-assistant consistency checks; not independent human review.
- `execution-sources.zip`: byte-exact versions of all executed source/protocol files, with an internal SHA-256 manifest matching `execution.json`. Use these bytes to audit execution hashes: Git may normalize Windows CRLF to LF. This archive does not contain weights, raw source/reference datasets or outcome bodies.

The runner refuses overwriting these artifacts. Reproduction is a separately budgeted run in an isolated checkout with the pinned local dependencies/assets, not permission to rerun the consumed allocation here. Its main command is `scripts/run_evidence_e0.py --remote-head <verified-source-commit>` through the existing WSL wrapper. No CUDA/model execution is needed for E0. Existing source-data rows are inspected for duplicate hashing; all reference/new-outcome roles remain sealed.

The original candidate scope and budget are preserved in the parent plan. E0 found that the broad nonidentical-output E2 cue gate cannot pass at n=256 under its frozen conservative fallback. The next requestable work is a separately frozen E1 timing study; E2 amendments and policy work are conditional, not automatic.
