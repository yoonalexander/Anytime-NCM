"""Input-only and synthetic E0 helpers. No model or output-body readers."""
from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import re

import numpy as np
from scipy.stats import beta, binom, norm
from sacrebleu.metrics import BLEU, CHRF

from anytime_ncm.wmt_data import StringRows

HEADER = re.compile(rb'^\{"identity":\s*"([a-f0-9]{64})",\s*"index":\s*(\d+),\s*"partition":\s*"([a-z0-9_]+)"')


class Budget:
    """Charge before work and reject exhausted allocations without a restart."""
    def __init__(self, limits, stream):
        self.limits = limits
        self.stream = stream
        self.counts = {'trials': 0, 'bootstrap_draws': 0, 'representative_datasets': 0}

    def consume(self, kind, amount, label):
        if kind not in self.counts or type(amount) is not int or amount <= 0:
            raise ValueError('Invalid budget charge')
        if self.counts[kind] + amount > self.limits[kind]:
            raise RuntimeError('E0 allocation exhausted: ' + kind)
        self.counts[kind] += amount
        self.stream.write(json.dumps({'kind': kind, 'amount': amount, 'label': label,
                                      'counts': dict(self.counts)}) + '\n')
        self.stream.flush()


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def header_inventory(path):
    """Never decode the JSON body, even if the bytes are malformed/poisoned."""
    counts = Counter()
    with Path(path).open('rb') as stream:
        for raw in stream:
            match = HEADER.match(raw)
            if match is None:
                raise ValueError('Noncanonical identity header: ' + str(path))
            counts[(match[3].decode('ascii'), int(match[2]), match[1].decode('ascii'))] += 1
    return counts


def allocate(manifest, sources, lock):
    """Fail before assigning roles if source or identity groups are inconsistent."""
    rows = [(part, entry) for part, entries in manifest['partitions'].items() for entry in entries]
    identities = [entry['identity'] for _, entry in rows]
    indices = [i for _, entry in rows for i in entry['indices']]
    if len(set(identities)) != len(identities) or sorted(indices) != list(range(len(sources))):
        raise ValueError('Identity collision or source coverage mismatch')
    source_groups = defaultdict(list)
    for part, entry in rows:
        if entry['index'] != min(entry['indices']):
            raise ValueError('Noncanonical source index')
        for i in entry['indices']:
            digest = hashlib.sha256(sources[i].encode('utf-8')).hexdigest()
            source_groups[digest].append((part, entry['identity'], i))
    duplicates = [group for group in source_groups.values() if len(group) > 1]
    if any(len({identity for _, identity, _ in group}) > 1 for group in duplicates):
        raise ValueError('Exact full-source duplicate crosses effective-prefix identities; amend grouping')
    reserved = manifest['partitions']['reserved']
    if len(reserved) != sum(lock['role_counts']):
        raise ValueError('Eligible reservation count differs; do not replenish')
    salt = lock['allocation_salt']
    ordered = sorted(reserved, key=lambda e: (
        hashlib.sha256((salt + e['identity']).encode('utf-8')).hexdigest(), e['index']))
    roles = {}
    offset = 0
    for role, count in zip(lock['role_order'], lock['role_counts'], strict=True):
        roles[role] = [dict(entry, original_partition='reserved', role=role,
                           source_text_sha256=hashlib.sha256(sources[entry['index']].encode('utf-8')).hexdigest(),
                           outcome_access_released=False)
                       for entry in ordered[offset:offset + count]]
        offset += count
    return roles, {'full_source_exact_duplicate_groups': len(duplicates),
                   'source_rows': len(sources), 'effective_prefix_groups': len(rows),
                   'document_ids_available': False, 'document_independence_established': False}


def cp_upper(k, n, alpha):
    if not 0 < alpha < 1 or n <= 0 or not 0 <= k <= n:
        raise ValueError('Invalid binomial interval inputs')
    return 1.0 if k == n else float(beta.isf(alpha, k + 1, n - k))


def minimum_coverage(alpha, margin=.02):
    if not 0 < alpha < 1 or not 0 < margin < 1:
        raise ValueError('Invalid coverage inputs')
    return math.ceil(math.log(alpha) / math.log1p(-margin))


def cue_interval(differences, alpha, structural=False):
    values = np.asarray(differences, dtype=float)
    if values.ndim != 1 or not np.isfinite(values).all() or np.any(np.abs(values) > 1):
        raise ValueError('Paired cue differences must be finite and in [-1,1]')
    if structural:
        if np.any(values != 0):
            raise ValueError('Structural equality contradicts observations')
        return {'lower': 0., 'upper': 0., 'coverage': len(values), 'structural': True}
    if not len(values):
        return {'lower': None, 'upper': None, 'coverage': 0, 'structural': False}
    return {'lower': -cp_upper(int((values < 0).sum()), len(values), alpha),
            'upper': cp_upper(int((values > 0).sum()), len(values), alpha),
            'coverage': len(values), 'structural': False}


