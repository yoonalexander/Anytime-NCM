"""Finite Phase 2 CUDA runs; request timers include deployed monitoring work."""
from datetime import datetime, timezone
import json
from pathlib import Path
import time
import torch

from anytime_ncm.online import OnlineRunner, WorkCounter
from anytime_ncm.online_policy import policy_spec, simulated_exit
from anytime_ncm.phase2 import (OUTPUT, LIMITS, begin, end, failed, save, examples, sources,
    verify_stage, offline_policies, warm_order, analyze_requests, verify_request, load_rows, execution_sources)
from anytime_ncm.screening import require
from anytime_ncm.screening_inference import load_candidate
from anytime_ncm.target_encoding import model_fingerprint
from anytime_ncm.sudoku import validate_solution
from anytime_ncm.dataset import sha256

def model_state(adapter):
    return {"generator":model_fingerprint(adapter.generator),"tokenizer":model_fingerprint(adapter.tokenizer.vqvae)}

def load(root):
    torch.set_num_threads(4)
    require(torch.cuda.is_available(),"Validated CUDA environment unavailable.")
    adapter=load_candidate(root,"easy")
    return adapter,OnlineRunner(adapter,root/"third_party/ncm")

def converted(result):
    return {**result,"generated_codes":result["generated_codes"][0].tolist()}

def emit_a(root):
    out,path,receipt=begin(root,"2a")
    work=None
    try:
        adapter,runner=load(root)
        receipt["state_before"]=model_state(adapter)
        (out/"upstream_level_hook.patch.txt").write_text(runner.patch,encoding="utf-8",newline="\n")
        work=WorkCounter(adapter,LIMITS["2a"]);receipt["counts"]=work.counts
        selected=examples(root,"2a")
        offline={r["dataset_index"]:r for r in load_rows(root/"results/followup/sudoku_easy_r3/trajectories.jsonl")}
        specs={"full":policy_spec("full"),"disabled":policy_spec("full"),
            "forced1":policy_spec("fixed",depth=1),"forced6":policy_spec("fixed",depth=6),
            "verified_all":policy_spec("verified",levels=list(range(1,13))),
            "stability":policy_spec("stability",min_level=2,patience=1)}
        with (out/"2a_requests.jsonl").open("x",encoding="utf-8",newline="\n") as stream:
            for e in selected:
                for name,spec in specs.items():
                    before=dict(work.counts);work.take("inputs");save(path,receipt)
                    if name=="disabled":
                        context=torch.tensor([e.puzzle],dtype=torch.long,device="cuda")
                        codes=runner.codes(context)
                        raw=adapter.pick_tokens(adapter.tokenizer.vqvae.decoder(adapter.vq.idx_to_z_q(codes)))[0].cpu().tolist()
                        result={"decoded_ids":raw,"decoded_text":adapter.decode_ids(raw),"exit_level":12,
                                "generated_codes":codes,"inspected_levels":[]}
                    else:
                        result=runner.request(e.puzzle,spec)
                    result=converted(result)
                    expected=simulated_exit(spec,offline[e.index]["levels"])
                    require(result["exit_level"]==expected and result["decoded_ids"]==offline[e.index]["levels"][expected-1]["decoded_ids"],
                            "Real offline/online parity failed.")
                    expected_codes=[c for s in offline[e.index]["levels"][:expected] for c in s["code_ids"]]
                    require(result["generated_codes"]==expected_codes,"Generated-prefix parity failed.")
                    counts={k:work.counts[k]-before[k] for k in before}
                    require(counts["generator_levels"]==expected,"Online stopping did not skip actual generator work.")
                    row={"sample_id":e.identity,"dataset_index":e.index,"partition":e.partition,
                         "case":name,"policy":spec,**result,"counts":counts}
                    stream.write(json.dumps(row,separators=(",",":"))+"\n");stream.flush()
                    receipt["completed_requests"]+=1
                save(path,receipt)
                if (e.index+1)%8==0:print(f"Phase 2A real parity {e.index+1}/32 inputs",flush=True)
        receipt["state_after"]=model_state(adapter)
        require(receipt["state_before"]==receipt["state_after"] and work.counts["inputs"]==192,"2A state/count failure.")
        receipt.update(real_inputs=32,requests=192,upstream_base="c70274273f489abc73832b2b98584a8483b6b203",
                       sampling_changed=False,vendored_checkout_modified=False,timed_requests=0)
        end(out,path,receipt,["2a_requests.jsonl","upstream_level_hook.patch.txt"])
    except Exception as error:
        failed(path,receipt,error);raise
    finally:
        if work:work.close()

