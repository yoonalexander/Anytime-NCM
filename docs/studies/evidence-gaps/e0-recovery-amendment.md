# E0 pre-execution recovery amendment

October 24, 2026, before any E0 source-string read, study trial or bootstrap draw. Original frozen protocol/source commit: `08a85cd709359f1e104471181374de92a9e2d18d`.

The initial CLI invocation exited at the clean-checkout guard, before creating `results/evidence_gaps/e0/` or importing/reading any model/outcome data. Windows Git saw clean main; WSL Git reported the submodule dirty because its Git configuration did not inherit Windows' global `core.autocrlf=true`. Submodule tracked files have LF index bytes and CRLF working bytes. WSL `diff --ignore-space-at-eol --exit-code` found no content differences, both Git installations resolve the pinned upstream commit, and the command-local CRLF normalization produces a clean status. These checks diagnosed the issue; ignoring whitespace is not the execution guard.

Recovery changes only the runner's Git metadata commands: set `core.autocrlf=true` and both known safe-directory paths for that invocation. Keep full Git status checking active. No global config, upstream file, sampling/statistical code, frozen protocol/lock, scientific gate or resource ceiling changes. Record this amendment in execution source digests.

The failed preparation invocation consumed zero input-audit rows, zero scenarios/trials/datasets/draws, zero model work and zero new outcomes/references. Preserve its [failure receipt](../../../results/evidence_gaps/e0-preexecution-failure-1.json). Preparation/failure time remains within the original one-hour setup allocation; no time or trial/draw allowance is refunded or expanded.

After committing/pushing this correction and verifying remote equality, permit one continuation into the original still-unstarted audit/simulation. The existing output-directory overwrite refusal remains active. A later scientific/collection failure still requires its own prospective recovery decision; this amendment is not general retry permission.
