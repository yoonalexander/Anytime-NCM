"""Prospective Q0 multiplicity audit; no empirical data or model access."""
from __future__ import annotations
import math
import numpy as np
from scipy.stats import binom
from anytime_ncm.q0_statistics import cp_upper, minimum_coverage, power_rows, mc_rate

CLAIM = .025
EXCLUSION = .025/40
OLD = .05/118
MARGINS = np.array([.5, 1., .02, .02])


def _probabilities(value, shape_suffix):
    x=np.asarray(value,dtype=float)
    if x.shape[-len(shape_suffix):] != shape_suffix:
        raise ValueError('Require complete locked endpoint/depth shape')
    if np.isinf(x).any() or np.any(np.isfinite(x)&((x<0)|(x>1))):
        raise ValueError('P-values must be [0,1] or unavailable NaN')
    return x


def joint_gate(quality_p, cost_p, exclusion_p, point_full, complete=True):
    """Conditional on valid marginal p-values; result is one joint claim only."""
    q=_probabilities(quality_p,(4,)); c=_probabilities(cost_p,(11,)); e=_probabilities(exclusion_p,(10,4))
    if q.shape[:-1]!=c.shape[:-1] or q.shape[:-1]!=e.shape[:-2]:
        raise ValueError('Leading dimensions must match')
    excluded=np.any(np.isfinite(e)&(e<=EXCLUSION),axis=-1)
    required=np.where(excluded,0.,c[...,:10])
    point=np.asarray(point_full,dtype=float)
    valid=(np.all(np.isfinite(q),axis=-1)&np.all(np.isfinite(c),axis=-1)
           &np.isfinite(point)&np.asarray(complete,dtype=bool))
    return valid & np.all(q<=CLAIM,axis=-1) & (c[...,10]<=CLAIM) & np.all(required<=CLAIM,axis=-1) & (point>=.05), excluded


def bounds_gate(candidate_upper, fixed_lower, savings_lower, point_full, complete=True):
    """Bounds must be computed at protocol levels; missing values are unavailable."""
    q=np.asarray(candidate_upper,dtype=float); f=np.asarray(fixed_lower,dtype=float); s=np.asarray(savings_lower,dtype=float)
    if q.shape!=(4,) or f.shape!=(10,4) or s.shape!=(11,):
        raise ValueError('All four endpoints and all eleven controls are required')
    if np.isinf(q).any() or np.isinf(f).any() or np.isinf(s).any():
        raise ValueError('Infinite bounds are not resolved confidence limits')
    qp=np.where(np.isfinite(q),np.where(q<=MARGINS,0.,1.),np.nan)
    ep=np.where(np.isfinite(f),np.where(f>MARGINS,0.,1.),np.nan)
    cp=np.where(np.isfinite(s),np.where(s>0,0.,1.),np.nan)
    passed,excluded=joint_gate(qp,cp,ep,point_full,complete)
    return {'global_go':bool(passed),'excluded_depths':(np.flatnonzero(excluded)+1).tolist(),
            'retained_depths':(np.flatnonzero(~excluded)+1).tolist()+[11]}


