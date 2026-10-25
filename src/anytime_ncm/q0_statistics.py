"""Q0 synthetic statistics only: no real-data/model readers or policy search."""
from __future__ import annotations
import math
import numpy as np
from scipy.stats import beta, binom

FAMILY = 59
TAIL = .05 / (2 * FAMILY)
MARGIN = .02


def minimum_coverage(alpha=TAIL, margin=MARGIN):
    if not 0 < alpha < 1 or not 0 < margin < 1:
        raise ValueError('Invalid alpha/margin')
    return math.ceil(math.log(alpha) / math.log1p(-margin))


def cp_upper(k, n, alpha=TAIL):
    if type(n) is not int or n < 1 or not 0 < alpha < 1:
        raise ValueError('Invalid n/alpha')
    k = np.asarray(k)
    if not np.isfinite(k).all() or np.any(k != np.floor(k)) or np.any((k < 0) | (k > n)):
        raise ValueError('Invalid event count')
    result = np.ones(k.shape, dtype=float)
    other = k < n
    result[other] = beta.isf(alpha, k[other] + 1, n - k[other])
    return result


def cue_interval(values, alpha=TAIL):
    x = np.asarray(values, dtype=float)
    if x.ndim != 1 or not np.isfinite(x).all() or np.any(np.abs(x) > 1):
        raise ValueError('Require finite paired losses in [-1,1]')
    if x.size == 0:
        return None
    return (-float(cp_upper(int(np.count_nonzero(x < 0)), len(x), alpha)),
            float(cp_upper(int(np.count_nonzero(x > 0)), len(x), alpha)))


def eb_upper(total, sum_squares, n, alpha=TAIL):
    if n < 2:
        return None
    mean = np.asarray(total, dtype=float) / n
    variance = np.maximum(0., (np.asarray(sum_squares) - n * mean**2) / (n - 1))
    logarithm = math.log(2 / alpha)
    return np.clip(mean + np.sqrt(2 * variance * logarithm / n)
                   + 14 * logarithm / (3 * (n - 1)), -1., 1.)


def mc_rate(events, trials):
    if not 0 <= events <= trials or trials < 1:
        raise ValueError('Invalid MC counts')
    lo = 0. if events == 0 else float(beta.ppf(.005, events, trials - events + 1))
    hi = 1. if events == trials else float(beta.isf(.005, events + 1, trials - events))
    return {'events': int(events), 'trials': trials, 'rate': events / trials, 'ci99': [lo, hi]}


def power_rows(ns, alpha=TAIL, alternative=.005):
    """Exact CP pass probability in the Bernoulli adverse-loss submodel."""
    ns = np.asarray(ns, dtype=int)
    k = binom.ppf(alpha, ns, MARGIN).astype(int)
    k -= (binom.cdf(k, ns, MARGIN) > alpha).astype(int)
    return k, binom.cdf(k, ns, alternative)


def rank_guard(draws, alpha=TAIL, family=FAMILY):
    if draws < 1:
        raise ValueError('Require draws')
    k = int(binom.ppf(.001 / (2 * family), draws, alpha))
    return {'draws': draws, 'rank': k, 'resolved': k > 0,
            'expected_tail_count': draws * alpha,
            'no_tail_probability': float(binom.pmf(0, draws, alpha))}


def interval(draws):
    x = np.sort(np.asarray(draws, dtype=float))
    if x.ndim != 1 or not len(x) or not np.isfinite(x).all():
        raise ValueError('Invalid bootstrap vector')
    g = rank_guard(len(x)); k = g['rank']
    return {'lower': float(x[k-1]) if k else None,
            'upper': float(x[-k]) if k else None, 'guard': g,
            'nominal95': np.quantile(x, [.025, .975]).tolist()}


def crossed_savings(base, candidate, identities, processes):
    b = np.asarray(base, dtype=float); c = np.asarray(candidate, dtype=float)
    if b.ndim != 2 or b.shape != c.shape or not np.isfinite(b).all() or not np.isfinite(c).all() or np.any(b <= 0) or np.any(c <= 0):
        raise ValueError('Require matched finite positive identity/process means')
    return 1 - c[identities[:, :, None], processes[:, None, :]].mean((1,2)) / b[identities[:, :, None], processes[:, None, :]].mean((1,2))


def quality_state(bounds):
    margins = {'bleu': .5, 'chrf': 1., 'numeric': .02, 'negation': .02}
    if set(bounds) != set(margins):
        raise ValueError('Require all four endpoints')
    if any(v is not None and v[0] > margins[k] for k,v in bounds.items()):
        return 'ruled_out'
    if all(v is not None and v[1] <= margins[k] for k,v in bounds.items()):
        return 'certified'
    return 'unresolved'


