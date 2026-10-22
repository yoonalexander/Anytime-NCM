"""Source-backed static figure and diagnosis memo for the R1B pilot."""

import os
from pathlib import Path


def formatted(value, digits=3):
    return "undefined" if value is None else f"{value:.{digits}f}"


def render_report(repository, output, analysis):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    paths = analysis["paths"]
    fig, axes = plt.subplots(2, 2, figsize=(11, 7.5), layout="constrained")
    for name, color, style, label in (
        ("target_encoded", "#2563eb", "-", "Target encoded (reference supplied)"),
        ("generated_saved", "#c56a12", "--", "Generated (cached Phase 1)"),
    ):
        levels = paths[name]["levels"]
        x = list(range(1, 13))
        axes[0, 0].plot(x, [100 * r["valid_count"] / 32 for r in levels], marker="o", color=color, linestyle=style, label=label)
        for ax, metric in ((axes[0, 1], "wrong_given_cells"), (axes[1, 0], "wrong_empty_cells"), (axes[1, 1], "invalid_units_total")):
            ax.plot(x, [r["metrics"][metric]["mean"] for r in levels], marker="o", color=color, linestyle=style, label=label)
    axes[0, 0].set(title="Primary-valid solutions", ylabel="Selected puzzles (%)", ylim=(0, 100))
    axes[0, 1].set(title="Reference errors at supplied clues", ylabel="Mean wrong given cells", ylim=(0, 30))
    axes[1, 0].set(title="Reference errors at originally empty positions", ylabel="Mean wrong empty cells", ylim=(0, 51))
    axes[1, 1].set(title="Invalid rows, columns, and boxes", ylabel="Mean invalid units / 27", ylim=(0, 27))
    for ax in axes.flat:
        ax.set(xlabel="Hierarchy level", xticks=range(1, 13))
        ax.grid(alpha=.18)
    axes[0, 0].legend(fontsize=8)
    fig.suptitle("R1B: 32 preselected exploration puzzles; oracle target encoding vs cached generation")
    fig.savefig(output / "prefix_comparison.png", dpi=180)
    plt.close(fig)

    target, generated = paths["target_encoded"], paths["generated_saved"]
    roots = Path(os.path.relpath(repository, output)).as_posix()
    lines = [
        "# R1B: target-encoded versus generated Sudoku prefixes", "",
        "**Completed:** October 22, 2026 (America/Toronto). **Pilot:** exactly 32 preselected exploration identities, indices 0–31.", "",
        "## Findings", "",
        f"- Target-encoded early-valid inputs (any level 1–11): **{target['early_valid_inputs']}/32**. Cached generated early-valid inputs: **{generated['early_valid_inputs']}/32**.",
        f"- Final target primary-valid outputs: **{target['levels'][-1]['valid_count']}/32**; exact reference-token round trips: **{target['levels'][-1]['exact_reference_token_count']}/32**; parsed-board reference matches: **{target['levels'][-1]['reference_agreement_count']}/32**.",
        f"- Final cached generated primary-valid outputs: **{generated['levels'][-1]['valid_count']}/32**. These are existing outputs, not a new generation run.",
        f"- Outcome: **{analysis['outcome']}**. {analysis['next_action']}",
        "", "This is a reference-based diagnostic, not an implementable stopping policy. The target path is given the solution; the generator path is not. No online latency, speedup, tokenizer training, or new Phase 2 go is established. The original hard-Sudoku no-go remains unchanged.",
        "", "## Execution and checks", "",
        "Exactly 32 normal upstream VQVAE.encode calls and 384 decoder forwards were used, at batch size 1, float32/eval, on the validated RTX 5060/WSL environment. In addition, 32 predeclared latent-only upstream final-reconstruction parity checks added no decoder evaluations. No warmups, generator construction/checkpoint model load, generator calls, or timing study occurred. Generator file bytes may be checksummed as part of inherited artifact integrity checks; no generator is instantiated.",
        "", "The encoder includes upstream pre-quantization normalization. Deterministic nearest-code encoding is required. Cumulative prefixes retain full [1, 89, 256] resolution and independent storage. Every final latent matched upstream bitwise, and tokenizer state fingerprints matched before/after the run. Synthetic encoding, normalization, full-resolution, storage, and suffix-isolation tests precede the pilot.",
        "", "These stored check declarations are traced to the source and recorded run. The model-free verifier recomputes output labels and statistics and checks integrity/budget; it does not rerun latent reconstruction or prove CUDA parity afresh.",
        "", "## Per-level primary validity and secondary scores", "",
        "| Level | Target valid / 32 | Generated valid / 32 | Target reference-board matches | Target official cell accuracy | Generated official cell accuracy |",
        "| ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for t, g in zip(target["levels"], generated["levels"]):
        ta, ga = t["official_cell_accuracy_mean"], g["official_cell_accuracy_mean"]
        lines.append(f"| {t['level']} | {t['valid_count']} | {g['valid_count']} | {t['reference_agreement_count']} | {formatted(None if ta is None else 100*ta, 2)}% | {formatted(None if ga is None else 100*ga, 2)}% |")
    lines += ["", "Official cell accuracy averages per-example zipped decoded-character scores and can overstate incomplete text. Undefined scores propagate to an undefined aggregate; explicit coverage is retained in analysis.json. Primary acceptance uses parseability, completeness, valid rows/columns/boxes, and supplied clues; reference equality is separate.",
              "", "![Prefix comparison](prefix_comparison.png)", "",
              "The target path uses batch 1; the cached generator outputs came from the original collection in batches up to 128. This asymmetric, oracle-input comparison helps localize hypotheses but cannot by itself isolate a causal bottleneck.",
              "", "## Reference/clue/constraint errors", "",
              "| Path | Level | Parseable / 32 | Mean wrong reference cells | Mean wrong given | Mean wrong empty | Mean blanks | Boards violating clues |",
              "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for name in ("target_encoded", "generated_saved"):
        for row in paths[name]["levels"]:
            m = row["metrics"]
            lines.append(f"| {name} | {row['level']} | {row['parseable_count']} | {formatted(m['wrong_reference_cells']['mean'])} | {formatted(m['wrong_given_cells']['mean'])} | {formatted(m['wrong_empty_cells']['mean'])} | {formatted(m['blank_cells']['mean'])} | {m['clue_violations']['positive_count']} |")
    lines += ["", "All per-level histograms, quantiles, row/column/box metrics, undefined coverage, paired differences, and given/empty position opportunities are in analysis.json and the 768-row board CSV. Wrong reference cells include blanks; duplicate counts ignore zero; invalid units include missing digits/blanks. These categories overlap. Rates must use each path/level's recorded parseable position denominator.",
              "", "## First-valid histogram", "",
              "| First valid level | Target encoded | Cached generated |", "| --- | ---: | ---: |"]
    for key in [str(k) for k in range(1, 13)] + ["never"]:
        lines.append(f"| {key} | {target['first_valid_counts'][key]} | {generated['first_valid_counts'][key]} |")
    lines += ["", "## All final round-trip failures", "",
              f"- Target primary-invalid dataset indices: **{target['final_primary_failure_indices']}**.",
              f"- Target parsed-board reference-mismatch indices: **{target['final_board_reference_mismatch_indices']}**.",
              f"- Target decoded-token mismatch indices: **{target['final_token_mismatch_indices']}**.",
              "", "An empty list means no observed failures in that category. Failed round trips are retained as outcomes; they are not silently removed or treated as proof of an adapter bug.",
              "", "## Late adjacent-level changes", "",
              "| Path | Boundary | Mean changed | Mean corrected | Mean corrupted | Mean wrong-to-different-wrong |",
              "| --- | --- | ---: | ---: | ---: | ---: |"]
    for name in ("target_encoded", "generated_saved"):
        for row in paths[name]["boundaries"][9:11]:
            m = row["metrics"]
            lines.append(f"| {name} | {row['from_level']}→{row['to_level']} | {formatted(m['changed_cells']['mean'])} | {formatted(m['corrected_cells']['mean'])} | {formatted(m['corrupted_cells']['mean'])} | {formatted(m['wrong_to_different_wrong_cells']['mean'])} |")
    lines += ["", "These future/reference-based labels are diagnostic only. Changed = corrected + corrupted + wrong-to-different-wrong; wrong-after = wrong-before − corrected + corrupted. The transition CSV retains all 352 boundaries per path (704 rows total), including undefined coverage for unparseable endpoints.",
              "", "## Representative examples", "",
              "Choose the lowest selected dataset index independently per predeclared category; categories may overlap. All final failures remain listed above regardless of representative selection.",
              "", "| Category | Dataset index |", "| --- | ---: |"]
    for name, case in analysis["representative_cases"].items():
        lines.append(f"| {name} | {case['dataset_index'] if case else 'none observed'} |")
    seen = set()
    for case in analysis["representative_cases"].values():
        if case is None or case["dataset_index"] in seen:
            continue
        seen.add(case["dataset_index"])
        lines += ["", f"### Exploration dataset index {case['dataset_index']}", "",
                  "Reference:", "", "~~~text"]
        lines += ["".join(map(str, case["reference"][i:i+9])) for i in range(0, 81, 9)]
        lines += ["~~~", ""]
        for name in ("target_levels", "generated_levels"):
            for k in (10, 11, 12):
                lines += [f"{name}, level {k}:", "", "~~~text", case[name][k-1], "~~~", ""]
    lines += ["", "## Interpretation and limits", "",
              "Early target validity would show that the target-encoding path can reach a useful decoded prefix for those inputs, not that a generated-code fix is sufficient. If target and generated paths both lack early valid outputs while target final round trips succeed, the tested target prefixes also fail exact validity. That supports examining tokenizer/decoder behavior as a hypothesis, not a proof that no alternative codes or decoder can work.",
              "", "The sample is deliberately fixed at 32 exploration identities. It is neither a development gate nor final evaluation and supplies no population-wide absence guarantee. No solution reference or retrospective label can be supplied to an online stopping controller.",
              "", "## Reproduce and verify", "",
              "[Analysis](analysis.json), [raw target records](targets.jsonl), [board CSV](board_metrics.csv), [transition CSV](transition_metrics.csv), [attempt and actual forward counts](attempt.json), [provenance](provenance.json).",
              "", f"[Frozen R1B protocol]({roots}/{str('docs/studies/sudoku-target-encoding-protocol.md')}), [implementation]({roots}/src/anytime_ncm/target_diagnostic.py), [GPU encoding contract]({roots}/src/anytime_ncm/target_encoding.py).",
              "", "From the prepared repository, without inference:", "", "~~~powershell",
              f"python scripts/diagnose_target_encoding.py --output {output.relative_to(repository).as_posix()} --verify",
              "~~~", "",
              "The original pilot budget is consumed. Do not rerun encoding merely to regenerate a report. Verification selectively loads only the 32 allowed puzzle/reference rows and cached records. Repeating released-checkpoint execution needs a separately declared allocation and fresh output directory. Report-only formatting changes can reuse saved raw targets without any model calls.",
              "", "## Next action", "", analysis["next_action"],
              "", "End R1B here. No R2 screen, checkpoint intervention, online stopping, controller training, or holdout evaluation was started."]
    (output / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
