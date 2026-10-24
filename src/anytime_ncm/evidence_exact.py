"""Prospective E2 exact-text diagnostic. Pure scheduling/statistics, no model calls."""
import random
import time
import numpy as np
from anytime_ncm.evidence_preflight import cue_interval, order_interval, crossed_ratio
from anytime_ncm.stronger_s1 import Corpus

METHODS = ['exact'] + [f'fixed:{d}' for d in range(1, 12)]
FAMILY = 59
TAIL = .05 / (2 * FAMILY)


def exact_depth(row):
    levels = row['levels']
    if len(levels) != 11 or [r['level'] for r in levels] != list(range(1, 12)):
        raise ValueError('Require all eleven ordered outputs')
    return next((r['level'] for r in levels if r['text'] == levels[-1]['text']), 11)


def make_schedule(entries, warm, trajectories):
    if len(entries) != 256 or len(warm) != 16 or len({e['identity'] for e in entries + warm}) != 272:
        raise ValueError('E2 population/overlap differs')
    if set(trajectories) != {e['index'] for e in entries + warm}:
        raise ValueError('Unexpected/missing output access')
    cells = list(METHODS)
    random.Random(20261026).shuffle(cells)
    rows = []
    for block in range(2):
        for repeat in range(5):
            for j, method in enumerate(cells):
                e = warm[(repeat * 12 + j) % 16]
                rows.append(dict(block=block, phase='warmup', repeat=repeat, order=j, method=method, **{k:e[k] for k in ('identity','index')}))
        population = entries if block == 0 else entries[::-1]
        for i, e in enumerate(population):
            for repeat in range(2):
                for j in range(12):
                    method = cells[(j + 512 * block + 2 * i + repeat) % 12]
                    rows.append(dict(block=block, phase='timed', repeat=repeat, order=j, method=method, **{k:e[k] for k in ('identity','index')}))
    for number, r in enumerate(rows):
        r.update(request_id=number, depth=exact_depth(trajectories[r['index']]) if r['method']=='exact' else int(r['method'].split(':')[1]),
                 schedule='every_level' if r['method']=='exact' else 'terminal')
    return rows


def quality_gate(intervals):
    margins = {'bleu':.5, 'chrf':1., 'numeric':.02, 'negation':.02}
    # All endpoints oriented as candidate minus full; lower is better only for negation.
    passed = all(v['upper'] is not None and (v['upper'] <= margins[k] if k=='negation' else v['lower'] >= -margins[k]) for k,v in intervals.items())
    failed = any(v['lower'] is not None and (v['lower'] > margins[k] if k=='negation' else v['upper'] < -margins[k]) for k,v in intervals.items())
    return 'pass' if passed else 'fail' if failed else 'unresolved'