def success(quality, point_full, full_lower, fixed_lowers):
    return (quality == 'certified' and point_full >= .05 and full_lower is not None
            and full_lower > 0 and bool(fixed_lowers)
            and all(v is not None and v > 0 for v in fixed_lowers))


class Budget:
    def __init__(self, limits, stream):
        self.limits = limits
        self.stream = stream
        self.counts = dict(trials=0, bootstrap_draws=0, datasets=0)

    def charge(self, kind, amount, label):
        import json
        if kind not in self.counts or type(amount) is not int or amount < 1:
            raise ValueError('Invalid budget charge')
        if self.counts[kind] + amount > self.limits[kind]:
            raise RuntimeError('Q0 budget exhausted: ' + kind)
        self.counts[kind] += amount
        self.stream.write(json.dumps({'kind':kind, 'amount':amount, 'label':label,
                                      'counts':dict(self.counts)}) + '\n')
        self.stream.flush()


def analytical(lock):
    ns = [*lock['grid_n'], 385]
    result = {'zero_event_floors':{}, 'zero_event_bounds':{}, 'power':{}, 'population_sensitivity':[]}
    for label, a in [('original89', .05/178), ('primary59', TAIL), ('optimistic_single_endpoint', .05)]:
        result['zero_event_floors'][label] = minimum_coverage(a)
        result['zero_event_bounds'][label] = {str(n): -math.expm1(math.log(a)/n) for n in ns}
    scan = np.arange(1, lock['analytical_max_n']+1)
    for p in [.005, .01, .02]:
        ks, powers = power_rows(scan, alternative=p)
        found = scan[powers >= lock['power_target']]
        result['power'][str(p)] = {'first_n_power80':int(found[0]) if len(found) else None,
            'grid':[{'n':n, 'max_adverse_events':int(ks[n-1]), 'power':float(powers[n-1])} for n in ns]}
    for n in lock['coverage_populations']:
        for prevalence in lock['coverage_prevalences']:
            result['population_sensitivity'].append({'total_groups':n,'assumed_prevalence':prevalence,
                'expected_coverage':n*prevalence,
                'probability_reaching_floor':float(binom.sf(minimum_coverage()-1,n,prevalence))})
    result['all_zero_boundary_acceptance_probability_n48'] = .98**48
    result['eb_zero_variance_floor_at_mean_zero'] = math.ceil(1+14*math.log(2/TAIL)/(3*MARGIN))
    result['hoeffding_zero_mean_floor_range2'] = math.ceil(2*math.log(1/TAIL)/MARGIN**2)
    result['future_bootstrap_guard'] = rank_guard(100000)
    result['consumed_union_max_numeric_coverage'] = 48+128+64
    return result