def mc_precision(draws, tail, intervals, allowance=.001):
    if draws <= 0 or not 0 < tail < .5 or intervals < 1:
        raise ValueError('Invalid Monte Carlo precision parameters')
    rank = int(binom.ppf(allowance / (2 * intervals), draws, tail))
    return {'draws': draws, 'tail_probability': tail, 'expected_tail_count': draws * tail,
            'zero_tail_probability': float(binom.pmf(0, draws, tail)),
            'tail_count_ci95': [int(x) for x in binom.ppf([.025, .975], draws, tail)],
            'conservative_one_based_rank': rank, 'quantile_resolved': rank >= 1}


def order_interval(draws, tail, intervals):
    draws = np.sort(np.asarray(draws, dtype=float))
    precision = mc_precision(len(draws), tail, intervals)
    k = precision['conservative_one_based_rank']
    return {'lower': float(draws[k - 1]) if k else None,
            'upper': float(draws[len(draws) - k]) if k else None,
            'degenerate': bool(np.ptp(draws) == 0), 'precision': precision}


def crossed_ratio(base, candidate, identity_indices, block_indices):
    """Means over crossed input/block axes with common indices for both methods."""
    base = np.asarray(base, dtype=float)
    candidate = np.asarray(candidate, dtype=float)
    if base.shape != candidate.shape or base.ndim != 2 or np.any(base <= 0) or np.any(candidate <= 0):
        raise ValueError('Require matched positive identity-by-process times')
    selected_base = base[identity_indices[:, :, None], block_indices[:, None, :]].mean(axis=(1, 2))
    selected_candidate = candidate[identity_indices[:, :, None], block_indices[:, None, :]].mean(axis=(1, 2))
    return 1 - selected_candidate / selected_base


def _cp_zero_or_counts(counts, coverage, alpha):
    result = np.full(np.shape(counts), np.nan)
    valid = coverage > 0
    complete = valid & (counts == coverage)
    other = valid & ~complete
    result[complete] = 1.
    result[other] = beta.isf(alpha, counts[other] + 1, coverage[other] - counts[other])
    return result


