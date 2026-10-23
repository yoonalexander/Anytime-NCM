"""WMT14 finite-stage provenance, restricted access and model-free analysis."""
import json,math
from pathlib import Path
import numpy as np
from anytime_ncm.dataset import sha256
from anytime_ncm.phase2 import save,load_rows
from anytime_ncm.screening import require
from anytime_ncm.wmt_data import StringRows,select_entries,identity
from anytime_ncm.wmt_policy import simulate,Stability,diagnostics
from anytime_ncm.wmt_metrics import scores,select_policies,paired_quality,claim_gate
from anytime_ncm.report import paired_bootstrap
OUTPUT="results/phase4/wmt14"
PROTOCOL="docs/studies/phase4-wmt14-protocol.md"
MANIFEST="docs/partitions/wmt14-phase4.json"
SOURCES=(PROTOCOL,"scripts/prepare_phase4.py","scripts/run_phase4.py","src/anytime_ncm/phase4.py",
 "src/anytime_ncm/phase4_run.py","src/anytime_ncm/phase4_render.py","src/anytime_ncm/wmt_data.py",
 "src/anytime_ncm/wmt_policy.py","src/anytime_ncm/wmt_metrics.py","src/anytime_ncm/wmt_model.py",
 "tests/test_phase4.py","src/anytime_ncm/online.py","src/anytime_ncm/upstream_adapter.py",
 "src/anytime_ncm/phase2.py","src/anytime_ncm/report.py","src/anytime_ncm/target_encoding.py",
 "third_party/ncm/models/next_concept.py","third_party/ncm/models/quant.py","third_party/ncm/models/vqvae.py",
 "third_party/ncm/scripts/eval_shard.py","third_party/ncm/scripts/eval_merge.py","third_party/ncm/tokenization/hf_tokenizer.py")
LIMITS={"4a":dict(inputs=3259,generator_levels=35849,decoder=5179,encoder=0),
 "4b":dict(inputs=800,generator_levels=8800,decoder=4800,encoder=0),
 "4c":dict(inputs=3104,generator_levels=34144,decoder=18624,encoder=0)}
def source_hashes(root):return {p:sha256(root/p) for p in SOURCES}
def pinned(root):
    inventory=json.loads((root/"configs/phase4_wmt_sources.json").read_text())
    p={MANIFEST:sha256(root/MANIFEST),"configs/phase4_wmt_sources.json":sha256(root/"configs/phase4_wmt_sources.json"),"results/phase4/wmt14/preflight.json":sha256(root/"results/phase4/wmt14/preflight.json")}
    for name,r in inventory["files"].items():
        require(sha256(root/name)==r["sha256"],"Pinned WMT input differs: "+name);p[name]=r["sha256"]
    return p
def begin(root,stage):
    out=root/OUTPUT;path=out/(stage+".json")
    require(not path.exists(),"WMT stage already attempted; no silent replay.")
    hashes=source_hashes(root);snapshot=out/"source_snapshots"/stage
    for name in hashes:
        p=snapshot/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((root/name).read_bytes())
    from datetime import datetime,timezone
    r={"stage":stage,"status":"started","started_utc":datetime.now(timezone.utc).isoformat(),
       "source_snapshot":snapshot.relative_to(root).as_posix(),"source_sha256":hashes,"inputs_sha256":pinned(root),
       "limits":LIMITS[stage],"counts":dict.fromkeys(LIMITS[stage],0),"completed_requests":0,"artifacts_sha256":{}}
    save(path,r);return out,path,r
def finish(out,path,r,names):
    from datetime import datetime,timezone
    r.update(status="complete",finished_utc=datetime.now(timezone.utc).isoformat(),
             artifacts_sha256={n:sha256(out/n) for n in names});save(path,r)
def failed(path,r,error):
    r.update(status="failed",error=repr(error));save(path,r)
def verify_stage(root,stage):
    out=root/OUTPUT;r=json.loads((out/(stage+".json")).read_text())
    require(r["status"]=="complete" and r["limits"]==LIMITS[stage],"Incomplete/changed WMT stage.")
    for k,v in r["counts"].items():require(type(v)is int and 0<=v<=LIMITS[stage][k],"WMT cap exceeded.")
    for name,h in r["source_sha256"].items():require(sha256(root/r["source_snapshot"]/name)==h,"Execution snapshot changed.")
    for name,h in r["inputs_sha256"].items():require(sha256(root/name)==h,"WMT input changed.")
    for name,h in r["artifacts_sha256"].items():require(sha256(out/name)==h,"WMT artifact changed.")
    require(r["state_before"]==r["state_after"],"NCM state changed.")
    return r
