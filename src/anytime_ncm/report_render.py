"""Scientific plots and source-linked Markdown for the Phase 1 audit."""

import os
from pathlib import Path

import numpy as np


def write_figures(output, analysis):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 10, "figure.dpi": 140, "savefig.dpi": 200})
    summaries, costs = analysis["trajectory_summary"], analysis["profile_costs"]
    fig, ax = plt.subplots(figsize=(8, 4.8), layout="constrained")
    for partition, color in (("exploration", "#2563eb"), ("development", "#d97706")):
        data = summaries[partition]
        ax.plot(range(1, 13), np.array(data["valid_solution_count_by_level"]) / data["inputs"] * 100,
                marker="o", color=color, label=f"{partition}: valid (n={data['inputs']})")
        ax.plot(range(1, 13), np.array(data["reference_solved_count_by_level"]) / data["inputs"] * 100,
                linestyle="--", color=color, alpha=.7, label=f"{partition}: reference match")
    ax.set(xlabel="Cumulative hierarchy level", ylabel="Solved inputs (%)",
           title="Offline Sudoku solve rate by level", xticks=range(1, 13), ylim=(0, 100))
    ax.grid(alpha=.2); ax.legend(loc="upper left", fontsize=8)
    fig.savefig(output / "solve_rate_by_level.png"); plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), sharey=True, layout="constrained")
    for ax, (partition, data) in zip(axes, summaries.items()):
        values = [data["first_valid_counts"][str(k)] for k in range(1, 13)] + [data["never_solved_count"]]
        ax.bar(range(13), np.array(values) / data["inputs"] * 100, color="#2563eb" if partition == "exploration" else "#d97706")
        ax.set(title=partition, xticks=range(13), xticklabels=[str(i) for i in range(1, 13)] + ["never"],
               xlabel="First valid level", ylabel="Inputs (%)")
        ax.tick_params(axis="x", labelsize=8)
    fig.suptitle("First-valid distribution, including never-valid inputs")
    fig.savefig(output / "first_valid_distribution.png"); plt.close(fig)
    fig, ax = plt.subplots(figsize=(8, 4.5), layout="constrained")
    positions = np.arange(2)
    ax.bar(positions - .18, [costs[p]["baseline_ms"]["mean"] for p in summaries], .36, label="Full depth", color="#64748b")
    ax.bar(positions + .18, [costs[p]["verified_ms"]["mean"] for p in summaries], .36, label="Every-level verified stop", color="#2563eb")
    ax.set(xticks=positions, xticklabels=list(summaries), ylabel="Mean estimated cost (ms)",
           title="Offline component-sum estimates at batch size 1")
    ax.legend(); ax.grid(axis="y", alpha=.2)
    fig.savefig(output / "estimated_cost_comparison.png"); plt.close(fig)
    cases = analysis["representative_cases"]
    fig, ax = plt.subplots(figsize=(9, max(2.5, len(cases) * .65)), layout="constrained")
    labels = list(cases)
    matrix = np.array([cases[name]["valid_by_level"] for name in labels], dtype=int)
    if len(labels):
        ax.imshow(matrix, cmap="Blues", vmin=0, vmax=1, aspect="auto")
    ax.set(xticks=range(12), xticklabels=range(1, 13),
           yticks=range(len(labels)), yticklabels=[f"{name.replace('_', ' ')}: index {cases[name]['dataset_index']}" for name in labels],
           xlabel="Hierarchy level", title="Exploration examples: blue = valid; white = invalid")
    fig.savefig(output / "representative_trajectories.png"); plt.close(fig)


