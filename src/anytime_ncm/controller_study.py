"""Prospective consumed-data controller study helpers; no model loading."""
import json
from pathlib import Path
import random
import re
import numpy as np
from anytime_ncm.evidence_preflight import order_interval
from anytime_ncm.latency_diagnostic import value_hash, LEVELS, cluster_draws
from anytime_ncm.stronger_s1 import validate_rows
from anytime_ncm.quality_controller import point_losses,point_pass
METHODS=('controller',)+tuple('fixed:%d'%d for d in range(1,12))
HEADER=re.compile(rb'^\{"identity":\s*"([a-f0-9]{64})",\s*"index":\s*(\d+),\s*"partition":\s*"([A-Za-z0-9_]+)"')

def selected_rows(path,entries,all_entries,meter):
    allowed={(e['origin'],e['index'],e['identity']) for e in all_entries}
    active={(e['origin'],e['index'],e['identity']) for e in entries}
    seen=set();rows=[]
    with Path(path).open('rb') as f:
        for line in f:
            m=HEADER.match(line)
            if m is None:raise ValueError('Invalid trajectory header before body decode')
            key=(m[3].decode(),int(m[2]),m[1].decode())
            if key not in allowed or key in seen:raise ValueError('Forbidden/duplicate header before body decode')
            seen.add(key)
            if key not in active:continue
            meter.take('trajectory_bodies');row=json.loads(line)
            if (row['partition'],row['index'],row['identity'])!=key:raise ValueError('Body/header mismatch')
            validate_rows([row]);rows.append(row)
    if seen!=allowed or len(rows)!=len(active):raise ValueError('Missing trajectory population')
    return sorted(rows,key=lambda r:r['index'])

def cache_row(row):
    return dict(identity=row['identity'],prefix=value_hash(row['prefix_ids']),
        codes={str(d):value_hash(row['codes'][:sum(LEVELS[:d])]) for d in range(1,12)},
        outputs={str(o['level']):dict(ids=value_hash(o['ids']),text=value_hash(o['text'])) for o in row['levels']})

def schedule(entries,predictions,session):
    if session not in (0,1) or len(entries)<16 or len(entries)!=len(predictions):raise ValueError('Invalid timing plan')
    rng=random.Random(20261029+session);out=[]
    def add(p,m,warm,repeat):
        e=entries[p]
        d,visits=predictions[p] if m=='controller' else (int(m.split(':')[1]),[int(m.split(':')[1])])
        out.append(dict(request_id=len(out),session=session,position=p,index=e['index'],identity=e['identity'],method=m,
            depth=d,visits=visits,warmup=warm,repeat=repeat))
    ms=list(METHODS);rng.shuffle(ms)
    for i,m in enumerate(ms):
        for j in range(5):add((i*5+j)%16,m,True,-1)
    for r in range(2):
        positions=list(range(len(entries)));rng.shuffle(positions)
        for p in positions:
            ms=list(METHODS);rng.shuffle(ms)
            for m in ms:add(p,m,False,r)
    return out

def work(request):return dict(inputs=1,generator_levels=request['depth'],decoder=len(request['visits']),encoder=0)
def sum_work(plan):return {k:sum(work(r)[k] for r in plan) for k in ('inputs','generator_levels','decoder','encoder')}

def timing_analysis(records,entries,quality,locked_comparator,early_inputs):
    n=len(entries);cells=np.full((2,n,2,12),np.nan)
    for r in records:
        if r['warmup']:continue
        key=(r['session'],r['position'],r['repeat'],METHODS.index(r['method']))
        if not np.isnan(cells[key]) or not r['parity'] or r['work']!=work(r) or not np.isfinite(r['wall_ms']) or r['wall_ms']<=0:raise ValueError('Invalid/duplicate timing cell')
        cells[key]=r['wall_ms']
    if not np.isfinite(cells).all():raise ValueError('Missing timing cells')
    groups=[e['component'] for e in entries];g=len(set(groups))
    if g<20:raise ValueError('Inadequate test components')
    picks=np.random.default_rng(20261029).integers(g,size=(20000,g))
    samples=cluster_draws(cells.mean(axis=(0,2)),groups,picks)
    summaries={}
    for m,method in enumerate(METHODS):
        v=cells[:,:,:,m]
        summaries[method]=dict(mean_ms=float(v.mean()),median_ms=float(np.median(v)),p95_ms=float(np.percentile(v,95)),session_mean_ms=v.mean(axis=(1,2)).tolist(),
            cuda_stream_mean_ms=float(np.mean([r['cuda_stream_span_ms'] for r in records if not r['warmup'] and r['method']==method])))
    contrasts={}
    for j,method in enumerate(METHODS[1:]):
        contrasts[method]=dict(savings=1-summaries['controller']['mean_ms']/summaries[method]['mean_ms'],
            session_savings=[1-a/b for a,b in zip(summaries['controller']['session_mean_ms'],summaries[method]['session_mean_ms'])],
            conditional_nominal_interval=order_interval(samples[:,j],.05/22,11))
    primary=contrasts['fixed:11'];pquality=quality['controller']['point_pass']
    if not pquality:decision='controller_quality_point_screen_failed'
    elif early_inputs==0:decision='controller_no_early_exits'
    elif primary['savings']<.05:decision='controller_insufficient_savings'
    elif (any(v<=0 for v in primary['session_savings']) or primary['conditional_nominal_interval']['lower'] is None
          or primary['conditional_nominal_interval']['lower']<=0 or contrasts[locked_comparator]['conditional_nominal_interval']['lower']<=0):decision='controller_latency_inconclusive'
    else:decision='exploratory_controller_screen_passed'
    return dict(decision=decision,methods=summaries,contrasts=contrasts,quality=quality,locked_fixed_comparator=locked_comparator,
        test_inputs=n,test_components=g,early_test_inputs=early_inputs,bootstrap_draws=20000,interval_family=11,tail_alpha=.05/22,
        conditional_on_observed_sessions=True,mc_rank_error_allowance=.001,Q0_passed=False,independent_confirmation=False,Q4_authorized=False,
        statistically_excluded_fixed_depths=[])
