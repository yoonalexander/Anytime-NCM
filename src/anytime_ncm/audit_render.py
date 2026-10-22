"""R3 scientific figure and report; all costs labeled as diagnostic estimates."""
from pathlib import Path
from anytime_ncm.audit import OUTPUT, PROTOCOL


def render(root, analysis):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import json
    out = Path(root) / OUTPUT
    fig, axes = plt.subplots(2, 2, figsize=(10, 7), layout="constrained")
    for partition, color in (("exploration", "#0072B2"), ("development", "#D55E00")):
        summary = analysis["trajectory_summary"][partition]
        axes[0, 0].plot(range(1, 13), [100 * n / summary["inputs"] for n in summary["valid_solution_count_by_level"]],
                       color=color, marker="o", label=partition.capitalize())
        axes[0, 1].plot(range(1, 13), [100 * q["official_cell_accuracy_mean"] for q in summary["quality_by_level"]],
                       color=color, marker="o", label=partition.capitalize())
    axes[0, 0].set(xlabel="Hierarchy level", ylabel="Primary-valid solutions (%)", ylim=(-2, 102))
    axes[0, 1].set(xlabel="Hierarchy level", ylabel="Official cell accuracy (%)", ylim=(-2, 102))
    dev = analysis["profile_costs"]["development"]
    axes[1, 0].bar(["Full depth", "Every-level verified"], [dev["baseline_ms"]["mean"], dev["verified_ms"]["mean"]],
                   color=["#777777", "#D55E00"])
    axes[1, 0].set(ylabel="Mean estimated request cost (ms)", title="Development: 100 identities x 5 repeats")
    fixed = analysis["fixed_depth_comparison"]["development"]
    axes[1, 1].plot([100 * f["collection_valid_rate"] for f in fixed],
                   [f["mean_estimated_ms"] for f in fixed], color="#0072B2", marker="o", label="Fixed depths")
    axes[1, 1].scatter([100 * dev["verified_valid_rate"]], [dev["verified_ms"]["mean"]],
                      color="#D55E00", marker="s", label="Verified estimate")
    axes[1, 1].set(xlabel="Primary validity (%)", ylabel="Mean estimated cost (ms)")
    for ax in axes.flat:
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", alpha=.2)
    for ax in (axes[0, 0], axes[0, 1], axes[1, 1]):
        ax.legend(frameon=False)
    fig.suptitle("R3 easy Sudoku: separately requested extension after negative R2", fontsize=12)
    fig.savefig(out / "audit_comparison.png", dpi=160)
    plt.close(fig)
    paired = dev["paired"]
    ci = paired["relative_mean_reduction_ci95"]
    metric = analysis["official_baseline"]
    lines = ["# R3 easy-Sudoku extended opportunity and cost audit", "",
        "**Completed:** October 22, 2026 (America/Toronto).", "",
        f'**Decision: {analysis["decision"]}.** Development estimated mean reduction '
        f'{100 * paired["relative_mean_reduction"]:.2f}%, paired 95% interval [{100 * ci[0]:.2f}%, {100 * ci[1]:.2f}%]. '
        'These are instrumented component-sum estimates, not measured online latency or speedup.', "",
        "## Entry exception and scope", "",
        "Neither easy nor medium qualified under R2's early-valid screen gate. The user's subsequent explicit "
        "'Do R3' request authorized this separate extension. Easy was chosen as the first candidate in the already "
        "declared order. R2's negative result, exhausted budget and source/protocol remain unchanged; this audit "
        "does not retroactively qualify it or confirm a positive pilot.", "",
        "The 32 screened easy exploration trajectories are reused within the total 1,000 exploration inputs; they "
        "are not independent confirmation examples. Another 400 development inputs complete the permitted audit. "
        "There is no medium extension, new policy search, target encoding, training, online stopping, or task change.", "",
        "## Quality and opportunity", "",
        "| Partition | Inputs | Early-valid inputs | Final primary-valid | Never valid |",
        "| --- | ---: | ---: | ---: | ---: |"]
    for p in ("exploration", "development"):
        s = analysis["trajectory_summary"][p]
        early = sum(s["first_valid_counts"][str(k)] for k in range(1, 12))
        lines.append(f'| {p} | {s["inputs"]} | {early} | {s["valid_solution_count_by_level"][-1]} | {s["never_solved_count"]} |')
    lines += ["", "| Partition | Level | Primary-valid | Parseable | Complete | Clue-consistent | Reference matches | Official cell accuracy |",
              "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for p in ("exploration", "development"):
        for q in analysis["trajectory_summary"][p]["quality_by_level"]:
            accuracy = "undefined" if q["official_cell_accuracy_mean"] is None else f'{100 * q["official_cell_accuracy_mean"]:.2f}%'
            lines.append(f'| {p} | {q["level"]} | {q["valid_solution_count"]} | {q["parseable_count"]} | '
                f'{q["complete_count"]} | {q["clue_consistent_count"]} | {q["reference_agreement_count"]} | {accuracy} |')
    lines += ["", "Primary validity checks format, completeness, rows/columns/boxes and supplied clues. Reference equality "
              "is diagnostic only. Official cell scores use zipped decoded characters and can overstate truncated outputs; "
              "defined/undefined coverage and other official scores are retained in analysis.json.", "",
              "![Audit comparison](audit_comparison.png)", "", "## Estimated costs and gate", "",
              "| Partition | Full mean / median / p95 (ms) | Verified mean / median / p95 (ms) | Mean reduction | Paired 95% interval |",
              "| --- | --- | --- | ---: | --- |"]
    for p in ("exploration", "development"):
        c = analysis["profile_costs"][p]
        def dist(key):
            return " / ".join(f'{c[key][k]:.3f}' for k in ("mean", "median", "p95"))
        lo, hi = c["paired"]["relative_mean_reduction_ci95"]
        lines.append(f'| {p} | {dist("baseline_ms")} | {dist("verified_ms")} | '
            f'{100 * c["paired"]["relative_mean_reduction"]:.2f}% | [{100 * lo:.2f}%, {100 * hi:.2f}%] |')
    lines += ["", f'Independent primary-label disagreements: **{analysis["independent_validity_disagreements"]}**; '
        f'false verifier accepts: **{analysis["false_verifier_accepts"]}**. '
        f'Development collection solve-loss count: **{analysis["collection_primary_solve_loss_counts"]["development"]}**. '
        f'Profile-versus-collection code/output disagreements: **{analysis["profile_collection_code_disagreements"]}/'
        f'{analysis["profile_collection_any_output_disagreements"]}** over all 1,000 repeats.', "",
        f'Estimated skipped levels/codes per development request: **{dev["mean_skipped_levels"]:.3f} / '
        f'{dev["mean_skipped_codes"]:.3f}**. Profile primary validity: baseline {100 * dev["baseline_valid_rate"]:.2f}%, '
        f'verified {100 * dev["verified_valid_rate"]:.2f}%. Paired quality difference '
        f'{paired["quality_difference"]:.5f}, interval {paired["quality_difference_ci95"]}.', "",
        "The unchanged gate requires >=5% reduction, lower interval bound >0, zero empirical quality loss and false "
        "accepts, and passed correctness. The interval resamples 100 development identities 10,000 times (seed 20261020), "
        "retaining all five repeats per identity. The 400-input development trajectory set also checks quality preservation.", "",
        f'Uncorrected gate: **{analysis["uncorrected_gate"]}**. Calibrated sensitivity gate: '
        f'**{analysis["calibration_sensitivity_gate"]}**. Sensitivity estimated reduction: '
        f'{100 * analysis["calibration_sensitivity_costs"]["development"]["paired"]["relative_mean_reduction"]:.2f}%. '
        "Calibration removes median empty-region/event allowances, not all hook/launch perturbation. A gate change is inconclusive.", "",
        "| Fixed depth | Mean estimated development ms | Profile validity | Full development validity |",
        "| ---: | ---: | ---: | ---: |"]
    for f in fixed:
        lines.append(f'| {f["level"]} | {f["mean_estimated_ms"]:.3f} | {100 * f["profile_valid_rate"]:.2f}% | {100 * f["collection_valid_rate"]:.2f}% |')
    best = analysis["development_selected_quality_feasible_fixed_depth"]
    lines += ["", f'Development-selected quality-feasible fixed depth: **{best["level"]}** '
        f'({best["mean_estimated_ms"]:.3f} ms). This comparison is selected on development, not evaluated on a final set.', "",
        "Monitoring reconstructs each prefix from scratch. Generation feedback is already in generation-stage measurements "
        "and is not charged again as monitoring. The estimate includes preparation, generation through exit, every scheduled "
        "assembly/reconstruction/decode/transfer/text/verifier/policy cost, with all checks on never-valid requests. "
        "Feature extraction is measured but excluded because this verifier-only policy does not use it. Loading, warmups, "
        "reference scoring, serialization and validation-only final parity decodes are excluded.", "",
        "## Official baseline, execution and reservations", "",
        f'The unchanged official evaluator reports **{metric["solved"]}/{metric["total"]}** solved '
        f'({metric["solved_percent"]:.2f}%), cell accuracy {metric["cell_percent"]:.2f}%, valid-grid '
        f'{metric["valid_grid_percent"]:.2f}%. These rounded aggregate official metrics do not independently rescore clues. '
        "No easy-setting paper-number parity is claimed; the historical hard-Sudoku +0.15-percentage-point discrepancy "
        "remains unexplained.", "",
        "All stages use the pinned easy checkpoint/config at batch 1, float32/eval on the RTX 5060/WSL pathway, with "
        "four CPU threads, deterministic official sampling, no compilation/autocast and no cache override. "
        "New evaluation allocation: 2,000 official baseline generations + 1,368 new collection generations + "
        "1,000 timed generations + ten warmups = **4,378 generations**. Decoder forwards total **31,536**. "
        "The new collection checks all 1,368 sets of prefixes independently; profiling checks 1,000 extra final "
        "reconstruction decodes and repeated/hooked parity. Extra parity evaluations are charged to the execution "
        "budget but excluded from estimated deployed cost.", "",
        "The official baseline internally reads/scores all 2,000 rows; only its printed aggregates are inspected. "
        "Its raw predictions remain local/ignored and are never opened by audit analysis. Adapter collection, profiling "
        "and analysis selectively materialize only exploration/development inputs/references. Both final partitions "
        "remain reserved for adaptive-policy work. All difficulty solution files are identical, so original row-index "
        "reservations are inherited across masks. Prior hard exploration/development exposure means difficulty views "
        "are related, not independent datasets. R2's identity-only hash traversal included reserved puzzle operands; "
        "unknown training overlap remains unresolved.", "",
        "## Decision and reproduction", ""]
    if analysis["decision"] == "go":
        lines += ["The new easy-setting gate supports a separately requested Phase 2 implementation/benchmark. "
                  "It does not change the original hard no-go or negative R2 screen, or establish measured online savings.", ""]
    else:
        lines += ["R3 supplies no new Phase 2 go. Retain the completed negative/inconclusive result and stop this audit "
                  "at its budget. A different method/task requires a separate request and protocol.", ""]
    lines += ["[Frozen R3 protocol](../../../" + PROTOCOL + "), [configuration](../../../configs/r3_easy.json), "
              "[analysis](analysis.json), [trajectory table](trajectory_table.csv), [completion evidence](completion.json).", "",
              "[Aggregate baseline receipt](baseline_metrics.json), [baseline stage](baseline.json), "
              "[collection stage](collection.json), [trajectories](trajectories.jsonl), [prefix checks](prefix_checks.jsonl), "
              "[profile stage](profiles.json), [profile metadata](profiles/run.json), "
              "[profile components](profiles/components.jsonl), [report provenance](report_provenance.json).", "",
              "~~~powershell", ".\\scripts\\wsl_python.ps1 -PythonArguments @('scripts/audit_sudoku_easy.py','verify')", "~~~", "",
              "Verification recomputes labels, partition selection, costs/bootstrap, gates, and hashes using saved "
              "permitted records, without torch/matplotlib imports or official raw prediction access. It does not "
              "rerun CUDA parity. The model-evaluation allocation is consumed; use saved evidence for report work.", ""]
    (out / "summary.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