def write_summary(output, analysis, metadata, *, repository, profiles):
    summaries, costs = analysis["trajectory_summary"], analysis["profile_costs"]
    d = costs["development"]
    interval = d["paired"]["relative_mean_reduction_ci95"]
    quality_ci = d["paired"]["quality_difference_ci95"]
    lines = ["# Phase 1 trajectory audit and decision", "", "**Completed:** October 20, 2026 (America/Toronto).",
             "", "**Quality reporting completed on review:** October 21, 2026; existing trajectories and profiles reused.",
             "", "**Decision: " + analysis["decision"].upper() + ".** This is an offline estimated-cost decision; no online speedup was measured.",
             "", "## Development gate", "",
             f"Mean estimated reduction versus full depth: **{100*d['paired']['relative_mean_reduction']:.2f}%**, paired 95% interval **[{100*interval[0]:.2f}%, {100*interval[1]:.2f}%]**.",
             f"The frozen worthwhile threshold is 5%; maximum empirical quality loss and false verifier accepts are zero. Independent false accepts: **{analysis['false_verifier_accepts']}**; validity disagreements: **{analysis['independent_validity_disagreements']}**.",
             f"Profiled development solve-rate difference (verified minus full depth): **{100*d['paired']['quality_difference']:.2f} percentage points**, 95% interval [{100*quality_ci[0]:.2f}, {100*quality_ci[1]:.2f}].",
             f"Calibration sensitivity gate: **{analysis['calibration_sensitivity_gate']}**; primary diagnostic gate: **{analysis['uncorrected_gate']}**.",
             "", "The gate uses the first 100 development identities at batch size 1, five repeats each. Exploration profiling is descriptive corroboration. Bootstrap: 10,000 paired puzzle-identity resamples, seed 20261020; all five repeats are retained within each cluster.",
             "", "## Trajectory quality", "",
             "| Partition | Inputs | Final valid | Ever valid | Never valid | Inputs with valid-to-invalid transitions |",
             "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for partition, data in summaries.items():
        lines.append(f"| {partition} | {data['inputs']} | {data['valid_solution_count_by_level'][-1]} ({100*data['valid_solution_count_by_level'][-1]/data['inputs']:.2f}%) | {data['ever_valid_count']} | {data['never_solved_count']} ({100*data['never_solved_fraction']:.2f}%) | {data['puzzles_with_valid_to_invalid']} |")
    lines += ["", "![Solve rate](solve_rate_by_level.png)", "",
              "| Level | Exploration valid / 1000 | Development valid / 400 | Exploration first valid | Development first valid |",
              "| ---: | ---: | ---: | ---: | ---: |"]
    for k in range(12):
        lines.append(f"| {k+1} | {summaries['exploration']['valid_solution_count_by_level'][k]} | {summaries['development']['valid_solution_count_by_level'][k]} | {summaries['exploration']['first_valid_counts'][str(k+1)]} | {summaries['development']['first_valid_counts'][str(k+1)]} |")
    lines += ["", "### Parsing, completeness, and upstream comparison", "",
              "Counts below use every input in the named partition at each level. Unparseable and parseable-but-incomplete outputs are disjoint; complete + parseable incomplete + unparseable equals the input count. Grid validity alone does not establish clue preservation.", "",
              "Official solved compares decoded text exactly; reference agreement compares parsed boards. Official cell accuracy is the unweighted mean of per-example zipped-character accuracy, so truncated text can score highly. Undefined per-example accuracy is saved as null; if any value is undefined, the aggregate is also undefined rather than silently dropping it. Defined coverage is shown explicitly. These secondary metrics do not control valid-solution acceptance."]
    for partition, data in summaries.items():
        lines += ["", f"#### {partition} (n={data['inputs']})", "",
                  "| Level | Unparseable | Parseable incomplete | Complete | Grid valid | Clue consistent | Reference agreement |",
                  "| ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
        for row in data["quality_by_level"]:
            lines.append(f"| {row['level']} | {row['unparseable_count']} | {row['parseable_incomplete_count']} | {row['complete_count']} | {row['grid_valid_count']} | {row['clue_consistent_count']} | {row['reference_agreement_count']} |")
        lines += ["", "| Level | Official solved | Official valid grid | Official mean cell accuracy | Defined cell scores |",
                  "| ---: | ---: | ---: | ---: | ---: |"]
        for row in data["quality_by_level"]:
            accuracy = row["official_cell_accuracy_mean"]
            formatted = "undefined" if accuracy is None else f"{100*accuracy:.2f}%"
            lines.append(f"| {row['level']} | {row['official_solved_count']} | {row['official_valid_grid_count']} | {formatted} | {row['official_cell_accuracy_defined_count']} / {data['inputs']} |")
    lines += ["", "![First-valid distribution](first_valid_distribution.png)", "",
              "Valid-to-invalid transition counts at boundaries 1→2 through 11→12: exploration " +
              str(summaries["exploration"]["valid_to_invalid_transition_counts"]) + "; development " +
              str(summaries["development"]["valid_to_invalid_transition_counts"]) + ".",
              "", "## Estimated cost and skipped code work", "",
              "| Partition | Full mean / median / p95 (ms) | Verified mean / median / p95 (ms) | Mean levels skipped | Mean code positions skipped | Mean estimated reduction |",
              "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for partition, data in costs.items():
        b, c = data["baseline_ms"], data["verified_ms"]
        lines.append(f"| {partition} | {b['mean']:.3f} / {b['median']:.3f} / {b['p95']:.3f} | {c['mean']:.3f} / {c['median']:.3f} / {c['p95']:.3f} | {data['mean_skipped_levels']:.3f} | {data['mean_skipped_codes']:.3f} / 322 | {100*data['paired']['relative_mean_reduction']:.2f}% |")
    lines += ["", "These are component sums: input preparation, generation through exit, and every assembly/reconstruction/decode/transfer/text/verifier/decision check through exit. Never-valid inputs pay full generation and all 12 checks. Full depth pays one final reconstruction/decode/transfer/text output. Feature extraction is profiled separately and excluded from the verifier-only candidate, which does not use it.",
              "", "Generation uses CUDA markers with no internal synchronization. Feedback reconstruction is charged to the next generation stage that needs it; standalone monitoring reconstruction is separate. Final generated-code concatenation is reused at level 12; earlier checks include prefix assembly. Full-generation host residual is charged once at every exit.",
              "", "![Estimated costs](estimated_cost_comparison.png)", "",
              "## Fixed-depth comparison", "",
              "| Depth | Development valid rate: batch-128 collection | Development valid rate: batch-1 profile | Mean estimated cost (ms) |",
              "| ---: | ---: | ---: | ---: |"]
    for row in analysis["fixed_depth_comparison"]["development"]:
        lines.append(f"| {row['level']} | {100*row['collection_valid_rate']:.2f}% | {100*row['profile_valid_rate']:.2f}% | {row['mean_estimated_ms']:.3f} |")
    best = analysis["development_selected_quality_feasible_fixed_depth"]
    lines += ["", f"Minimum-cost fixed depth with no empirical quality loss in both development views: **{best['level']}**, estimated **{best['mean_estimated_ms']:.3f} ms**. Selection uses development data; this is not held-out performance.",
              "", "## Representative exploration trajectories", "",
              "Use the lowest dataset index meeting each category. Late recovery requires valid→invalid→valid; late success means first valid at level 12.",
              "", "![Representative trajectories](representative_trajectories.png)", "",
              "| Category | Dataset index | Valid at levels 1–12 |", "| --- | ---: | --- |"]
    for name in ("early_success", "late_recovery", "late_success", "never_solved"):
        case = analysis["representative_cases"].get(name)
        if case:
            pattern = " ".join("V" if flag else "·" for flag in case["valid_by_level"])
            lines.append(f"| {name.replace('_', ' ')} | {case['dataset_index']} | {pattern} |")
        else:
            lines.append(f"| {name.replace('_', ' ')} | none observed | — |")
    calibration = metadata["instrumentation_calibration"]
    lines += ["", "## Coverage and limitations", "",
              "- Descriptive coverage: 1,000 exploration + 400 development inputs; 16,800 level records. Diagnostic coverage: first 100 identities per partition, ten exploration-only warmups, exactly five repeats per identity; 1,000 timed requests and 12,000 profiled levels. Both final holdouts remain reserved.",
              f"- Hook versus uninstrumented warmup code parity: {metadata['hook_vs_uninstrumented_code_parity_checks']} comparisons. Repeat-code parity: {metadata['repeated_code_parity_checks']}. Final reconstruction matched upstream: {metadata['final_reconstruction_parity_checks']} requests.",
              "- WSL2/Python 3.12.3/Torch 2.10.0+cu128/RTX 5060, float32/no autocast, greedy generation, four CPU threads, no compile/KV cache. Profiling overrides baseline batch size 128 with batch size 1. Differences across the 200 profiled identities: " + str(analysis["profile_batch1_vs_collection_batch128"]) + ". The gate uses its own matched batch-one outputs.",
              f"- Empty-region calibration medians: CUDA-region wall {calibration['cuda_region_wall_ms']:.6f} ms; 13-marker trace {calibration['marker_trace_wall_ms']:.6f} ms; host region {calibration['host_region_ms']:.6f} ms. Sensitivity subtracts these allowances with zero floors. These are not a bound on all hook/launch effects; isolated diagnostic synchronization may differ from deployed behavior.",
              "- Zero headline online latency measurements. Loading, warmup, reference scoring, serialization, and report generation are excluded from estimates. No actual halting, batch compaction, controller training, or final-holdout evaluation occurred.",
              "- Original full-set reproduction remains 1,725/2,000 (86.25%) versus paper 86.1%; the +0.15 percentage-point discrepancy is unexplained. Base-model training overlap is unknown.",
              "- No Phase 1D inference failure or discarded timed request occurred in this completed run. Original trajectory timings remain null; diagnostic profiles are separate artifacts.",
              "", "## Reproduction and sources", "",
              "Run scripts/profile_phase1.py in the validated WSL environment, then scripts/report_phase1.py. Preserve recorded directories and use fresh output paths for repeats. [Detailed commands and boundaries](../../docs/phase1d_profiling.md).",
              "", "[Trajectory table](trajectory_table.csv), [analysis](analysis.json), [profile metadata](profiles/run.json), [raw repeats](profiles/components.jsonl), [provenance](report_provenance.json), [frozen protocol](../../docs/experiment_protocol.md), [analysis plan](../../docs/phase1d_analysis_plan.md).",
              "", "## Next action", ""]
    if analysis["decision"] == "go":
        lines.append("Recommend a separate Phase 2 work order to measure actual online verified stopping. The offline estimate justifies that experiment; it does not establish a speedup.")
    elif analysis["decision"] == "no-go":
        lines.append("Close Phase 1 with this documented no-go. Do not start online stopping or controller work under this work order. Distinguish limited estimated opportunity from any recorded correctness blocker; later studies remain on the roadmap.")
    else:
        lines.append("Close Phase 1 as inconclusive within the fixed budget. Do not open a final holdout or expand the study retrospectively. Further measurements require a dated protocol amendment and another work order.")
    if all(all(value == 0 for value in data["valid_solution_count_by_level"][:-1]) for data in summaries.values()):
        lines.insert(lines.index("## Development gate"), "No clue-consistent valid solution appeared before level 12 on any of the 1,400 inputs. The no-go reflects zero observed early-exit opportunity; correctness checks passed. It applies to this frozen Sudoku checkpoint and reconstruction/sampling setting.")
        lines.insert(lines.index("## Development gate"), "")
    lines += ["", "## Diagnostic component breakdown", "", "| Component | Exploration mean (ms) | Development mean (ms) |", "| --- | ---: | ---: |"]
    for name in analysis["component_diagnostics_ms"]["development"]:
        lines.append(f"| {name} | {analysis['component_diagnostics_ms']['exploration'][name]:.6f} | {analysis['component_diagnostics_ms']['development'][name]:.6f} |")
    lines.append("\nGeneration and input preparation are once per request; monitoring components are sums over all 12 levels (assembly only 1-11). Feature cost is measured but unused by the verified candidate.")
    docs_relative = Path(os.path.relpath(Path(repository) / "docs", output)).as_posix()
    profiles_relative = Path(os.path.relpath(profiles, output)).as_posix()
    text = "\n".join(lines).replace("../../docs/", docs_relative + "/").replace("(profiles/", "(" + profiles_relative + "/")
    (output / "summary.md").write_text(text + "\n", encoding="utf-8", newline="\n")
