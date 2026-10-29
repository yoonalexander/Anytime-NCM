"""Cheap causal quality-benefit proxies; corpus gates remain separate."""
import math
import re
import numpy as np
from sacrebleu.metrics import BLEU, CHRF
from anytime_ncm.wmt_policy import cues, diagnostics
from anytime_ncm.latency_diagnostic import LEVELS

MARGINS=np.array([.5,1.,.02,.02])
TARGETS=('bleu','chrf','numeric_reference_f1','negation_cue_mismatch_rate')
FEATURES=('level','source_length','source_numbers','source_negation','text_length','word_count',
          'numbers','negation','unique_tokens','adjacent_repeat','unique_codes','code_entropy',
          'last_level_unique','history_available','token_change','cue_change','length_change','token_jaccard','level_gap')
GERMAN_NEGATION=re.compile(r'\b(?:nicht|kein\w*|ohne|nie)\b',re.I)

class Meter:
    def __init__(self,limits,stream=None):self.limits=dict(limits);self.counts=dict.fromkeys(limits,0);self.stream=stream
    def take(self,key,n=1):
        if type(n)is not int or n<1 or self.counts[key]+n>self.limits[key]:raise RuntimeError('Controller allocation exhausted: '+key)
        self.counts[key]+=n
        if self.stream:
            import json
            self.stream.write(json.dumps(dict(kind=key,amount=n,total=self.counts[key]))+'\n');self.stream.flush()

def features(source,level,codes,ids,text,previous=None):
    if (type(level)is not int or level not in (8,10) or len(codes)!=sum(LEVELS[:level]) or len(ids)!=64
            or any(type(i)is not int for i in codes+ids)):
        raise ValueError('Only exact current prefixes at decision levels are accepted')
    if previous is not None and (previous['level']!=8 or level!=10 or len(previous['ids'])!=64):
        raise ValueError('History must be the actual earlier level8 observation')
    from collections import Counter
    counts=Counter(codes);probs=np.array(list(counts.values()),dtype=float)/len(codes)
    nums,neg=cues(text);sn,_=cues(source);last=codes[-LEVELS[level-1]:]
    history=previous is not None
    change=sum(a!=b for a,b in zip(ids,previous['ids']))/64 if history else 0.
    union=set(ids)|set(previous['ids']) if history else set()
    return np.array([level/11,len(source)/1024,len(sn)/4,bool(GERMAN_NEGATION.search(source)),len(text)/256,len(text.split())/64,
        len(nums)/4,neg,len(set(ids))/64,sum(a==b for a,b in zip(ids,ids[1:]))/63,len(counts)/len(codes),
        -float(np.sum(probs*np.log2(probs)))/12,len(set(last))/len(last),history,change,
        history and cues(text)!=cues(previous['text']),(len(text)-len(previous['text']))/256 if history else 0.,
        len(set(ids)&set(previous['ids']))/len(union) if history and union else 0.,(level-previous['level'])/11 if history else 0.],dtype=float)

class Controller:
    def __init__(self,spec,meter=None):
        self.spec=spec;self.meter=meter
        if spec['kind'] not in ('full','stability','ridge'):raise ValueError('Unknown controller')
        self.models={}
        if spec['kind']=='ridge':
            for d in (8,10):
                m=spec['models'][str(d)]
                mean,scale,coef=(np.asarray(m[k],dtype=float) for k in ('mean','scale','coef'))
                if mean.shape!=(19,) or scale.shape!=(19,) or coef.shape!=(20,4) or np.any(scale<=0) or not all(np.isfinite(x).all() for x in (mean,scale,coef)):
                    raise ValueError('Malformed frozen linear model')
                self.models[d]=(mean,scale,coef)
    def observe(self,source,level,codes,ids,text,previous):
        if type(level)is not int or level not in (8,10):raise ValueError('Only scheduled decision levels')
        if self.meter:self.meter.take('decisions')
        if self.spec['kind']=='full':return False
        if self.spec['kind']=='stability':
            if previous is None:return False
            if level!=10 or previous['level']!=8:raise ValueError('Invalid stability history')
            return bool(sum(a!=b for a,b in zip(ids,previous['ids']))/64<=self.spec['epsilon'] and cues(text)==cues(previous['text']))
        if self.meter:self.meter.take('features')
        x=features(source,level,codes,ids,text,previous);mean,scale,coef=self.models[level]
        predicted=np.r_[(x-mean)/scale,1.]@coef
        return bool(max(0.,float(np.max(predicted)))<=self.spec['threshold'])

