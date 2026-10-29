"""Native full-generation development traces with prefix-isolated offline features."""
import numpy as np
import torch
from anytime_ncm.online import IncrementalLatent
from anytime_ncm.quality_controller import features
from anytime_ncm.causal_light import logit_summary
from anytime_ncm.causal_confidence import cue_features

def current_logits(model,codes,level,monitor=None):
    if type(level)is not int or not 1<=level<=11 or codes.ndim!=2 or codes.shape[0]!=1 or codes.shape[1]<sum(model.vq.levels[:level]):raise ValueError('Invalid current prefix request')
    monitor=IncrementalLatent(model.vq) if monitor is None else monitor
    current=codes[:,:sum(model.vq.levels[:level])]
    return model.tokenizer.vqvae.decoder(monitor.snapshot(current,level))

@torch.no_grad()
def trace_request(model,source,meter=None):
    if any(m.training for net in (model.net,model.tokenizer.vqvae) for m in net.modules()):raise ValueError('Require eval mode')
    prefix=model.official['prefix'](source);context=torch.tensor([prefix],dtype=torch.long,device=next(model.net.parameters()).device)
    try:codes=model.net.generate(None,context,**model.kwargs)
    finally:model.net._cfg=None
    if codes.shape!=(1,sum(model.vq.levels)):raise ValueError('Wrong native full code shape')
    code_values=codes[0].cpu().tolist();monitor=IncrementalLatent(model.vq);levels=[];vectors=[];previous=None
    for d in range(1,12):
        logits=current_logits(model,codes,d,monitor);picked=model.pick(logits);ids=picked[0].cpu().tolist();text=model.decode(ids);levels.append(dict(level=d,ids=ids,text=text))
        if d in (8,10):
            if meter:meter.take('cheap_features');meter.take('selected_logit_features');meter.take('cue_features')
            current=code_values[:sum(model.vq.levels[:d])];base=features(source,d,current,ids,text,previous)
            signal=logit_summary(logits,ids,'selected_logit',model.official.get('EOS'),picked);v=np.r_[base,signal,cue_features(source,text)]
            if not np.isfinite(v).all():raise ValueError('Nonfinite development feature')
            vectors.append(dict(level=d,values=v.tolist()));previous=dict(level=d,ids=ids,text=text)
    direct=model.pick(model.tokenizer.vqvae.decoder(model.vq.idx_to_z_q(codes)))[0].cpu().tolist()
    if direct!=levels[-1]['ids'] or model.decode(direct)!=levels[-1]['text']:raise ValueError('Direct native-final decoder parity failed')
    return dict(prefix_ids=prefix,codes=code_values,levels=levels,features=vectors,native_final_parity=True)
