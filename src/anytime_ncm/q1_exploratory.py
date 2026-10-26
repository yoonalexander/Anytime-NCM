"""Bounded consumed-data oracle diagnostics; no causal selector or model imports."""
import json
import math
import re
import numpy as np
from anytime_ncm.stronger_s1 import Corpus, validate_rows, need, digest
from anytime_ncm.evidence_timing import value_hash

HEADER=re.compile(rb'^\{"identity":\s*"([a-f0-9]{64})",\s*"index":\s*(\d+),\s*"partition":\s*"([A-Za-z0-9_]+)"')

SCHEDULES={'terminal_oracle':list(range(1,12)), 'sparse_8_10_11':[8,10,11],
           'sparse_9_10_11':[9,10,11], 'sparse_10_11':[10,11]}
MARGINS={'bleu':.5,'chrf':1.,'numeric_reference_f1':.02,'negation_cue_mismatch_rate':.02}

def losses(candidate,full):
    return {k:None if candidate.get(k) is None or full.get(k) is None else
            float((candidate[k]-full[k]) if k=='negation_cue_mismatch_rate' else (full[k]-candidate[k])) for k in MARGINS}

def feasible(candidate,full):
    v=losses(candidate,full)
    return all(v[k] is not None and math.isfinite(v[k]) and v[k]<=m+1e-10 for k,m in MARGINS.items())

def read_rows(path,groups,charge):
    allowed={(part,e['index'],e['identity']) for part,es in groups.items() for e in es}
    seen=set();result={p:[] for p in groups}
    with path.open('rb') as f:
        for line in f:
            m=HEADER.match(line);need(m is not None,'Invalid trajectory header')
            key=(m[3].decode(),int(m[2]),m[1].decode())
            need(key in allowed and key not in seen,'Forbidden/duplicate trajectory before body decode')
            charge('trajectory_bodies',1);row=json.loads(line)
            need((row['partition'],row['index'],row['identity'])==key,'Header/body mismatch')
            seen.add(key);result[key[0]].append(row)
    need(seen==allowed,'Incomplete trajectories')
    for rows in result.values():
        rows.sort(key=lambda r:r['index']);validate_rows(rows)
    return result

def exact_depths(rows):
    return np.array([next(k+1 for k,s in enumerate(r['levels']) if s['text']==r['levels'][-1]['text']) for r in rows])

def timing_cells(entries,rows,records,warmups):
    n=len(entries);need(len(rows)==n,'Timing population size')
    need([(r['index'],r['identity']) for r in rows]==[(e['index'],e['identity']) for e in entries],'Timing population order')
    positions={e['index']:i for i,e in enumerate(entries)};warm={(e['index'],e['identity']) for e in warmups}
    cells=np.full((n,2,2,12),np.nan);exact=exact_depths(rows);warm_count=0
    for r in records:
        if r['phase']=='warmup':
            need((r['index'],r['identity']) in warm,'Forbidden warmup identity');warm_count+=1;continue
        need(r['phase']=='timed' and r['index'] in positions,'Forbidden timing identity')
        i=positions[r['index']];need(r['identity']==entries[i]['identity'],'Timing identity mismatch')
        need(r['method'] in ['exact']+[f'fixed:{k}' for k in range(1,12)],'Invalid timing method')
        method=0 if r['method']=='exact' else int(r['method'].split(':')[1]);depth=int(exact[i]) if method==0 else method
        need(r['block'] in (0,1) and r['repeat'] in (0,1),'Invalid timing cell coordinates')
        need(r['depth']==depth and r['schedule']==('every_level' if method==0 else 'terminal'),'Timing schedule/depth')
        need(r['parity'] is True and r['work']==dict(inputs=1,generator_levels=depth,decoder=depth if method==0 else 1,encoder=0),'Execution parity/work')
        need(math.isfinite(r['wall_ms']) and r['wall_ms']>0,'Invalid latency')
        state=rows[i]['levels'][depth-1]
        need(r['text_sha256']==value_hash(state['text']) and r['ids_sha256']==value_hash(state['ids']),'Output hash parity')
        slot=(i,r['block'],r['repeat'],method);need(np.isnan(cells[slot]),'Duplicate timing cell');cells[slot]=r['wall_ms']
    need(np.isfinite(cells).all(),'Missing timing cell')
    return cells,warm_count