def analytical(lock):
    scan=np.arange(1,lock['analytical_max_n']+1)
    ns=list(dict.fromkeys(lock['cue_ns']+lock['analytic_extra_ns']))
    alphas={'historical59':OLD,'split_IUT_claim':CLAIM,'simultaneous_exclusion':EXCLUSION,'optimistic_single_endpoint':.05}
    result={'design_alphas':alphas,'zero_event_floors':{},'power':{},'grid':[],
            'population_sensitivity':[], 'zero_event_half_margin_floor':minimum_coverage(CLAIM,.01)}
    for label,a in alphas.items():
        result['zero_event_floors'][label]=minimum_coverage(a)
    for label,a in [('historical59',OLD),('split_IUT_claim',CLAIM)]:
        result['power'][label]={}
        for p in [.005,.01,.02,.03]:
            critical,powers=power_rows(scan,alpha=a,alternative=p)
            met=scan[powers>=lock['power_target']]
            result['power'][label][str(p)]={'first_n_power80':int(met[0]) if len(met) else None,
                'grid':[{'n':n,'max_adverse':int(critical[n-1]),'power':float(powers[n-1])} for n in ns]}
    for n in ns:
        k=np.arange(n+1)
        row={'n':n,'zero_adverse_upper_new':float(cp_upper(0,n,CLAIM)),
             'zero_adverse_upper_old':float(cp_upper(0,n,OLD)),'exact_checks':[]}
        for label,a in alphas.items():
            u=cp_upper(k,n,a)
            if np.max(np.abs(binom.cdf(k[:-1],n,u[:-1])-a))>1e-10:
                raise AssertionError('CP beta/CDF inversion mismatch')
            for p in lock['analytic_ps']:
                weights=binom.pmf(k,n,p)
                cover=float(weights[u>=p].sum()); passed=u<=.02
                if cover<1-a-1e-12:raise AssertionError('Exact one-sided coverage')
                pass_probability=float(weights[passed].sum())
                if p>=.02 and pass_probability>a+1e-12:raise AssertionError('Boundary/outside false acceptance')
                row['exact_checks'].append({'method':label,'p':p,'upper_coverage':cover,
                    'pass_probability':pass_probability,
                    'pass_and_half_margin_precision_probability':float(weights[passed & (u-k/n<=.01)].sum())})
        result['grid'].append(row)
    for total in lock['population_ns']:
        n=np.arange(total+1); _,powpositive=power_rows(np.maximum(n,1),alpha=CLAIM,alternative=.005)
        powpositive=np.where(n>0,powpositive,0.)
        for prevalence in lock['coverage_prevalences']:
            weights=binom.pmf(n,total,prevalence)
            result['population_sensitivity'].append({'total_groups':total,'assumed_prevalence':prevalence,
                'expected_covered':total*prevalence,'probability_reach_zero_event_floor':float(binom.sf(minimum_coverage(CLAIM)-1,total,prevalence)),
                'numeric_power_p005_mixture':float(weights@powpositive)})
    result['bootstrap_rank_precision']=[{'draws':b,'tail':a,'rank':int(binom.ppf(.001/55,b,a))}
                                        for b in [10000,100000] for a in [CLAIM,EXCLUSION]]
    result['consumed_numeric_coverage']={'verified_E2_covered':48,'other_consumed_groups':192,'union_upper_bound':240,'actual_union_coverage':'unknown'}
    result['theorem_bounds']={'any_false_exclusion':40*EXCLUSION,'false_global_go_or_any_false_exclusion':.05,
                              'single_fixed_false_go_bound':CLAIM+4*EXCLUSION}
    return result


def _sanity(count,n,expected,lock):
    a=lock['mc_sanity_family_allowance']/(2*len(lock['gate_cases']))
    low=int(binom.ppf(a,n,expected)); high=int(binom.isf(a,n,expected))
    if not low<=count<=high:raise AssertionError('Frozen MC sanity range violated')
    return {'expected_probability':expected,'allowed_count_range':[low,high],'passed':True}


