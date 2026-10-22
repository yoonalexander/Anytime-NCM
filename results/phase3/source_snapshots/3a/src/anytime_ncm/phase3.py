"""Phase 3 bounded receipts, restricted access, training/evaluation analysis."""
from datetime import datetime,timezone
import json,math
from pathlib import Path
from anytime_ncm.dataset import Example,_TokenRows,puzzle_identity,sha256
from anytime_ncm.screening import require
from anytime_ncm.phase2 import save,load_rows,inputs as phase2_inputs,policy_spec,verify_request
from anytime_ncm.learned_features import offline_trace,probability
from anytime_ncm.sudoku import validate_solution
from anytime_ncm.report import independent_valid

OUTPUT="results/phase3"
PROTOCOL="docs/studies/phase3-easy-learned-protocol.md"
SOURCES=(PROTOCOL,"src/anytime_ncm/phase3.py","src/anytime_ncm/train_policy.py",
 "src/anytime_ncm/learned_features.py","src/anytime_ncm/learned_online.py",
 "src/anytime_ncm/phase3_run.py","src/anytime_ncm/phase3_render.py","scripts/run_phase3.py",
 "tests/test_learned_policy.py","tests/test_policy_no_future_leakage.py",
 "src/anytime_ncm/online.py","src/anytime_ncm/online_policy.py","src/anytime_ncm/phase2.py",
 "src/anytime_ncm/phase2_run.py","src/anytime_ncm/dataset.py","src/anytime_ncm/sudoku.py",
 "src/anytime_ncm/report.py","src/anytime_ncm/screening_inference.py",
 "src/anytime_ncm/upstream_adapter.py","src/anytime_ncm/target_encoding.py",
 "third_party/ncm/models/next_concept.py","third_party/ncm/models/quant.py","third_party/ncm/models/vqvae.py")
LIMITS={"3a":dict(inputs=0,generator_levels=0,decoder=0,encoder=0),
 "3b":dict(inputs=2170,generator_levels=26040,decoder=16120,encoder=0),
 "3c":dict(inputs=6370,generator_levels=76440,decoder=47320,encoder=0)}

def source_hashes(root):return {p:sha256(root/p) for p in SOURCES}
def pinned(root):
    return {**phase2_inputs(root),
        **{p:sha256(root/p) for p in ("results/phase2/development_analysis.json","results/phase2/policy_lock.json",
            "results/phase2/completion.json","results/followup/sudoku_easy_r3/completion.json")}}
def select_entries(manifest,stage,released=False):
    allowed={"train":("exploration",1000),"development":("development",400),
             "3b":("development",100),"warmup":("exploration",10),"3c":("phase3_final",300)}
    if stage not in allowed:raise ValueError("Unknown/restricted Phase 3 access.")
    if stage=="3c" and not released:raise ValueError("Final access requires a released policy lock.")
    name,count=allowed[stage]
    rows=sorted(manifest["partitions"][name],key=lambda r:r["index"])
    require(len(rows)>=count,"Missing reserved identities.")
    return [dict(r,partition=name) for r in rows[:count]]
def examples(root,stage):
    release=checked_lock(root) if stage=="3c" else None
    manifest=json.loads((root/"docs/partitions/sudoku-easy-r2.json").read_text(encoding="utf-8"))
    entries=select_entries(manifest,stage,release is not None);indices={r["index"] for r in entries}
    data=[_TokenRows((root/("data/sudoku/easy/"+name)).read_bytes()).select(indices,length,2000)
          for name,length in (("puzzles.pickle",91),("solutions.pickle",89))]
    result=[]
    for r in entries:
        i=r["index"];puzzle=data[0][i];reference=data[1][i]
        require(puzzle_identity(puzzle)==r["puzzle_sha256"],"Selected identity differs.")
        require(validate_solution(puzzle,reference).is_valid_solution,"Bad selected reference.")
        result.append(Example(i,r["partition"],r["puzzle_sha256"],puzzle,reference))
    return tuple(result)

def begin(root,stage):
    out=root/OUTPUT;out.mkdir(parents=True,exist_ok=True);path=out/(stage+".json")
    require(not path.exists(),"Stage already attempted; no silent retry.")
    hashes=source_hashes(root);snapshot=out/"source_snapshots"/stage
    for name in hashes:
        p=snapshot/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((root/name).read_bytes())
    r={"study":"Phase 3","stage":stage,"status":"started","started_utc":datetime.now(timezone.utc).isoformat(),
       "entry_exception":"explicit user request despite negative headroom gate",
       "source_sha256":hashes,"source_snapshot":snapshot.relative_to(root).as_posix(),
       "inputs_sha256":pinned(root),"limits":LIMITS[stage],"counts":dict.fromkeys(LIMITS[stage],0),
       "completed_requests":0,"artifacts_sha256":{}}
    save(path,r);return out,path,r
