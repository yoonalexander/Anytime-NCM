# Known limitations

- Sections 6 and 7 and Phases 1A-1B are complete. The Phase 1C collector and later research modules remain placeholders; timing and halting tests are not implemented.
- The validated environment is Linux x86_64 / WSL2 / Python 3.12.3 on this RTX 5060. Native Windows/host Python 3.14 inference is unvalidated.
- The full official baseline is 1,725/2,000 (86.25%); paper v1 reports 86.1%. The +0.15 percentage-point discrepancy has no established cause. Exact paper-number/prediction parity is not claimed.
- Existing baseline results retain official solved/cell/valid-grid metrics and have not been independently rescored. Phase 1A implements clue-consistent solution validation; Phase 1B adds full-resolution prefix decoding. All 88 implemented tests pass. Final-output parity with the unchanged official evaluator is established on the matched 32-input exploration smoke run, not all platforms/batch sizes.
- Research YAML configurations are proposed templates; setup uses the official config directly.
- Prefix decoding has been checked for shape, storage, isolation, and final parity; no intermediate quality analysis or stored trajectory dataset exists. No online stopping hook, trained controller, visualization, or measured adaptive speedup exists.
- Baseline process durations include loading/scoring and are not inference latency.
- The descriptive evaluator scored reserved holdouts internally; only aggregates were inspected. Future policy selection must follow the frozen phase-specific holdout rules and access disclosures.
- Checkpoints, datasets, caches, the environment, and raw prediction pickles are local/ignored. The dependency lock is platform-specific; another machine must recreate the environment and downloads.
- The authoritative design remains `Anytime_NCM_Design_Document.md`; `DESIGN.md` is a navigation entry point.