def analyze(trajectories, entries, refs, records, plan, seconds=3600, draws=100000):
    begin = time.monotonic()
    if len(records) != len(plan) or any(any(r[k]!=p[k] for k in p) for r,p in zip(records,plan,strict=True)):
        raise ValueError('Missing/reordered execution')
    for r in records:
        expected = dict(inputs=1,generator_levels=r['depth'],decoder=r['depth'] if r['method']=='exact' else 1,encoder=0)
        if not r['parity'] or r['work'] != expected or r['wall_ms'] <= 0:
            raise ValueError('Execution parity/work/time failure')
    rows = [trajectories[e['index']] for e in entries]
    corpus = Corpus(rows, refs)
    n = len(rows)
    assignments = [np.array([exact_depth(r) for r in rows])] + [np.full(n,d) for d in range(1,12)]
    direct = {method:corpus.direct(a) for method,a in zip(METHODS,assignments,strict=True)}
    if any(rows[i]['levels'][int(d)-1]['text'] != rows[i]['levels'][-1]['text'] for i,d in enumerate(assignments[0])):
        raise ValueError('Exact structural contract failed')
    rng = np.random.Generator(np.random.PCG64(20261026))
    ix = rng.integers(0,n,size=(draws,n),dtype=np.int32)
    blocks = rng.integers(0,2,size=(draws,2),dtype=np.int32)
    boot = {}
    # Corpus statistics are summed for each resample, never sentence-score averaged.
    for name, metric in corpus.metric.items():
        boot[name] = np.empty((12,draws))
        for j,a in enumerate(assignments):
            stats = corpus.stats[name][np.arange(n), a-1]
            for start in range(0,draws,500):
                if time.monotonic()-begin > seconds: raise RuntimeError('E2 analysis wall cap')
                totals = stats[ix[start:start+500]].sum(axis=1)
                boot[name][j,start:start+len(totals)] = [metric._compute_score_from_stats(s.tolist()).score for s in totals]
            print(f'E2 corpus bootstrap: {name} {METHODS[j]} complete',flush=True)
    quality = {}
    for j,(method,a) in enumerate(zip(METHODS,assignments,strict=True)):
        structural = method in ('exact','fixed:11')
        intervals = {}
        for name in ('bleu','chrf'):
            intervals[name] = dict(order_interval(boot[name][j]-boot[name][-1],TAIL,FAMILY), difference=direct[method][name]-direct['fixed:11'][name],structural=structural)
            if structural:
                if np.any(boot[name][j]!=boot[name][-1]): raise ValueError('Structural corpus equality contradicted')
                intervals[name].update(lower=0.,upper=0.)
        selected = (np.arange(n),a-1)
        intervals['numeric'] = cue_interval((corpus.numeric[selected]-corpus.numeric[:,-1])[corpus.covered],TAIL,structural=structural)
        intervals['negation'] = cue_interval(corpus.negation[selected]-corpus.negation[:,-1],TAIL,structural=structural)
        quality[method] = dict(metrics=direct[method],intervals=intervals,status=quality_gate(intervals))
    data = np.full((n,2,2,12),np.nan)
    positions = {e['identity']:i for i,e in enumerate(entries)}
    for r in records:
        if r['phase']=='timed': data[positions[r['identity']],r['block'],r['repeat'],METHODS.index(r['method'])] = r['wall_ms']
    if not np.isfinite(data).all(): raise ValueError('Missing timing cells')
    means = data.mean(axis=2)
    timing = {}
    for j,method in enumerate(METHODS[1:],1):
        values = crossed_ratio(means[:,:,j],means[:,:,0],ix,blocks)
        timing[method] = dict(order_interval(values,TAIL,FAMILY), relative_mean_reduction=float(1-means[:,:,0].mean()/means[:,:,j].mean()),
                             process_reductions=[float(1-means[:,b,0].mean()/means[:,b,j].mean()) for b in range(2)])
    potentially_feasible = [m for m in METHODS[1:] if quality[m]['status']!='fail']
    versus_full = timing['fixed:11']
    positive = versus_full['relative_mean_reduction']>=.05 and versus_full['lower'] is not None and versus_full['lower']>0
    frontier = positive and all(timing[m]['lower'] is not None and timing[m]['lower']>0 for m in potentially_feasible)
    decision = 'exact_headroom_and_fixed_frontier_pass' if frontier else ('bounded_exact_no_go' if versus_full['upper'] is not None and versus_full['upper']<.05 else 'exact_headroom_inconclusive')
    return dict(decision=decision,quality=quality,timing_exact_versus_fixed=timing,potentially_feasible_fixed=potentially_feasible,
                methods={m:dict(mean_ms=float(data[:,:,:,j].mean()),median_ms=float(np.median(data[:,:,:,j])),p95_ms=float(np.percentile(data[:,:,:,j],95)),process_mean_ms=data[:,:,:,j].mean(axis=(0,2)).tolist()) for j,m in enumerate(METHODS)},
                exact_depth_counts={str(d):int((assignments[0]==d).sum()) for d in range(1,12)},
                early_exact_inputs=int((assignments[0]<11).sum()),mean_exact_depth=float(assignments[0].mean()),
                family_intervals=FAMILY,tail_alpha=TAIL,bootstrap_draws=draws,bootstrap_seed=20261026,
                practical_cost_screen_pass=positive,fixed_frontier_pass=frontier,controller_entry_released=False,
                analysis_wall_seconds=time.monotonic()-begin,
                limitations=['clairvoyant exact-text assignment, not online recognition','two process blocks only','unknown document/training overlap','aggregate-baseline-exposed audit inputs, not final confirmation','earliest exact exit is not a certified latency optimum','nonidentical rules excluded prospectively by E0 cue-coverage obstruction'])