def finish(out,path,record,names):
    record.update(status="complete",finished_utc=datetime.now(timezone.utc).isoformat(),
                  artifacts_sha256={n:sha256(out/n) for n in names})
    save(path,record)
def failed(path,record,error):
    record.update(status="failed",error=repr(error),finished_utc=datetime.now(timezone.utc).isoformat());save(path,record)
def verify_stage(root,stage):
    out=root/OUTPUT;r=json.loads((out/(stage+".json")).read_text(encoding="utf-8"))
    require(r["status"]=="complete" and r["limits"]==LIMITS[stage],"Incomplete/changed stage.")
    require(all(type(v)is int and 0<=v<=LIMITS[stage][k] for k,v in r["counts"].items()),"Work cap differs.")
    for n,h in r["source_sha256"].items():require(sha256(root/r["source_snapshot"]/n)==h,"Execution snapshot changed.")
    for n,h in r["inputs_sha256"].items():require(sha256(root/n)==h,"Pinned input changed.")
    for n,h in r["artifacts_sha256"].items():require(sha256(out/n)==h,"Stage artifact changed.")
    if stage!="3a":require(r["state_before"]==r["state_after"],"Model state changed.")
    return r
def checked_lock(root):
    out=root/OUTPUT;verify_stage(root,"3a");verify_stage(root,"3b")
    lock=json.loads((out/"policy_lock.json").read_text(encoding="utf-8"))
    require(lock["status"]=="frozen" and lock["source_sha256"]==source_hashes(root),"Execution lock changed.")
    for n,h in lock["artifacts_sha256"].items():require(sha256(out/n)==h,"Policy lock artifact changed.")
    release=json.loads((out/"policy_lock_release.json").read_text(encoding="utf-8"))
    require(release["github_main"]==release["local_head"] and release["working_lock_matches_committed_blob"]
        and release["policy_lock_sha256"]==sha256(out/"policy_lock.json"),"Unreleased policy lock.")
    return lock
def selected_methods(root):
    out=root/OUTPUT;training=json.loads((out/"training.json").read_text(encoding="utf-8"))
    old=json.loads((root/"results/phase2/development_analysis.json").read_text(encoding="utf-8"))
    methods={name:old["final_methods"][name] for name in ("full","fixed","verified_all","verified_selected","stability")}
    for family in ("base","internal"):
        chosen=training["selected"][family]
        methods["learned_"+family]={"kind":"learned","model":chosen["model"],
                                   "minimum":chosen["minimum"],"threshold":chosen["threshold"]}
    return methods

def verify_row(row,e,spec,offline=None):
    verify_request(row,e,spec)
    require(independent_valid(e.puzzle,row["decoded_ids"])==row["valid"],"Independent validity differs.")
    if spec["kind"]=="learned":
        from anytime_ncm.learned_features import FeatureTracker,LENGTHS
        tracker=FeatureTracker(e.puzzle,spec["model"]["family"]);trace=row["learned_trace"]
        require([t["level"] for t in trace]==list(range(spec["minimum"],row["exit_level"]+1)),"Missing inspection.")
        require(row["decoder_forwards"]==len(trace) and row["inspected_levels"]==[t["level"] for t in trace],"Learned decode count differs.")
        for t in trace:
            level=t["level"];end=sum(LENGTHS[:level]);start=end-LENGTHS[level-1]
            f=tracker.observe(level,t["decoded_ids"],row["generated_codes"][start:end])
            require(list(f)==t["features"] and abs(probability(spec["model"],f)-t["probability"])<1e-12,"Causal score differs.")
            require(math.isfinite(t["feature_policy_ms"]) and t["feature_policy_ms"]>=0,"Invalid feature timing.")
            if level<row["exit_level"]:require(t["probability"]<spec["threshold"],"Ignored learned stop.")
        require(trace[-1]["decoded_ids"]==row["decoded_ids"],"Exit trace differs.")
        if row["exit_level"]<12:require(trace[-1]["probability"]>=spec["threshold"],"Unjustified learned exit.")
        if offline is not None:
            depth,expected=offline_trace(spec["model"],offline["levels"],e.puzzle,spec["minimum"],spec["threshold"])
            require(depth==row["exit_level"],"Offline learned exit differs.")
            for actual,wanted in zip(trace,expected,strict=True):
                require(all(actual[k]==v for k,v in wanted.items()),"Offline learned observation differs.")
    elif offline is not None:
        from anytime_ncm.online_policy import simulated_exit
        require(row["exit_level"]==simulated_exit(spec,offline["levels"]),"Offline baseline exit differs.")
    if offline is not None:
        d=row["exit_level"];state=offline["levels"][d-1]
        require(row["decoded_ids"]==state["decoded_ids"] and row["generated_codes"]==
                [c for s in offline["levels"][:d] for c in s["code_ids"]],"Saved prefix parity differs.")