def checked_lock(root):
    out=root/OUTPUT;verify_stage(root,"4a");verify_stage(root,"4b")
    lock=json.loads((out/"policy_lock.json").read_text());release=json.loads((out/"policy_lock_release.json").read_text())
    require(lock["sources"]==source_hashes(root),"WMT source lock changed.")
    for n,h in lock["artifacts"].items():require(sha256(out/n)==h,"WMT locked artifact changed.")
    require(release["github_main"]==release["local_head"] and release["working_lock_matches_committed_blob"]
            and release["policy_lock_sha256"]==sha256(out/"policy_lock.json"),"WMT policy lock unreleased.")
    return lock
def examples(root,stage):
    manifest=json.loads((root/MANIFEST).read_text())
    selected=select_entries(manifest,stage,checked_lock(root) is not None if stage=="final" else False)
    indices={r["index"] for r in selected}
    sources=StringRows((root/"data/wmt14/sources.pickle").read_bytes()).select(indices)
    refs=StringRows((root/"data/wmt14/reference_translations.pickle").read_bytes()).select(indices)
    return [dict(r,source=sources[r["index"]],reference=refs[r["index"]]) for r in selected]
def decode_ids(root,ids):
    from tokenizers import Tokenizer
    tok=Tokenizer.from_file(str(root/"artifacts/wmt14/text_tokenizer/tokenizer.json"))
    eos=tok.token_to_id("<|im_end|>");pad=tok.token_to_id("<|endoftext|>")
    ids=ids[:ids.index(eos)] if eos in ids else ids
    return tok.decode([i for i in ids if i not in (eos,pad)],skip_special_tokens=True)
def verify_row(root,row,e,spec,offline=None,decoder=None):
    lengths=(1,4,8,14,20,26,32,40,48,56,64);depth=row["exit_level"]
    require(row["identity"]==e["identity"] and row["index"]==e["index"] and row["partition"]==e["partition"]
            and row["policy"]==spec,"WMT request identity/spec differs.")
    require(len(row["prefix_ids"])==96 and identity(row["prefix_ids"])==e["identity"],"WMT effective prefix differs.")
    require(type(depth)is int and 1<=depth<=11 and row["generator_levels"]==depth,"WMT work/exit differs.")
    require(len(row["codes"])==sum(lengths[:depth]) and all(type(c)is int and 0<=c<4096 for c in row["codes"]),"WMT code prefix invalid.")
    dec=decoder or (lambda ids:decode_ids(root,ids))
    require(len(row["ids"])==64 and dec(row["ids"])==row["text"],"WMT decoded IDs/text differ.")
    for k in ("wall_ms","gpu_elapsed_ms","peak_allocated_bytes"):require(math.isfinite(row[k]) and row[k]>=0,"Invalid WMT measurement.")
    if spec["kind"] in ("stability","guarded"):
        tracker=Stability(spec);expected=list(range(spec["minimum"],depth+1))
        require(row["inspections"]==expected and [s["level"] for s in row["trace"]]==expected
                and row["decoder_forwards"]==len(expected),"WMT inspections/work differ.")
        for t in row["trace"]:
            require(dec(t["ids"])==t["text"],"WMT trace text differs.")
            stop,change=tracker.observe(t["level"],t["ids"],t["text"])
            require(t["change"]==change and (not stop or t["level"]==depth),"WMT causal stop differs.")
        require(row["trace"][-1]["ids"]==row["ids"],"WMT final trace differs.")
        if depth<11:require(stop,"No causal justification for early stop.")
    else:require(not row["trace"] and row["decoder_forwards"]==1,"Fixed/full decoder work differs.")
    if offline:
        expected=simulate(spec,offline["levels"]);state=offline["levels"][expected-1]
        require(depth==expected and row["ids"]==state["ids"] and row["codes"]==offline["codes"][:sum(lengths[:depth])],"WMT offline/online parity differs.")

