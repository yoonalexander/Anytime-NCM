"""Actual current-state stopping for frozen joint-risk policies."""
import numpy as np
import torch
from anytime_ncm.online import IncrementalLatent
from anytime_ncm.forced_wmt import forced_request
from anytime_ncm.quality_controller import features
from anytime_ncm.causal_confidence import cue_features
from anytime_ncm.causal_light import logit_summary
from anytime_ncm.joint_risk_controller import decision

@torch.no_grad()
def joint_request(model,source,spec,meter=None):
    if spec['kind']=='full':return forced_request(model,source,11,'terminal')
    if spec['kind']!='joint_ridge' or spec['decision_levels'] not in ([8],[8,10]) or spec['group'] not in ('cheap','selected_logit'):raise ValueError('Invalid frozen policy')
    if any(m.training for net in (model.net,model.tokenizer.vqvae) for m in net.modules()):raise ValueError('Require eval mode')
    prefix=model.official['prefix'](source);context=torch.tensor([prefix],dtype=torch.long,device=next(model.net.parameters()).device)
    monitor=IncrementalLatent(model.vq);observations=[];vectors=[];prefix_codes=[];previous=None
    def observe(level,codes):
        nonlocal previous
        logits=model.tokenizer.vqvae.decoder(monitor.snapshot(codes,level));picked=model.pick(logits);ids=picked[0].cpu().tolist();text=model.decode(ids)
        observations.append(dict(level=level,ids=ids,text=text))
        if level==11:return True
        current_codes=codes[0].cpu().tolist();prefix_codes.append(dict(level=level,codes=current_codes))
        if meter:meter.take('cheap_features')
        base=features(source,level,current_codes,ids,text,previous)
        if spec['group']=='selected_logit':
            if meter:meter.take('selected_logit_features')
            summary=logit_summary(logits,ids,'selected_logit',model.official.get('EOS'),picked)
        else:summary=np.zeros(3)
        if spec['group']=='selected_logit' or spec['cue_guard']:
            if meter:meter.take('cue_features')
            cues=cue_features(source,text)
        else:cues=np.zeros(5)
        v=np.r_[base,summary,cues];vectors.append(dict(level=level,values=v.tolist()))
        stop=decision(spec,level,v,meter);previous=dict(level=level,ids=ids,text=text);return stop
    observe.inspection_levels=frozenset(spec['decision_levels']+[11]);codes=model.codes(context,callback=observe,maximum=11);depth=observations[-1]['level']
    expected=[d for d in spec['decision_levels']+[11] if d<=depth]
    if codes.shape!=(1,sum(model.vq.levels[:depth])) or [o['level'] for o in observations]!=expected:raise ValueError('Wrong actual stopping boundary/schedule')
    return dict(prefix_ids=prefix,codes=codes,exit_level=depth,observations=observations,ids=observations[-1]['ids'],text=observations[-1]['text'],features=vectors,prefix_codes=prefix_codes)
