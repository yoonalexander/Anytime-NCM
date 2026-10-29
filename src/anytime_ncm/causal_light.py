"""Lighter current-logit instrumentation; no entropy, future outputs or fitted weights."""
import time
import numpy as np
import torch
from anytime_ncm.online import IncrementalLatent
from anytime_ncm.quality_controller import FEATURES,features
from anytime_ncm.causal_confidence import cue_features,CUE_NAMES

KINDS=('cheap','margin','selected_logit')
FEATURE_NAMES=dict(cheap=FEATURES,margin=FEATURES+('margin_mean','margin_p10','margin_min')+CUE_NAMES,
    selected_logit=FEATURES+('selected_logit_mean','selected_logit_p10','selected_logit_min')+CUE_NAMES)

@torch.no_grad()
def logit_summary(logits,ids,kind,eos=None,picked_ids=None):
    if kind not in ('margin','selected_logit') or logits.ndim!=3 or logits.shape[0]!=1 or logits.shape[1]!=64 or logits.shape[2]<2 or len(ids)!=64:
        raise ValueError('Require frozen current-logit summary inputs')
    end=ids.index(eos)+1 if eos is not None and eos in ids else 64;current=logits[0,:end]
    if kind=='margin':
        v=current.topk(2,dim=-1).values;scalar=v[:,0]-v[:,1]
    else:
        if picked_ids is None:index=torch.tensor(ids[:end],dtype=torch.long,device=logits.device)[:,None]
        else:
            if picked_ids.shape!=(1,64) or picked_ids.dtype!=torch.long or picked_ids.device!=logits.device:raise ValueError('Require current picked IDs')
            index=picked_ids[0,:end,None]
        scalar=current.gather(-1,index).squeeze(-1)
    a=scalar.cpu().numpy();out=np.array([a.mean(),np.quantile(a,.1),a.min()],dtype=float)
    if not np.isfinite(out).all() or (kind=='margin' and out.min()<-1e-6):raise ValueError('Invalid light signal')
    return out

@torch.no_grad()
def instrumented_request(model,source,kind,meter=None):
    if kind not in KINDS:raise ValueError('Unknown light instrumentation')
    if any(m.training for net in (model.net,model.tokenizer.vqvae) for m in net.modules()):raise ValueError('Require eval mode')
    prefix=model.official['prefix'](source)
    context=torch.tensor([prefix],dtype=torch.long,device=next(model.net.parameters()).device)
    monitor=IncrementalLatent(model.vq);observations=[];vectors=[];prefix_codes=[];previous=None;component_ms=dict(cheap=0.,extra=0.)
    def observe(level,codes):
        nonlocal previous
        logits=model.tokenizer.vqvae.decoder(monitor.snapshot(codes,level));picked=model.pick(logits)
        ids=picked[0].cpu().tolist();text=model.decode(ids);current_codes=codes[0].cpu().tolist()
        prefix_codes.append(dict(level=level,codes=current_codes));observations.append(dict(level=level,ids=ids,text=text))
        if level<11:
            if meter:meter.take('cheap_features')
            started=time.perf_counter_ns();v=features(source,level,current_codes,ids,text,previous);component_ms['cheap']+=(time.perf_counter_ns()-started)/1e6
            if kind!='cheap':
                if meter:meter.take(kind+'_features');meter.take('cue_features')
                started=time.perf_counter_ns();signal=logit_summary(logits,ids,kind,model.official.get('EOS'),picked)
                v=np.r_[v,signal,cue_features(source,text)];component_ms['extra']+=(time.perf_counter_ns()-started)/1e6
            if not np.isfinite(v).all():raise ValueError('Nonfinite light feature vector')
            vectors.append(dict(level=level,values=v.tolist()));previous=dict(level=level,ids=ids,text=text)
        return False
    observe.inspection_levels=frozenset((8,10,11));codes=model.codes(context,callback=observe,maximum=11)
    if codes.shape!=(1,sum(model.vq.levels)) or [o['level'] for o in observations]!=[8,10,11]:raise ValueError('Wrong light schedule')
    return dict(prefix_ids=prefix,codes=codes,exit_level=11,observations=observations,ids=observations[-1]['ids'],text=observations[-1]['text'],
        features=vectors,component_ms=component_ms,prefix_codes=prefix_codes)
