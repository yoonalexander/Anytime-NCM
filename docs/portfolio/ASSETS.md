# Curated portfolio and review assets

| Asset | Use | Evidence boundary |
| --- | --- | --- |
| [Architecture SVG](../assets/architecture.svg) / [PNG](../assets/architecture.png) |README and website overview|Original illustration; not an execution screenshot|
| [Results SVG](../assets/results.svg) / [PNG](../assets/results.png) |Measured outcome graphic|Saved aggregate evidence; two processes/one repeat, quality points only|
| [Figure sources](../assets/sources.json) |Trace exact values/provenance|Pinned public source paths and SHA-256|
| [Historical WMT viewer screenshot](../../results/phase5/screenshots/wmt-desktop.png) |Evidence interface preview|Original Phase 5 screenshot, not the final controller run|
| [Historical Sudoku viewer screenshot](../../results/phase5/screenshots/sudoku-desktop.png) |Exact-constraint evidence preview|Original Phase 5 interface|
| [Historical E2 figure](../../paper/stronger-research-v4/figures/quality-latency.png) |Earlier negative diagnostic|Different population/method; not a temporal performance trend|
| [Historical v4 manuscript](../../paper/stronger-research-v4/main.pdf) |Background reading|Internal draft predating the later controller campaign; its rights/authorship/review limitations remain|
| [Latest campaign report](../studies/quality-tolerant/campaign-20261029-final-report.md) |Detailed final findings|Authoritative later campaign scope/limits|

Rebuild the new figures from frozen aggregates with `scripts/build_presentation_assets.py` in the existing plotting environment. Rendering is presentation work, not new inference, fitting or statistical simulation. Use a full-resolution image or the accompanying text/table on narrow layouts; preserve qualifications with any crop. No upstream promotional performance graphic is reused as this project's result.
