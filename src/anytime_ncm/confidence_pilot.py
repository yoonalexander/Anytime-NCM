"""Frozen pilot scheduling and descriptive paired measurement; no fitting."""
import random
import numpy as np
from anytime_ncm.quality_controller import FEATURES
CONFIDENCE_NAMES=('margin_mean','margin_p10','margin_min','entropy_mean','entropy_p90','entropy_max')
CUE_NAMES=('source_has_numbers','source_number_recall','source_number_precision','source_numbers_equal','negation_cue_agreement')
RICH_NAMES=FEATURES+CONFIDENCE_NAMES+CUE_NAMES

def schedule(entries,session):
    if len(entries)!=16 or session not in (0,1):raise ValueError('Frozen sixteen-input pilot only')
    rng=random.Random(20261029+session);out=[];kinds=['cheap','rich'];rng.shuffle(kinds)
    def add(p,kind,warmup,repeat):
        e=entries[p];out.append(dict(request_id=len(out),session=session,position=p,index=e['index'],identity=e['identity'],kind=kind,warmup=warmup,repeat=repeat))
    for k,kind in enumerate(kinds):
        for j in range(5):add((k*5+j)%16,kind,True,-1)
    order={p:bool(rng.getrandbits(1)) for p in range(16)}
    for repeat in (0,1):
        positions=list(range(16));rng.shuffle(positions)
        for p in positions:
            pair=['cheap','rich']
            if order[p] != bool(repeat):pair.reverse()
            for kind in pair:add(p,kind,False,repeat)
    return out

def analyze(records):
    cells={};values={};summary={};components={};paired={}
    for r in records:
        expected=19 if r['kind']=='cheap' else 30
        if not r['parity'] or r['work']!=dict(inputs=1,generator_levels=11,decoder=3,encoder=0):raise ValueError('Invalid pilot work/parity')
        if [f['level'] for f in r['features']]!=[8,10] or any(len(f['values'])!=expected or not np.isfinite(f['values']).all() for f in r['features']):raise ValueError('Invalid causal feature record')
        for f in r['features']:
            key=(r['index'],r['kind'],f['level']);v=np.array(f['values'])
            if key in values and not np.allclose(values[key],v,rtol=1e-5,atol=1e-6):raise ValueError('Repeated feature inconsistency')
            values[key]=v
        if r['warmup']:continue
        key=(r['session'],r['position'],r['repeat'],r['kind'])
        if key in cells or not np.isfinite(r['wall_ms']) or r['wall_ms']<=0:raise ValueError('Duplicate/invalid pilot cell')
        cells[key]=r
    if len(cells)!=128:raise ValueError('Missing pilot timing cells')
    for session in (0,1):
        diffs=[]
        for p in range(16):
            for repeat in (0,1):
                cheap=cells[(session,p,repeat,'cheap')];rich=cells[(session,p,repeat,'rich')]
                for a,b in zip(cheap['features'],rich['features']):
                    if not np.allclose(a['values'],b['values'][:19],rtol=0,atol=0):raise ValueError('Rich extraction altered cheap features')
                diffs.append(rich['wall_ms']-cheap['wall_ms'])
        paired[str(session)]=dict(mean_added_ms=float(np.mean(diffs)),median_added_ms=float(np.median(diffs)),p95_added_ms=float(np.percentile(diffs,95)),pairs=32)
        for kind in ('cheap','rich'):
            rows=[r for k,r in cells.items() if k[0]==session and k[3]==kind];times=[r['wall_ms'] for r in rows]
            summary[str(session)+':'+kind]=dict(mean_ms=float(np.mean(times)),median_ms=float(np.median(times)),p95_ms=float(np.percentile(times,95)),
                component_cheap_mean_ms=float(np.mean([r['component_ms']['cheap'] for r in rows])),component_extra_mean_ms=float(np.mean([r['component_ms']['extra'] for r in rows])))
    indexes=sorted({r['index'] for r in records});variation={}
    if len(indexes)!=16:raise ValueError('Wrong pilot population')
    for level in (8,10):
        matrix=np.array([values[(i,'rich',level)][19:] for i in indexes]);ranges=np.ptp(matrix,axis=0)
        variation[str(level)]=dict(ranges=dict(zip(CONFIDENCE_NAMES+CUE_NAMES,ranges.tolist())),margin_varies=bool(np.any(ranges[:3]>1e-6)),entropy_varies=bool(np.any(ranges[3:6]>1e-6)))
    varies=all(v['margin_varies'] and v['entropy_varies'] for v in variation.values())
    cheap_enough=all(p['mean_added_ms']<=1.+1e-9 and p['p95_added_ms']<=3.+1e-9 for p in paired.values())
    decision='pilot_passed' if varies and cheap_enough else 'pilot_no_confidence_variation' if not varies else 'pilot_cost_screen_failed'
    return dict(decision=decision,finite_and_parity=True,repeated_features_consistent=True,confidence_varies=varies,cost_screen_passed=cheap_enough,
        paired_sessions=paired,methods=summary,variation=variation,thresholds=dict(mean_added_ms=1.,p95_added_ms=3.),
        independent_quality_evidence=False,predictive_usefulness_established=False,Q0_passed=False,confirmation_authorized=False)
