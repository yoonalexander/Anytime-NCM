"""Bounded WMT checkpoint execution; official function bodies and matched request clocks."""
from datetime import datetime,timezone
import json,time
import torch
from anytime_ncm.phase4 import (OUTPUT,LIMITS,begin,finish,failed,save,examples,verify_row,load_rows,
    audit_analysis,analyze,checked_lock,source_hashes)
from anytime_ncm.wmt_model import WmtModel,LEVELS,independent_prefixes
from anytime_ncm.upstream_adapter import reconstruct_prefixes
from anytime_ncm.target_encoding import model_fingerprint
from anytime_ncm.dataset import sha256
from anytime_ncm.screening import require
from anytime_ncm.wmt_data import StringRows
from anytime_ncm.wmt_metrics import scores

class Work:
    def __init__(self,model,limits):
        self.counts=dict.fromkeys(limits,0);self.calls=dict(generator_levels=0,decoder=0,encoder=0)
        self.limits=limits;self.handles=[]
        for module,key in ((model.net.transformer.blocks[0],"generator_levels"),
            (model.tokenizer.vqvae.decoder,"decoder"),(model.tokenizer.vqvae.encoder,"encoder")):
            self.handles.append(module.register_forward_pre_hook(lambda m,args,k=key:self.hook(k,args[0].shape[0])))
    def hook(self,key,n):self.take(key,n);self.calls[key]+=1
    def take(self,key,n=1):
        require(self.counts[key]+n<=self.limits[key],"WMT model-work cap exhausted: "+key);self.counts[key]+=n
    def close(self):
        for h in self.handles:h.remove()
def state(model):return {"generator":model_fingerprint(model.net),"tokenizer":model_fingerprint(model.tokenizer.vqvae)}
def load(root):
    torch.set_num_threads(4);require(torch.cuda.is_available(),"Validated CUDA required.")
    return WmtModel(root)
def baseline(root,model,work,n):
    indices=set(range(n))
    sources=StringRows((root/"data/wmt14/sources.pickle").read_bytes()).select(indices)
    refs=StringRows((root/"data/wmt14/reference_translations.pickle").read_bytes()).select(indices)
    hyps=[];started=time.perf_counter();torch.cuda.reset_peak_memory_stats()
    for start in range(0,n,8):
        batch=list(range(start,min(start+8,n)));work.take("inputs",len(batch));torch.manual_seed(20261023)
        x=torch.tensor([model.official["prefix"](sources[i]) for i in batch],device="cuda")
        hyps.extend(model.official["run"](x));model.official["RAW"].clear()
        if start%400==0:print(f"Official WMT baseline {n}: {start}/{n}",flush=True)
    result={"rows":n,"batch_size":8,"released_batch_size":64,"override":"predeclared memory headroom",
        "metrics":scores(hyps,[refs[i] for i in range(n)]),"process_seconds":time.perf_counter()-started,
        "process_seconds_are_not_warm_latency":True,"peak_allocated_bytes":torch.cuda.max_memory_allocated(),
        "prior_final_access":"internally scored all official rows; aggregate-only analyst inspection"}
    if n==32:result["exploration_smoke_outputs"]=[{"index":i,"text":h} for i,h in enumerate(hyps)]
    return result
@torch.no_grad()
def audit(root):
    out,path,r=begin(root,"4a");work=None
    try:
        model=load(root);r["state_before"]=state(model);work=Work(model,LIMITS["4a"]);r["counts"]=work.counts
        save(out/"official_smoke.json",baseline(root,model,work,32));save(path,r)
        save(out/"official_full.json",baseline(root,model,work,3003));save(path,r)
        entries=examples(root,"audit_exploration")+examples(root,"audit_development")
        with (out/"trajectories.jsonl").open("x",encoding="utf-8",newline="\n") as stream:
            for ix,e in enumerate(entries):
                torch.manual_seed(20261023)
                prefix=model.official["prefix"](e["source"]);context=torch.tensor([prefix],device="cuda")
                work.take("inputs");save(path,r)
                codes=model.codes(context) if ix<32 else model.net.generate(None,context,**model.kwargs)
                snapshots=reconstruct_prefixes(model.vq,codes);independent=independent_prefixes(model.vq,codes)
                require(len({z.untyped_storage().data_ptr() for z in snapshots})==11,"Snapshots alias.")
                levels=[]
                for level,(z,check) in enumerate(zip(snapshots,independent,strict=True),1):
                    torch.testing.assert_close(z,check,rtol=0,atol=0)
                    ids=model.pick(model.tokenizer.vqvae.decoder(z))[0].cpu().tolist()
                    levels.append({"level":level,"ids":ids,"text":model.decode(ids)})
                if ix<32:
                    torch.manual_seed(20261023);captured={};original=model.net.generate
                    def capture(*args,**kwargs):
                        g=original(*args,**kwargs);captured["codes"]=g;return g
                    model.net.generate=capture
                    work.take("inputs");save(path,r)
                    try:official=model.official["run"](context)[0]
                    finally:model.net.generate=original
                    require(torch.equal(codes,captured["codes"]) and levels[-1]["ids"]==model.official["RAW"][-1]
                        and levels[-1]["text"]==official,"WMT official/disabled exact parity failed.")
                    model.official["RAW"].clear()
                row={"identity":e["identity"],"index":e["index"],"partition":e["partition"],"prefix_ids":prefix,
                     "codes":codes[0].cpu().tolist(),"levels":levels}
                stream.write(json.dumps(row,separators=(",",":"),ensure_ascii=True)+"\n");stream.flush()
                r["completed_requests"]+=1;save(path,r)
                if (ix+1)%16==0:print(f"WMT audit {ix+1}/192 inputs; independent prefixes and final parity passed",flush=True)
        r.update(state_after=state(model),forward_calls=work.calls,exact_official_parity_inputs=32,
            full_resolution_checked_inputs=192,official_rows=3035,phase4_final_rows_materialized=0,
            execution={"python":__import__("sys").version.split()[0],"torch":torch.__version__,"cuda":torch.version.cuda,
                "gpu":torch.cuda.get_device_name(),"precision":"float32/eval","cpu_threads":4,"compile":False,"autocast":False})
        finish(out,path,r,["official_smoke.json","official_full.json","trajectories.jsonl"])
        analysis=audit_analysis(root);save(out/"audit_analysis.json",analysis)
        print("Phase 4A complete; selected development methods",analysis["selection"]["methods"],flush=True)
    except Exception as error:failed(path,r,error);raise
    finally:
        if work:work.close()

