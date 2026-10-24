# E2 evidence bundle

[Outcome and limitations](summary.md) · [Protocol](../../../docs/studies/evidence-gaps/e2-protocol.md) · [Execution](execution.json) · [All comparisons](analysis.json) · [Separate checks](independent-checks.json).

Completed once under source lock `d88b7c495df37635b3497661e3e9b56169c1576f`: 256 new audit trajectories, two fresh paired timing processes, 12,664 requests in total. Result: bounded no-go for the exact-final-text assignment with every-level observation; no controller/final release.

The three `*-starts.jsonl` files are pre-call ledgers; `*-requests.jsonl` are observed work/parity/timing records. `collection-execution.json`, `0-execution.json`, `1-execution.json` record environments and immutable model fingerprints. `execution-sources.zip` contains the exact source bytes and hashes. `trajectories.jsonl` and `timing-schedule.json` retain the audit outputs and deterministically derived forced assignments. No checkpoint, raw source/reference pickle or tokenizer weights are redistributed here; pinned assets remain required locally, with rights/access unresolved as documented by the repository.

`access-release.json` applies only to E2's 256 groups; copied E0 entry flags retain their historical meaning. The parent E0 manifest remains unchanged. E3/E4 and unallocated groups stay closed. `reference-access.json` records the 256 execution materializations; the separate verification receipt records the second permitted read of those same references.

The runner refuses an existing result directory and the checker preserves its first receipt. Do not rerun model stages or overwrite receipts. Later reproducibility work must preserve this bundle and declare any new model-work allocation prospectively. The 96-test pre-inference JUnit is linked from the protocol directory; historical full-suite JUnit records were not replaced.
