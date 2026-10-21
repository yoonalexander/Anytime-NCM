# Known limitations

- Sections 6 and 7 and Phase 1 (1A-1D) are complete, with a no-go from zero early valid solutions in the frozen Sudoku setting. Both final holdouts remain reserved. Online stopping, controller training, and later studies are unimplemented.
- The validated environment is Linux x86_64 / WSL2 / Python 3.12.3 on this RTX 5060. Native Windows/host Python 3.14 inference is unvalidated.
- The full official baseline is 1,725/2,000 (86.25%); paper v1 reports 86.1%. The +0.15 percentage-point discrepancy has no established cause. Exact paper-number/prediction parity is not claimed.
- Existing baseline results retain official solved/cell/valid-grid metrics and have not been independently rescored. Phase 1A implements clue-consistent solution validation; Phase 1B adds full-resolution prefix decoding. All 186 implemented tests pass. Final-output parity with the unchanged official evaluator is established on the matched 32-input exploration smoke run, not all platforms/batch sizes.
- Smoke/full YAML configs now drive offline collection with strict partition/budget checks. The stopping-policy YAML remains a proposed template; baseline setup uses the official upstream config.
- Offline JSONL contains 12 levels for 1,000 exploration and 400 development puzzles. No valid output appeared before level 12. The Phase 1 report and scientific figures are complete. Diagnostic profiles cover the first 100 indices of each partition, five repeats each, after ten exploration warmups.
- Every-level verification added an estimated 44.18% development cost (95% interval 43.45%-45.02%). This is a component-sum diagnostic estimate, with instrumentation sensitivity disclosed; it is not measured online latency. Original trajectory timing fields remain null; measured costs are in separate profile artifacts.
- Profiling used batch size 1 versus collection batches up to 128. Intermediate tokens differed on five profiled identities; final tokens/validity matched. The gate uses its own matched batch-one outputs.
- No online stopping hook, trained controller, interactive viewer, or measured adaptive speedup exists. The no-go applies to this frozen checkpoint/reconstruction/sampling setting; other tasks and checkpoints remain untested.
- The selective dataset reader supports the exact pinned protocol-4 integer-list grammar. It reads/checksums raw file bytes and traverses their structure, while materializing only selected token rows. Unsupported serialization formats require explicit revalidation.
- Baseline process durations include loading/scoring and are not inference latency.
- The descriptive evaluator scored reserved holdouts internally; only aggregates were inspected. Future policy selection must follow the frozen phase-specific holdout rules and access disclosures.
- Checkpoints, datasets, caches, the environment, and raw prediction pickles are local/ignored. The dependency lock is platform-specific; another machine must recreate the environment and downloads.
- The authoritative design remains `Anytime_NCM_Design_Document.md`; `DESIGN.md` is a navigation entry point.