def order(methods,index):
    names=list(methods);shift=index%len(names);return names[shift:]+names[:shift]
def timed(model,source,spec,start_event,end_event):
    torch.cuda.reset_peak_memory_stats();torch.cuda.synchronize();torch.manual_seed(20261023)
    started=time.perf_counter_ns();start_event.record()
    result=model.request(source,spec)
    end_event.record();torch.cuda.synchronize()
    wall=(time.perf_counter_ns()-started)/1e6
    return result,wall,start_event.elapsed_time(end_event),torch.cuda.max_memory_allocated()
def bench(root,stage,methods):
    out,path,r=begin(root,stage);work=None
    try:
        if stage=="4c":
            manifest=json.loads((root/"docs/partitions/wmt14-phase4.json").read_text())
            save(out/"holdout_access.json",{"started_utc":datetime.now(timezone.utc).isoformat(),"phase4_final_groups":256,
              "canonical_indices":[e["index"] for e in manifest["partitions"]["phase4_final"]],
              "policy_lock_sha256":sha256(out/"policy_lock.json"),"prior_access":"official full aggregate baseline only"})
        selected=examples(root,"development" if stage=="4b" else "final");warm=examples(root,"warmup")
        model=load(root);r.update(state_before=state(model),methods=methods,method_order=list(methods),repeats=3,warmup_requests=0,timed_requests=0)
        work=Work(model,LIMITS[stage]);r["counts"]=work.counts;save(path,r)
        for i,e in enumerate(warm):
            for name in order(methods,i):
                work.take("inputs");save(path,r);torch.manual_seed(20261023);model.request(e["source"],methods[name]);r["warmup_requests"]+=1
        r["warmup_counts"]=dict(work.counts);save(path,r)
        start_event,end_event=torch.cuda.Event(enable_timing=True),torch.cuda.Event(enable_timing=True)
        old={x["identity"]:x for x in load_rows(out/"trajectories.jsonl")} if stage=="4b" else {}
        with (out/(stage+"_requests.jsonl")).open("x",encoding="utf-8",newline="\n") as stream:
            for i,e in enumerate(selected):
                for repeat in range(3):
                    for name in order(methods,i+repeat):
                        spec=methods[name];before=dict(work.counts);work.take("inputs");save(path,r)
                        result,wall,gpu,peak=timed(model,e["source"],spec,start_event,end_event)
                        result["codes"]=result["codes"][0].cpu().tolist()
                        counts={k:work.counts[k]-before[k] for k in before}
                        row={"identity":e["identity"],"index":e["index"],"partition":e["partition"],
                             "method":name,"repeat":repeat,"policy":spec,**result,"wall_ms":wall,
                             "gpu_elapsed_ms":gpu,"peak_allocated_bytes":peak,
                             "generator_levels":counts["generator_levels"],"decoder_forwards":counts["decoder"]}
                        verify_row(root,row,e,spec,old.get(e["identity"]),model.decode)
                        stream.write(json.dumps(row,separators=(",",":"),ensure_ascii=True)+"\n");stream.flush()
                        r["timed_requests"]+=1;r["completed_requests"]+=1
                save(path,r)
                if (i+1)%8==0:print(f"WMT {stage.upper()}: {i+1}/{len(selected)} inputs; {r['timed_requests']} timed requests",flush=True)
        r.update(state_after=state(model),forward_calls=work.calls,execution={
            "gpu":torch.cuda.get_device_name(),"torch":torch.__version__,"cuda":torch.version.cuda,
            "batch_size":1,"precision":"float32/eval","cpu_threads":4,"compile":False,"autocast":False})
        finish(out,path,r,[stage+"_requests.jsonl"]+(["holdout_access.json"] if stage=="4c" else []))
    except Exception as error:failed(path,r,error);raise
    finally:
        if work:work.close()
def development(root):
    from anytime_ncm.phase4 import verify
    out=root/OUTPUT;verify(root,False)
    methods=json.loads((out/"audit_analysis.json").read_text())["selection"]["methods"]
    bench(root,"4b",methods);save(out/"development_analysis.json",analyze(root,"4b"))
    save(out/"policy_lock.json",{"status":"frozen","frozen_utc":datetime.now(timezone.utc).isoformat(),
        "methods":methods,"sources":source_hashes(root),"artifacts":{n:sha256(out/n) for n in
        ("4a.json","4b.json","audit_analysis.json","development_analysis.json")},
        "quality_tolerances":{"bleu":.5,"chrf":1.},"latency_minimum_reduction":.05,
        "bootstrap":{"resamples":10000,"seed":20261023},"phase4_final_groups_opened":0})
    print("WMT 4B complete; commit/push policy lock before final access.",flush=True)
def final(root):
    lock=checked_lock(root);bench(root,"4c",lock["methods"])
