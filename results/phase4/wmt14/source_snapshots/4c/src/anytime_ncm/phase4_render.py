"""Source-backed WMT14 quality/latency report and standalone research figures."""
import html,json
from anytime_ncm.phase4 import OUTPUT,examples
from anytime_ncm.phase2 import load_rows,save

def render(root,a):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from sacrebleu.metrics import CHRF
    out=root/OUTPUT;audit=json.loads((out/"audit_analysis.json").read_text())
    baseline=json.loads((out/"official_full.json").read_text())
    dev=json.loads((out/"development_analysis.json").read_text())
    lock=json.loads((out/"policy_lock.json").read_text())
    methods=list(a["summary"]);s=a["summary"];primary=s["adaptive"]
    fig,axes=plt.subplots(1,3,figsize=(16,5),layout="constrained")
    for ax,vals,label in zip(axes,([s[m]["wall_ms"]["mean"] for m in methods],
         [s[m]["quality"]["bleu"] for m in methods],[s[m]["quality"]["chrf"] for m in methods]),
         ("Mean ready-output wall latency (ms)","Corpus BLEU","Corpus chrF")):
        ax.bar(methods,vals,color=["#d55e00" if m=="adaptive" else "#0072b2" for m in methods])
        ax.set_ylabel(label);ax.grid(axis="y",alpha=.2);ax.set_ylim(bottom=0)
    fig.suptitle("Phase 4 WMT14: 256 assigned final inputs x 3 repeats; batch 1")
    fig.savefig(out/"comparison.png",dpi=140);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(11,4),layout="constrained")
    for ax,name in zip(axes,("bleu","chrf")):
        for part in ("exploration","development"):
            ax.plot(range(1,12),[x[name] for x in audit["partitions"][part]["quality_by_level"]],marker="o",label=part)
        ax.set_xlabel("Completed generator level");ax.set_ylabel("Corpus "+name);ax.set_xticks(range(1,12));ax.legend();ax.grid(alpha=.2)
    fig.savefig(out/"quality_by_level.png",dpi=140);plt.close(fig)
    trajectories=load_rows(out/"trajectories.jsonl")
    exploration=[r for r in trajectories if r["partition"]=="exploration"]
    es={e["identity"]:e for e in examples(root,"audit_exploration")}
    metric=CHRF();transitions=[]
    for r in exploration:
        ref=es[r["identity"]]["reference"]
        values=[metric.sentence_score(x["text"],[ref]).score for x in r["levels"]]
        for level in range(1,11):transitions.append((values[level]-values[level-1],r["index"],level,r))
    selected=[("first exploration inputs",r,None) for r in sorted(exploration,key=lambda r:r["index"])[:3]]
    if transitions:
        for label,t in (("largest sentence-chrF improvement",min(transitions,key=lambda x:(-x[0],x[1],x[2]))),
                         ("largest sentence-chrF damage",min(transitions,key=lambda x:(x[0],x[1],x[2])))):
            selected.append((label,t[3],{"from":t[2],"to":t[2]+1,"sentence_chrf_difference":t[0]}))
    def excerpt(text):
        words=text.split();return " ".join(words[:15])+(" ..." if len(words)>15 else "")
    example_rows=[]
    for label,r,t in selected:
        e=es[r["identity"]]
        example_rows.append({"selection":label,"index":r["index"],"source":excerpt(e["source"]),"reference":excerpt(e["reference"]),"source_reference_are_excerpts":True,
             "transition":t,"levels":r["levels"]})
    save(out/"examples.json",example_rows)
    lines=["# Phase 4: WMT14 German-to-English generalization","",
      "**Completed:** October 23, 2026 (America/Toronto).","",
      f"**Primary practical-speedup gate: {a['decision']}.** Strong fixed-depth gate: **{a['primary_vs_fixed']['gate']}**. Adaptive-frontier claim: **{a['adaptive_frontier_claim']}**.","",
      "## Scope and task-grounded baseline","",
      "This explicitly requested phase evaluates the released WMT14 De-En checkpoint, not XSum. It preserves all earlier Sudoku results and stops before Phase 5. No checkpoint/controller training, paid compute, sampling change or task-general correctness verifier was introduced.","",
      f"The verbatim pinned official prefix/pick_tokens/dec/run bodies reproduce all {baseline['rows']} released rows at batch 8 (release default 64, predeclared memory override). Cased BLEU **{baseline['metrics']['bleu']:.3f}**, lowercase BLEU **{baseline['metrics']['bleu_lowercase']:.3f}**, chrF **{baseline['metrics']['chrf']:.3f}**. This is an operational released-checkpoint reproduction; exact paper-number or default-batch parity is not claimed. Whole baseline duration includes loading/processing and is not warm request latency.","",
      "The pre-tokenizer is pinned Qwen/Qwen3-0.6B tokenizer data only; its language-model weights were not downloaded. The NCM generator predicts 11 code levels (1,4,8,14,20,26,32,40,48,56,64), 313 code positions. The source is truncated/padded to 96 token IDs and the decoder emits 64 target IDs before official EOS truncation/special-token filtering. Learned L1 cascade upsampling, intermediate GroupNorm and residual transforms are preserved. These semantics differ from Sudoku and were independently tested.","",
      "## Frozen allocation, metrics and tolerances","",
      "All 3,003 effective padded source-prefix identities were distinct. The input-only manifest allocates 512 exploration groups, 256 development, 256 phase4_final and 1,979 reserved/unused groups. First 32 official rows belong to exploration. The offline audit uses 128 exploration and 64 development groups; the final comparison uses all 256 assigned final groups. No reference is used for partitioning. The official full baseline had prior internal final-reference scoring with aggregate-only analyst access; unknown base-model overlap remains. This is a reserved policy-evaluation subset, not an entirely untouched official test set.","",
      "Cased corpus BLEU and corpus chrF use pinned sacreBLEU defaults matching upstream. Maximum acceptable empirical losses versus full depth are **0.5 BLEU** and **1.0 chrF point** on their 0–100 scales. Final support requires paired quality lower interval bounds within both margins, >=5% mean ready-output latency reduction with lower interval >0, and disclosed heuristic guardrails. A frontier claim must also beat the strong development-selected fixed depth at matched quality. Quality/latency uncertainty is retained; an inconclusive result is not relabeled success.","",
      "Numeric reference F1 uses literal English digit-number sets only where references contain digit numbers. Negation cue mismatch uses no/not/never/neither/without/n't presence. These are heuristic diagnostics and causal transition guards, not factual/polarity truth labels. Written numbers, punctuation formats, paraphrases, not-only constructions and source/reference disagreement can produce misses or false flags. No semantic-equivalence or factual-consistency guarantee follows from BLEU/chrF or these cues.","",
      "## Offline full-resolution quality and non-monotonicity","","![Quality by completed level](quality_by_level.png)","",
      "| Level | Exploration BLEU | Exploration chrF | Development BLEU | Development chrF |",
      "| --- | ---: | ---: | ---: | ---: |"]
    for k in range(11):
        e=audit["partitions"]["exploration"]["quality_by_level"][k];d=audit["partitions"]["development"]["quality_by_level"][k]
        lines.append(f"| {k+1} | {e['bleu']:.3f} | {e['chrf']:.3f} | {d['bleu']:.3f} | {d['chrf']:.3f} |")
    lines+=["","| Development transition | Sentence-chrF improves | Damages | Unchanged | Mean sentence-chrF change |",
       "| --- | ---: | ---: | ---: | ---: |"]
    for t in audit["partitions"]["development"]["adjacent_sentence_chrf"]:
        lines.append(f"| {t['from']} to {t['to']} | {t['improved']} | {t['damaged']} | {t['unchanged']} | {t['mean_sentence_chrf_change']:.3f} |")
    dpart=audit["partitions"]["development"]
    damages=sum(t["damaged"] for t in dpart["adjacent_sentence_chrf"])
    lines+=["",f"Development has {damages}/{10*dpart['inputs']} adjacent sentence-chrF deteriorations despite improving corpus quality. These are reference-metric deteriorations, not verified factual errors."]
    fallback_note=("Both selected adaptive families inspect only levels 10 and 11. The first inspection cannot stop, so these are degenerate full-depth fallbacks with no possible early-generation savings, not demonstrated adaptive headroom." if all(lock["methods"][m]["minimum"]==10 for m in ("stability","adaptive")) else "The selected inspection schedules are fixed using development only.")
    lines+=["","Transition direction uses sentence chrF as an offline reference-based diagnostic. It is distinct from corpus chrF/BLEU and does not become an inference feature. The retrospective best-prefix quality is an offline oracle, not a deployable policy. Full trajectories and all targeted per-level metrics are retained in the audit artifacts.","",
      "## Development policy choices","",
      f"Strong fixed depth: **{lock['methods']['fixed']['depth']}**. Stability: {lock['methods']['stability']}. Primary guarded stability: {lock['methods']['adaptive']}.","",
      fallback_note,"",
      "All 11 fixed depths and 36 adaptive candidates are retained. Development uses point quality/heuristic margins; selection minimizes inspected decodes, then generated levels using the declared tie breaks. First observation cannot stop, and level 11 is unconditional fallback. Guarded stability additionally requires unchanged current/previous digit-number and negation cues. No reference, future output, metric, oracle label or sample identity enters online decisions. Online development timings do not expand or retune the candidate family. Selection uses the predeclared inspection-count proxy, not an exhaustive measured-latency search over all possible adaptive policies.","",
      "| Development method | Mean wall ms | BLEU | chrF | Early timed requests |","| --- | ---: | ---: | ---: | ---: |"]
    for m,d in dev["summary"].items():lines.append(f"| {m} | {d['wall_ms']['mean']:.3f} | {d['quality']['bleu']:.3f} | {d['quality']['chrf']:.3f} | {d['early_requests']} |")
    lines+=["","## Frozen final comparison","","![Final quality and actual cost](comparison.png)","",
      "| Method | BLEU | chrF | Wall mean / median / p95 ms | Mean levels / inspections | Early timed requests | Peak allocated MiB | Serial warm requests/s |",
      "| --- | ---: | ---: | --- | --- | ---: | ---: | ---: |"]
    for m,d in s.items():
        w=d["wall_ms"];q=d["quality"]
        lines.append(f"| {m} | {q['bleu']:.3f} | {q['chrf']:.3f} | {w['mean']:.3f} / {w['median']:.3f} / {w['p95']:.3f} | {d['mean_levels']:.3f} / {d['mean_inspections']:.3f} | {d['early_requests']} | {d['peak_allocated_bytes']/1048576:.2f} | {d['serial_warm_requests_per_second']:.3f} |")
    lines+=["","| Method | Mean latency reduction vs full | Paired 95% interval | BLEU difference / 95% interval | chrF difference / 95% interval | Gate |",
       "| --- | ---: | --- | --- | --- | --- |"]
    for m,d in s.items():
        t=d["timing_vs_full"];b=d["quality_vs_full"]["bleu"];c=d["quality_vs_full"]["chrf"]
        ci=t["relative_mean_reduction_ci95"]
        lines.append(f"| {m} | {100*t['relative_mean_reduction']:.2f}% | [{100*ci[0]:.2f}%, {100*ci[1]:.2f}%] | {b['difference']:.3f} / {[round(x,3) for x in b['ci95']]} | {c['difference']:.3f} / {[round(x,3) for x in c['ci95']]} | {d['gate']} |")
    fixed=a["primary_vs_fixed"];t=fixed["timing"]
    lines+=["",f"Primary versus selected fixed mean reduction: {100*t['relative_mean_reduction']:.2f}%, paired interval {[round(100*x,3) for x in t['relative_mean_reduction_ci95']]}; quality differences/intervals are retained in analysis. Gate: **{fixed['gate']}**.","",
      "| Method | Reference-number F1 | References with digit numbers | Negation-cue mismatch rate | Mean CUDA stream elapsed ms |",
      "| --- | ---: | ---: | ---: | ---: |"]
    for m,d in s.items():
        q=d["quality"];nf="unavailable" if q["numeric_reference_f1"] is None else f"{q['numeric_reference_f1']:.4f}"
        lines.append(f"| {m} | {nf} | {q['numeric_reference_coverage']} | {q['negation_cue_mismatch_rate']:.4f} | {d['gpu_elapsed_ms_mean']:.3f} |")
    conclusion=("These bounded data support the predeclared adaptive frontier claim at the stated metric tolerances." if a["adaptive_frontier_claim"] else
       "This bounded WMT comparison does not establish a practical adaptive frontier advantage under the predeclared quality/cost rule.")
    lines+=["","## What transfers from Sudoku","",conclusion+" Unlike Sudoku, translation quality is graded and there is no cheap exact acceptance predicate here. The audit measures when later levels improve or damage reference-based quality, while the final experiment charges actual monitoring cost. The Sudoku absence of early exact solutions cannot be treated as a universal statement about language generation; equally, approximate metric similarity cannot establish semantic correctness or safety.","",
      "## Deterministic exploration examples","",
      "The first three exploration inputs and the largest adjacent sentence-chrF improvement/damage are chosen by the frozen rule (ties by index then level). These are diagnostics, not policy inputs. Source/reference excerpts, indices and all generated levels are saved in [examples.json](examples.json); full pinned inputs remain in the local dataset files."]
    for e in example_rows:
        lines+=["",f"**{e['selection']}; source index {e['index']}**"+(f"; transition {e['transition']}" if e["transition"] else ""),""]
        for label,text in (("Source",e["source"]),("Reference",e["reference"]),("Level 1",e["levels"][0]["text"]),("Full depth",e["levels"][-1]["text"])):
            text=html.escape(text).replace("\n"," ").replace(chr(96),"'")
            lines.append("> "+label+": "+text[:700])
    lines+=["","## Timing, provenance and limitations","",
      "All methods use the same frozen float32/eval checkpoint, pinned tokenizer, top-k1/top-p0 sampling, batch 1 and four CPU threads on RTX 5060/WSL2. Each request includes source tokenization, context transfer, generation, full-resolution reconstruction, decoding, transfers, text and actual features/policy. Request-boundary synchronization and algorithm-required transfers are included; no diagnostic per-stage synchronization is inserted. Loading, exploration warmups, offline reference scoring, diagnostic code transfer and serialization are excluded. Balanced cyclic ordering and three repeats are recorded. CUDA event elapsed includes host gaps, not kernel-busy time. Peak allocation is not total GPU memory; reciprocal serial latency is not batched throughput.","",
      "Quality intervals use 10,000 paired identity resamples (seed 20261023) with exact sacreBLEU sufficient-statistic reconstruction, checked against direct corpus scoring. All three latency repeats remain together in timing resamples. Quality uses repeat 0 after deterministic output consistency checks. This is one fixed allocation and finite checkpoint/task/sample, not multi-seed or multi-task confirmation.","",
      "The official batch-8 baseline and batch-one study are distinct; 32 matched batch-one official/disabled-hook requests establish exact codes/tokens/text parity, and all 192 audit reconstructions match independent learned-cascade arithmetic. Development requests match offline exits/prefixes. Per-stage source snapshots and model fingerprints preserve execution versions and unchanged weights/buffers. Synthetic tests separately prove actual forced generator skipping and future-code isolation.","",
      f"Final actual counts: {a['counts']}; final timed requests {a['timed_requests']} plus {a['warmup_requests']} exploration warmups. Total predeclared Phase 4 caps:7,163 generations /78,793 sample-weighted generator levels /28,603 decoder forwards /zero full encoder forwards. Raw-prefix encoder embedding lookups still occur. Model evaluation failures/retries, if any, must remain recorded; budgets cannot silently expand.","",
      "The full official baseline exposed aggregates for all released test examples before policy work; training-data contamination is unknown. Only assigned final groups are opened for the frozen final comparison; remaining groups stay unavailable to study policy selection. Reusing the evaluated final subset later cannot support an untouched-test claim. Numbers/negation cues and BLEU/chrF do not provide factual-consistency guarantees. Prior Sudoku metrics, checkpoints, protocols and negative findings remain unchanged. Phase 5 has not started.","",
      "## Evidence and reproduction","",
      "[Protocol](../../../docs/studies/phase4-wmt14-protocol.md), [sources](../../../configs/phase4_wmt_sources.json), [manifest](../../../docs/partitions/wmt14-phase4.json), [preflight](preflight.json), [official baseline](official_full.json), [4A receipt](4a.json), [audit](audit_analysis.json), [4B receipt](4b.json), [development](development_analysis.json), [policy lock](policy_lock.json), [lock release](policy_lock_release.json), [access](holdout_access.json), [4C receipt](4c.json), [analysis](analysis.json), [completion](completion.json), [report provenance](report_provenance.json).","",
      "~~~powershell",".\\scripts\\wsl_python.ps1 -PythonArguments @('scripts/run_phase4.py','verify')","~~~","",
      "Verification recomputes selection, causal exits, quality, paired statistics, counts and hashes from saved records without torch/matplotlib imports; pinned local artifacts are still required. It does not replay model inference. The allocation is consumed; do not rerun 4a/4b/4c to reproduce a report.",""]
    (out/"summary.md").write_text("\n".join(lines),encoding="utf-8",newline="\n")