def calibration(probabilities,labels):
    require(len(probabilities)==len(labels)>0,"Missing calibration states.")
    require(all(math.isfinite(p) and 0<=p<=1 for p in probabilities) and all(y in (0,1) for y in labels),"Invalid calibration values.")
    bins=[]
    for i in range(10):
        ix=[j for j,p in enumerate(probabilities) if min(int(p*10),9)==i]
        bins.append({"lower":i/10,"upper":(i+1)/10,"count":len(ix),
                     "mean_probability":sum(probabilities[j] for j in ix)/len(ix) if ix else None,
                     "valid_rate":sum(labels[j] for j in ix)/len(ix) if ix else None})
    n=len(labels)
    return {"states":n,"positives":sum(labels),"brier":sum((p-y)**2 for p,y in zip(probabilities,labels))/n,
            "log_loss":-sum(y*math.log(max(1e-15,p))+(1-y)*math.log(max(1e-15,1-p)) for p,y in zip(probabilities,labels))/n,
            "bins":bins}

def analyze(root,stage):
    from anytime_ncm.phase2 import analyze_requests,_check_benchmark_counts
    out=root/OUTPUT;r=verify_stage(root,stage)
    methods=r["methods"];selected=examples(root,stage);by_id={e.identity:e for e in selected}
    rows=load_rows(out/(stage+"_requests.jsonl"))
    offline={r["sample_id"]:r for r in load_rows(root/"results/followup/sudoku_easy_r3/trajectories.jsonl")} if stage=="3b" else {}
    for row in rows:verify_row(row,by_id[row["sample_id"]],methods[row["method"]],offline.get(row["sample_id"]))
    _check_benchmark_counts(r,rows)
    expected=2100 if stage=="3b" else 6300
    require(len(rows)==r["completed_requests"]==r["timed_requests"]==expected and r["warmup_requests"]==70,"Incomplete benchmark.")
    summaries=analyze_requests(rows,methods,selected)
    import numpy as np
    from anytime_ncm.report import paired_bootstrap,decision_gate
    indexed={(x["sample_id"],x["repeat"],x["method"]):x for x in rows}
    base=np.array([[indexed[e.identity,k,"fixed"]["wall_ms"] for k in range(3)] for e in selected])
    primary=np.array([[indexed[e.identity,k,"learned_internal"]["wall_ms"] for k in range(3)] for e in selected])
    q=np.array([[int(indexed[e.identity,k,"learned_internal"]["valid"])-int(indexed[e.identity,k,"fixed"]["valid"]) for k in range(3)] for e in selected])
    fixed=paired_bootstrap(base,primary,q,seed=20261022)
    fixed_gate=decision_gate(fixed,quality_loss=max(0,-fixed["quality_difference"]),
                            false_accepts=summaries["learned_internal"]["false_early_accepts"])
    calibration_results={}
    for method in ("learned_base","learned_internal"):
        group=[x for x in rows if x["method"]==method and x["repeat"]==0]
        probabilities=[];labels=[];clusters=[];cpu=[]
        for row in group:
            ps=[t["probability"] for t in row["learned_trace"]]
            ys=[int(validate_solution(by_id[row["sample_id"]].puzzle,t["decoded_ids"]).is_valid_solution) for t in row["learned_trace"]]
            probabilities.extend(ps);labels.extend(ys);clusters.append((ps,ys))
        data=calibration(probabilities,labels);rng=np.random.default_rng(20261022)
        stats=[]
        # Cluster resampling keeps all inspected states of each identity.
        sums=np.array([[sum((p-y)**2 for p,y in zip(ps,ys)),
             -sum(y*math.log(max(1e-15,p))+(1-y)*math.log(max(1e-15,1-p)) for p,y in zip(ps,ys)),len(ps)] for ps,ys in clusters])
        for _ in range(100):
            draw=rng.integers(0,len(sums),size=(100,len(sums)));s=sums[draw].sum(axis=1);stats.extend((s[:,:2]/s[:,2:]).tolist())
        ci=np.percentile(np.asarray(stats),[2.5,97.5],axis=0)
        data.update(brier_ci95=ci[:,0].tolist(),log_loss_ci95=ci[:,1].tolist(),
             coverage="deployed inspected states; repeat 0 only; identity-cluster uncertainty")
        cpu=[sum(t["feature_policy_ms"] for t in x["learned_trace"]) for x in rows if x["method"]==method]
        data["mean_feature_policy_cpu_ms"]=sum(cpu)/len(cpu)
        calibration_results[method]=data
    # Paired current-state prediction comparison, separate from online speedup.
    paired_states=[];matched=True
    for e in selected:
        b=indexed[e.identity,0,"learned_base"]["learned_trace"]
        n=indexed[e.identity,0,"learned_internal"]["learned_trace"]
        if [t["level"] for t in b]!=[t["level"] for t in n]:
            matched=False;break
        delta=[]
        for bt,nt in zip(b,n,strict=True):
            require(bt["decoded_ids"]==nt["decoded_ids"],"Ablation inspected outputs differ.")
            y=int(validate_solution(e.puzzle,bt["decoded_ids"]).is_valid_solution)
            delta.append((nt["probability"]-y)**2-(bt["probability"]-y)**2)
        paired_states.append((sum(delta),len(delta)))
    ablation={"matched_inspected_states":matched,"interpretation":"internal minus base Brier; negative favors internal; descriptive feature ablation"}
    if matched:
        d=np.asarray(paired_states);rng=np.random.default_rng(20261022);values=[]
        for _ in range(100):
            draw=rng.integers(0,len(d),size=(100,len(d)));s=d[draw].sum(axis=1);values.extend((s[:,0]/s[:,1]).tolist())
        ablation.update(brier_difference=float(d[:,0].sum()/d[:,1].sum()),brier_difference_ci95=np.percentile(values,[2.5,97.5]).tolist())
    subgroup={}
    for name,predicate in (("clues_le_27",lambda c:c<=27),("clues_gt_27",lambda c:c>27)):
        ids={e.identity for e in selected if predicate(sum(1<=t<=9 for t in e.puzzle))}
        subgroup[name]={"identities":len(ids),"methods":{}}
        for m in methods:
            group=[x for x in rows if x["sample_id"] in ids and x["method"]==m]
            subgroup[name]["methods"][m]={"valid_inputs":sum(x["valid"] for x in group if x["repeat"]==0),
                 "mean_wall_ms":sum(x["wall_ms"] for x in group)/len(group) if group else None}
    return {"study":"Phase 3","stage":stage,"status":"complete","decision":summaries["learned_internal"]["gate_vs_full"],
       "primary_method":"learned_internal","summary":summaries,"primary_vs_fixed":fixed,"primary_fixed_gate":fixed_gate,
       "adaptive_frontier_claim":summaries["learned_internal"]["gate_vs_full"]=="go" and fixed_gate=="go",
       "calibration":calibration_results,"internal_ablation":ablation,"subgroups":subgroup,"counts":r["counts"],"identities":len(selected),
       "timed_requests":len(rows),"warmup_requests":70,"repeats":3}

def report(root):
    from anytime_ncm.phase3_render import render
    out=root/OUTPUT;a=analyze(root,"3c");save(out/"analysis.json",a);render(root,a)
    save(out/"report_provenance.json",{"sources":source_hashes(root),
         "artifacts":{n:sha256(out/n) for n in ("analysis.json","summary.md","comparison.png")},
         "stages":{s:sha256(out/(s+".json")) for s in ("3a","3b","3c")}})
    return a
def verify(root):
    from anytime_ncm.train_policy import verify_training
    out=root/OUTPUT;verify_training(root);checked_lock(root)
    p=json.loads((out/"report_provenance.json").read_text(encoding="utf-8"))
    require(p["sources"]==source_hashes(root),"Report sources changed.")
    for n,h in p["artifacts"].items():require(sha256(out/n)==h,"Report artifact changed.")
    for s,h in p["stages"].items():require(sha256(out/(s+".json"))==h,"Stage receipt changed.")
    for stage,name in (("3b","development_analysis.json"),("3c","analysis.json")):
        require(analyze(root,stage)==json.loads((out/name).read_text(encoding="utf-8")),"Saved analysis differs.")
    return json.loads((out/"analysis.json").read_text(encoding="utf-8"))
