# Known limitations

- Sections 6 and 7 and Phases 1A-1C are complete. The permitted 1,400-input offline collection is saved and validated. Phase 1D profiling/plots/decision and later research remain pending; timing and halting tests are not implemented.
- The validated environment is Linux x86_64 / WSL2 / Python 3.12.3 on this RTX 5060. Native Windows/host Python 3.14 inference is unvalidated.
- The full official baseline is 1,725/2,000 (86.25%); paper v1 reports 86.1%. The +0.15 percentage-point discrepancy has no established cause. Exact paper-number/prediction parity is not claimed.
- Existing baseline results retain official solved/cell/valid-grid metrics and have not been independently rescored. Phase 1A implements clue-consistent solution validation; Phase 1B adds full-resolution prefix decoding. All 140 implemented tests pass. Final-output parity with the unchanged official evaluator is established on the matched 32-input exploration smoke run, not all platforms/batch sizes.
- Smoke/full YAML configs now drive offline collection with strict partition/budget checks. The stopping-policy YAML remains a proposed template; baseline setup uses the official upstream config.
- Offline JSONL contains 12 levels for each of 1,000 exploration and 400 development puzzles, including per-level correctness/reference diagnostics. Aggregate trajectory analysis, cost profiling, and the decision report remain Phase 1D. All component timings are null. No online stopping hook, trained controller, visualization, or measured adaptive speedup exists.
- The selective dataset reader supports the exact pinned protocol-4 integer-list grammar. It reads/checksums raw file bytes and traverses their structure, while materializing only selected token rows. Unsupported serialization formats require explicit revalidation.
- Baseline process durations include loading/scoring and are not inference latency.
- The descriptive evaluator scored reserved holdouts internally; only aggregates were inspected. Future policy selection must follow the frozen phase-specific holdout rules and access disclosures.
- Checkpoints, datasets, caches, the environment, and raw prediction pickles are local/ignored. The dependency lock is platform-specific; another machine must recreate the environment and downloads.
- The authoritative design remains `Anytime_NCM_Design_Document.md`; `DESIGN.md` is a navigation entry point.
