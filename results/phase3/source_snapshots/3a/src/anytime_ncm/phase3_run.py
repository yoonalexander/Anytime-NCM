"""Finite released-checkpoint Phase 3 development/final requests."""
from datetime import datetime,timezone
import json
import torch
from anytime_ncm.phase3 import (OUTPUT,LIMITS,begin,finish,failed,save,examples,selected_methods,
    verify_row,load_rows,analyze,verify_stage,checked_lock,source_hashes)
from anytime_ncm.phase2 import warm_order
from anytime_ncm.phase2_run import timed_request,model_state
from anytime_ncm.learned_online import LearnedRunner
from anytime_ncm.online import WorkCounter
from anytime_ncm.screening_inference import load_candidate
from anytime_ncm.screening import require
from anytime_ncm.sudoku import validate_solution
from anytime_ncm.dataset import sha256

def bench(root,stage,methods):
    out,path,receipt=begin(root,stage);work=None
    try:
        if stage=="3c":
            manifest=json.loads((root/"docs/partitions/sudoku-easy-r2.json").read_text(encoding="utf-8"))
            save(out/"holdout_access.json",{"stage":stage,"started_utc":datetime.now(timezone.utc).isoformat(),
                 "policy_lock_sha256":sha256(out/"policy_lock.json"),
                 "selected_phase3_final_indices":[r["index"] for r in manifest["partitions"]["phase3_final"]],
                 "phase3_final_rows":300,"phase2_final_rows_materialized":0,
                 "prior_access":"full official baselines scored internally, aggregate-only analyst access; identity-only hashes traversed all rows"})
        selected=examples(root,stage);warmups=examples(root,"warmup")
        old={r["sample_id"]:r for r in load_rows(root/"results/followup/sudoku_easy_r3/trajectories.jsonl")} if stage=="3b" else {}
        receipt.update(methods=methods,repeats=3,warmup_requests=0,timed_requests=0,
            selected_examples=[{"index":e.index,"sample_id":e.identity,"partition":e.partition} for e in selected])
        torch.set_num_threads(4);require(torch.cuda.is_available(),"Validated GPU unavailable.")
        adapter=load_candidate(root,"easy");runner=LearnedRunner(adapter,root/"third_party/ncm")
        receipt["state_before"]=model_state(adapter);work=WorkCounter(adapter,LIMITS[stage])
        receipt["counts"]=work.counts;save(path,receipt)
        for i,e in enumerate(warmups):
            for name in warm_order(methods,i):
                work.take("inputs");save(path,receipt);runner.request(e.puzzle,methods[name]);receipt["warmup_requests"]+=1
        receipt["warmup_counts"]=dict(work.counts);save(path,receipt)
        torch.cuda.synchronize()
        start,end=torch.cuda.Event(enable_timing=True),torch.cuda.Event(enable_timing=True)
        with (out/(stage+"_requests.jsonl")).open("x",encoding="utf-8",newline="\n") as stream:
            for i,e in enumerate(selected):
                for repeat in range(3):
                    for name in warm_order(methods,i+repeat):
                        spec=methods[name];before=dict(work.counts)
                        work.take("inputs");save(path,receipt)
                        result,wall,gpu,peak=timed_request(runner,e.puzzle,spec,start,end)
                        result["generated_codes"]=result["generated_codes"][0].tolist()
                        verdict=validate_solution(e.puzzle,result["decoded_ids"],reference=e.reference)
                        counts={k:work.counts[k]-before[k] for k in before}
                        row={"sample_id":e.identity,"dataset_index":e.index,"partition":e.partition,
                             "method":name,"repeat":repeat,"policy":spec,**result,"wall_ms":wall,
                             "gpu_elapsed_ms":gpu,"peak_allocated_bytes":peak,"valid":verdict.is_valid_solution,
                             "reference_agreement":verdict.reference_agreement,
                             "false_early_accept":result["exit_level"]<12 and not verdict.is_valid_solution,
                             "generator_levels":counts["generator_levels"],"decoder_forwards":counts["decoder"]}
                        verify_row(row,e,spec,old.get(e.identity))
                        stream.write(json.dumps(row,separators=(",",":"),allow_nan=False)+"\n");stream.flush()
                        receipt["timed_requests"]+=1;receipt["completed_requests"]+=1
                save(path,receipt)
                if (i+1)%10==0:print(f"Phase {stage.upper()}: {i+1}/{len(selected)} identities; {receipt['timed_requests']} timed requests",flush=True)
        receipt["state_after"]=model_state(adapter)
        require(receipt["state_before"]==receipt["state_after"],"Model state mutated.")
        receipt["execution"]={"python":__import__("sys").version.split()[0],"torch":torch.__version__,
            "cuda":torch.version.cuda,"gpu":torch.cuda.get_device_name(),"precision":"float32/eval","batch_size":1,
            "cpu_threads":4,"autocast":False,"compile":False,"kv_cache":False}
        finish(out,path,receipt,[stage+"_requests.jsonl"]+(["holdout_access.json"] if stage=="3c" else []))
    except Exception as error:failed(path,receipt,error);raise
    finally:
        if work:work.close()

def development(root):
    from anytime_ncm.train_policy import verify_training
    out=root/OUTPUT;verify_training(root)
    methods=selected_methods(root);bench(root,"3b",methods)
    analysis=analyze(root,"3b");save(out/"development_analysis.json",analysis)
    save(out/"policy_lock.json",{"study":"Phase 3","status":"frozen","frozen_utc":datetime.now(timezone.utc).isoformat(),
        "methods":methods,"primary_method":"learned_internal","source_sha256":source_hashes(root),
        "artifacts_sha256":{n:sha256(out/n) for n in ("training.json","3a.json","3b.json","development_analysis.json")},
        "bootstrap":{"resamples":10000,"seed":20261022,"unit":"paired identity with all three repeats"},
        "phase3_final_rows_materialized_before_lock":0})
    print("Phase 3B complete; lock must be committed/pushed before final access.",flush=True)
def final(root):
    lock=checked_lock(root);bench(root,"3c",lock["methods"])
