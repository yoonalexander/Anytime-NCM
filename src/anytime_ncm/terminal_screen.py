"""Pure post hoc screen of already released E2 timings; no model/data loaders."""
import json
import numpy as np
from anytime_ncm.evidence_preflight import crossed_ratio, order_interval
from anytime_ncm.evidence_timing import value_hash


def assemble(entries, trajectories, records):
    if len(entries)!=256 or len(trajectories)!=256: raise ValueError('Population differs')
    allowed={e['index']:e['identity'] for e in entries}
    if {(r['index'],r['identity']) for r in trajectories}!=set(allowed.items()): raise ValueError('Output allowlist differs')
    depths={r['index']:next(k+1 for k,l in enumerate(r['levels']) if l['text']==r['levels'][-1]['text']) for r in trajectories}
    by_index={r['index']:r for r in trajectories}
    positions={e['index']:i for i,e in enumerate(entries)}
    cells=np.full((256,2,2,12),np.nan)
    for r in records:
        if r['phase']=='warmup':continue
        if r['phase']!='timed' or allowed.get(r['index'])!=r['identity']:raise ValueError('Forbidden timing identity')
        method=0 if r['method']=='exact' else int(r['method'].split(':')[1])
        depth=depths[r['index']] if method==0 else method
        if r['depth']!=depth or r['schedule']!=('every_level' if method==0 else 'terminal'):raise ValueError('Timing method differs')
        expected=dict(inputs=1,generator_levels=depth,decoder=depth if method==0 else 1,encoder=0)
        if not r['parity'] or r['work']!=expected or not np.isfinite(r['wall_ms']) or r['wall_ms']<=0:raise ValueError('Invalid execution')
        old=by_index[r['index']]['levels'][depth-1]
        if r['text_sha256']!=value_hash(old['text']) or r['ids_sha256']!=value_hash(old['ids']):raise ValueError('Selected output parity differs')
        slot=(positions[r['index']],r['block'],r['repeat'],method)
        if np.isfinite(cells[slot]):raise ValueError('Duplicate timing cell')
        cells[slot]=r['wall_ms']
    if not np.isfinite(cells).all():raise ValueError('Missing timing cell')
    chosen=np.stack([cells[i,:,:,depths[e['index']]] for i,e in enumerate(entries)])
    return {'terminal_exact':chosen,'full':cells[:,:,:,11],'dense_exact':cells[:,:,:,0]},depths


def calculate(data,draws=100000):
    rng=np.random.Generator(np.random.PCG64(20261026))
    ix=rng.integers(0,256,size=(draws,256),dtype=np.int32)
    blocks=rng.integers(0,2,size=(draws,2),dtype=np.int32)
    means={k:v.mean(axis=2) for k,v in data.items()}
    summaries={k:dict(mean_ms=float(v.mean()),median_ms=float(np.median(v)),p95_ms=float(np.percentile(v,95)),process_mean_ms=v.mean(axis=(0,2)).tolist()) for k,v in data.items()}
    contrasts={}
    for candidate,base in [('terminal_exact','full'),('dense_exact','terminal_exact')]:
        samples=crossed_ratio(means[base],means[candidate],ix,blocks)
        contrasts[candidate+'_versus_'+base]=dict(order_interval(samples,.0125,2),relative_mean_reduction=float(1-means[candidate].mean()/means[base].mean()),process_reductions=[float(1-means[candidate][:,b].mean()/means[base][:,b].mean()) for b in range(2)])
    result=contrasts['terminal_exact_versus_full']
    return dict(methods=summaries,contrasts=contrasts,decision='do_not_budget_same_exact_family' if result['upper'] is not None and result['upper']<.05 else 'budget_priority_unresolved',
        post_hoc=True,integrated_online_policy_benchmark=False,certified_global_oracle_optimum=False,E3_release=False,E4_release=False,draws=draws,seed=20261026,tail=.0125)