def audit_analysis(root):
    from sacrebleu.metrics import CHRF
    rows=load_rows(root/OUTPUT/"trajectories.jsonl")
    entries={e["identity"]:e for s in ("audit_exploration","audit_development") for e in examples(root,s)}
    require(len(rows)==192 and {r["identity"] for r in rows}==set(entries),"WMT audit coverage differs.")
    from tokenizers import Tokenizer
    tok=Tokenizer.from_file(str(root/"artifacts/wmt14/text_tokenizer/tokenizer.json"))
    eos=tok.token_to_id("<|im_end|>");pad=tok.token_to_id("<|endoftext|>")
    for row in rows:
        require(identity(row["prefix_ids"])==row["identity"] and len(row["prefix_ids"])==96,"Audit prefix identity differs.")
        require(len(row["codes"])==313 and all(type(c)is int and 0<=c<4096 for c in row["codes"]),"Audit code hierarchy differs.")
        require([s["level"] for s in row["levels"]]==list(range(1,12)),"Audit levels incomplete.")
        for state in row["levels"]:
            ids=state["ids"];require(len(ids)==64 and all(type(i)is int and 0<=i<151680 for i in ids),"Audit decoded ID contract differs.")
            visible=ids[:ids.index(eos)] if eos in ids else ids
            text=tok.decode([i for i in visible if i not in (eos,pad)],skip_special_tokens=True)
            require(text==state["text"],"Audit raw decoded IDs/text differ.")
    receipt=verify_stage(root,"4a")
    require(receipt["counts"]==LIMITS["4a"] and receipt["exact_official_parity_inputs"]==32
        and receipt["full_resolution_checked_inputs"]==192,"Audit measured work/parity coverage differs.")
    result={}
    for part in ("exploration","development"):
        group=[r for r in rows if r["partition"]==part];refs=[entries[r["identity"]]["reference"] for r in group]
        by_level=[scores([r["levels"][d-1]["text"] for r in group],refs) for d in range(1,12)]
        transitions=[];metric=CHRF()
        for d in range(1,11):
            diffs=[metric.sentence_score(r["levels"][d]["text"],[entries[r["identity"]]["reference"]]).score-
                   metric.sentence_score(r["levels"][d-1]["text"],[entries[r["identity"]]["reference"]]).score for r in group]
            transitions.append({"from":d,"to":d+1,"improved":sum(x>1e-12 for x in diffs),"damaged":sum(x< -1e-12 for x in diffs),
                                "unchanged":sum(abs(x)<=1e-12 for x in diffs),"mean_sentence_chrf_change":float(np.mean(diffs))})
        result[part]={"inputs":len(group),"quality_by_level":by_level,"adjacent_sentence_chrf":transitions}
    dev=[r for r in rows if r["partition"]=="development"];refs=[entries[r["identity"]]["reference"] for r in dev]
    selection=select_policies(dev,refs)
    return {"task":"wmt14","partitions":result,"selection":selection}

