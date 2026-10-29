"""Pure scheduling, hash parity and paired document timing summaries."""
import hashlib
import json
import random
import numpy as np
from anytime_ncm.evidence_preflight import order_interval

METHODS = ('assigned_sparse',) + tuple('fixed:%d' % d for d in range(1, 12))
LEVELS = (1, 4, 8, 14, 20, 26, 32, 40, 48, 56, 64)

def value_hash(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=True, separators=(',', ':')).encode()).hexdigest()

def observations(method, depth):
    if method not in METHODS or type(depth) is not int or not 1 <= depth <= 11:
        raise ValueError('Invalid method/depth')
    if method == 'assigned_sparse':
        if depth not in (8, 10, 11): raise ValueError('Invalid sparse exit')
        return [d for d in (8, 10, 11) if d <= depth]
    if method != 'fixed:%d' % depth: raise ValueError('Fixed method/depth differ')
    return [depth]

def work(request):
    return dict(inputs=1, generator_levels=request['depth'],
                decoder=len(observations(request['method'], request['depth'])), encoder=0)

def make_schedule(entries, exits, session):
    if (session not in (0, 1) or len(entries) != len(exits) or len(entries) < 16
            or len({e['index'] for e in entries}) != len(entries)):
        raise ValueError('Invalid schedule population')
    for d in exits: observations('assigned_sparse', d)
    rng = random.Random(20261028 + session)
    result = []
    def add(position, method, warmup, repeat):
        e = entries[position]
        depth = exits[position] if method == 'assigned_sparse' else int(method.split(':')[1])
        result.append(dict(request_id=len(result), session=session, position=position,
                           index=e['index'], identity=e['identity'], method=method, depth=depth,
                           warmup=warmup, repeat=repeat))
    methods = list(METHODS); rng.shuffle(methods)
    for m, method in enumerate(methods):
        for j in range(5): add((m * 5 + j) % 16, method, True, -1)
    for repeat in range(2):
        positions = list(range(len(entries))); rng.shuffle(positions)
        for p in positions:
            methods = list(METHODS); rng.shuffle(methods)
            for method in methods: add(p, method, False, repeat)
    return result

def parity_cache(row):
    if (row['partition'] != 'E2_audit' or len(row['prefix_ids']) != 96 or len(row['codes']) != sum(LEVELS)
            or [o['level'] for o in row['levels']] != list(range(1, 12))
            or any(len(o['ids']) != 64 or not isinstance(o['text'], str) for o in row['levels'])):
        raise ValueError('Invalid consumed E2 trajectory')
    return dict(identity=row['identity'], prefix=value_hash(row['prefix_ids']),
                codes={str(d): value_hash(row['codes'][:sum(LEVELS[:d])]) for d in range(1, 12)},
                outputs={str(o['level']): dict(ids=value_hash(o['ids']), text=value_hash(o['text'])) for o in row['levels']})

def check_parity(result, expected, request):
    depth = request['depth']
    visits = observations(request['method'], depth)
    hashes = dict(prefix=value_hash(result['prefix_ids']), codes=value_hash(result['codes'][0].cpu().tolist()),
                  outputs={str(o['level']): dict(ids=value_hash(o['ids']), text=value_hash(o['text'])) for o in result['observations']})
    if (result['exit_level'] != depth or [o['level'] for o in result['observations']] != visits
            or hashes['prefix'] != expected['prefix'] or hashes['codes'] != expected['codes'][str(depth)]
            or any(hashes['outputs'][str(d)] != expected['outputs'][str(d)] for d in visits)
            or result['ids'] != result['observations'][-1]['ids'] or result['text'] != result['observations'][-1]['text']):
        raise ValueError('Output/prefix parity failed')
    return hashes

def cluster_draws(cells, groups, picks):
    """Input-weighted paired ratios: sum whole document totals, not document means."""
    cells = np.asarray(cells, dtype=float)
    groups = np.asarray(groups)
    picks = np.asarray(picks, dtype=int)
    unique = sorted(set(groups.tolist()))
    if (cells.ndim != 2 or cells.shape[1] != len(METHODS) or len(groups) != len(cells)
            or not np.isfinite(cells).all() or np.any(cells <= 0) or len(unique) < 2
            or picks.ndim != 2 or picks.shape[1] != len(unique) or np.any(picks < 0) or np.any(picks >= len(unique))):
        raise ValueError('Invalid paired document resampling')
    totals = np.array([cells[groups == g].sum(axis=0) for g in unique])
    sampled = totals[picks].sum(axis=1)
    return 1 - sampled[:, :1] / sampled[:, 1:]