def visits(a,schedule):
    a=np.asarray(a);allowed=SCHEDULES[schedule]
    need(np.isin(a,allowed).all(),'Exit outside schedule')
    return np.ones(len(a),dtype=int) if schedule=='terminal_oracle' else np.array([sum(k<=d for k in allowed) for d in a])

def costs(a,schedule,profile,h,decision=.05,hfactor=1.):
    a=np.asarray(a,dtype=int);v=visits(a,schedule)
    need(len(profile)==11 and np.isfinite(profile).all() and min(profile)>0 and h>=0 and decision>=0 and hfactor>=0,'Invalid cost assumptions')
    return np.asarray(profile)[a-1]+(0 if schedule=='terminal_oracle' else h*hfactor*(v-1)+decision*v)

def search(corpus,schedule,profile,h,emit,cap=2000,passes=2):
    a=np.full(corpus.n,11,dtype=int);count=0;accepted=0
    def evaluate(x,kind):
        nonlocal count
        need(count<cap,'Search assignment cap');count+=1
        s,hit=corpus.evaluate(x);emit(dict(kind=kind,attempt=count,assignment_sha256=digest(x),cache_hit=hit))
        return s
    full=evaluate(a,'start');termination='pass_cap'
    for sweep in range(passes):
        changed=False
        for i in range(corpus.n):
            choices=sorted((d for d in SCHEDULES[schedule] if d<a[i]),key=lambda d:(float(costs([d],schedule,profile,h)[0]),d))
            for d in choices:
                if count>=cap:termination='assignment_cap';break
                v=a.copy();v[i]=d;s=evaluate(v,'candidate')
                if feasible(s,full) and costs([d],schedule,profile,h)[0]<costs([a[i]],schedule,profile,h)[0]-1e-12:
                    a=v;accepted+=1;changed=True;break
            if termination=='assignment_cap':break
        if termination=='assignment_cap':break
        if not changed:termination='no_improving_coordinate_in_complete_pass';break
    return dict(exits=a.tolist(),assignment_sha256=digest(a),evaluations=count,accepted_changes=accepted,termination=termination,
                certified_optimum=False,metrics=corpus.direct(a))

def describe(corpus,a,full,schedule,profile,h,cells=None):
    a=np.asarray(a,dtype=int);metrics,_=corpus.evaluate(a);v=visits(a,schedule)
    primary=costs(a,schedule,profile,h);fullcost=float(profile[10])
    selected=None
    if cells is not None:selected=np.stack([cells[i,:,:,int(d)] for i,d in enumerate(a)])
    return dict(metrics=metrics,losses=losses(metrics,full),point_quality_pass=feasible(metrics,full),early_inputs=int(sum(a<11)),
        approximate_early_inputs=sum(int(d<11 and r['levels'][d-1]['text']!=r['levels'][-1]['text']) for r,d in zip(corpus.rows,a)),
        exit_distribution={str(k):int(sum(a==k)) for k in range(1,12)},observation_distribution={str(k):int(sum(v==k)) for k in sorted(set(v.tolist()))},
        projected_mean_ms=float(primary.mean()),projected_full_savings=float(1-primary.mean()/fullcost),
        selected_terminal_assembly=None if selected is None else dict(mean_ms=float(selected.mean()),block_mean_ms=selected.mean(axis=(0,2)).tolist(),full_savings=float(1-selected.mean()/cells[:,:,:,11].mean())),
        sensitivity=[dict(h_factor=f,decision_ms=b,projected_mean_ms=float(costs(a,schedule,profile,h,b,f).mean()),full_savings=float(1-costs(a,schedule,profile,h,b,f).mean()/fullcost)) for f in (0,.5,1,2) for b in (0,.05,.2)])
