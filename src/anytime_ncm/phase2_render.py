"""Scientific warm online comparison and transparent Phase 2 entry/report."""
import json
from pathlib import Path
from anytime_ncm.phase2 import OUTPUT
def render(root,analysis):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    out=root/OUTPUT
    summary=analysis["final_summary"];primary=analysis["primary_method"];names=list(summary)
    fig,axes=plt.subplots(1,3,figsize=(12,4),layout="constrained")
    labels=[n.replace("verified_","verify ").replace("_","\n") for n in names]
    colors=["#D55E00" if n==primary else "#0072B2" for n in names]
    axes[0].bar(labels,[summary[n]["wall_ms"]["mean"] for n in names],color=colors)
    axes[0].set(ylabel="Mean actual request wall latency (ms)")
    axes[1].bar(labels,[100*summary[n]["valid_rate"] for n in names],color=colors)
    axes[1].set(ylabel="Primary-valid requests (%)",ylim=(0,102))
    axes[2].bar(labels,[summary[n]["generator_levels"]["mean"] for n in names],color=colors)
    axes[2].set(ylabel="Mean generator levels executed",ylim=(0,12.5))
    for ax in axes:
        ax.grid(axis="y",alpha=.2);ax.spines[["top","right"]].set_visible(False)
        ax.tick_params(axis="x",labelsize=8,rotation=20)
    fig.suptitle("Phase 2: 300 reserved easy-Sudoku inputs x 3 repeats; warm batch 1",fontsize=12)
    fig.savefig(out/"online_comparison.png",dpi=160);plt.close(fig)
    p=summary[primary];paired=p["paired_vs_full"];lo,hi=paired["relative_mean_reduction_ci95"]
    lock=json.loads((out/"policy_lock.json").read_text(encoding="utf-8"))
    dev=json.loads((out/"development_analysis.json").read_text(encoding="utf-8"))
    lines=["# Phase 2: actual online verified stopping","",
        "**Completed:** October 22, 2026 (America/Toronto).","",
        f'**Primary claim gate: {analysis["decision"]}.** Development-selected policy: **{primary}**, '
        f'schedule {lock["methods"][primary]["levels"]}. Actual mean wall-latency reduction versus full depth '
        f'**{100*paired["relative_mean_reduction"]:.2f}%**, paired 95% interval '
        f'**[{100*lo:.2f}%, {100*hi:.2f}%]**. No component sums are used as online latency.',"",
        "## Entry and completed work","",
        "The original hard Phase 1 no-go, negative R2 screens and easy R3 no-go remain unchanged. The user's explicit "
        "request to unblock and finish Phase 2 authorized a separately frozen online engineering/measurement experiment "
        "despite the unmet opportunity gate. This is not a retrospective offline go. No checkpoint training, "
        "quality relaxation, task change, or Phase 3 final access occurred.","",
        "2A adds an isolated completed-level callback/limit to the actual pinned generate body. The upstream checkout "
        "remains unchanged; a unified patch and exact base/source receipts are saved. Synthetic tests and 192 real "
        "requests over 32 exploration identities establish disabled code/token/text parity, actual one/six-level "
        "forced work, causal observation isolation, offline/online exit-output equivalence and final fallback.","",
        "2B reuses saved development trajectories to select a strong quality-feasible fixed depth and a stability "
        "baseline. It benchmarks four verifier schedules, full depth, fixed depth and stability on 100 development "
        "identities x three repeats, after ten exploration warmups per method. The policy lock was committed/pushed "
        "before final access. 2C evaluates the frozen methods together on the reserved 300 Phase 2 final identities.","",
        "![Actual online comparison](online_comparison.png)","",
        "## Final measured comparison","",
        "| Method | Valid inputs / 300 | Early requests | False early accepts | Wall mean / median / p95 ms | Mean CUDA event elapsed ms | Peak allocated MiB | Mean levels / inspections | Serial warm requests/s |",
        "| --- | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |"]
    for name,s in summary.items():
        wall=" / ".join(f'{s["wall_ms"][k]:.3f}' for k in ("mean","median","p95"))
        lines.append(f'| {name} | {s["valid_inputs"]} | {s["early_requests"]} | {s["false_early_accepts"]} | '
            f'{wall} | {s["gpu_event_elapsed_ms"]["mean"]:.3f} | {s["peak_allocated_bytes"]/1024**2:.2f} | '
            f'{s["generator_levels"]["mean"]:.3f} / {s["inspections"]["mean"]:.3f} | {s["batch1_requests_per_second"]:.3f} |')
    lines+=["","Each method has three repeats per input. Valid-input counts use deterministic, repeat-consistent outputs. "
        "Early requests count all repeats. Final invalid fallback outputs are model failures, not false early accepts. "
        "Independent units/clues validation is recomputed outside request timing. References never enter the online policy.","",
        "| Method | Mean reduction vs full | Paired 95% interval | Quality difference | Quality 95% interval | Gate |",
        "| --- | ---: | --- | ---: | --- | --- |"]
    for name,s in summary.items():
        pair=s["paired_vs_full"];low,high=pair["relative_mean_reduction_ci95"]
        lines.append(f'| {name} | {100*pair["relative_mean_reduction"]:.2f}% | [{100*low:.2f}%, {100*high:.2f}%] | '
                     f'{pair["quality_difference"]:.5f} | {pair["quality_difference_ci95"]} | {s["gate_vs_full"]} |')
    lines+=["","| Method | Reference matches / 300 | Official solved / 300 | Official valid grids / 300 | Official cell accuracy |",
        "| --- | ---: | ---: | ---: | ---: |"]
    for name,item in summary.items():
        accuracy=item["official_cell_accuracy_mean"]
        score="undefined" if accuracy is None else f"{100*accuracy:.2f}%"
        lines.append(f'| {name} | {item["reference_match_inputs"]} | {item["official_solved_inputs"]} | '
                     f'{item["official_valid_grid_inputs"]} | {score} |')
    lines+=["","Secondary official metrics use the pinned decoded-text definitions and do not replace clue-consistent primary validity. "
            "Cell accuracy uses zipped decoded characters; undefined coverage is retained in analysis.",""]
    fixed=analysis["primary_vs_fixed"]
    lines+=["",f'Primary-versus-selected-fixed reduction: {100*fixed["relative_mean_reduction"]:.2f}%, '
        f'interval {[round(100*x,2) for x in fixed["relative_mean_reduction_ci95"]]}; gate **{analysis["primary_fixed_gate"]}**. '
        f'Adaptive frontier claim: **{analysis["adaptive_frontier_claim"]}**.',"",
        "The unchanged claim rule requires >=5% mean wall reduction, lower interval bound >0, zero empirical solve-rate "
        "loss, zero false early accepts, and passed parity/correctness. Intervals use 10,000 paired identity resamples, "
        "seed 20261022, retaining all three repeats. Finite-sample zero errors are not a population guarantee.","",
        "## Development choices and bounded unblocking","",
        f'Selected strong fixed depth: **{dev["selection"]["fixed_depth"]}**. Selected verifier candidate: '
        f'**{dev["selected_verifier"]}**, using actual mean development latency with zero observed quality loss/false '
        "early accepts. Candidates were schedules 1–12, 6–12, 10–12 and 12 only. A level-12-only schedule is a "
        "degenerate checking baseline with no possible generation savings; it is not adaptive headroom.","",
        f'Stability spec: {dev["selection"]["selected_stability"]["spec"]}. It was selected from minimum levels '
        "{2,6,10} and unchanged-transition patience {1,2}, using all 400 development trajectories, zero invalid "
        "early exits/solve loss, and fewest decoded inspections. This uses current/past decoded IDs only. "
        "Decoder-logit uncertainty was absent from the saved study, so an unvalidated entropy baseline was not added. "
        "The retrospective first-valid oracle stays an analysis-only comparison.","",
        "Incremental monitoring lazily adds each available codebook's full-resolution learned/residual contribution "
        "once, rather than recomputing all past contributions at every check. Deferred schedules avoid intermediate "
        "decoder/verifier work. These optimizations preserve exact output and sampling; the measurements determine "
        "whether they help. They cannot create an early valid decoded board.","",
        "| Development method | Mean wall ms | Primary-valid rate | False early accepts |",
        "| --- | ---: | ---: | ---: |"]
    for n,s in dev["online_development"].items():
        lines.append(f'| {n} | {s["wall_ms"]["mean"]:.3f} | {100*s["valid_rate"]:.2f}% | {s["false_early_accepts"]} |')
    lines+=["","## Timing, resource and access limits","",
        "All methods use the same float32/eval checkpoint, batch 1, four CPU threads and deterministic official "
        "sampling on the RTX 5060/WSL pathway, without compilation/autocast/KV caching. Method order rotates by "
        "identity and repeat to balance order effects. Host wall timing synchronizes before/after the ready output "
        "and includes input preparation, generation, incremental reconstruction, decoding, transfers, text, features, "
        "verifier and policy work actually used. There is no diagnostic internal synchronization. Model loading, "
        "warmup, offline references, code diagnostics transfer and serialization are excluded consistently.","",
        "CUDA event elapsed is stream elapsed including host-driven gaps, not kernel-busy time. Two timing events "
        "and non-mutating level/decoder counters are included consistently. Peak allocated bytes are not total "
        "device memory. Serial warm requests/s is reciprocal mean timed request latency, not a batched-throughput "
        "or whole-process claim.","",
        f'Final active methods: {len(lock["methods"])}; final timed requests: {analysis["final_timed_requests"]}; '
        f'exploration-only final warmups: {analysis["warmup_requests"]}. Aliases: {analysis["aliases"]}. '
        "The total phase has hard caps of 6,912 input-generations, 82,400 first-block level evaluations and 45,694 "
        "decoder forwards; actual stage counts are retained in analysis/receipts. Failed attempts must be retained; "
        "no silent model-evaluation retry or input replacement is allowed.","",
        "The original Phase 2 identity reservation is used across difficulty masks because released solution files "
        "are byte-identical. Official full baselines previously scored these rows internally with aggregate-only "
        "analyst inspection. Policies and statistics were frozen before per-input Phase 2 final token/output access; "
        "this is a held-out policy-evaluation subset of the released test data, not a claim of zero prior aggregate "
        "exposure or known absence of base-model contamination. The 300 aligned Phase 3 final rows remain unavailable. "
        "The restricted scanner traverses file structure without materializing unselected token operands.","",
        "## Offline estimate versus measured monitoring","",
        f'Final every-level measured overhead relative to full depth is '
        f'{100*(summary["verified_all"]["wall_ms"]["mean"]/summary["full"]["wall_ms"]["mean"]-1):.2f}%. '
        "R3 estimated 39.31% overhead on easy development using from-scratch monitoring and isolated component "
        "synchronizations. This Phase 2 implementation instead reuses incremental reconstruction and measures a "
        "whole ready-output request on a different cohort. Compare the sign and practical gate, not the numeric "
        "difference as a calibrated speedup or prediction error. Development selected deferred checking to reduce "
        "overhead; level-12-only checking cannot save generator work.","",
        "Input-integrity verification reuses R2's identity-only hashing of all puzzle rows, including reserved "
        "operands, without retaining those token rows/boards. The restricted inference/scoring reader materializes "
        "only the selected Phase 2 final rows and skips Phase 3 token operands. No per-input Phase 3 board, "
        "reference or prediction is inspected. Prior aggregate exposure is disclosed above.","",
        "The 2A patch emitter initially omitted Git's no-final-newline marker. A format-only finalizer retained "
        "the initial artifact and corrected the recorded diff; git apply --check passed. The tested online engine "
        "and all model outputs were unchanged, with zero added model evaluations.","",
        "## Evidence and reproduction","",
        "[Protocol](../../docs/studies/phase2-easy-online-protocol.md), [upstream patch](upstream_level_hook.patch.txt), "
        "[2A receipt](2a.json), [2B receipt](2b.json), [2C receipt](2c.json), [policy lock](policy_lock.json), "
        "[committed lock release](policy_lock_release.json), [holdout access](holdout_access.json), "
        "[analysis](analysis.json), [completion](completion.json), [report provenance](report_provenance.json).","",
        "~~~powershell",".\\scripts\\wsl_python.ps1 -PythonArguments @('scripts/run_phase2.py','verify')","~~~","",
        "Saved-data verification recomputes labels, selections, paired summaries/bootstrap/gates and checks work "
        "counts, frozen lock/access, source snapshots and artifact hashes without torch/matplotlib imports. "
        "It does not replay GPU parity. All model-evaluation budgets are consumed; reporting reuses saved records.","",
        "Phase 2 is complete as an online engineering/measurement experiment. A negative outcome provides no "
        "practical-speedup claim or automatic learned-controller work. Phase 3 requires a separate headroom "
        "justification and work order; its final set remains reserved.",""]
    (out/"summary.md").write_text("\n".join(lines),encoding="utf-8",newline="\n")