def analyze(records, entries, documents, quality, draws=20000):
    if draws != 20000: raise ValueError('Frozen bootstrap count differs')
    n = len(entries)
    cells = np.full((2, n, 2, len(METHODS)), np.nan)
    for row in records:
        if row['warmup']: continue
        key = (row['session'], row['position'], row['repeat'], METHODS.index(row['method']))
        if not np.isnan(cells[key]): raise ValueError('Duplicate timing cell')
        if not row['parity'] or row['wall_ms'] <= 0 or row['work'] != work(row): raise ValueError('Invalid timing cell')
        cells[key] = row['wall_ms']
    if not np.isfinite(cells).all(): raise ValueError('Missing timing cells')
    means = cells.mean(axis=(0, 2))
    group_map = {e['index']: e['document_sha256'] for e in documents}
    groups = [group_map[e['index']] for e in entries]
    g = len(set(groups))
    if g < 20: raise ValueError('Insufficient document coverage for diagnostic intervals')
    rng = np.random.default_rng(20261028)
    picks = rng.integers(g, size=(draws, g))
    samples = cluster_draws(means, groups, picks)
    summaries = {}
    for m, method in enumerate(METHODS):
        values = cells[:, :, :, m]
        summaries[method] = dict(mean_ms=float(values.mean()), median_ms=float(np.median(values)),
            p95_ms=float(np.percentile(values, 95)), session_mean_ms=values.mean(axis=(1, 2)).tolist(),
            cuda_stream_mean_ms=float(np.mean([r['cuda_stream_span_ms'] for r in records if not r['warmup'] and r['method'] == method])))
    contrasts = {}
    for m, method in enumerate(METHODS[1:]):
        base = summaries[method]['mean_ms']; assigned = summaries['assigned_sparse']['mean_ms']
        interval = order_interval(samples[:, m], .05 / 22, 11)
        contrasts[method] = dict(full_relative_or_fixed_relative_savings=1-assigned/base,
            session_savings=[1-a/b for a,b in zip(summaries['assigned_sparse']['session_mean_ms'], summaries[method]['session_mean_ms'])],
            conditional_nominal_interval=interval)
    primary = contrasts['fixed:11']
    passing = [k for k,v in quality['baselines'].items() if k.startswith('fixed:') and v['point_quality_pass']]
    comparator = min(passing, key=lambda k:summaries[k]['mean_ms']) if passing else None
    good = (primary['full_relative_or_fixed_relative_savings'] >= .05
        and all(v > 0 for v in primary['session_savings'])
        and primary['conditional_nominal_interval']['lower'] is not None and primary['conditional_nominal_interval']['lower'] > 0
        and comparator is not None and contrasts[comparator]['conditional_nominal_interval']['lower'] > 0)
    decision = ('measured_assigned_exit_headroom' if good else
                'insufficient_assigned_exit_savings' if primary['full_relative_or_fixed_relative_savings'] < .05 else 'inconclusive_assigned_exit_headroom')
    return dict(methods=summaries, contrasts=contrasts, decision=decision, input_count=n, source_documents=g,
        bootstrap_draws=draws, tail_alpha=.05/22, interval_family=11, mc_rank_failure_allowance=.001,
        conditional_on_observed_sessions=True, independent_quality_evidence=False,
        point_quality_feasible_fixed=passing, fastest_point_quality_feasible_fixed=comparator,
        statistically_excluded_fixed_depths=[], Q0_passed=False, controller_trained=False, Q3_authorized=False,
        controller_overhead_budget_ms_for_5_percent=.95*summaries['fixed:11']['mean_ms']-summaries['assigned_sparse']['mean_ms'])


def document_components(documents, prefix_manifest):
    """Union source documents linked by existing effective-prefix aliases."""
    mapping = {r['index']: r['document_sha256'] for r in documents}
    parent = {d:d for d in mapping.values()}
    def find(d):
        while parent[d] != d:
            parent[d] = parent[parent[d]]; d = parent[d]
        return d
    for entries in prefix_manifest['partitions'].values():
        for e in entries:
            docs = [mapping[i] for i in e['indices']]
            for d in docs[1:]:
                a,b = find(docs[0]), find(d)
                parent[max(a,b)] = min(a,b)
    return [dict(index=i, document_sha256=find(d)) for i,d in sorted(mapping.items())]