def gate_trials(lock,budget,check):
    rng=np.random.Generator(np.random.PCG64(lock['gate_seed'])); report=[]
    for name in lock['gate_cases']:
        check(); t=lock['gate_trials_each']; budget.charge('trials',t,name)
        q=np.zeros((t,4)); c=np.zeros((t,11)); e=np.ones((t,10,4)); point=.1; complete=True
        u=rng.random(t); claim_false=False; expected_error=0.; expected_go=1.; expected_exclusion=0.; negative=None
        if name.startswith('candidate_null_'):
            j=['bleu','chrf','numeric','negation'].index(name.removeprefix('candidate_null_'))
            q[:,j]=u; claim_false=True; expected_go=expected_error=CLAIM
        elif name=='full_cost_null':
            c[:,10]=u; claim_false=True; expected_go=expected_error=CLAIM
        elif name in ['one_fixed_cost_null','ten_fixed_null_shared']:
            depths=[0] if name=='one_fixed_cost_null' else list(range(10))
            for d in depths:
                c[:,d]=u
                e[:,d,:]=(u[:,None]-(CLAIM+np.arange(4)*EXCLUSION))%1
            claim_false=True; expected_go=expected_error=CLAIM+4*EXCLUSION; expected_exclusion=4*EXCLUSION
        elif name=='all_requirements_true':pass
        elif name=='numeric_undefined':q[:,2]=np.nan; expected_go=0.
        elif name=='timing_incomplete':complete=False; expected_go=0.
        elif name=='missing_fixed_depth':c[:,9]=np.nan; expected_go=0.
        elif name=='point_savings_025':point=.025; expected_go=0.
        elif name=='exclusions_independent':
            e=rng.random((t,10,4)); expected_exclusion=expected_error=1-(1-EXCLUSION)**40
        elif name=='exclusions_shared':
            e[:]=u[:,None,None]; expected_exclusion=expected_error=EXCLUSION
        elif name=='exclusions_disjoint':
            e[:]=((u[:,None]-np.arange(40)*EXCLUSION)%1).reshape(t,10,4)
            expected_exclusion=expected_error=40*EXCLUSION
        elif name=='invalid_unadjusted_exclusion_OR':
            e[:,0,:]=(u[:,None]-np.arange(4)*.05)%1; c[:,0]=(u-4*.05)%1
            claim_false=True; expected_go=expected_error=CLAIM+4*EXCLUSION; expected_exclusion=4*EXCLUSION
            invalid=np.any(e[:,0,:]<=.05,axis=1)|(c[:,0]<=.05)
            negative={'invalid_rule':'unadjusted any-quality-or-cost route','rate':mc_rate(int(invalid.sum()),t),
                      'sanity':_sanity(int(invalid.sum()),t,.25,lock)}
        elif name=='invalid_four_candidate_selection':
            uniforms=rng.random((t,4)); q[:,2]=uniforms[:,0]; claim_false=True
            expected_go=expected_error=CLAIM
            invalid=np.any(uniforms<=CLAIM,axis=1)
            negative={'invalid_rule':'choose any of four independently tested candidate winners','rate':mc_rate(int(invalid.sum()),t),
                      'sanity':_sanity(int(invalid.sum()),t,1-(1-CLAIM)**4,lock)}
        else:raise ValueError('Unfrozen gate case')
        go,excluded=joint_gate(q,c,e,point,complete)
        wrong_exclusion=np.any(excluded,axis=1)
        false_go=go if claim_false else np.zeros(t,dtype=bool)
        # Every simulated exclusion tests a truly feasible control in these null cases.
        combined=wrong_exclusion|false_go
        row={'case':name,'global_claim_false':claim_false,'global_go':mc_rate(int(go.sum()),t),
             'false_exclusion':mc_rate(int(wrong_exclusion.sum()),t),
             'false_global_go_or_exclusion':mc_rate(int(combined.sum()),t),
             'checks':{'global_go':_sanity(int(go.sum()),t,expected_go,lock),
                       'false_exclusion':_sanity(int(wrong_exclusion.sum()),t,expected_exclusion,lock),
                       'combined_error':_sanity(int(combined.sum()),t,expected_error,lock)}}
        if negative is not None:row['negative_control']=negative
        report.append(row)
    return report


def cue_trials(lock,budget,check):
    rng=np.random.Generator(np.random.PCG64(lock['cue_seed'])); report=[]
    for n in lock['cue_ns']:
        for case in lock['cue_cases']:
            check(); t=lock['cue_trials_each']; budget.charge('trials',t,f'{case}:{n}')
            magnitude=1.; truth=0.; cluster=None
            if case=='zero':k=np.zeros(t,dtype=int)
            elif case in ['rare005','boundary02','outside03']:
                truth={'rare005':.005,'boundary02':.02,'outside03':.03}[case]; k=rng.binomial(n,truth,t)
            elif case=='fractional':
                k=rng.binomial(n,.1,t); magnitude=.1; truth=.01
            elif case=='cluster8':
                truth=.02; cluster=rng.binomial(n//8,truth,t); k=cluster*8
            else:raise ValueError('Unfrozen cue case')
            row={'n':n,'case':case,'true_mean_loss':truth,'methods':{}}
            for label,a in [('historical59',OLD),('split_IUT_claim',CLAIM)]:
                u=cp_upper(k,n,a)
                row['methods'][label]={'noninferiority_pass':mc_rate(int((u<=.02).sum()),t),
                    'upper_bound_coverage':mc_rate(int((u>=truth).sum()),t),
                    'pass_and_half_margin_precision':mc_rate(int(((u<=.02)&(u-magnitude*k/n<=.01)).sum()),t)}
            if cluster is not None:
                u=cp_upper(cluster,n//8,CLAIM)
                row['cluster_unit_noninferiority_pass']=mc_rate(int((u<=.02).sum()),t)
                row['cluster_unit_upper_coverage']=mc_rate(int((u>=truth).sum()),t)
                vals=np.arange(n//8+1)
                row['naive_exact_false_pass']=float(binom.pmf(vals,n//8,truth)[cp_upper(vals*8,n,CLAIM)<=.02].sum())
            report.append(row)
    return report