def trial_grid(lock, consume):
    results = []
    trials = lock['trials_per_scenario']
    for position, (scenario, n) in enumerate((s, n) for s in lock['scenarios'] for n in lock['sample_sizes']):
        consume('trials', trials, label=f"{scenario['name']}/{n}")
        rng = np.random.Generator(np.random.PCG64(lock['trial_seed'] + position))
        cluster = scenario['cluster_size']
        z = rng.normal(size=(trials, n))
        if cluster > 1:
            group = np.repeat(rng.normal(size=(trials, n // cluster)), cluster, axis=1)
            z = np.sqrt(lock['cluster_rho']) * group + np.sqrt(1 - lock['cluster_rho']) * z
        reduction = scenario['latency_reduction'] + lock['latency_proxy_sd'] * z
        b = scenario['bleu_proxy_difference'] + lock['bleu_proxy_sd'] * rng.normal(size=(trials, n))
        c = scenario['chrf_proxy_difference'] + lock['chrf_proxy_sd'] * rng.normal(size=(trials, n))
        covered = rng.binomial(n, scenario['numeric_coverage'], size=trials)
        losses = rng.binomial(covered, scenario['adverse_probability'])
        neg_losses = rng.binomial(n, scenario['adverse_probability'], size=trials)
        stages = {}
        for stage in ('E2', 'E4'):
            alpha = lock[stage]['tail_alpha']
            critical = norm.isf(alpha)
            lower = reduction.mean(axis=1) - critical * reduction.std(axis=1, ddof=1) / np.sqrt(n)
            latency = (reduction.mean(axis=1) >= .05) & (lower > 0)
            q = ((b.mean(axis=1) - critical * b.std(axis=1, ddof=1) / np.sqrt(n) >= -.5)
                 & (c.mean(axis=1) - critical * c.std(axis=1, ddof=1) / np.sqrt(n) >= -1.))
            numeric_u = _cp_zero_or_counts(losses, covered, alpha)
            neg_u = _cp_zero_or_counts(neg_losses, np.full(trials, n), alpha)
            cue_pass = (numeric_u <= lock['cue_margin']) & (neg_u <= lock['cue_margin'])
            stats = {'latency_proxy_pass_fraction': float(latency.mean()),
                     'normal_quality_proxy_pass_fraction': float(q.mean()),
                     'cue_pass_fraction': float(cue_pass.mean()),
                     'nonidentical_joint_proxy_pass_fraction': float((latency & q & cue_pass).mean()),
                     'structural_exact_latency_proxy_pass_fraction': float(latency.mean()),
                     'mean_numeric_coverage': float(covered.mean()),
                     'undefined_numeric_trials': int((covered == 0).sum()),
                     'naive_latency_interval_covers_true_fraction': float((np.abs(reduction.mean(axis=1) - scenario['latency_reduction']) <= critical * reduction.std(axis=1, ddof=1) / np.sqrt(n)).mean())}
            if cluster > 1:
                group_means = reduction.reshape(trials, n // cluster, cluster).mean(axis=2)
                half = critical * group_means.std(axis=1, ddof=1) / np.sqrt(n // cluster)
                stats['known_cluster_latency_interval_covers_true_fraction'] = float((np.abs(group_means.mean(axis=1) - scenario['latency_reduction']) <= half).mean())
            stages[stage] = stats
        results.append({'scenario': scenario['name'], 'n': n, 'trials': trials, 'stages': stages})
    return results


def representative_bootstraps(lock, consume):
    summaries = []
    metric = {'bleu': BLEU(), 'chrf': CHRF()}
    for position, (family, n) in enumerate((f, n) for f in lock['representative_families'] for n in lock['sample_sizes']):
        consume('bootstrap_draws', lock['representative_bootstrap_draws'], label=f'{family}/{n}')
        consume('representative_datasets', 1, label=f'{family}/{n}')
        rng = np.random.Generator(np.random.PCG64(lock['bootstrap_seed'] + position))
        refs = [f'the careful worker does not move the {i % 23 + 10} small boxes today' for i in range(n)]
        hyps = [s.replace('small', 'large') if (family == 'one_in_20' and i % 20 == 0) or (family == 'one_in_five' and i % 5 == 0) or (family == 'clustered' and (i // 8) % 5 == 0) else s for i, s in enumerate(refs)]
        stats = {}
        points = {}
        for name, m in metric.items():
            a = np.asarray(m._extract_corpus_statistics(hyps, [refs]), dtype=np.int64)
            b = np.asarray(m._extract_corpus_statistics(refs, [refs]), dtype=np.int64)
            point = m._compute_score_from_stats(a.sum(axis=0).tolist()).score - m._compute_score_from_stats(b.sum(axis=0).tolist()).score
            direct = m.corpus_score(hyps, [refs]).score - m.corpus_score(refs, [refs]).score
            if abs(point - direct) > 1e-10:
                raise ValueError('Synthetic corpus parity failure')
            stats[name] = (a, b)
            points[name] = point
        base = 130 * np.exp(rng.normal(0, .15, size=(n, 1))) * np.exp(rng.normal(0, .03, size=(1, 4)))
        candidate = base * np.exp(np.log(.95) - .04**2 / 2 + rng.normal(0, .04, size=(n, 4)))
        collected = {'bleu': [], 'chrf': [], 'timing_reduction': []}
        remaining = lock['representative_bootstrap_draws']
        while remaining:
            batch = min(128, remaining)
            ix = rng.integers(0, n, size=(batch, n))
            blocks = rng.integers(0, 4, size=(batch, 4))
            for name, m in metric.items():
                a, b = stats[name]
                aa, bb = a[ix].sum(axis=1), b[ix].sum(axis=1)
                collected[name].extend(m._compute_score_from_stats(x.tolist()).score - m._compute_score_from_stats(y.tolist()).score for x, y in zip(aa, bb, strict=True))
            collected['timing_reduction'].extend(crossed_ratio(base, candidate, ix, blocks).tolist())
            remaining -= batch
        summaries.append({'family': family, 'n': n, 'draws': lock['representative_bootstrap_draws'],
                          'corpus_direct_parity': True, 'quality_points': points,
                          'timing_reduction_point': float(1 - candidate.mean() / base.mean()),
                          'intervals': {name: {label: order_interval(values, tail, count) for label, tail, count in [
                              ('nominal95', .025, 1), ('E2_tail_on_10000_draws', lock['E2']['tail_alpha'], 89),
                              ('E4_tail_on_10000_draws', lock['E4']['tail_alpha'], 10)]}
                              for name, values in collected.items()}})
    return summaries


def input_audit(root, lock):
    root = Path(root)
    manifest_path = root / 'docs/partitions/wmt14-phase4.json'
    source_path = root / 'data/wmt14/sources.pickle'
    if sha(manifest_path) != lock['manifest_sha256'] or sha(source_path) != lock['source_pickle_sha256']:
        raise ValueError('Pinned input digest differs')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    config_path = root / 'configs/phase4_wmt_sources.json'
    config = json.loads(config_path.read_text(encoding='utf-8'))
    if (config['dataset_revision'] != '6580ba41a4b0a976dde876fbe84d25327617b0e6'
            or config['model_revision'] != 'd342ce8aaea58830eef3b8ad473664673e41f692'
            or config['text_tokenizer_revision'] != 'c1899de289a04d12100db370d81485cdf75e47ca'):
        raise ValueError('Pinned revision metadata differs')
    sources = StringRows(source_path.read_bytes()).select(set(range(3003)))
    roles, grouping = allocate(manifest, sources, lock)
    parts = manifest['partitions']
    audit = [('exploration', e) for e in parts['exploration'][:128]] + [('development', e) for e in parts['development'][:64]]
    expectations = {'results/phase4/wmt14/trajectories.jsonl': (audit, 1),
                    'results/phase4/wmt14/4b_requests.jsonl': ([('development', e) for e in parts['development'][:64]], 12),
                    'results/phase4/wmt14/4c_requests.jsonl': ([('phase4_final', e) for e in parts['phase4_final']], 12)}
    exposure = {}
    reserved_ids = {e['identity'] for e in parts['reserved']}
    for path, (entries, repeats) in expectations.items():
        counts = header_inventory(root / path)
        expected = Counter({(part, e['index'], e['identity']): repeats for part, e in entries})
        if counts != expected or reserved_ids & {identity for _, _, identity in counts}:
            raise ValueError('Unexpected previously exposed WMT identity: ' + path)
        exposure[path] = {'rows': sum(counts.values()), 'identities': len(counts), 'reserved_intersection': 0,
                          'body_json_decodes': 0, 'sha256': sha(root / path)}
    for split, size in [('exploration', 128), ('development', 64)]:
        path = f'results/stronger_research/s1/{split}/access.json'
        access = json.loads((root / path).read_text(encoding='utf-8'))
        if access['identities'] != parts[split][:size]:
            raise ValueError('S1 exposure allowlist differs')
        exposure[path] = {'identities': size, 'reserved_intersection': 0, 'sha256': sha(root / path)}
    build_path = root / 'results/phase5/build.json'
    build = json.loads(build_path.read_text(encoding='utf-8'))
    for name, digest in build['artifacts'].items():
        if sha(root / 'results/phase5' / name) != digest:
            raise ValueError('Viewer artifact differs from recorded build: ' + name)
    result_paths = sorted(p.relative_to(root).as_posix() for p in (root / 'results').rglob('*') if p.is_file() and not p.relative_to(root).as_posix().startswith('results/evidence_gaps/'))
    suspicious = [p for p in result_paths if ('wmt' in p.lower() or p.endswith('.jsonl')) and not p.startswith((
        'results/phase1/', 'results/phase2/', 'results/phase3/', 'results/phase4/wmt14/',
        'results/phase5/', 'results/stronger_research/', 'results/followup/'))]
    if suspicious:
        raise ValueError('Unclassified plausible outcome paths: ' + str(suspicious))
    cache_paths = sorted(p.relative_to(root).as_posix() for name in ('tmp', '.cache', 'cache', 'outputs', 'logs')
                         if (root / name).exists() for p in (root / name).rglob('*') if p.is_file())
    unknown_cache = [p for p in cache_paths if 'wmt' in p.lower() and p.endswith(('.jsonl', '.json', '.pickle', '.pkl', '.csv'))]
    if unknown_cache:
        raise ValueError('Unclassified plausible WMT cache paths: ' + str(unknown_cache))
    return {'roles': roles, 'E1_existing_exploration': parts['exploration'][:16],
            'grouping': grouping, 'exposure_headers': exposure,
            'viewer_artifacts_match_build': True, 'viewer_source_population': 'same 192 audited identities; source reviewed; no viewer/catalog body decoded',
            'result_path_inventory': result_paths, 'unclassified_plausible_outcome_paths': suspicious,
            'local_cache_path_inventory': cache_paths,
            'config_lock': {'path': 'configs/phase4_wmt_sources.json', 'sha256': sha(config_path),
                            'dataset_revision': config['dataset_revision'], 'model_revision': config['model_revision'],
                            'text_tokenizer_revision': config['text_tokenizer_revision'],
                            'expected_assets': {p: {'sha256': info['sha256'], 'size': info['size']} for p, info in config['files'].items()},
                            'weights_not_rehashed_or_loaded': True},
            'prior_exposure': 'all 3003 groups: official full baseline aggregate; reserved per-input outcomes not found in recorded adaptive studies',
            'limitations': ['unrecorded/external analyst access cannot be excluded', 'unknown checkpoint-training overlap', 'no document identifiers; effective-prefix/exact-source groups are not proven independent documents'],
            'source_pickle_sha256': sha(source_path), 'manifest_sha256': sha(manifest_path)}
