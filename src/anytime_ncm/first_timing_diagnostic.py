"""First full-relative timing diagnostic after preserved phase09 technical failure."""
import random
import numpy as np
from anytime_ncm.evidence_preflight import order_interval
METHODS=('controller','fixed:11')
def plans(entries,predictions,session):
    if session not in (0,1) or len(entries)!=1188 or len(predictions)!=1188:raise ValueError('Fixed development diagnostic allocation')
    rng=random.Random(20261029+session);out=[]
    def add(i,method,warmup):
        d,v=predictions[i] if method=='controller' else (11,[11]);e=entries[i]
        if (d,v) not in ((8,[8]),(11,[8,11]),(11,[11])):raise ValueError('Invalid selected schedule')
        out.append(dict(request_id=len(out),session=session,position=i,year=e['year'],index=e['index'],identity=e['identity'],method=method,depth=d,visits=v,warmup=warmup,repeat=-1 if warmup else 0))
    methods=list(METHODS);rng.shuffle(methods)
    for j,m in enumerate(methods):
        for k in range(5):add((5*j+k)%16,m,True)
    positions=list(range(1188));rng.shuffle(positions)
    for i in positions:
        methods=list(METHODS);rng.shuffle(methods)
        for m in methods:add(i,m,False)
    return out

def paired_draws(cells,groups,picks):
    a=np.asarray(cells,dtype=float);g=np.asarray(groups);p=np.asarray(picks,dtype=int);unique=sorted(set(g.tolist()))
    if a.ndim!=2 or a.shape!=(len(g),2) or not np.isfinite(a).all() or np.any(a<=0) or len(unique)<2 or p.ndim!=2 or p.shape[1]!=len(unique) or np.any(p<0) or np.any(p>=len(unique)):raise ValueError('Invalid paired timing components')
    totals=np.asarray([a[g==v].sum(0) for v in unique]);s=totals[p].sum(1);return 1-s[:,0]/s[:,1]

def analyze(records,entries,quality):
    n=len(entries);cells=np.full((2,n,2),np.nan)
    for r in records:
        if r['warmup']:continue
        ix=(r['session'],r['position'],METHODS.index(r['method']))
        if not np.isnan(cells[ix]) or not r['parity'] or not np.isfinite(r['wall_ms']) or r['wall_ms']<=0:raise ValueError('Invalid/duplicate timing cell')
        cells[ix]=r['wall_ms']
    if not np.isfinite(cells).all():raise ValueError('Missing first diagnostic timing cell')
    groups=[e['component'] for e in entries];g=len(set(groups))
    if g!=60:raise ValueError('Fixed60component allocation')
    picks=np.random.default_rng(20261029).integers(g,size=(20000,g));draws=paired_draws(cells.mean(0),groups,picks);interval=order_interval(draws,.05/22,11)
    summary={m:dict(mean_ms=float(cells[:,:,i].mean()),median_ms=float(np.median(cells[:,:,i])),p95_ms=float(np.percentile(cells[:,:,i],95)),session_mean_ms=cells[:,:,i].mean(1).tolist()) for i,m in enumerate(METHODS)}
    saving=1-summary['controller']['mean_ms']/summary['fixed:11']['mean_ms'];sessions=[1-a/b for a,b in zip(summary['controller']['session_mean_ms'],summary['fixed:11']['session_mean_ms'])];timing_pass=bool(saving>=.05 and all(v>0 for v in sessions) and interval['lower'] is not None and interval['lower']>0)
    return dict(status='negative_controller_quality_point_screen' if not quality['controller']['point_pass'] else 'development_timing_diagnostic_only',methods=summary,mean_saving=saving,session_savings=sessions,conditional_nominal_interval=interval,timing_screen_passed=timing_pass,quality_point_pass=quality['controller']['point_pass'],inputs=n,components=g,timed_repeats_per_input_method_session=1,sessions=2,bootstrap_draws=20000,retained_nominal_tail_alpha=.05/22,retained_mc_family=11,observed_contrasts=1,conditional_on_observed_sessions=True,unmeasured_fixed_depths=list(range(1,11)),statistically_excluded_fixed_depths=[],original_phase09_matrix_complete=False,Q0_passed=False,independent_quality_guarantee=False,original_success_contract_established=False,post_evaluation_retuning=False)