def timed_request(runner,puzzle,spec,start_event,end_event):
    torch.cuda.reset_peak_memory_stats()
    torch.cuda.synchronize()
    started=time.perf_counter_ns()
    start_event.record()
    result=runner.request(puzzle,spec)
    end_event.record()
    torch.cuda.synchronize()
    wall=(time.perf_counter_ns()-started)/1e6
    gpu=start_event.elapsed_time(end_event)
    peak=torch.cuda.max_memory_allocated()
    return result,wall,gpu,peak

def bench(root,stage,methods,offline=None):
    out,path,receipt=begin(root,stage)
    work=None
    if stage=="2c":
        # Record selected final identities/access before token operands are opened.
        manifest=json.loads((root/"docs/partitions/sudoku-easy-r2.json").read_text(encoding="utf-8"))
        save(out/"holdout_access.json",{"stage":"2c","started_utc":datetime.now(timezone.utc).isoformat(),
            "policy_lock_sha256":sha256(out/"policy_lock.json"),"phase2_final_indices":[r["index"] for r in manifest["partitions"]["phase2_final"]],
            "phase2_final_rows":300,"phase3_final_rows_materialized":0,
            "prior_access":"unchanged official full baselines scored internally; aggregate-only analyst inspection",
            "reader":"restricted non-executing token scanner; unselected operands not materialized"})
    selected=examples(root,stage)
    warmups=examples(root,"warmup")
    receipt.update(methods=methods,repeats=3,selected_examples=[{"index":e.index,"sample_id":e.identity,"partition":e.partition} for e in selected],
                   warmup_inputs=10,warmup_requests=0,timed_requests=0,phase3_final_rows_materialized=0)
    try:
        adapter,runner=load(root);receipt["state_before"]=model_state(adapter)
        work=WorkCounter(adapter,LIMITS[stage]);receipt["counts"]=work.counts;save(path,receipt)
        for i,e in enumerate(warmups):
            for name in warm_order(methods,i):
                work.take("inputs");save(path,receipt)
                runner.request(e.puzzle,methods[name])
                receipt["warmup_requests"]+=1
        receipt["warmup_counts"]=dict(work.counts)
        save(path,receipt)
        torch.cuda.synchronize()
        start_event,end_event=torch.cuda.Event(enable_timing=True),torch.cuda.Event(enable_timing=True)
        with (out/(stage+"_requests.jsonl")).open("x",encoding="utf-8",newline="\n") as stream:
            for i,e in enumerate(selected):
                for repeat in range(3):
                    for name in warm_order(methods,i+repeat):
                        spec=methods[name];before=dict(work.counts)
                        work.take("inputs");save(path,receipt)
                        result,wall,gpu,peak=timed_request(runner,e.puzzle,spec,start_event,end_event)
                        result=converted(result)
                        verdict=validate_solution(e.puzzle,result["decoded_ids"],reference=e.reference)
                        counts={k:work.counts[k]-before[k] for k in before}
                        row={"sample_id":e.identity,"dataset_index":e.index,"partition":e.partition,
                            "method":name,"repeat":repeat,"policy":spec,**result,"wall_ms":wall,"gpu_elapsed_ms":gpu,
                            "peak_allocated_bytes":peak,"valid":verdict.is_valid_solution,
                            "reference_agreement":verdict.reference_agreement,
                            "false_early_accept":result["exit_level"]<12 and not verdict.is_valid_solution,
                            "generator_levels":counts["generator_levels"],"decoder_forwards":counts["decoder"]}
                        verify_request(row,e,spec,None if offline is None else offline[e.identity])
                        stream.write(json.dumps(row,separators=(",",":"),allow_nan=False)+"\n");stream.flush()
                        receipt["timed_requests"]+=1;receipt["completed_requests"]+=1
                save(path,receipt)
                if (i+1)%10==0:print(f"Phase {stage.upper()} benchmark {i+1}/{len(selected)} identities; {receipt['timed_requests']} timed requests",flush=True)
        receipt["state_after"]=model_state(adapter)
        require(receipt["state_before"]==receipt["state_after"],"Benchmark mutated model weights/buffers.")
        receipt["execution"]={"python":__import__("sys").version.split()[0],"torch":torch.__version__,"cuda":torch.version.cuda,
             "gpu":torch.cuda.get_device_name(),"precision":"float32/eval","batch_size":1,"cpu_threads":4,
             "compile":False,"autocast":False,"kv_cache":False,"gpu_time":"CUDA event stream elapsed, including host gaps"}
        end(out,path,receipt,[stage+"_requests.jsonl"]+(["holdout_access.json"] if stage=="2c" else []))
        return selected
    except Exception as error:
        failed(path,receipt,error);raise
    finally:
        if work:work.close()

