"""Static scientific figures and Markdown for the saved exploration diagnosis."""

import os
from pathlib import Path


def render_figures(output, analysis):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 10, "figure.dpi": 140, "savefig.dpi": 180,
                         "axes.spines.top": False, "axes.spines.right": False})
    groups = analysis["groups"]
    all_levels = groups["all"]["levels"]
    x = list(range(1, 13))
    blue, orange, grey = "#2563eb", "#c56a12", "#64748b"
    fig, axes = plt.subplots(2, 2, figsize=(11, 8), layout="constrained")
    for metric, label, color, style in (("wrong_given_cells", "Given positions", blue, "-"),
                                         ("wrong_empty_cells", "Originally empty positions", orange, "--")):
        axes[0, 0].plot(x, [r["metrics"][metric]["mean"] for r in all_levels], marker="o", color=color, linestyle=style, label=label)
    axes[0, 0].set(title="Reference errors by position type", ylabel="Mean wrong cells / puzzle", ylim=(0, 81))
    for kind, label, color, style in (("given", "Given positions", blue, "-"), ("empty", "Originally empty positions", orange, "--")):
        axes[0, 1].plot(x, [100 * r["pooled_wrong_" + kind + "_rate"] for r in all_levels],
                        marker="o", color=color, linestyle=style, label=label)
    axes[0, 1].set(title="Reference errors with position-specific denominators", ylabel="Wrong cell opportunities (%)", ylim=(0, 100))
    for family, color, style in (("row", blue, "-"), ("column", orange, "--"), ("box", grey, ":")):
        axes[1, 0].plot(x, [r["metrics"][family + "_invalid_units"]["mean"] for r in all_levels],
                       marker="o", color=color, linestyle=style, label=family.capitalize())
    axes[1, 0].set(title="Invalid units, including incomplete units", ylabel="Mean invalid units / puzzle", ylim=(0, 9.3))
    for name, color, style in (("final_success", blue, "-"), ("final_failure", orange, "--")):
        data = groups[name]
        axes[1, 1].plot(x, [r["metrics"]["wrong_reference_cells"]["mean"] for r in data["levels"]],
                       marker="o", color=color, linestyle=style,
                       label=name.replace("_", " ") + f" (n={data['inputs']})")
    axes[1, 1].set(title="Retrospective final-outcome groups", ylabel="Mean wrong reference cells / puzzle", ylim=(0, 81))
    for ax in axes.flat:
        ax.set(xlabel="Hierarchy level", xticks=x)
        ax.grid(alpha=.18)
        ax.legend(fontsize=8)
    fig.suptitle("Saved exploration trajectories: 1,000 puzzles; 12,000 states")
    fig.savefig(output / "error_trends.png")
    plt.close(fig)

    fig, axes = plt.subplots(1, 3, figsize=(14, 4.7), sharey=True, layout="constrained")
    maximum = max(sum(row["metrics"][metric]["mean"] or 0 for metric in
                      ("corrected_cells", "corrupted_cells", "wrong_to_different_wrong_cells"))
                  for group in groups.values() for row in group["boundaries"])
    for ax, name in zip(axes, ("all", "final_success", "final_failure")):
        data = groups[name]
        bottom = [0.] * 11
        for metric, label, color, hatch in (("corrected_cells", "Wrong to correct", blue, None),
                                            ("corrupted_cells", "Correct to wrong", orange, "//"),
                                            ("wrong_to_different_wrong_cells", "Wrong to different wrong", grey, "..")):
            values = [r["metrics"][metric]["mean"] for r in data["boundaries"]]
            ax.bar(range(11), values, bottom=bottom, color=color, label=label, hatch=hatch, linewidth=.4)
            bottom = [a + b for a, b in zip(bottom, values)]
        ax.set(title=name.replace("_", " ") + f" (n={data['inputs']})",
               xticks=range(11), xticklabels=[f"{k}→{k+1}" for k in range(1, 12)],
               xlabel="Adjacent hierarchy levels", ylim=(0, maximum * 1.15))
        ax.tick_params(axis="x", rotation=45)
        ax.grid(axis="y", alpha=.18)
    axes[0].set_ylabel("Mean changed cells / puzzle")
    axes[0].legend(fontsize=8, loc="upper left")
    fig.suptitle("Reference-labeled changes; final-outcome groups are retrospective")
    fig.savefig(output / "transition_changes.png")
    plt.close(fig)

    fig, axes = plt.subplots(2, 3, figsize=(11, 6.6), sharex=True, sharey=True, layout="constrained")
    edges = list(range(0, 86, 5))
    for row, name in enumerate(("final_success", "final_failure")):
        group = groups[name]
        for col, level in enumerate((10, 11, 12)):
            histogram = group["levels"][level - 1]["metrics"]["wrong_reference_cells"]["histogram"]
            bins = [0.] * (len(edges) - 1)
            for value, count in histogram.items():
                bins[min(int(value) // 5, len(bins) - 1)] += 100 * count / group["inputs"]
            ax = axes[row, col]
            ax.bar(edges[:-1], bins, width=5, align="edge", color=blue, edgecolor="white", linewidth=.5)
            ax.set(title=f"Level {level}; " + name.replace("_", " ") + f" (n={group['inputs']})",
                   xlabel="Wrong reference cells (5-cell bins)", ylabel="Puzzles in group (%)",
                   xlim=(0, 85), ylim=(0, 100), xticks=(0, 20, 40, 60, 80))
            ax.grid(axis="y", alpha=.18)
    fig.suptitle("Late-level error distributions; groups defined by final primary validity")
    fig.savefig(output / "late_error_distributions.png")
    plt.close(fig)


def write_summary(output, analysis, repository):
    groups = analysis["groups"]
    all_group = groups["all"]
    final, before = all_group["levels"][-1], all_group["levels"][-2]
    last_change = all_group["boundaries"][-1]
    m11, m12 = before["metrics"], final["metrics"]
    roots = Path(os.path.relpath(repository, output)).as_posix()
    lines = [
        "# R1A: diagnosis of saved exploration Sudoku prefixes", "",
        "**Completed:** October 22, 2026 (America/Toronto). **Scope:** 1,000 exploration puzzles, 12,000 states, 11,000 adjacent transitions. No new inference or timed requests.", "",
        "## Findings", "",
        f"- Original exploration primary counts are reproduced: zero valid outputs at levels 1–11; **{final['valid_count']}/1,000** valid at level 12. The original hard-Sudoku no-go is unchanged.",
        f"- At level 11, mean wrong reference cells are **{m11['wrong_reference_cells']['mean']:.3f}**: **{m11['wrong_given_cells']['mean']:.3f}** at supplied clues and **{m11['wrong_empty_cells']['mean']:.3f}** at originally empty positions. **{m11['clue_violations']['positive_count']}/1,000** boards violate at least one clue.",
        f"- From level 11 to 12, mean corrected cells are **{last_change['metrics']['corrected_cells']['mean']:.3f}**, mean correct-to-wrong cells **{last_change['metrics']['corrupted_cells']['mean']:.3f}**, and mean wrong-to-different-wrong cells **{last_change['metrics']['wrong_to_different_wrong_cells']['mean']:.3f}**.",
        f"- At level 12, **{m12['clue_violations']['positive_count']}** boards violate clues and **{m12['blank_cells']['positive_count']}** contain blanks. **{groups['final_failure']['inputs']}** remain invalid; completeness or clue preservation alone is insufficient.",
        "", "These are reference-labeled descriptions, not a causal explanation. The study has not encoded target solutions or changed a checkpoint. Final-outcome groups are retrospective and cannot be deployed as stopping features.",
        "", "## Definitions and coverage", "",
        "Wrong cells include blanks. Given and empty positions are disjoint; clue violations include blank values at given positions. Invalid units include blank or missing-digit units; duplicate metrics ignore zero. Duplicate excess is filled values minus distinct nonzero values. Row, column, box, clue, and reference-error categories overlap; their totals must not be treated as disjoint mistakes.",
        "", f"All {sum(r['parseable_inputs'] for r in all_group['levels']):,} selected states are parseable; unparseable states: {sum(r['unparseable_inputs'] for r in all_group['levels'])}. Each level has {before['given_cell_opportunities']:,} given-cell and {before['empty_cell_opportunities']:,} originally empty-cell opportunities, totaling {before['all_cell_opportunities']:,} cells from 1,000 puzzles.",
        "", f"Level-11 wrong-cell distribution: median {m11['wrong_reference_cells']['median']:.1f}, p95 {m11['wrong_reference_cells']['p95']:.1f}, range {m11['wrong_reference_cells']['min']}–{m11['wrong_reference_cells']['max']}. At level 12: median {m12['wrong_reference_cells']['median']:.1f}, p95 {m12['wrong_reference_cells']['p95']:.1f}, range {m12['wrong_reference_cells']['min']}–{m12['wrong_reference_cells']['max']}. These are descriptive distributions, not confidence intervals.",
        "", "Pooled given/empty error rates use total wrong cells divided by the respective summed position opportunities. All counts, exact histograms, linear-interpolation quantiles, sums, and defined/undefined coverage are retained in analysis.json.",
        "", "| Level | Mean wrong cells | Mean wrong given | Mean wrong empty | Mean blanks | Boards violating clues |",
        "| ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in all_group["levels"]:
        m = row["metrics"]
        lines.append(f"| {row['level']} | {m['wrong_reference_cells']['mean']:.3f} | {m['wrong_given_cells']['mean']:.3f} | {m['wrong_empty_cells']['mean']:.3f} | {m['blank_cells']['mean']:.3f} | {m['clue_violations']['positive_count']} / {row['inputs']} |")
    lines += ["", "![Error trends](error_trends.png)", "",
              "| Level | Mean invalid rows / 9 | Mean invalid columns / 9 | Mean invalid boxes / 9 | Mean conflicting cells |",
              "| ---: | ---: | ---: | ---: | ---: |"]
    for row in all_group["levels"]:
        m = row["metrics"]
        lines.append(f"| {row['level']} | {m['row_invalid_units']['mean']:.3f} | {m['column_invalid_units']['mean']:.3f} | {m['box_invalid_units']['mean']:.3f} | {m['conflicting_cells']['mean']:.3f} |")
    lines += ["", "## Late levels by retrospective final outcome", "",
              "| Group | Inputs | Level | Mean wrong cells | Mean wrong given | Mean wrong empty | Primary valid |",
              "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for name in ("final_success", "final_failure"):
        group = groups[name]
        for row in group["levels"][9:12]:
            m = row["metrics"]
            lines.append(f"| {name} | {group['inputs']} | {row['level']} | {m['wrong_reference_cells']['mean']:.3f} | {m['wrong_given_cells']['mean']:.3f} | {m['wrong_empty_cells']['mean']:.3f} | {row['valid_count']} |")
    lines += ["", "Membership is defined by final primary validity, so the final difference in primary-valid counts is tautological. This is an error-pattern comparison, not a predictive evaluation or proof of uniqueness of the supplied reference solution.",
              "", "![Late error distributions](late_error_distributions.png)", "",
              "## Changes between adjacent levels", "",
              "| Boundary | Mean changed | Mean corrected | Mean corrupted | Mean wrong-to-different-wrong | Puzzles with any corruption |",
              "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for row in all_group["boundaries"]:
        m = row["metrics"]
        lines.append(f"| {row['from_level']}→{row['to_level']} | {m['changed_cells']['mean']:.3f} | {m['corrected_cells']['mean']:.3f} | {m['corrupted_cells']['mean']:.3f} | {m['wrong_to_different_wrong_cells']['mean']:.3f} | {m['corrupted_cells']['positive_count']} / {row['inputs']} |")
    lines += ["", "| Retrospective group | Boundary | Mean changed | Mean corrected | Mean corrupted | Mean wrong-to-different-wrong |",
              "| --- | --- | ---: | ---: | ---: | ---: |"]
    for name in ("final_success", "final_failure"):
        for row in groups[name]["boundaries"][9:11]:
            m = row["metrics"]
            lines.append(f"| {name} | {row['from_level']}→{row['to_level']} | {m['changed_cells']['mean']:.3f} | {m['corrected_cells']['mean']:.3f} | {m['corrupted_cells']['mean']:.3f} | {m['wrong_to_different_wrong_cells']['mean']:.3f} |")
    lines += ["", "Changed = corrected + corrupted + wrong-to-different-wrong for every transition. Wrong-after = wrong-before − corrected + corrupted. A change can fill/create a blank as well; blank transitions overlap these categories.",
              "", "![Reference-labeled changes](transition_changes.png)", "",
              "## Representative examples", "",
              "Choose the lowest dataset index satisfying each predeclared category; categories may share an example. Absent categories are not fabricated.",
              "", "| Category | Dataset index |", "| --- | ---: |"]
    cases = analysis["representative_cases"]
    for name, case in cases.items():
        lines.append(f"| {name} | {case['dataset_index'] if case else 'none observed'} |")
    seen = set()
    for case in cases.values():
        if case is None or case["dataset_index"] in seen:
            continue
        seen.add(case["dataset_index"])
        lines += ["", f"### Exploration dataset index {case['dataset_index']}", ""]
        for label, board in [("Puzzle", case["puzzle"]), ("Reference", case["reference"])] + [(f"Level {k}", board) for k, board in zip((10, 11, 12), case["boards"])]:
            lines += [label + ":", "", "~~~text"]
            if board is None:
                lines.append("unparseable")
            else:
                lines += ["".join(str(v) if v else "." for v in board[r:r + 9]) for r in range(0, 81, 9)]
            lines += ["~~~", ""]
    access = analysis["access"]
    lines += ["", "## Reproducibility and boundaries", "",
              f"Selected puzzle/reference rows per file: {access['selected_puzzle_rows']}. Exploration trajectories deserialized: {access['exploration_records_deserialized']}. Development lines skipped before JSON parsing: {access['development_lines_skipped_before_json']}. Development trajectories deserialized: {access['development_records_deserialized']}; sealed rows materialized: {access['sealed_rows_materialized']}; model calls: 0; timed requests: 0.",
              "", "The source JSONL is checksummed in full, but only exploration rows are deserialized or analyzed. Original aggregate exploration counts are checked against the recorded Phase 1 analysis. All historical empirical artifacts remain unchanged.",
              "", "[Analysis](analysis.json), [board metrics](board_metrics.csv), [transition metrics](transition_metrics.csv), [provenance](provenance.json).",
              "", f"[Pre-analysis plan]({roots}/docs/studies/sudoku-prefix-diagnosis-plan.md), [implementation]({roots}/src/anytime_ncm/diagnosis.py), [tests]({roots}/tests/test_diagnosis.py).",
              "", "From the prepared repository:", "", "~~~powershell",
              f"python scripts/diagnose_sudoku_prefixes.py --output {output.relative_to(repository).as_posix()} --verify",
              "~~~", "",
              "To reproduce into a fresh directory, run the same command without --verify in the validated WSL environment, selecting a new output path under results/followup/. Only figure generation needs Matplotlib; verification is model-free and uses the Python standard library plus existing local dataset artifacts.",
              "", "## Interpretation and next action", "",
              f"All {all_group['boundaries'][9]['metrics']['corrupted_cells']['positive_count']} exploration puzzles lose at least one previously reference-correct cell at 10→11, even while aggregate reference error declines. At 11→12, {last_change['metrics']['corrupted_cells']['positive_count']} puzzles have such a regression; all belong to the final-failure group. Individual cell correctness is therefore not monotonically preserved by refinement.",
              "", "The observed final-level recovery of all supplied clues motivates separately tracking given-position and empty-position errors in R1B target-encoded prefixes. It does not establish that an explicit clue-copy mechanism exists or that changing only the generator would fix early outputs.",
              "", "The error taxonomy describes how decoded boards fail. It does not establish whether target-encoded prefixes could solve early, whether generated codes are the bottleneck, or whether another frozen checkpoint would behave differently.",
              "", "Proceed next only with the separately scoped R1B protocol: encode the same preselected 32 exploration references, decode all target-code prefixes, and compare with their already saved generated prefixes. Successful target final round trips are a necessary diagnostic check; early target success would establish an early representable solution for those inputs, not prove that changing only the generator fixes all failures. If both paths fail early, retain tokenizer/decoder limitations as a hypothesis rather than an impossibility result.",
              "", "Implementation preflight: the first run rejected selection metadata before trajectory analysis because the new guard expected sample_id rather than the historical puzzle_sha256 field. The guard was corrected and a regression fixture added. The successful diagnosis retained every exploration input. Report-only additions reused the same data and added no inference or timed observations.",
              "", "R1A closes after this descriptive report. No R1B encoding, new checkpoint screen, online stopping, controller fitting, final-holdout evaluation, or speedup measurement occurred."]
    (output / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def render_diagnosis(output, analysis, repository):
    render_figures(output, analysis)
    write_summary(output, analysis, repository)
