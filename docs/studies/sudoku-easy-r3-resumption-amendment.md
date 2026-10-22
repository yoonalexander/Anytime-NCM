# R3 resumption amendment 1: metadata I/O interruption

**Declared:** October 22, 2026 (America/Toronto), after the first collection process failed and before any resumed model call.
**Authorization:** Existing user work order "Do R3"; this amendment completes that scope without increasing its model-evaluation budget.
**Original protocol:** [R3 easy protocol](sudoku-easy-r3-protocol.md), unchanged.

The first collection process completed **499 trajectories**, including the 32 reused R2 outputs and **467 new generations**. All 467 independent/final-latent prefix checks were saved. Observed generator-level and decoder counters both equal **5,604 = 467 x 12**; encoder forwards remain zero.

The process then reserved input slot 468, but writing collection.json raised OSError(22, Invalid argument) **before** context preparation or the next generate call. There is exactly one pending, already reserved input slot and no partial model evaluation at that slot. The error handler successfully recorded a failed stage. Preserve that JSON as collection.failed_attempt_1.json, along with byte lengths/hashes of the saved trajectory/check prefixes and the initial 301-test report.

## Allowed continuation

- Retain all 499 completed rows and 467 checks byte-for-byte; validate their identities/order before appending.
- Reload the exact frozen checkpoint and require its starting fingerprint to match the original starting fingerprint. The interrupted process did not record an end fingerprint; do not claim to have measured one.
- Resume the next unrun identity using the **already reserved** slot 468, without reserving a duplicate slot. Then reserve normally before subsequent inputs. No completed generation, failed model generation, or statistical sample is rerun/replaced.
- Complete exactly 901 unrun trajectory identities, yielding 1,368 total new collection generations and the same original R3 total **4,378 new generations / 31,536 decoder forwards**. No budget increase, seed change, candidate change, new warmup, or new inference family.
- Use a separate versioned resumption runner. Original R3 source/protocol files and their baseline/partial-stage source hashes remain unchanged. Record the new runner, amendment and focused-test hashes as an additional execution provenance group on resumed collection, subsequent profiling, and reporting.
- Replace only stage-metadata persistence with bounded atomic tempfile-write/replace retries. These are filesystem operations, add no model calls and occur outside timed request regions. Model code, sampling, reconstruction, policies, measurements, bootstrap and gates remain unchanged.
- Run the original profiling function once under this metadata writer, within its untouched 1,010-generation / 13,120-decode allocation.
- Record a second collection execution segment, the original failure and prefix checks in completion/report evidence. Verify both original-source hashes and additional execution-source hashes; verify saved file prefixes against their pre-resumption receipts.
- A second failure involving uncommitted model work requires a further pre-execution amendment. Do not silently retry model evaluation.

This is an infrastructure interruption, not an observed Sudoku model-quality failure. Invalid model outputs already collected remain results. R2's negative result and the original hard-Sudoku no-go remain unchanged.
