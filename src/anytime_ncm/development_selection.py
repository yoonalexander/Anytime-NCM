"""Header-filtered calibration access and fixed saved-score policy replay."""
import json
from pathlib import Path
import numpy as np

def key(e):return str(e['year'])+':'+str(e['index'])

def select_private(path,entries,all_entries,kind,meter,expected_warmups=5):
    if kind not in ('trace','reference'):raise ValueError('Unknown private stream kind')
    allowed={key(e):e['role'] for e in all_entries};active={key(e) for e in entries};selected={};seen=set();warmups=0;count=0
    if len(allowed)!=len(all_entries) or not active<=set(allowed):raise ValueError('Invalid allocation')
    marker=b', "prefix_ids":' if kind=='trace' else b', "reference":'
    with Path(path).open('rb') as f:
        for raw in f:
            cut=raw.find(marker)
            if not raw.startswith(b'{') or cut<0 or cut>1024:raise ValueError('Invalid metadata header before body decode')
            header=json.loads(raw[:cut]+b'}');k=key(header)
            if k not in allowed or header['role']!=allowed[k]:raise ValueError('Unallocated private header before body decode')
            meter.take(kind+'_headers');count+=1;warm=header.get('warmup',False)
            if kind=='trace' and type(warm)is not bool:raise ValueError('Invalid warmup header')
            if warm:
                if kind!='trace' or header['role']!='development_fit':raise ValueError('Forbidden warmup header')
                warmups+=1;continue
            if k in seen:raise ValueError('Duplicate nonwarm header')
            seen.add(k)
            if k not in active:continue
            meter.take('calibration_'+kind+'_bodies');body=json.loads(raw)
            if key(body)!=k or body['role']!=header['role']:raise ValueError('Body/header mismatch')
            selected[k]=body
    if seen!=set(allowed) or set(selected)!=active or warmups!=(expected_warmups if kind=='trace' else 0) or count!=len(allowed)+warmups:raise ValueError('Missing private population')
    return selected

def replay_scores(spec,scores8,scores10,features8,features10):
    a=np.asarray(features8,dtype=float);b=np.asarray(features10,dtype=float);n=len(a)
    if a.shape!=(n,27) or b.shape!=a.shape or not np.isfinite(a).all() or not np.isfinite(b).all():raise ValueError('Invalid saved causal features')
    if spec['kind']=='full':return [(11,[11]) for _ in range(n)]
    s8=np.asarray(scores8,dtype=float);s10=np.asarray(scores10,dtype=float)
    if s8.shape!=(n,) or s10.shape!=(n,) or not np.isfinite(s8).all() or not np.isfinite(s10).all() or spec['decision_levels'] not in ([8],[8,10]):raise ValueError('Invalid saved scores/schedule')
    threshold=spec['threshold'];guard=spec['cue_guard'];out=[]
    for i in range(n):
        good8=s8[i]<=threshold and (not guard or (a[i,25]==1 and a[i,26]==1))
        if good8:out.append((8,[8]));continue
        if spec['decision_levels']==[8]:out.append((11,[8,11]));continue
        good10=s10[i]<=threshold and (not guard or (b[i,25]==1 and b[i,26]==1))
        out.append((10,[8,10]) if good10 else (11,[8,10,11]))
    return out

def estimated_cost(spec,assignments,profile,h,extra):
    if spec['kind']=='full':return float(profile[11])
    if h<0 or extra<0:raise ValueError('Negative frozen cost')
    surcharge=extra if spec['group']!='cheap' or spec['cue_guard'] else 0.
    return float(np.mean([profile[d]+(len(v)-1)*h+sum(level<11 for level in v)*surcharge for d,v in assignments]))
