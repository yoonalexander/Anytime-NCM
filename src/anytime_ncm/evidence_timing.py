"""Pure E1 scheduling and paired descriptive analysis; no model imports."""
from collections import Counter
import hashlib
import json
import random
import numpy as np

DEPTHS = (1, 4, 7, 10, 11)


def make_schedule(entries):
    if len(entries) != 16 or len({e['identity'] for e in entries}) != 16:
        raise ValueError('E1 needs exactly sixteen distinct existing identities')
    cells = [(schedule, depth) for schedule in ('terminal', 'every_level') for depth in DEPTHS]
    random.Random(20261025).shuffle(cells)
    rows = []
    for block in range(2):
        for warm_round in range(2):
            for j, (schedule, depth) in enumerate(cells):
                entry = entries[(warm_round * 10 + j) % 16]
                rows.append(dict(block=block, phase='warmup', identity=entry['identity'], index=entry['index'],
                                 repeat=warm_round, schedule=schedule, depth=depth, order=j))
        population = entries if block == 0 else list(reversed(entries))
        for i, entry in enumerate(population):
            for repeat in range(3):
                offset = block * 48 + i * 3 + repeat
                for order in range(10):
                    schedule, depth = cells[(order + offset) % 10]
                    rows.append(dict(block=block, phase='timed', identity=entry['identity'], index=entry['index'],
                                     repeat=repeat, schedule=schedule, depth=depth, order=order))
    for i, row in enumerate(rows):
        row['request_id'] = i
    validate_schedule(rows, entries)
    return rows


def validate_schedule(rows, entries):
    if len(rows) != 1000 or [r['request_id'] for r in rows] != list(range(1000)):
        raise ValueError('E1 request count/order differs')
    allowed = {(e['identity'], e['index']) for e in entries}
    if any((r['identity'], r['index']) not in allowed for r in rows):
        raise ValueError('Forbidden E1 identity')
    if sum(r['depth'] for r in rows) != 6600 or sum(1 if r['schedule'] == 'terminal' else r['depth'] for r in rows) != 3800:
        raise ValueError('E1 depth/decoder budget differs')
    for block in range(2):
        selected = [r for r in rows if r['block'] == block]
        expected = Counter({(e['identity'], repeat, schedule, depth): 1 for e in entries for repeat in range(3)
                            for schedule in ('terminal', 'every_level') for depth in DEPTHS})
        actual = Counter((r['identity'], r['repeat'], r['schedule'], r['depth']) for r in selected if r['phase'] == 'timed')
        warm = Counter((r['schedule'], r['depth']) for r in selected if r['phase'] == 'warmup')
        if len(selected) != 500 or actual != expected or len(warm) != 10 or set(warm.values()) != {2}:
            raise ValueError('E1 paired/warmup coverage differs')


def value_hash(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=True, separators=(',', ':')).encode()).hexdigest()


def analyze(rows, schedule, entries):
    validate_schedule(schedule, entries)
    if len(rows) != 1000 or any(any(row[k] != expected[k] for k in expected) for row, expected in zip(rows, schedule, strict=True)):
        raise ValueError('Missing/changed E1 request record')
    if not all(row['parity'] for row in rows):
        raise ValueError('Cannot analyze failed parity')
    keys = [(s, d) for s in ('terminal', 'every_level') for d in DEPTHS]
    position = {e['identity']: i for i, e in enumerate(entries)}
    data = np.full((2, 16, 3, 10), np.nan)
    summaries = {}
    for row in rows:
        expected = {'inputs': 1, 'generator_levels': row['depth'], 'decoder': 1 if row['schedule'] == 'terminal' else row['depth'], 'encoder': 0}
        if row['work'] != expected:
            raise ValueError('Work counters differ')
        if row['phase'] == 'timed':
            data[row['block'], position[row['identity']], row['repeat'], keys.index((row['schedule'], row['depth']))] = row['wall_ms']
    if not np.isfinite(data).all() or np.any(data <= 0):
        raise ValueError('Missing/nonpositive timing')
    rng = np.random.Generator(np.random.PCG64(20261025))
    ix = rng.integers(0, 16, size=(10000, 16))
    means = data.mean(axis=2)  # block, identity, cell
    boot = means[:, ix, :].mean(axis=2)  # block, bootstrap, cell
    full = keys.index(('terminal', 11))
    for j, key in enumerate(keys):
        values = data[:, :, :, j].ravel()
        summaries[f'{key[0]}:{key[1]}'] = {'mean_ms': float(values.mean()), 'median_ms': float(np.median(values)),
                                        'p95_ms': float(np.percentile(values, 95)),
                                        'process_mean_ms': data[:, :, :, j].mean(axis=(1, 2)).tolist()}

    def contrast(candidate, baseline):
        result = {}
        for label, a, b, aa, bb in [('pooled', means[:, :, candidate].mean(), means[:, :, baseline].mean(), boot[:, :, candidate].mean(axis=0), boot[:, :, baseline].mean(axis=0)),
                                   *[(f'block_{i}', means[i, :, candidate].mean(), means[i, :, baseline].mean(), boot[i, :, candidate], boot[i, :, baseline]) for i in range(2)]]:
            result[label] = {'relative_mean_reduction': float(1 - a / b), 'absolute_mean_difference_ms': float(a - b),
                             'relative_mean_reduction_ci95_nominal': np.percentile(1 - aa / bb, [2.5, 97.5]).tolist()}
        return result

    versus_full = {f'{s}:{d}': contrast(j, full) for j, (s, d) in enumerate(keys)}
    monitoring = {str(d): contrast(keys.index(('every_level', d)), keys.index(('terminal', d))) for d in DEPTHS}
    cheaper = [key for key, comparison in versus_full.items() if not key.endswith(':11') and comparison['pooled']['relative_mean_reduction'] > 0]
    return {'cells': summaries, 'versus_terminal_11': versus_full, 'every_level_versus_terminal': monitoring,
            'identity_bootstrap_draws': 10000, 'process_population_uncertainty_identified': False,
            'cheaper_early_forced_cells_point_only': cheaper,
            'decision': 'cheaper_forced_path_observed_not_adaptive_speedup' if cheaper else 'no_cheaper_forced_path_in_pilot',
            'limitations': ['sixteen previously exposed inputs', 'two process blocks only', 'nominal descriptive intervals without multiplicity correction',
                            'no quality scoring, causal selector, oracle assignment or fresh confirmation']}
