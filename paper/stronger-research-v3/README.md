# Stronger-research manuscript candidate v3

Internal local draft, October 24, 2026. **Not ready for submission.** Human authorship/affiliations, rights/license choice and independent scientific review remain unconfirmed. The source intentionally labels that status; the project label is not a verified human byline.

- main.pdf: compiled 9-page manuscript, visually checked after the final build.
- main.tex: editable source with embedded primary bibliography.
- figures/: three vector PDF figures, PNG previews and exact reviewed data.
- history/: unchanged pre-synthesis README and RESEARCH_PAPER v2 bytes.
- NOT_SUBMISSION_READY.md: remaining human decisions and current source-linked arXiv guidance.
- manuscript-source.zip: local source/figures bundle only; never uploaded.

The empirical snapshot is 39e4533. Exact historical and new execution sources are in study receipts. The research reports finite point-feasible mixed WMT exits, failed conditional quality noninferiority and unmeasured actual early-exit latency. The practical gate is inconclusive, not a demonstrated speedup. S3 was blocked and S2B/S4 deferred.

## Build locally

With existing pdfLaTeX (no shell escape, dependency auto-install disabled):

```powershell
pdflatex --disable-installer -interaction=nonstopmode -halt-on-error main.tex
pdflatex --disable-installer -interaction=nonstopmode -halt-on-error main.tex
```

Run inside this folder. Standard TeX distributions can omit the MiKTeX-specific --disable-installer option; no online package installation was used for the retained build. The Codex built-in LaTeX compiler also checked this project successfully. Figures are static PDFs and require no on-the-fly conversion.

From the repository root, the existing pinned WSL environment exports figures using scripts/render_stronger_research_figures.py. This reads only the saved new study summaries. Independent calculation and timing recheck commands are in results/stronger_research/s5a/summary.md; use new receipt paths. Do not rerun scripts/run_stronger_s1.py or model stages to refresh a manuscript: consumed allocations cannot be silently replayed. The new S1/S2 runners reject existing execution directories.

Large weights/datasets are excluded from Git; source/checkpoint/data revisions and local availability are recorded by S0 and historical receipts. No project-wide redistribution license is inferred. The local ZIP is preparation material, not permission to publish.

## Limits and review

All 451 software tests passed. Independent calculation means a separate implementation by the same assistant, not an external scientist or hardware replication. The source-ledger and bootstrap checks passed; no fresh evaluation data or actual early-exit benchmark was added. Quality/cost assumptions, selection uncertainty, unknown training overlap and unproven mechanisms are explicit in the manuscript.

Substantial AI assistance contributed to implementation, analysis, literature synthesis and writing. Human authors must review its accuracy, citations, disclosures, byline, affiliations and rights before accepting responsibility for submission.

## Exact execution bytes across platforms

Recorded hashes describe the executed working-tree bytes. Windows text writes can use CRLF while Git stores normalized LF; text identity alone is not byte identity. The separate `results/stronger_research/execution-sources.zip` preserves the exact S0 lock/allowlist and S1/S2/checker source bytes, with an internal SHA-256 manifest. For a clean cross-platform reproduction, use a separate checkout, restore that archive's relative paths there, obtain only the pinned local data assets, and write checks to new receipt paths. Do not rewrite frozen receipts or silently relax byte checks to hide line-ending drift. The LaTeX source ZIP similarly preserves the exact compiled source/figure bytes.
