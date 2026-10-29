# Delivery verification inventory

Research conclusions and engineering checks are different. This closeout adds no real checkpoint inference, corpus collection, controller fitting, target encoding, confirmation access or research-ledger reset.

## Software

The unchanged baseline suite passed **759 main tests + 61 isolated Q0 tests = 820**. The first broad run's three setup failures are retained: a blocked tokenizer metadata read and two assertions requiring a no-model process. The guarded runner fixes the environment/grouping without changing old tests or research algorithms. Four pinned text-tokenizer metadata reads were allowed; raw corpora/neural weights, GPU, external networking and research-evidence writes were blocked. [Baseline summary](../../results/delivery/20261029/baseline-summary.json).

The final integrated suite passed **770 main + 61 Q0 = 831 checks**; [final main](../../results/delivery/20261029/final-main.json) and [final Q0](../../results/delivery/20261029/final-q0.json) retain the exact guarded runs.

New CLI regressions cover exact aggregate provenance/negative boundaries, version/help/plain/JSON output, explicit repository resolution and dispatch, fresh-process dependency isolation and independent resource loading. Their initial source-subprocess setup failure and corrected result are retained. Clean installation acceptance tests both wheel and sdist from outside the checkout, builds the wheel from the sdist, verifies archive contents/notices, both entry points, examples, missing-checkout errors, zero runtime dependencies and `pip check`.

```powershell
.\scripts\wsl_python.ps1 -PythonArguments @('scripts/run_delivery_tests.py','final-main','--group','main')
.\scripts\wsl_python.ps1 -PythonArguments @('scripts/run_delivery_tests.py','final-q0','--group','q0')
```

Each label is a new ignored test workspace; existing outputs are not overwritten. Final integrated results and clean-install records are under [results/delivery/20261029](../../results/delivery/20261029). Portable CI tests installation only on Windows/Linux, not research models. A green packaging check is not a scientific success claim.

## Research artifacts and history

[Artifact/source compatibility](ARTIFACT_AUDIT.md) explains strict historical verifiers versus the current source-aware audit. Baseline saved verifiers passed before intentional metadata refreshes. Exact old bytes and all original scientific locks/charges/failures remain retained. Current audit results enumerate current hashes, explicit archival resolutions and optional private digest checks.

## Visuals and release

New results and architecture graphics are reproducibly rendered by `scripts/build_presentation_assets.py` from the public aggregate snapshot and pinned source hashes. The architecture is labeled illustration. The results figure includes units, population, point-tolerance limits and conditional timing uncertainty. Existing viewer screenshots/manuscripts are labeled historical. Visual inspection and browser/installation/release-download checks are recorded in the delivery completion receipt.

The published release checksum record must verify each asset downloaded from its public URL against the local verified bytes and `SHA256SUMS`. The Git release tag targets the verified integrated code; later main commits may add verification receipts. No package registry or paid service is used.

## Limits that remain

- BLEU point tolerance fails; independent quality assurance and a complete potentially feasible fixed-depth frontier are absent.
- The original full timing matrix and its missing terminal receipts are not silently repaired by a smaller diagnostic.
- Private corpora/checkpoints are not redistributed; full model experimentation cannot be reproduced from a wheel alone.
- Original manuscript independent review, rights/authorship and journal submission remain unperformed. No project-wide license has been invented.
