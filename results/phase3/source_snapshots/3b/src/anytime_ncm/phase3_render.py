"""Saved-data scientific report and standalone comparison figure."""
import json
from anytime_ncm.phase3 import OUTPUT

def render(root,a):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    out=root/OUTPUT;training=json.loads((out/"training.json").read_text(encoding="utf-8"))
    methods=list(a["summary"]);summ=a["summary"];primary=summ[a["primary_method"]]
    fig,axes=plt.subplots(1,3,figsize=(18,5),layout="constrained")
    labels=[m.replace("_"," ") for m in methods];colors=["#d55e00" if m=="learned_internal" else "#0072b2" for m in methods]
    for ax,values,label in zip(axes,([summ[m]["wall_ms"]["mean"] for m in methods],
         [summ[m]["valid_rate"]*100 for m in methods],[summ[m]["generator_levels"]["mean"] for m in methods]),
         ("Mean actual request wall latency (ms)","Primary-valid inputs (%)","Mean generator levels")):
        ax.bar(labels,values,color=colors);ax.set_ylabel(label);ax.tick_params(axis="x",rotation=30);ax.set_ylim(bottom=0)
        ax.grid(axis="y",alpha=.2)
    fig.suptitle("Phase 3: 300 reserved easy-Sudoku inputs x 3 repeats; warm batch 1")
    fig.savefig(out/"comparison.png",dpi=130);plt.close(fig)
    p=primary["paired_vs_full"];ci=p["relative_mean_reduction_ci95"]
    lines=["# Phase 3: learned stopping on easy Sudoku","",
      "**Completed:** October 22, 2026 (America/Toronto).","",
      f"**Practical-speedup gate: {a['decision']}.** Primary: learned_internal. Mean wall reduction versus full depth {100*p['relative_mean_reduction']:.2f}%, paired 95% interval [{100*ci[0]:.2f}%, {100*ci[1]:.2f}%]. Strong fixed-depth gate: **{a['primary_fixed_gate']}**. Adaptive-frontier claim: **{a['adaptive_frontier_claim']}**.","",
      "## Work order and entry","",
      "The user explicitly requested finishing Phase 3 regardless of the negative headroom evidence. This separately frozen experiment completes that request without relabeling Phase 1/R2/R3/Phase 2 as go. No new positive early-output opportunity was assumed. No checkpoint training, task change, quality relaxation or paid compute was used.","",
      "## Training, selection and causal contract","",
      "Six standardized logistic regressions were fit on 1,000 exploration identities / 12,000 level states, using current solution validity as the sufficiency target. Positive pre-final training/development states: "+str(training["positive_pre_final_states"])+". Training positives: "+str(training["training_positive_states"])+"; development positives: "+str(training["development_positive_states"])+". The shortage of positive early labels limits what the learner can learn; high pooled prediction quality may primarily reflect level number.","",
      "Base features are level/code counts, input clue density, decoded token histogram, change from the previous inspected output and its availability. Internal adds current codebook histogram/entropy/concentration/distinctness/adjacent changes. These are discrete code statistics, not hidden activations or logits. Neither model receives unit/clue validity flags, solutions, references, future outputs or sample identity. Input clue density is Sudoku-specific, so this is not a task-general result.","",
      "Exploration alone supplies normalization and fitting. C is selected on all 400 development trajectories by current-state log loss. Threshold/minimum selection uses the declared family and requires zero invalid early exits and no solve loss, then fewest mean inspections. Normalization never sees either final split. Fitting uses consecutive observations; the deployed tracker uses its selected inspection history. Per-schedule calibration is reported separately.","",
      "| Model | Selected C | Inspection minimum | Threshold | Development mean inspections |","| --- | ---: | ---: | ---: | ---: |"]
    for family,s in training["selected"].items():
        lines.append(f"| {family} | {s['model']['C']} | {s['minimum']} | {s['threshold']} | {s['mean_inspections']:.3f} |")
    lines+=["","All candidate coefficients, normalization, convergence iterations, losses, reliability bins and policy choices are retained in [training.json](training.json). Development online benchmarking adds no model/threshold candidates. Policies were committed/pushed before Phase 3 final access.","",
      "## Final measured comparison","","![Measured final comparison](comparison.png)","",
      "| Method | Valid inputs | Early requests | Invalid early accepts | Wall mean / median / p95 ms | CUDA event mean ms | Peak allocated MiB | Mean levels / inspections | Serial warm requests/s |",
      "| --- | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |"]
    for m,s in summ.items():
        w=s["wall_ms"]
        lines.append(f"| {m} | {s['valid_inputs']}/300 | {s['early_requests']} | {s['false_early_accepts']} | {w['mean']:.3f} / {w['median']:.3f} / {w['p95']:.3f} | {s['gpu_event_elapsed_ms']['mean']:.3f} | {s['peak_allocated_bytes']/1048576:.2f} | {s['generator_levels']['mean']:.3f} / {s['inspections']['mean']:.3f} | {s['batch1_requests_per_second']:.3f} |")
    lines+=["","| Method | Mean wall reduction vs full | Paired 95% interval | Quality difference | Quality 95% interval | Gate |",
        "| --- | ---: | --- | ---: | --- | --- |"]
    for m,s in summ.items():
        p=s["paired_vs_full"];ci=p["relative_mean_reduction_ci95"]
        lines.append(f"| {m} | {100*p['relative_mean_reduction']:.2f}% | [{100*ci[0]:.2f}%, {100*ci[1]:.2f}%] | {p['quality_difference']:.5f} | {p['quality_difference_ci95']} | {s['gate_vs_full']} |")
    f=a["primary_vs_fixed"]
    lines+=["",f"Primary versus selected fixed reduction: {100*f['relative_mean_reduction']:.2f}%; paired interval {[round(100*x,3) for x in f['relative_mean_reduction_ci95']]}. The fixed comparator was selected using development, not final outcomes.","",
      "The claim rule requires >=5% mean wall reduction, lower paired interval >0, zero empirical solve loss and zero invalid early accepts with correctness/parity passed. Both full and strong fixed comparisons must pass for a frontier claim. Statistics use 10,000 paired identity bootstrap resamples, seed 20261022, retaining all three repeats. Finite-sample zero errors do not guarantee population correctness.","",
      "## Calibration and internal-feature ablation","",
      "| Model | Inspected states (repeat 0) | Brier / paired-cluster 95% interval | Log loss / cluster 95% interval | Mean included feature+score CPU ms/request |",
      "| --- | ---: | --- | --- | ---: |"]
    for m,c in a["calibration"].items():
        lines.append(f"| {m} | {c['states']} | {c['brier']:.6f} / {c['brier_ci95']} | {c['log_loss']:.6f} / {c['log_loss_ci95']} | {c['mean_feature_policy_cpu_ms']:.4f} |")
    lines+=["","These probabilities concern CURRENT validity at the deployed inspection levels. Repeat 0 supplies calibration states; all repeats supply latency. Reliability-bin counts, mean scores and valid rates are retained in analysis. Identity cluster resampling keeps all inspected states together. No extra final decoding was done to fill uninspected levels. Feature+score CPU timing excludes GPU reconstruction/decoding and code/token transfers; all of those are included in actual request latency.","",
      "The internal ablation compares only the stated discrete-code statistics with the stated decoded/input features. It does not test all transformer statistics, establish cross-task H3, or manufacture early-positive training labels. "+str(a.get("internal_ablation",{})),"",
      "## Predeclared clue-count subgroups","",
      "| Subgroup | Inputs | Full valid | Internal valid | Full mean ms | Internal mean ms |","| --- | ---: | ---: | ---: | ---: | ---: |"]
    for name,g in a["subgroups"].items():
        full=g["methods"]["full"];internal=g["methods"]["learned_internal"]
        fm="unavailable" if full["mean_wall_ms"] is None else f"{full['mean_wall_ms']:.3f}"
        im="unavailable" if internal["mean_wall_ms"] is None else f"{internal['mean_wall_ms']:.3f}"
        lines.append(f"| {name} | {g['identities']} | {full['valid_inputs']} | {internal['valid_inputs']} | {fm} | {im} |")
    lines+=["","Subgroups are descriptive and were fixed at <=27 versus >27 input clues before final access. They do not tune policies or create additional confirmatory claims.","",
      "## Execution, access and limitations","",
      "The model checkpoint/weights/buffers and upstream checkout stay unchanged. Real development requests match saved R3 exit codes/outputs and causal scores. Synthetic small-generator tests separately exercise actual learned early stops, fallback and future/reference isolation. Three repeats per final input are checked for identical outputs; labels are independently recomputed from Sudoku units and clues outside request timing.","",
      "Headline timing uses matched synchronized ready-output wall boundaries, float32/eval, batch 1 and four CPU threads on the RTX 5060/WSL pathway. It includes input preparation, generation, reconstruction, decoding, necessary transfers, learned features/scoring and policy callbacks. Loading, exploration warmups, reference scoring, diagnostic code transfer and serialization are excluded. CUDA event elapsed includes host-driven gaps and is not kernel-busy time. Peak allocated bytes are not total device memory. Requests/s is reciprocal serial warm mean latency, not batched throughput. Included counters/events and CPU submeasurement timers add instrumentation overhead.","",
      f"Development: 2,100 timed requests +70 exploration warmups. Final: {a['timed_requests']} timed requests +70 exploration warmups. Final actual counts: {a['counts']}. Predeclared total caps: 8,540 input-generations / 102,480 levels / 63,440 decoder forwards / zero encodings. No model evaluation retry, extra seed, sample replacement, policy retuning or post-final calibration fit is permitted.","",
      "The inherited reserved phase3_final subset contains 300 easy-mask identities; it has now been used. Related difficulty masks share solution rows; exploration/development exposure and prior full-baseline aggregates were disclosed before access. Identity hashing traverses all reserved operands without retaining boards. The restricted inference/scoring reader opens only the selected final subset and exploration warmups; phase2_final is not used for training/selection or this evaluation. Unknown base-model overlap and shared difficulty views prevent an entirely untouched official-test claim.","",
      "Saved checkpoints cannot be altered by a stopping policy. With no useful early outputs, a learned classifier can only preserve full generation while adding monitoring cost, or risk invalid early accepts. The measured result is specific to this frozen setting, feature family, threshold grid and sample; it does not prove a population impossibility. Phase 3 is complete as a positive-or-negative experiment. No automatic Phase 4 work is authorized.","",
      "## Evidence and reproduction","",
      "[Protocol](../../docs/studies/phase3-easy-learned-protocol.md), [training](training.json), [3A receipt](3a.json), [development](development_analysis.json), [3B receipt](3b.json), [policy lock](policy_lock.json), [lock release](policy_lock_release.json), [access](holdout_access.json), [3C receipt](3c.json), [analysis](analysis.json), [completion](completion.json), [provenance](report_provenance.json).","",
      "~~~powershell",".\\scripts\\wsl_python.ps1 -PythonArguments @('scripts/run_phase3.py','verify')","~~~","",
      "Saved-data verification recomputes causal scores, labels, calibration, development selection, paired metrics/intervals and gates without torch/matplotlib imports. It checks execution snapshots, input/output hashes and work caps; it does not replay GPU parity. Model-work budgets are consumed; do not rerun 3a/3b/3c to reproduce a report.",""]
    (out/"summary.md").write_text("\n".join(lines),encoding="utf-8",newline="\n")
