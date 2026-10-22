"""Static scientific figure and Markdown report from verified R2 screen outputs."""
import json
from pathlib import Path

from anytime_ncm.dataset import sha256
from anytime_ncm.screening import OUTPUT, PROTOCOL, save, verify_screen


def render(root):
    root = Path(root)
    analyses = verify_screen(root)
    out = root / OUTPUT
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8), layout="constrained")
    colors = ("#0072B2", "#D55E00")
    for analysis, color in zip(analyses, colors):
        name = analysis["candidate"].capitalize()
        axes[0].plot(range(1, 13), [x["valid_count"] for x in analysis["levels"]],
                     marker="o", label=name, color=color)
        values = [x["metrics"]["wrong_reference_cells"]["mean"] for x in analysis["levels"]]
        axes[1].plot(range(1, 13), values, marker="o", label=name, color=color)
    axes[0].set(ylabel="Primary-valid boards (of 32)", ylim=(-.7, 33))
    axes[1].set(ylabel="Mean wrong reference cells", ylim=(-1, 82))
    for ax in axes:
        ax.set(xlabel="Hierarchy level", xticks=range(1, 13))
        ax.grid(axis="y", alpha=.2)
        ax.spines[["top", "right"]].set_visible(False)
        ax.legend(frameon=False)
    fig.suptitle("R2: fixed 32-input exploration screens; no timing study", fontsize=12)
    fig.savefig(out / "screen_comparison.png", dpi=160)
    plt.close(fig)
    text = ["# R2: bounded easy/medium Sudoku checkpoint screen", "",
        "**Completed:** October 22, 2026 (America/Toronto). Candidate order: easy, then medium only after a negative easy screen.", "",
        "## Decision", ""]
    selected = next((a["candidate"] for a in analyses if a["qualifies_for_R3"]), None)
    if selected:
        text += [f"**{selected.capitalize()} qualifies for a separately requested R3 opportunity/cost audit.** "
                 "The screen found an independently verified primary-valid output before level 12. "
                 "This alone establishes neither worthwhile savings nor a new Phase 2 go.", ""]
    else:
        text += ["**Both screens are negative at the declared budget. Close the released-Sudoku first-valid path at this budget.** "
                 "Do not expand the sample, add seeds, train a controller, or proceed to Phase 2 under this result. "
                 "Zero early solutions in 32 inputs per candidate is not a population impossibility claim.", ""]
    text += ["The R1A/R1B diagnoses warranted testing a changed difficulty/checkpoint. No unresolved correctness failure "
             "required changing the original hard-Sudoku study. Its no-go remains unchanged.", "",
        "| Candidate | Inputs | Early valid inputs | Final primary-valid | Final token/text parity | Screen decision |",
        "| --- | ---: | ---: | ---: | ---: | --- |"]
    for a in analyses:
        text.append(f'| {a["candidate"]} | 32 | {len(a["early_valid_indices"])} | {a["final_valid_count"]}/32 | 32/32 | {a["decision"]} |')
    text += ["", "![Screen comparison](screen_comparison.png)", "", "## Per-level results", "",
        "| Candidate | Level | Primary-valid / 32 | Reference matches / 32 | Official solved / 32 | Official valid grid / 32 | Official cell accuracy | Mean wrong cells | Mean wrong given | Mean wrong empty | Parseable / 32 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for a in analyses:
        for level in a["levels"]:
            m = level["metrics"]
            def mean(key):
                value = m[key]["mean"]
                return "undefined" if value is None else f"{value:.3f}"
            cell = m["official_cell_accuracy"]
            accuracy = "undefined" if cell["undefined_count"] else f'{100 * cell["mean"]:.2f}%'
            text.append(f'| {a["candidate"]} | {level["level"]} | {level["valid_count"]} | {level["reference_match_count"]} | '
                f'{m["official_solved"]["sum"]} | {m["official_valid_grid"]["sum"]} | {accuracy} | '
                f'{mean("wrong_reference_cells")} | {mean("wrong_given_cells")} | {mean("wrong_empty_cells")} | {m["parseable"]["sum"]} |')
    text += ["", "Primary acceptance requires parseability, completeness, valid rows/columns/boxes, and clue preservation. "
             "Reference agreement is a diagnostic, not an acceptance condition. Official solved/valid-grid scores retain "
             "upstream definitions, which do not independently enforce clues. Official cell accuracy uses zipped decoded "
             "characters and can overstate truncated outputs. Undefined coverage is retained; error means use parseable outputs.", "",
             "## First-valid levels and every early/never-valid identity", "",
             "| First valid level | " + " | ".join(a["candidate"] for a in analyses) + " |",
             "| --- | " + " | ".join("---:" for _ in analyses) + " |"]
    for key in [*(str(i) for i in range(1, 13)), "never"]:
        text.append("| " + key + " | " + " | ".join(str(a["first_valid_histogram"][key]) for a in analyses) + " |")
    for a in analyses:
        text += ["", f'**{a["candidate"]}:** early-valid indices {a["early_valid_indices"]}; never-valid indices {a["never_valid_indices"]}.']
    text += ["", "## Execution and correctness", ""]
    for a in analyses:
        c = a["candidate"]
        attempt = json.loads((out / c / "attempt.json").read_text())
        text += [f'- **{c}:** 32 official comparator generations plus 32 adapter generations (64 full-depth input-evaluations); '
                 f'768 generator level evaluations, 416 decoder forwards, zero encoder forwards. '
                 f'32 declared upstream latent-parity and 32 independent full-prefix checks. '
                 f'Peak CUDA allocated memory {attempt["peak_cuda_allocated_bytes"] / 1024**2:.1f} MiB (fit check only).']
    text += ["", "Both paths use batch 1, float32/eval, deterministic released sampling, the same loaded checkpoint, "
             "and four CPU threads on the validated RTX 5060/WSL pathway. The comparator executes the unchanged pinned "
             "eval_shard prefix/pick_tokens/dec/run function bodies; CLI data loading is replaced by selective access "
             "to the fixed 32 identities. This is a matched comparator, not a new full-set official reproduction. "
             "No warmups, retries, additional seeds, timing profile, training, or target encoding occurred.", "",
             "All paired final token IDs/text match exactly. Each full-resolution prefix matched independent functional "
             "embedding/convolution/interpolation arithmetic; final latents matched upstream; snapshots have independent "
             "storage and are finite. Generator/tokenizer state fingerprints match before and after. Synthetic tests "
             "preceded released-checkpoint execution. Invalid outputs remain in the raw records.", "",
             "## Partitions, overlap, and limits", "",
             "The easy, medium, and hard solution files are byte-identical at the pinned release. R2 inherits all 2,000 "
             "row-index partitions from the original manifest, protecting shared solutions across different clue masks. "
             "Candidate puzzle identities are incrementally hashed for all 2,000 rows, including reserved operands, "
             "without retaining those token rows/boards. Cross-partition input collisions are rejected. This identity-only "
             "traversal is disclosed separately from board/reference materialization.", "",
             "Each executed candidate materializes only puzzle/reference rows 0–31, all inherited exploration. No "
             "development/final-holdout boards, reference rows, or outputs are materialized. These are related difficulty "
             "views with previously exposed exploration solutions, not independent datasets. The original full baseline "
             "previously scored reserved hard rows internally with aggregate-only access. Unknown base-model training "
             "overlap and the original unexplained +0.15-percentage-point paper reproduction discrepancy remain unresolved.", "",
             "The small, fixed screen detects opportunity only. It does not identify a universal tokenizer cause, "
             "bound population absence, measure monitoring costs, or claim online speedup. No R3, online stopping, "
             "controller training, or natural-language study has started.", "",
             "## Evidence and verification", "",
             "[Frozen protocol](../../../" + PROTOCOL + "), [release inventory](../../../configs/r2_sources.json).", ""]
    for a in analyses:
        c = a["candidate"]
        text += [f'- **{c}:** [manifest](../../../docs/partitions/sudoku-{c}-r2.json), '
                 f'[preflight]({c}/preflight.json), [attempt]({c}/attempt.json), '
                 f'[raw paired records]({c}/records.jsonl), [raw comparators]({c}/comparators.jsonl), '
                 f'[analysis]({c}/analysis.json), [board CSV]({c}/board_metrics.csv), [provenance]({c}/provenance.json).']
    text += ["", "~~~powershell", "python scripts/screen_sudoku_checkpoints.py --verify", "~~~", "",
             "Verification recomputes selection, labels, analysis, tables, candidate order, hashes and stored budgets/check "
             "declarations without torch/matplotlib imports or model calls. It does not rerun GPU latent parity. "
             "The execution budget is consumed; use saved records for report work. [Completion evidence](completion.json).", ""]
    (out / "summary.md").write_text("\n".join(text), encoding="utf-8", newline="\n")
    save(out / "report_provenance.json", {"study": "R2", "artifacts_sha256": {
        name: sha256(out / name) for name in ("summary.md", "screen_comparison.png")},
        "candidate_provenance_sha256": {a["candidate"]: sha256(out / a["candidate"] / "provenance.json") for a in analyses}})
    return analyses
