"""Phase 2 frozen selections, finite-stage receipts and model-free paired analysis."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time

from anytime_ncm.dataset import Example, _TokenRows, puzzle_identity, sha256
from anytime_ncm.online_policy import policy_spec, simulated_exit
from anytime_ncm.screening import require
from anytime_ncm.sudoku import validate_solution
from anytime_ncm.trajectories import decoded_text

OUTPUT = "results/phase2"
PROTOCOL = "docs/studies/phase2-easy-online-protocol.md"
SOURCE_PATHS = (PROTOCOL, "src/anytime_ncm/online.py", "src/anytime_ncm/online_policy.py",
    "src/anytime_ncm/phase2.py", "src/anytime_ncm/phase2_run.py", "src/anytime_ncm/phase2_render.py",
    "scripts/run_phase2.py", "scripts/finalize_phase2_patch.py", "tests/test_online.py", "tests/test_phase2.py",
    "src/anytime_ncm/screening_inference.py", "src/anytime_ncm/upstream_adapter.py",
    "src/anytime_ncm/sudoku.py", "src/anytime_ncm/report.py", "src/anytime_ncm/dataset.py",
    "third_party/ncm/models/next_concept.py", "third_party/ncm/models/quant.py",
    "third_party/ncm/models/vqvae.py", "configs/r2_sources.json")
LIMITS = {"2a": {"inputs": 192, "generator_levels": 1760, "decoder": 864, "encoder": 0},
          "2b": {"inputs": 2170, "generator_levels": 26040, "decoder": 11160, "encoder": 0},
          "2c": {"inputs": 4550, "generator_levels": 54600, "decoder": 33670, "encoder": 0}}

def save(path, value):
    path = Path(path)
    data = json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
    for attempt in range(10):
        temporary = None
        try:
            fd, name = tempfile.mkstemp(prefix=".phase2-", suffix=".tmp", dir=path.parent)
            temporary = Path(name)
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f: f.write(data)
            os.replace(temporary, path)
            return
        except OSError:
            if attempt == 9: raise
            time.sleep(.05)
        finally:
            if temporary: temporary.unlink(missing_ok=True)

def sources(root):
    return {name: sha256(root / name) for name in SOURCE_PATHS}

def inputs(root):
    paths = ("docs/partitions/sudoku-easy-r2.json", "docs/partitions/sudoku-hard.json",
        "docs/experiment_protocol.md", "results/followup/sudoku_easy_r3/trajectories.jsonl",
        "results/followup/sudoku_easy_r3/analysis.json",
        "results/followup/sudoku_checkpoint_screen/easy/provenance.json",
        "artifacts/sudoku/easy/config.yaml", "artifacts/sudoku/easy/generator.pt",
        "artifacts/sudoku/easy/tokenizer.pt", "data/sudoku/easy/puzzles.pickle",
        "data/sudoku/easy/solutions.pickle")
    prior = root/"results/followup/sudoku_easy_r3"
    provenance = json.loads((prior/"report_provenance.json").read_text(encoding="utf-8"))
    collection = json.loads((prior/"collection.json").read_text(encoding="utf-8"))
    require(sha256(prior/"analysis.json")==provenance["artifacts_sha256"]["analysis.json"]
            and sha256(prior/"trajectories.jsonl")==collection["artifacts_sha256"]["trajectories.jsonl"],
            "Prior R3 evidence changed.")
    # R2 checks pins/config/data and shared-solution reservations before any new access.
    from anytime_ncm.screening import verify_candidate
    verify_candidate(root, "easy")
    return {name: sha256(root / name) for name in paths}

def select_entries(manifest, stage, lock=None):
    if stage not in ("2a", "2b", "2c", "warmup"):
        raise ValueError("Unknown Phase 2 access stage.")
    if stage == "2c":
        require(lock is not None and lock["status"] == "frozen" and lock["phase3_final_access"] is False,
                "Final token access requires a frozen source-matched policy lock.")
        rows = manifest["partitions"]["phase2_final"]
        require(len(rows) == 300, "Expected 300 Phase 2 final identities.")
        return [dict(row, partition="phase2_final") for row in sorted(rows, key=lambda x: x["index"])]
    name, count = ("development", 100) if stage == "2b" else ("exploration", 10 if stage == "warmup" else 32)
    return [dict(row, partition=name) for row in sorted(manifest["partitions"][name], key=lambda x:x["index"])[:count]]

def examples(root, stage):
    manifest = json.loads((root / "docs/partitions/sudoku-easy-r2.json").read_text(encoding="utf-8"))
    lock = checked_lock(root) if stage == "2c" else None
    selected = select_entries(manifest, stage, lock)
    indices = {r["index"] for r in selected}
    data = [_TokenRows((root / ("data/sudoku/easy/" + name)).read_bytes()).select(indices, length, 2000)
            for name, length in (("puzzles.pickle", 91), ("solutions.pickle", 89))]
    result = []
    for row in selected:
        index = row["index"]
        require(puzzle_identity(data[0][index]) == row["puzzle_sha256"], "Input identity differs.")
        require(validate_solution(data[0][index], data[1][index], reference=data[1][index]).is_valid_solution,
                "Invalid Phase 2 reference.")
        result.append(Example(index, row["partition"], row["puzzle_sha256"], data[0][index], data[1][index]))
    return tuple(result)

def begin(root, stage):
    out = root / OUTPUT
    out.mkdir(parents=True, exist_ok=True)
    path = out / (stage + ".json")
    require(not path.exists(), "Stage already attempted; no silent model-work retry.")
    hashes, pinned = sources(root), inputs(root)
    snapshot = out / "source_snapshots" / stage
    for name in hashes:
        target = snapshot / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((root / name).read_bytes())
    record = {"study": "Phase 2", "stage": stage, "status": "started",
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "entry_exception": "explicit user-directed online experiment after negative offline gates",
        "source_sha256": hashes, "source_snapshot": snapshot.relative_to(root).as_posix(),
        "inputs_sha256": pinned, "limits": LIMITS[stage], "counts": dict.fromkeys(LIMITS[stage], 0),
        "completed_requests": 0, "artifacts_sha256": {}}
    if stage != "2a":
        a = verify_stage(root, "2a")
        for key in ("src/anytime_ncm/online.py", "src/anytime_ncm/online_policy.py"):
            require(hashes[key] == a["source_sha256"][key], "Online engine changed since real parity.")
    save(path, record)
    return out, path, record

def end(out, path, record, names):
    record.update(status="complete", finished_utc=datetime.now(timezone.utc).isoformat(),
                  artifacts_sha256={name: sha256(out / name) for name in names})
    save(path, record)

def failed(path, record, error):
    record.update(status="failed", error=repr(error), finished_utc=datetime.now(timezone.utc).isoformat())
    save(path, record)

def verify_stage(root, stage):
    out = root / OUTPUT
    record = json.loads((out / (stage + ".json")).read_text(encoding="utf-8"))
    require(record["status"] == "complete" and record["limits"] == LIMITS[stage], "Incomplete/changed Phase 2 stage.")
    for key, count in record["counts"].items():
        require(type(count) is int and 0 <= count <= LIMITS[stage][key], "Stage work cap exceeded.")
    for name, expected in record["source_sha256"].items():
        require(sha256(root / record["source_snapshot"] / name) == expected, "Execution source receipt changed.")
    for name, expected in record["inputs_sha256"].items():
        require(sha256(root / name) == expected, "Frozen Phase 2 input changed: " + name)
    for name, expected in record["artifacts_sha256"].items():
        require(sha256(out / name) == expected, "Phase 2 artifact changed: " + name)
    require(record["state_before"] == record["state_after"], "Recorded model state changed.")
    return record

def offline_policies(trajectories, old_analysis):
    rows = [r for r in trajectories if r["partition"] == "development"]
    require(len(rows) == 400, "Policy selection needs exactly 400 development trajectories.")
    fixed = old_analysis["fixed_depth_comparison"]["development"]
    feasible = [x for x in fixed if x["collection_valid_rate"] >= fixed[-1]["collection_valid_rate"]]
    selected_fixed = min(feasible, key=lambda x:(x["mean_estimated_ms"],x["level"]))["level"]
    candidates = []
    for minimum in (2,6,10):
        for patience in (1,2):
            spec = policy_spec("stability", min_level=minimum, patience=patience)
            invalid_early = loss = inspections = early = 0
            for row in rows:
                depth = simulated_exit(spec, row["levels"])
                valid = row["levels"][depth-1]["correctness"]["is_valid_solution"]
                final = row["levels"][-1]["correctness"]["is_valid_solution"]
                invalid_early += depth < 12 and not valid
                loss += final and not valid
                early += depth < 12
                inspections += sum(level<=depth for level in spec["levels"])
            candidates.append({"spec":spec,"invalid_early":invalid_early,"solve_loss":loss,
                "early":early,"mean_inspections":inspections/400,"feasible":invalid_early==loss==0})
    eligible = [x for x in candidates if x["feasible"]]
    chosen = min(eligible, key=lambda x:(x["mean_inspections"],-x["spec"]["min_level"],x["spec"]["patience"])) if eligible else candidates[-2]
    methods = {"full":policy_spec("full"),"fixed":policy_spec("fixed",depth=selected_fixed),
        "verified_all":policy_spec("verified",levels=list(range(1,13))),
        "verified_6":policy_spec("verified",levels=list(range(6,13))),
        "verified_10":policy_spec("verified",levels=[10,11,12]),
        "verified_12":policy_spec("verified",levels=[12]),"stability":chosen["spec"]}
    return {"methods":methods,"fixed_depth":selected_fixed,"stability_candidates":candidates,
        "selected_stability":chosen,"selection_source":"400 development trajectories; no final outcomes",
        "uncertainty_signal":"decoder logits absent from frozen trajectories; no entropy baseline introduced"}

def warm_order(methods, index):
    names = list(methods)
    shift = index % len(names)
    return names[shift:] + names[:shift]

def execution_sources(root):
    import ast
    paths = ("src/anytime_ncm/online.py","src/anytime_ncm/online_policy.py","src/anytime_ncm/phase2_run.py")
    hashes = {name:sha256(root/name) for name in paths}
    source = (root/"src/anytime_ncm/phase2.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    parts = [ast.get_source_segment(source,n) for n in tree.body if isinstance(n,ast.FunctionDef)
             and n.name in ("inputs","examples","select_entries")]
    hashes["phase2_access_functions"] = hashlib.sha256("\n".join(parts).encode()).hexdigest()
    return hashes

def checked_lock(root):
    out = root / OUTPUT
    b = verify_stage(root, "2b")
    lock = json.loads((out / "policy_lock.json").read_text(encoding="utf-8"))
    require(lock["status"]=="frozen" and lock["execution_source_sha256"]==execution_sources(root), "Policy/source lock differs.")
    require(lock["stage2b_sha256"]==sha256(out/"2b.json") and lock["phase3_final_access"] is False,
            "Policy lock stage/access differs.")
    require(lock["development_analysis_sha256"]==sha256(out/"development_analysis.json")
            and lock["protocol_sha256"]==sha256(root/PROTOCOL),"Development/protocol lock changed.")
    release = json.loads((out/"policy_lock_release.json").read_text(encoding="utf-8"))
    require(release["policy_lock_sha256"]==sha256(out/"policy_lock.json")
            and release["github_main"]==release["local_head"],"Policy lock has not been committed/pushed and released.")
    return lock

def verify_request(row, example, expected_spec, offline=None):
    from anytime_ncm.report import independent_valid
    require(row["sample_id"]==example.identity and row["dataset_index"]==example.index
            and row["partition"]==example.partition and row["policy"]==expected_spec, "Request identity/spec differs.")
    ids=row["decoded_ids"]
    require(len(ids)==89 and all(type(t)is int and 0<=t<=11 for t in ids)
            and decoded_text(ids)==row["decoded_text"],"Output token/text contract differs.")
    correct=validate_solution(example.puzzle,ids,reference=example.reference)
    require(independent_valid(example.puzzle,ids)==correct.is_valid_solution,"Independent primary validity differs.")
    require(row["valid"] is correct.is_valid_solution,"Saved validity differs.")
    require(1<=row["exit_level"]<=12 and row["generator_levels"]==row["exit_level"],"Work/exit differs.")
    lengths=(1,2,4,6,9,13,18,26,37,50,67,89)
    require(len(row["generated_codes"])==sum(lengths[:row["exit_level"]])
            and all(type(c)is int and 0<=c<16 for c in row["generated_codes"]),"Generated-prefix contract differs.")
    require(row["false_early_accept"]==(row["exit_level"]<12 and not correct.is_valid_solution),"False-accept label differs.")
    import math
    for name in ("wall_ms","gpu_elapsed_ms","peak_allocated_bytes"):
        require(isinstance(row[name],(int,float)) and math.isfinite(row[name]) and row[name]>=0,"Invalid measurement.")
    if offline is not None:
        depth=simulated_exit(expected_spec,offline["levels"])
        require(row["exit_level"]==depth and ids==offline["levels"][depth-1]["decoded_ids"],"Offline/online exit-output mismatch.")

def analyze_requests(rows, method_specs, expected_examples, repeats=3):
    import numpy as np
    from anytime_ncm.report import paired_bootstrap, decision_gate
    expected={(e.identity,r,m) for e in expected_examples for r in range(repeats) for m in method_specs}
    require(len(rows)==len(expected) and {(r["sample_id"],r["repeat"],r["method"]) for r in rows}==expected,
            "Missing/extra/duplicate paired requests.")
    indexed={(r["sample_id"],r["repeat"],r["method"]):r for r in rows}
    summaries={}
    def distribution(values):
        data=np.asarray(values,dtype=float)
        return {"mean":float(data.mean()),"median":float(np.median(data)),"p95":float(np.percentile(data,95))}
    for method in method_specs:
        group=[indexed[e.identity,r,method] for e in expected_examples for r in range(repeats)]
        full=[indexed[e.identity,r,"full"] for e in expected_examples for r in range(repeats)]
        for a,b in zip(group,full,strict=True):
            if a["exit_level"]==12:
                require(a["decoded_ids"]==b["decoded_ids"] and a["generated_codes"]==b["generated_codes"],
                        "Full-depth request parity differs.")
        for e in expected_examples:
            repeated=[indexed[e.identity,r,method] for r in range(repeats)]
            require(all(x["decoded_ids"]==repeated[0]["decoded_ids"] and
                        x["generated_codes"]==repeated[0]["generated_codes"] for x in repeated),
                    "Deterministic request outputs changed across repeats.")
        wall=np.array([r["wall_ms"] for r in group]).reshape(-1,repeats)
        base=np.array([r["wall_ms"] for r in full]).reshape(-1,repeats)
        q=np.array([int(r["valid"])-int(b["valid"]) for r,b in zip(group,full)]).reshape(-1,repeats)
        paired=paired_bootstrap(base,wall,q,seed=20261022)
        false=sum(r["false_early_accept"] for r in group)
        loss=max(0,-float(q.mean()))
        summaries[method]={"requests":len(group),"valid_inputs":sum(group[i*repeats]["valid"] for i in range(len(expected_examples))),
            "valid_rate":float(np.mean([r["valid"] for r in group])),"false_early_accepts":false,
            "early_requests":sum(r["exit_level"]<12 for r in group),
            "wall_ms":distribution([r["wall_ms"] for r in group]),
            "gpu_event_elapsed_ms":distribution([r["gpu_elapsed_ms"] for r in group]),
            "peak_allocated_bytes":max(r["peak_allocated_bytes"] for r in group),
            "generator_levels":distribution([r["generator_levels"] for r in group]),
            "generated_codes":distribution([len(r["generated_codes"]) for r in group]),
            "inspections":distribution([len(r["inspected_levels"]) for r in group]),
            "batch1_requests_per_second":1000/float(wall.mean()),"paired_vs_full":paired,
            "gate_vs_full":decision_gate(paired,quality_loss=loss,false_accepts=false)}
    return summaries

def load_rows(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]

def verify_a(root):
    receipt=verify_stage(root,"2a")
    if "patch_format_correction" in receipt:
        fix=receipt["patch_format_correction"]
        require(sha256(root/fix["source_path"])==fix["sha256"] and fix["git_apply_check"] is True
                and fix["additional_model_calls"]==0 and fix["model_code_changed"] is False,
                "Patch-format receipt differs.")
    rows=load_rows(root/OUTPUT/"2a_requests.jsonl")
    selected=examples(root,"2a")
    original={r["sample_id"]:r for r in load_rows(root/"results/followup/sudoku_easy_r3/trajectories.jsonl")}
    cases={"full","disabled","forced1","forced6","verified_all","stability"}
    require(len(rows)==192 and {(r["sample_id"],r["case"]) for r in rows}==
            {(e.identity,c) for e in selected for c in cases},"2A paired-case coverage differs.")
    totals=dict.fromkeys(LIMITS["2a"],0)
    for row in rows:
        expected=simulated_exit(row["policy"],original[row["sample_id"]]["levels"])
        state=original[row["sample_id"]]["levels"][expected-1]
        codes=[c for s in original[row["sample_id"]]["levels"][:expected] for c in s["code_ids"]]
        require(row["exit_level"]==expected and row["decoded_ids"]==state["decoded_ids"]
                and row["decoded_text"]==state["decoded_text"] and row["generated_codes"]==codes,
                "2A real parity differs from saved offline output.")
        require(row["counts"]["generator_levels"]==expected and row["counts"]["inputs"]==1,"2A call skipping differs.")
        for key in totals:totals[key]+=row["counts"][key]
    require(totals==receipt["counts"] and totals["inputs"]==192,"2A counters/coverage differ.")
    return {"status":"complete","real_inputs":32,"requests":192,"exact_parity_cases":192,
            "forced_depths":[1,6],"counts":totals}

def verify_development(root):
    verify_a(root)
    receipt=verify_stage(root,"2b")
    out=root/OUTPUT
    old=load_rows(root/"results/followup/sudoku_easy_r3/trajectories.jsonl")
    old_analysis=json.loads((root/"results/followup/sudoku_easy_r3/analysis.json").read_text(encoding="utf-8"))
    selection=offline_policies(old,old_analysis)
    require(selection==json.loads((out/"development_candidates.json").read_text(encoding="utf-8")),
            "Development candidate selection differs.")
    selected=examples(root,"2b");by_id={r["sample_id"]:r for r in old}
    rows=load_rows(out/"2b_requests.jsonl");by_example={e.identity:e for e in selected}
    for row in rows:verify_request(row,by_example[row["sample_id"]],selection["methods"][row["method"]],by_id[row["sample_id"]])
    summaries=analyze_requests(rows,selection["methods"],selected)
    saved=json.loads((out/"development_analysis.json").read_text(encoding="utf-8"))
    require(saved["online_development"]==summaries and saved["selection"]==selection,"Development analysis differs.")
    eligible=[n for n in selection["methods"] if n.startswith("verified") and summaries[n]["false_early_accepts"]==0
              and summaries[n]["valid_rate"]>=summaries["full"]["valid_rate"]]
    winner=min(eligible,key=lambda n:(summaries[n]["wall_ms"]["mean"],n))
    require(saved["selected_verifier"]==winner,"Selected schedule differs.")
    require(receipt["timed_requests"]==2100 and receipt["warmup_requests"]==70 and receipt["counts"]["inputs"]==2170,
            "Development request budget differs.")
    _check_benchmark_counts(receipt,rows)
    return saved

def _check_benchmark_counts(receipt,rows):
    warm=receipt["warmup_counts"]
    require(receipt["counts"]["inputs"]==warm["inputs"]+len(rows)
            and receipt["counts"]["generator_levels"]==warm["generator_levels"]+sum(r["generator_levels"] for r in rows)
            and receipt["counts"]["decoder"]==warm["decoder"]+sum(r["decoder_forwards"] for r in rows)
            and receipt["counts"]["encoder"]==0,"Headline work counters differ.")

def final_analysis(root):
    import numpy as np
    from anytime_ncm.report import paired_bootstrap,decision_gate
    development=verify_development(root)
    lock=checked_lock(root);receipt=verify_stage(root,"2c")
    selected=examples(root,"2c");rows=load_rows(root/OUTPUT/"2c_requests.jsonl")
    methods=lock["methods"];by_id={e.identity:e for e in selected}
    for row in rows:verify_request(row,by_id[row["sample_id"]],methods[row["method"]])
    summary=analyze_requests(rows,methods,selected)
    require(receipt["timed_requests"]==300*3*len(methods) and receipt["warmup_requests"]==10*len(methods),
            "Final request budget differs.")
    _check_benchmark_counts(receipt,rows)
    primary=lock["primary_method"]
    indexed={(r["sample_id"],r["repeat"],r["method"]):r for r in rows}
    fixed=[];adaptive=[];difference=[]
    for e in selected:
        fixed.append([indexed[e.identity,r,"fixed"]["wall_ms"] for r in range(3)])
        adaptive.append([indexed[e.identity,r,primary]["wall_ms"] for r in range(3)])
        difference.append([int(indexed[e.identity,r,primary]["valid"])-int(indexed[e.identity,r,"fixed"]["valid"]) for r in range(3)])
    versus_fixed=paired_bootstrap(np.array(fixed),np.array(adaptive),np.array(difference),seed=20261022)
    loss=max(0,-versus_fixed["quality_difference"])
    fixed_gate=decision_gate(versus_fixed,quality_loss=loss,false_accepts=summary[primary]["false_early_accepts"])
    access=json.loads((root/OUTPUT/"holdout_access.json").read_text(encoding="utf-8"))
    require(access["phase3_final_rows_materialized"]==0 and access["policy_lock_sha256"]==sha256(root/OUTPUT/"policy_lock.json"),
            "Final access record differs.")
    return {"study":"Phase 2","setting":"easy","status":"complete","entry_exception":
        "explicit online engineering/measurement work order despite negative Phase 1/R3 opportunity gates",
        "decision":summary[primary]["gate_vs_full"],"primary_method":primary,
        "final_summary":summary,"primary_vs_fixed":versus_fixed,"primary_fixed_gate":fixed_gate,
        "adaptive_frontier_claim":summary[primary]["gate_vs_full"]=="go" and fixed_gate=="go",
        "development_selected_verifier":development["selected_verifier"],"aliases":lock["aliases"],
        "phase2_final_inputs":300,"repeats":3,"phase3_final_rows_materialized":0,
        "counts":{name:verify_stage(root,name)["counts"] for name in ("2a","2b","2c")},
        "warmup_requests":receipt["warmup_requests"],"final_timed_requests":receipt["timed_requests"],
        "prior_baselines":"hard/easy full official evaluators internally scored reserved rows with aggregate-only analyst inspection",
        "measurement":"synchronized warm request wall time; CUDA event stream elapsed; batch1 serial request rate only",
        "oracle":"retrospective saved development first-valid labels are analysis-only; never an online input"}

def report(root):
    from anytime_ncm.phase2_render import render
    out=root/OUTPUT
    analysis=final_analysis(root)
    save(out/"analysis.json",analysis)
    render(root,analysis)
    save(out/"report_provenance.json",{"study":"Phase 2","analysis_source_sha256":sources(root),
        "stage_sha256":{s:sha256(out/(s+".json")) for s in ("2a","2b","2c")},
        "policy_lock_sha256":sha256(out/"policy_lock.json"),
        "policy_release_sha256":sha256(out/"policy_lock_release.json"),
        "artifacts_sha256":{name:sha256(out/name) for name in ("analysis.json","summary.md","online_comparison.png")}})
    return analysis

def verify_report(root):
    out=root/OUTPUT
    provenance=json.loads((out/"report_provenance.json").read_text(encoding="utf-8"))
    require(provenance["analysis_source_sha256"]==sources(root),"Current report sources differ.")
    for name,expected in provenance["artifacts_sha256"].items():
        require(sha256(out/name)==expected,"Report artifact differs.")
    for stage,expected in provenance["stage_sha256"].items():
        require(sha256(out/(stage+".json"))==expected,"Stage receipt differs.")
    require(provenance["policy_lock_sha256"]==sha256(out/"policy_lock.json")
            and provenance["policy_release_sha256"]==sha256(out/"policy_lock_release.json"),"Final lock/release changed.")
    analysis=final_analysis(root)
    require(analysis==json.loads((out/"analysis.json").read_text(encoding="utf-8")),"Recomputed final analysis differs.")
    return analysis