def analyze(root,stage):
    from tokenizers import Tokenizer
    from anytime_ncm.wmt_metrics import feasible
    out=root/OUTPUT;r=verify_stage(root,stage);methods=r["methods"]
    require(set(methods)=={"full","fixed","stability","adaptive"},"Missing WMT comparison method.")
    chosen=json.loads((out/"audit_analysis.json").read_text())["selection"]["methods"]
    require(methods==chosen,"Benchmarked WMT policies differ from development selection.")
    selected=examples(root,"development" if stage=="4b" else "final")
    es={e["identity"]:e for e in selected};rows=load_rows(out/(stage+"_requests.jsonl"))
    expected={(e["identity"],k,m) for e in selected for k in range(3) for m in methods}
    require(r["warmup_requests"]==32 and len(rows)==(768 if stage=="4b" else 3072),"WMT benchmark budget/coverage differs.")
    require(len(rows)==len(expected) and {(x["identity"],x["repeat"],x["method"]) for x in rows}==expected,"WMT paired requests missing/duplicate.")
    tok=Tokenizer.from_file(str(root/"artifacts/wmt14/text_tokenizer/tokenizer.json"))
    eos=tok.token_to_id("<|im_end|>");pad=tok.token_to_id("<|endoftext|>")
    def dec(ids):
        ids=ids[:ids.index(eos)] if eos in ids else ids
        return tok.decode([i for i in ids if i not in (eos,pad)],skip_special_tokens=True)
    offline={x["identity"]:x for x in load_rows(out/"trajectories.jsonl")} if stage=="4b" else {}
    for x in rows:verify_row(root,x,es[x["identity"]],methods[x["method"]],offline.get(x["identity"]),dec)
    warm=r["warmup_counts"]
    require(r["counts"]["inputs"]==warm["inputs"]+len(rows)
        and r["counts"]["generator_levels"]==warm["generator_levels"]+sum(x["generator_levels"] for x in rows)
        and r["counts"]["decoder"]==warm["decoder"]+sum(x["decoder_forwards"] for x in rows),"WMT headline counters differ.")
    ix={(x["identity"],x["repeat"],x["method"]):x for x in rows}
    refs=[e["reference"] for e in selected];base=[ix[e["identity"],0,"full"]["text"] for e in selected]
    fullquality=scores(base,refs);summary={}
    for m in methods:
        group=[ix[e["identity"],k,m] for e in selected for k in range(3)]
        for e in selected:
            one=ix[e["identity"],0,m]
            for k in (1,2):require(ix[e["identity"],k,m]["ids"]==one["ids"] and ix[e["identity"],k,m]["codes"]==one["codes"],"WMT repeated output differs.")
            if one["exit_level"]==11:require(one["ids"]==ix[e["identity"],0,"full"]["ids"],"WMT final output differs from full.")
        hyps=[ix[e["identity"],0,m]["text"] for e in selected]
        basewall=np.array([[ix[e["identity"],k,"full"]["wall_ms"] for k in range(3)] for e in selected])
        wall=np.array([x["wall_ms"] for x in group]).reshape(-1,3)
        timing=paired_bootstrap(basewall,wall,np.zeros_like(wall),seed=20261023)
        timing.pop("quality_difference");timing.pop("quality_difference_ci95")
        quality=scores(hyps,refs);intervals=paired_quality(hyps,base,refs)
        summary[m]={"quality":quality,"quality_vs_full":intervals,"timing_vs_full":timing,
          "gate":claim_gate(timing,intervals,feasible(quality,fullquality)),
          "wall_ms":{"mean":float(wall.mean()),"median":float(np.median(wall)),"p95":float(np.percentile(wall,95))},
          "gpu_elapsed_ms_mean":float(np.mean([x["gpu_elapsed_ms"] for x in group])),
          "peak_allocated_bytes":max(x["peak_allocated_bytes"] for x in group),
          "mean_levels":float(np.mean([x["exit_level"] for x in group])),
          "mean_inspections":float(np.mean([len(x["inspections"]) for x in group])),
          "mean_codes":float(np.mean([len(x["codes"]) for x in group])),
          "early_requests":sum(x["exit_level"]<11 for x in group),"serial_warm_requests_per_second":1000/float(wall.mean())}
    fixedwall=np.array([[ix[e["identity"],k,"fixed"]["wall_ms"] for k in range(3)] for e in selected])
    adaptivewall=np.array([[ix[e["identity"],k,"adaptive"]["wall_ms"] for k in range(3)] for e in selected])
    timing=paired_bootstrap(fixedwall,adaptivewall,np.zeros_like(fixedwall),seed=20261023)
    timing.pop("quality_difference");timing.pop("quality_difference_ci95")
    primary=[ix[e["identity"],0,"adaptive"]["text"] for e in selected];fixed=[ix[e["identity"],0,"fixed"]["text"] for e in selected]
    quality=paired_quality(primary,fixed,refs)
    fixedgate=claim_gate(timing,quality,feasible(scores(primary,refs),scores(fixed,refs)))
    return {"task":"wmt14","stage":stage,"status":"complete","inputs":len(selected),"timed_requests":len(rows),
       "warmup_requests":r["warmup_requests"],"summary":summary,"decision":summary["adaptive"]["gate"],
       "primary_vs_fixed":{"timing":timing,"quality":quality,"gate":fixedgate},
       "adaptive_frontier_claim":summary["adaptive"]["gate"]=="go" and fixedgate=="go","counts":r["counts"]}

def report(root):
    from anytime_ncm.phase4_render import render
    out=root/OUTPUT;a=analyze(root,"4c");save(out/"analysis.json",a);render(root,a)
    save(out/"report_provenance.json",{"sources":source_hashes(root),"stages":{s:sha256(out/(s+".json")) for s in ("4a","4b","4c")},
       "artifacts":{n:sha256(out/n) for n in ("analysis.json","summary.md","comparison.png","quality_by_level.png","examples.json")}})
    return a
def verify(root,final=True):
    out=root/OUTPUT;verify_stage(root,"4a")
    require(audit_analysis(root)==json.loads((out/"audit_analysis.json").read_text()),"WMT audit/selection differs.")
    if not final:return {"status":"verified"}
    checked_lock(root);p=json.loads((out/"report_provenance.json").read_text())
    require(p["sources"]==source_hashes(root),"WMT report sources changed.")
    for n,h in p["artifacts"].items():require(sha256(out/n)==h,"WMT report artifact changed.")
    for s,h in p["stages"].items():require(sha256(out/(s+".json"))==h,"WMT stage changed.")
    for stage,name in (("4b","development_analysis.json"),("4c","analysis.json")):
        require(analyze(root,stage)==json.loads((out/name).read_text()),"WMT recomputed result differs.")
    return json.loads((out/"analysis.json").read_text())
