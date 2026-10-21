# Section 7 setup results

Validated WSL2 Ubuntu / Python 3.12.3 / PyTorch 2.10.0+cu128 / RTX 5060.

| Official run | Solved | Solve rate | Cell accuracy | Valid-grid rate |
| --- | --- | --- | --- | --- |
| Smoke | 24/32 | 75.00% | 97.26% | 75.00% |
| Full hard Sudoku | 1725/2000 | 86.25% | 98.36% | 86.25% |

Both runs exited successfully without upstream source edits or a batch-size override. Environment, artifact checksums, source pins, protocol/partition hashes, and complete command lines are recorded in adjacent metadata and baseline run folders.

Paper v1 reports 86.1%; the observed difference is +0.15 percentage points, with no established cause. Exact paper parity and adaptive speedup are not claimed. See [the reproduction log](../../docs/reproduction_log.md) for details. Research beyond Section 7 has not started.