def trials(lock, budget, check):
    rng = np.random.Generator(np.random.PCG64(lock['trial_seed']))
    report = []
    for n in lock['grid_n']:
        table = cp_upper(np.arange(n+1), n)
        for case in lock['case_order']:
            check(); t = lock['trials_per_case']; budget.charge('trials',t,f'{case}:{n}')
            plus = np.zeros(t,dtype=int); minus = plus.copy(); magnitude = 1.; truth = 0.
            if case in ('rare','boundary','outside'):
                p = {'rare':.005,'boundary':.02,'outside':.03}[case]
                plus = rng.binomial(n,p,t); truth=p
            elif case == 'fractional':
                plus = rng.binomial(n,.1,t); magnitude=.1; truth=.01
            elif case == 'balanced':
                counts = rng.multinomial(n,[.02,.02,.96],t); plus=counts[:,0]; minus=counts[:,1]
            elif case == 'benefit':
                minus = rng.binomial(n,.03,t); truth=-.03
            elif case == 'cluster8':
                cluster_counts = rng.binomial(n//8,.02,t); plus=cluster_counts*8; truth=.02
            elif case != 'zero':
                raise ValueError('Unfrozen scenario')
            totals = magnitude*(plus-minus); squares=magnitude**2*(plus+minus)
            upper=table[plus]; lower=-table[minus]; eb=eb_upper(totals,squares,n)
            eblo=-eb_upper(-totals,squares,n)
            entry={'case':case,'n':n,'true_mean_loss':truth,
                'primary_pass':mc_rate(int(np.sum(upper<=MARGIN)),t),
                'primary_coverage':mc_rate(int(np.sum((lower<=truth)&(truth<=upper))),t),
                'eb_diagnostic_pass':mc_rate(int(np.sum(eb<=MARGIN)),t),
                'eb_diagnostic_coverage':mc_rate(int(np.sum((eblo<=truth)&(truth<=eb))),t)}
            entry['primary_power80_mc_lower_met']=entry['primary_pass']['ci99'][0]>=.8
            if case=='cluster8':
                cu=cp_upper(cluster_counts,n//8)
                entry['cluster_unit_pass']=mc_rate(int(np.sum(cu<=MARGIN)),t)
                entry['cluster_unit_coverage']=mc_rate(int(np.sum(truth<=cu)),t)
                # Exact stress-test rejection probabilities; no MC uncertainty here.
                entry['naive_exact_false_pass_at_boundary']=float(binom.pmf(np.arange(n//8+1),n//8,.02)[table[np.arange(n//8+1)*8]<=MARGIN].sum())
            report.append(entry)
    return report


def text_bootstrap(lock, budget, check):
    from sacrebleu.metrics import BLEU, CHRF
    result=[]; n=lock['text_n']; b=lock['text_draws_each']
    for pos, name in enumerate(['identical','one_row','every_fifth','cluster8']):
        check(); budget.charge('datasets',1,name)
        refs=[f'the blue bird number {i} does not leave the quiet garden today' for i in range(n)]
        full=list(refs); candidate=list(full)
        changed=[] if pos==0 else ([0] if pos==1 else (list(range(0,n,5)) if pos==2 else list(range(8))))
        for i in changed: candidate[i]=f'a red tree number {i+1} will leave a noisy city tomorrow'
        metrics=[]
        for metric in [BLEU(),CHRF()]:
            fs=np.asarray(metric._extract_corpus_statistics(full,[refs]),dtype=np.int64)
            cs=np.asarray(metric._extract_corpus_statistics(candidate,[refs]),dtype=np.int64)
            point=metric._compute_score_from_stats(fs.sum(0).tolist()).score-metric._compute_score_from_stats(cs.sum(0).tolist()).score
            direct=metric.corpus_score(full,[refs]).score-metric.corpus_score(candidate,[refs]).score
            if abs(point-direct)>1e-10: raise AssertionError('Corpus direct parity')
            metrics.append((metric,fs,cs,point,direct))
        values=[[],[]]; rng=np.random.Generator(np.random.PCG64(lock['text_seed']+pos))
        for start in range(0,b,lock['chunk']):
            check(); count=min(lock['chunk'],b-start); budget.charge('bootstrap_draws',count,name)
            idx=rng.integers(0,n,(count,n))
            for j,(metric,fs,cs,_,_) in enumerate(metrics):
                for f,c in zip(fs[idx].sum(1),cs[idx].sum(1),strict=True):
                    values[j].append(metric._compute_score_from_stats(f.tolist()).score-metric._compute_score_from_stats(c.tolist()).score)
        result.append({'dataset':name,'n':n,'changed_rows':len(changed),'metrics':[
            {'metric':type(m).__name__,'point_loss':point,'direct_loss':direct,'interval':interval(v),'signature':str(m.get_signature())}
            for (m,_,_,point,direct),v in zip(metrics,values,strict=True)]})
    return result


def timing_bootstrap(lock,budget,check):
    budget.charge('datasets',1,'timing'); n=lock['timing_n']; b=lock['timing_draws']
    i=np.arange(n)[:,None]; p=np.arange(2)[None,:]; r=np.arange(3)[None,None,:]
    repeats=100+2*i+5*p+np.broadcast_to(r-1,(n,2,3)).mean(2)
    # Explicit repeat averaging; no extra independent units.
    raw=repeats[:,:,None]+np.broadcast_to(r-1,(n,2,3)); base=raw.mean(2)
    perturb=np.sin(i+3*p); perturb-=perturb.mean()
    effects=[0.,.025,.05,.10]; candidates=[base*(1-e)+perturb for e in effects]
    values=[[] for _ in effects]; rng=np.random.Generator(np.random.PCG64(lock['timing_seed']))
    for start in range(0,b,lock['chunk']):
        check(); count=min(lock['chunk'],b-start); budget.charge('bootstrap_draws',count,'timing')
        identities=rng.integers(0,n,(count,n)); processes=rng.integers(0,2,(count,2))
        for v,c in zip(values,candidates,strict=True): v.extend(crossed_savings(base,c,identities,processes).tolist())
    return [{'effect':e,'point_savings':float(1-c.mean()/base.mean()),'interval':interval(v),
             'process_points':(1-c.mean(0)/base.mean(0)).tolist(),
             'lower_uncertainty_le025':bool((1-c.mean()/base.mean())-interval(v)['lower']<=.025)}
            for e,c,v in zip(effects,candidates,values,strict=True)]