def replay(controller,source,row):
    if controller.spec['kind']=='full':return 11,[11]
    previous=None;visits=[]
    for d in (8,10):
        observation=row['levels'][d-1];visits.append(d)
        if controller.observe(source,d,row['codes'][:sum(LEVELS[:d])],observation['ids'],observation['text'],previous):return d,visits
        previous=dict(level=d,ids=observation['ids'],text=observation['text'])
    return 11,visits+[11]

def sentence_targets(row,reference,meter):
    b=BLEU(effective_order=True);c=CHRF()
    state={}
    for d in (8,10,11):
        meter.take('sentence_label_pairs')
        text=row['levels'][d-1]['text'];diag=diagnostics(text,reference)
        state[d]=[b.sentence_score(text,[reference]).score,c.sentence_score(text,[reference]).score,
                  diag['numeric_reference_f1'],float(diag['negation_cue_mismatch'])]
    result={}
    for d in (8,10):
        values=[state[11][0]-state[d][0],state[11][1]-state[d][1],
                None if state[11][2] is None else state[11][2]-state[d][2],state[d][3]-state[11][3]]
        result[d]=[None if v is None else v/MARGINS[i] for i,v in enumerate(values)]
    return result

def fit_models(rows,sources,references,meter):
    xs={8:[],10:[]};ys={8:[],10:[]}
    for row in rows:
        labels=sentence_targets(row,references[row['index']],meter);previous=None
        for d in (8,10):
            meter.take('features');o=row['levels'][d-1]
            xs[d].append(features(sources[row['index']],d,row['codes'][:sum(LEVELS[:d])],o['ids'],o['text'],previous))
            ys[d].append(labels[d]);previous=dict(level=d,ids=o['ids'],text=o['text'])
    models={}
    for d in (8,10):
        x=np.asarray(xs[d]);mean=x.mean(axis=0);scale=x.std(axis=0);scale[scale<1e-12]=1.
        design=np.column_stack([(x-mean)/scale,np.ones(len(x))]);coef=[];counts=[]
        for t in range(4):
            active=np.array([v[t] is not None for v in ys[d]],dtype=bool)
            if active.sum()<12:raise ValueError('Insufficient training labels')
            target=np.array([v[t] for v in ys[d] if v[t] is not None]);z=design[active]
            penalty=np.eye(design.shape[1])*10.;penalty[-1,-1]=0.
            meter.take('fits');coef.append(np.linalg.solve(z.T@z+penalty,z.T@target));counts.append(int(active.sum()))
        models[str(d)]=dict(mean=mean.tolist(),scale=scale.tolist(),coef=np.column_stack(coef).tolist(),label_counts=counts)
    return models

def candidates(models):
    result=[dict(name='full',kind='full')]
    result += [dict(name='stability:'+str(e),kind='stability',epsilon=e) for e in (0.,2/64,4/64)]
    result += [dict(name='ridge:'+str(t),kind='ridge',threshold=t,models=models) for t in (0.,.5,1.,2.,4.)]
    return result

def point_losses(candidate,full):
    return dict(bleu=full['bleu']-candidate['bleu'],chrf=full['chrf']-candidate['chrf'],
        numeric_reference_f1=None if candidate['numeric_reference_f1'] is None else full['numeric_reference_f1']-candidate['numeric_reference_f1'],
        negation_cue_mismatch_rate=candidate['negation_cue_mismatch_rate']-full['negation_cue_mismatch_rate'])

def point_pass(candidate,full):
    loss=point_losses(candidate,full)
    return all(loss[k] is not None and math.isfinite(loss[k]) and loss[k]<=margin+1e-10 for k,margin in zip(TARGETS,MARGINS))
