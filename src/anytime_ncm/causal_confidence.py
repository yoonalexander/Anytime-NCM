"""Current decoder confidence and literal cue features; no future or ID inputs."""
import math
import time
import numpy as np
import torch
from anytime_ncm.online import IncrementalLatent
from anytime_ncm.quality_controller import FEATURES,features,GERMAN_NEGATION
from anytime_ncm.wmt_policy import cues

CONFIDENCE_NAMES=('margin_mean','margin_p10','margin_min','entropy_mean','entropy_p90','entropy_max')
CUE_NAMES=('source_has_numbers','source_number_recall','source_number_precision','source_numbers_equal','negation_cue_agreement')
RICH_NAMES=FEATURES+CONFIDENCE_NAMES+CUE_NAMES

@torch.no_grad()
def confidence_features(logits,ids,eos=None):
    if logits.ndim!=3 or logits.shape[0]!=1 or logits.shape[1]!=64 or logits.shape[2]<2 or len(ids)!=64:
        raise ValueError('Require current one-input full-resolution logits')
    end=ids.index(eos)+1 if eos is not None and eos in ids else 64
    current=logits[0,:end,:]
    top=current.topk(2,dim=-1).values
    margin=top[:,0]-top[:,1]
    logp=current.log_softmax(dim=-1)
    entropy=-(logp.exp()*logp).sum(dim=-1)/math.log(current.shape[-1])
    values=torch.stack((margin,entropy)).cpu().numpy()
    result=np.array([values[0].mean(),np.quantile(values[0],.1),values[0].min(),
                     values[1].mean(),np.quantile(values[1],.9),values[1].max()],dtype=float)
    if not np.isfinite(result).all():raise ValueError('Nonfinite confidence signal')
    if result[:3].min() < -1e-6 or result[3:].min() < -1e-6 or result[3:].max()>1+1e-6:
        raise ValueError('Confidence summaries outside expected bounds')
    return result

def cue_features(source,text):
    sn,_=cues(source);tn,neg=cues(text);s,t=set(sn),set(tn);match=len(s&t)
    return np.array([bool(s),match/len(s) if s else 1.,match/len(t) if t else float(not s),s==t,
        bool(GERMAN_NEGATION.search(source))==neg],dtype=float)

@torch.no_grad()
def instrumented_request(model,source,kind,meter=None):
    if kind not in ('cheap','rich'):raise ValueError('Unknown fixed instrumentation')
    if any(m.training for net in (model.net,model.tokenizer.vqvae) for m in net.modules()):raise ValueError('Require eval mode')
    prefix=model.official['prefix'](source)
    context=torch.tensor([prefix],dtype=torch.long,device=next(model.net.parameters()).device)
    monitor=IncrementalLatent(model.vq);observations=[];vectors=[];previous=None;component_ms=dict(cheap=0.,extra=0.)
    def observe(level,codes):
        nonlocal previous
        logits=model.tokenizer.vqvae.decoder(monitor.snapshot(codes,level))
        ids=model.pick(logits)[0].cpu().tolist();text=model.decode(ids)
        observations.append(dict(level=level,ids=ids,text=text))
        if level<11:
            if meter:meter.take('cheap_features')
            started=time.perf_counter_ns()
            v=features(source,level,codes[0].cpu().tolist(),ids,text,previous)
            component_ms['cheap']+=(time.perf_counter_ns()-started)/1e6
            if kind=='rich':
                if meter:meter.take('confidence_features');meter.take('cue_features')
                started=time.perf_counter_ns()
                confidence=confidence_features(logits,ids,model.official.get('EOS'))
                v=np.r_[v,confidence,cue_features(source,text)]
                component_ms['extra']+=(time.perf_counter_ns()-started)/1e6
            if not np.isfinite(v).all():raise ValueError('Nonfinite feature vector')
            vectors.append(dict(level=level,values=v.tolist()))
            previous=dict(level=level,ids=ids,text=text)
        return False
    observe.inspection_levels=frozenset((8,10,11))
    codes=model.codes(context,callback=observe,maximum=11)
    if codes.shape!=(1,sum(model.vq.levels)) or [o['level'] for o in observations]!=[8,10,11]:raise ValueError('Wrong fixed instrumentation schedule')
    return dict(prefix_ids=prefix,codes=codes,exit_level=11,observations=observations,ids=observations[-1]['ids'],text=observations[-1]['text'],features=vectors,component_ms=component_ms)
