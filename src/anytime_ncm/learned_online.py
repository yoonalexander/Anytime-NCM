"""Learned callbacks reuse the proven isolated generator and incremental monitor."""
import time
import torch
from anytime_ncm.online import OnlineRunner,IncrementalLatent
from anytime_ncm.learned_features import FeatureTracker,probability,LENGTHS

class LearnedRunner(OnlineRunner):
    @torch.no_grad()
    def request(self,puzzle,spec):
        if spec["kind"]!="learned":return super().request(puzzle,spec)
        model=spec["model"];minimum=spec["minimum"];threshold=spec["threshold"]
        if type(minimum)is not int or not 1<=minimum<=12 or not 0<=threshold<=1:
            raise ValueError("Invalid learned policy bounds.")
        adapter=self.adapter
        if any(m.training for net in (adapter.generator,adapter.tokenizer.vqvae) for m in net.modules()):
            raise ValueError("All models must be in eval mode.")
        context=torch.tensor([puzzle],dtype=torch.long,device=next(adapter.generator.parameters()).device)
        monitor=IncrementalLatent(adapter.vq);tracker=FeatureTracker(puzzle,model["family"])
        trace=[];latest={}
        def callback(level,prefix):
            latent=monitor.snapshot(prefix,level)
            ids=adapter.pick_tokens(adapter.tokenizer.vqvae.decoder(latent))[0].cpu().tolist()
            text=adapter.decode_ids(ids)
            current=prefix[0,-LENGTHS[level-1]:].cpu().tolist()
            started=time.perf_counter_ns()
            features=tracker.observe(level,ids,current);p=probability(model,features)
            cpu_ms=(time.perf_counter_ns()-started)/1e6
            trace.append({"level":level,"features":list(features),"probability":p,
                          "decoded_ids":ids,"feature_policy_ms":cpu_ms})
            latest.update(ids=ids,text=text,level=level)
            return bool(level<12 and p>=threshold)
        callback.inspection_levels=frozenset(range(minimum,13))
        codes=self.codes(context,callback=callback,maximum=12)
        depth=latest["level"]
        return {"decoded_ids":latest["ids"],"decoded_text":latest["text"],"exit_level":depth,
                "generated_codes":codes,"inspected_levels":[r["level"] for r in trace],"learned_trace":trace}
