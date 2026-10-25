# Evidence synthesis v4: local review candidate

[Eight-page manuscript](main.pdf) · [Editable LaTeX](main.tex) · [Claim-to-evidence map](CLAIM_EVIDENCE.md) · [Review questions and data access](REVIEW_PACKET.md) · [Remaining human decisions](OPEN_ITEMS.md) · [Primary sources](SOURCE_NOTES.md).

Prepared October 24, 2026 from completed records through the saved terminal-cost screen and M0 review. **Internal local draft; not submission-ready or independently reviewed.** The project label in the PDF is not a verified human author list. No one was contacted; no submission-platform upload or submission occurred. Human responsibility, rights/license and independent scientific review remain unresolved.

The main result is bounded:43/256 E2 inputs have an early exact-final-text prefix, but the prospectively timed every-level assignment costs 13.41% more than full. A separately locked, explicitly post hoc assembly of measured terminal requests saves 2.67%, exploratory interval[1.74%,3.73%], below 5% even with no earlier inspections. These are different estimands. Neither is a deployed selector, global optimum, universal impossibility result or safety guarantee. All fixed early depths fail an adjusted corpus-quality endpoint in E2. No controller/model/final-confirmation branch was executed.

Version3 and all original protocols/receipts/empirical artifacts are retained unchanged. `history/RESEARCH_SYNTHESIS-v3.md` preserves the prior root synthesis bytes. Two new standard scientific figures use only E2/screen aggregate JSON, with a retained `figures/reviewed-data.json` audit trail. They introduce no new outcome or reference reads. Current evidence baseline for manuscript preparation: `298f2e6`; execution versions remain their own locked commits.

## Files and build

**Current complete review archive:** [review-packet-with-access.zip](review-packet-with-access.zip). It adds the E0 role allocation and E2 access-release metadata omitted from the initial archive. [The append-only correction receipt](../../results/evidence_gaps/p1/access-bundle-correction.json) records the original/current hashes. The initial `review-packet.zip` and first P1 receipt remain preserved; the source ZIP's review notes describe that initial packaging snapshot. TeX, PDF, figures and empirical records are unchanged.

- `main.pdf`, `main.tex`: reviewed PDF and complete source with embedded bibliography.
- `figures/`: two static PDF figures, PNG previews and exact plotted aggregate values.
- `manuscript-source.zip`: TeX, figures and the local review documentation; no weights/data.
- `review-packet.zip`: self-contained PDF/source/review notes plus selected small frozen protocols/aggregate receipts and a checksum manifest. It deliberately excludes source/reference datasets, weights, raw trajectories/selected timing cells and final-output bodies.
- [Preparation/visual checks](../../results/evidence_gaps/p1/summary.md): exact artifact hashes, compiler logs and limits.

Inside this directory, the existing MiKTeX build is:

```powershell
pdflatex --disable-installer -no-shell-escape -interaction=nonstopmode -halt-on-error main.tex
pdflatex --disable-installer -no-shell-escape -interaction=nonstopmode -halt-on-error main.tex
```

Other installed TeX distributions may omit the MiKTeX-specific installer flag; do not enable network installs or shell escape to rebuild this packet. The app's built-in compiler also successfully compiled the final source. Poppler rendered all eight final pages, all visually inspected. No overfull/underfull boxes or undefined citations/references remain in the final retained log; the expected disabled-shell warning is unrelated to source correctness.

`scripts/build_evidence_review_figures.py` exports aggregate-only figures once and refuses existing outputs. Reproduction must use a separate destination/checkout and preserve this export. Study runners refuse consumed result paths; do not rerun a model phase merely to rebuild a manuscript. Exact working-tree archives matter because Git LF normalization may differ from executed CRLF source bytes.

## Verification and limits

The historical saved-cycle full suite recorded 451 passes; E2 recorded 96 focused tests, and the terminal screen32. These are different snapshots/selections, not additive counts or a new full-suite claim. Separate checks verify ledger/corpus/cue/timing arithmetic, not independent human science or general statistical coverage. Future reproduction needs the pinned assets and must respect the closed E3/E4 population; this source-only packet does not grant data/model/project redistribution rights.