def development(root):
    out=root/OUTPUT
    verify_stage(root,"2a")
    trajectories=load_rows(root/"results/followup/sudoku_easy_r3/trajectories.jsonl")
    old=json.loads((root/"results/followup/sudoku_easy_r3/analysis.json").read_text(encoding="utf-8"))
    selection=offline_policies(trajectories,old)
    save(out/"development_candidates.json",selection)
    by_id={r["sample_id"]:r for r in trajectories}
    selected=bench(root,"2b",selection["methods"],by_id)
    rows=load_rows(out/"2b_requests.jsonl")
    summaries=analyze_requests(rows,selection["methods"],selected)
    eligible=[name for name in selection["methods"] if name.startswith("verified")
              and summaries[name]["false_early_accepts"]==0
              and summaries[name]["valid_rate"]>=summaries["full"]["valid_rate"]]
    require(eligible,"No safe verifier schedule; correctness investigation required.")
    chosen=min(eligible,key=lambda n:(summaries[n]["wall_ms"]["mean"],n))
    methods={n:selection["methods"][n] for n in ("full","fixed","verified_all")}
    aliases={}
    if chosen=="verified_all":aliases["verified_selected"]="verified_all"
    else:methods["verified_selected"]=selection["methods"][chosen]
    methods["stability"]=selection["methods"]["stability"]
    analysis={"study":"Phase 2B","selection":selection,"online_development":summaries,
              "selected_verifier":chosen,"final_methods":methods,"aliases":aliases,
              "primary_method":"verified_selected" if "verified_selected" in methods else "verified_all"}
    save(out/"development_analysis.json",analysis)
    lock={"study":"Phase 2","status":"frozen","frozen_utc":datetime.now(timezone.utc).isoformat(),
        "methods":methods,"aliases":aliases,"primary_method":analysis["primary_method"],"repeats":3,
        "phase3_final_access":False,"source_sha256":sources(root),"execution_source_sha256":execution_sources(root),"stage2b_sha256":sha256(out/"2b.json"),
        "development_analysis_sha256":sha256(out/"development_analysis.json"),
        "protocol_sha256":sha256(root/"docs/studies/phase2-easy-online-protocol.md"),
        "bootstrap":{"seed":20261022,"resamples":10000,"unit":"paired identity; all three repeats retained"}}
    save(out/"policy_lock.json",lock)
    print("Phase 2B selected",chosen,"for primary verification; freeze written before final access.",flush=True)

def final(root):
    from anytime_ncm.phase2 import checked_lock
    lock=checked_lock(root)
    bench(root,"2c",lock["methods"])
