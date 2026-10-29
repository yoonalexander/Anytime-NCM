"""Counterbalanced light-signal cost precision study; no learned model or quality inference."""
import itertools
import random
import numpy as np
from anytime_ncm.quality_controller import FEATURES
KINDS=('cheap','margin','selected_logit')
SIGNALS=('margin','selected_logit')

def schedule(entries,session):
    if len(entries)!=16 or session not in (0,1):raise ValueError('Frozen light pilot only')
    rng=random.Random(20261030+session);out=[];warm=list(KINDS);rng.shuffle(warm)
    def add(p,kind,warmup,repeat):
        e=entries[p];out.append(dict(request_id=len(out),session=session,position=p,index=e['index'],identity=e['identity'],kind=kind,warmup=warmup,repeat=repeat))
    for k,kind in enumerate(warm):
        for j in range(5):add((k*5+j)%16,kind,True,-1)
    bases={p:rng.sample(list(KINDS),3) for p in range(16)}
    permutations=list(itertools.permutations(range(3)))+[(0,1,2),(1,2,0)]
    for repeat in range(8):
        positions=list(range(16));rng.shuffle(positions)
        for p in positions:
            for index in permutations[repeat]:add(p,bases[p][index],False,repeat)
    return out

def analyze(records):
    cells={};values={}
    for r in records:
        dim=19 if r['kind']=='cheap' else 27
        if not r['parity'] or r['work']!=dict(inputs=1,generator_levels=11,decoder=3,encoder=0):raise ValueError('Light pilot work/parity failed')
        if [f['level'] for f in r['features']]!=[8,10] or any(len(f['values'])!=dim or not np.isfinite(f['values']).all() for f in r['features']):raise ValueError('Light feature shape/finiteness')
        for f in r['features']:
            key=(r['index'],r['kind'],f['level']);v=np.array(f['values'])
            if key in values and not np.allclose(values[key],v,rtol=1e-5,atol=1e-6):raise ValueError('Inconsistent light feature repeats')
            values[key]=v
        if r['warmup']:continue
        key=(r['session'],r['position'],r['repeat'],r['kind'])
        if key in cells or not np.isfinite(r['wall_ms']) or r['wall_ms']<=0 or not np.isfinite(r['component_ms']['extra']) or r['component_ms']['extra']<0:raise ValueError('Invalid light cell')
        cells[key]=r
    if len(cells)!=768:raise ValueError('Missing light timing cells')
    indexes=sorted({r['index'] for r in records})
    if len(indexes)!=16:raise ValueError('Wrong light population')
    detail={};qualified=[]
    for kind in SIGNALS:
        variation={}
        for level in (8,10):
            matrix=np.array([values[(i,kind,level)][19:22] for i in indexes]);ranges=np.ptp(matrix,axis=0)
            variation[str(level)]=dict(summary_ranges=ranges.tolist(),varies=bool(np.any(ranges>1e-6)))
        sessions={}
        for session in (0,1):
            differences=[];components=[];times=[]
            for p in range(16):
                for repeat in range(8):
                    a=cells[(session,p,repeat,'cheap')];b=cells[(session,p,repeat,kind)]
                    for x,y in zip(a['features'],b['features']):
                        if not np.array_equal(x['values'],y['values'][:19]):raise ValueError('Light extraction changed cheap features')
                    differences.append(b['wall_ms']-a['wall_ms']);components.append(b['component_ms']['extra']);times.append(b['wall_ms'])
            sessions[str(session)]=dict(pairs=128,mean_added_ready_ms=float(np.mean(differences)),median_added_ready_ms=float(np.median(differences)),
                p95_added_ready_ms=float(np.percentile(differences,95)),mean_synchronous_extra_ms=float(np.mean(components)),p95_synchronous_extra_ms=float(np.percentile(components,95)),
                method_mean_ms=float(np.mean(times)))
        good=all(v['varies'] for v in variation.values()) and all(v['mean_synchronous_extra_ms']<=1+1e-9 and v['p95_synchronous_extra_ms']<=3+1e-9 and v['mean_added_ready_ms']<=5+1e-9 for v in sessions.values())
        detail[kind]=dict(variation=variation,sessions=sessions,collection_cost_and_variation_pass=good)
        if good:qualified.append(kind)
    chosen=next((s for s in SIGNALS if s in qualified),None)
    cheap={str(s):dict(mean_ms=float(np.mean([r['wall_ms'] for k,r in cells.items() if k[0]==s and k[3]=='cheap'])),
        p95_ms=float(np.percentile([r['wall_ms'] for k,r in cells.items() if k[0]==s and k[3]=='cheap'],95))) for s in (0,1)}
    return dict(decision='light_signal_collection_supported' if chosen else 'no_light_signal_qualified',selected_signal=chosen,qualified=qualified,signals=detail,cheap=cheap,
        cost_screen_basis='synchronous extra extraction component inside actual request; not paired whole-request overhead',
        original_entropy_pilot_whole_request_gate_still_failed=True,whole_controller_speedup_established=False,predictive_usefulness_established=False,Q0_passed=False,
        confirmation_authorized=False,thresholds=dict(mean_synchronous_extra_ms=1,p95_synchronous_extra_ms=3,large_whole_path_mean_guard_ms=5))
