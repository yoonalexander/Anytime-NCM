"""Actual causal sparse stopping, charging every feature/decision in request time."""
import torch
from anytime_ncm.online import IncrementalLatent
from anytime_ncm.forced_wmt import forced_request

@torch.no_grad()
def controller_request(model,source,controller):
    if controller.spec['kind']=='full':return forced_request(model,source,11,'terminal')
    if any(m.training for net in (model.net,model.tokenizer.vqvae) for m in net.modules()):raise ValueError('Require eval mode')
    prefix=model.official['prefix'](source)
    context=torch.tensor([prefix],dtype=torch.long,device=next(model.net.parameters()).device)
    monitor=IncrementalLatent(model.vq);observations=[];previous=None
    def observe(level,codes):
        nonlocal previous
        ids=model.pick(model.tokenizer.vqvae.decoder(monitor.snapshot(codes,level)))[0].cpu().tolist()
        text=model.decode(ids);observations.append(dict(level=level,ids=ids,text=text))
        if level==11:return True
        current_codes=codes[0].cpu().tolist() if controller.spec['kind']=='ridge' else []
        stop=controller.observe(source,level,current_codes,ids,text,previous)
        previous=dict(level=level,ids=ids,text=text)
        return stop
    observe.inspection_levels=frozenset((8,10,11))
    codes=model.codes(context,callback=observe,maximum=11)
    depth=observations[-1]['level']
    if codes.shape!=(1,sum(model.vq.levels[:depth])):raise ValueError('Wrong causal boundary')
    return dict(prefix_ids=prefix,codes=codes,exit_level=depth,observations=observations,
                ids=observations[-1]['ids'],text=observations[-1]['text'])
