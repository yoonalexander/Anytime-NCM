"""Exact zero-event extremal review; no corpus/model readers or simulations."""
from collections import Counter
from fractions import Fraction as F
from itertools import product
import json,math

def need(v,message):
    if not v:raise ValueError(message)
def positive_counts(counts):
    need(isinstance(counts,(list,tuple)) and all(type(c) is int and c>=0 for c in counts),'Invalid counts')
    return sorted((c for c in counts if c),reverse=True)
def rational(x):
    need(isinstance(x,(F,int,str)) and not isinstance(x,bool),'Require exact rational input')
    return F(x)
def record(x):
    x=rational(x);return dict(numerator=str(x.numerator),denominator=str(x.denominator),decimal=float(x))

def zero_extremum(counts,delta):
    """Sharp sup P(all zeros), with independent Y_j in[0,c_j/sum(c)]."""
    c=positive_counts(counts);d=rational(delta);need(0<=d<=1,'Delta outside unit interval')
    if not c:return None
    C=sum(c)
    if d==0:return dict(probability=F(1),tau=F(c[0]),active_counts=[],probabilities=[])
    if d==1:return dict(probability=F(0),tau=F(0),active_counts=c,probabilities=[F(1)]*len(c))
    total=0
    for k,x in enumerate(c,1):
        total+=x;tau=(F(total)-d*C)/k;next_c=c[k] if k<len(c) else 0
        if 0<tau<x and tau>=next_c:
            active=c[:k];ps=[1-tau/a for a in active]
            need(sum((F(a,C)*p for a,p in zip(active,ps)),F(0))==d,'Exact mean constraint')
            probability=math.prod((1-p for p in ps),start=F(1))
            return dict(probability=probability,tau=tau,active_counts=active,probabilities=ps)
    raise AssertionError('No exact active set')

def sharp_zero_bracket(counts,alpha='1/40',steps=64,charge=lambda *a:None):
    a=rational(alpha);need(0<a<1 and type(steps)is int and 1<=steps<=64,'Invalid root allocation')
    if not positive_counts(counts):return None
    lo=F(0);hi=F(1)
    for _ in range(steps):
        charge('waterfill_evaluations',1);mid=(lo+hi)/2
        if zero_extremum(counts,mid)['probability']>a:lo=mid
        else:hi=mid
    need(hi-lo==F(1,2**steps),'Root bracket width')
    return lo,hi

def equal_top_witness(counts,delta,charge=lambda *a:None):
    c=positive_counts(counts);d=rational(delta);need(0<d<1,'Invalid witness delta')
    if not c:return None
    C=sum(c);T=0;best=None
    for k,x in enumerate(c,1):
        charge('top_k_evaluations',1);T+=x
        if T<d*C:continue
        p=d*C/T;q=(1-p)**k
        if best is None or q>best['probability']:best=dict(k=k,top_count_total=T,event_probability=p,probability=q,active_counts=c[:k])
    return best

def extract_profiles(raw,max_bytes=16<<20):
    """Decode only final top-level profiles member; preceding private rows byte-skipped."""
    need(isinstance(raw,bytes) and len(raw)<=max_bytes,'Profile file size/type cap')
    marker=b'\n  "profiles": '
    need(raw.count(marker)==1,'Ambiguous/missing profiles marker')
    i=raw.index(marker)
    selected=json.loads(b'{'+raw[i+3:])
    need(list(selected)==['profiles'],'Unexpected trailing root metadata')
    profiles=selected['profiles'];need(set(profiles)=={'development','confirmation'},'Unexpected roles')
    for p in profiles.values():
        need(set(p)=={'inputs','numeric'} and len(p['inputs'])==len(p['numeric']),'Unexpected profile fields')
        positive_counts(p['inputs']);positive_counts(p['numeric'])
        need(all(n>0 and 0<=m<=n for n,m in zip(p['inputs'],p['numeric'])),'Invalid paired profile counts')
    return profiles

def deterministic_grids(charge):
    result=[];thresholds=[F(1,100),F(1,50),F(201,10000)]
    for counts in ([1,3],[1,2,5],[1,4,4,9]):
        extrema={}
        for d in thresholds:
            charge('waterfill_evaluations',1);extrema[d]=zero_extremum(counts,d)['probability']
        checked=0
        for digits in product(range(11),repeat=len(counts)):
            charge('grid_points',1);ps=[F(x,10) for x in digits]
            mean=sum((F(c,sum(counts))*p for c,p in zip(counts,ps)),F(0));q=math.prod((1-p for p in ps),start=F(1))
            for d in thresholds:
                charge('grid_comparisons',1)
                if mean>=d:need(q<=extrema[d],'Grid probability exceeds exact optimum')
            checked+=1
        result.append(dict(counts=list(counts),points=checked,thresholds=3,passed=True))
    return result

def target_counterexamples():
    result=[]
    for probs,counts,means in [([F(1,2)]*2,[1,9],[F(1),F(0)]),([F(99,100),F(1,100)],[1,100],[F(0),F(1)])]:
        expected_realized_ratio=sum((p*d for p,d in zip(probs,means)),F(0))
        ratio_expected=sum((p*c*d for p,c,d in zip(probs,counts,means)),F(0))/sum((p*c for p,c in zip(probs,counts)),F(0))
        need(expected_realized_ratio!=ratio_expected,'Counterexample accidentally equal')
        result.append(dict(probabilities=[record(p) for p in probs],counts=counts,per_input_losses=[record(d) for d in means],expected_realized_ratio=record(expected_realized_ratio),ratio_of_expected_totals=record(ratio_expected)))
    return result

def review_profile(counts,charge):
    c=positive_counts(counts);need(bool(c),'Unavailable real denominator')
    J=len(c);C=sum(c);b=F(max(c),C);cases=[]
    for d in [F(1,100),F(1,50),F(201,10000)]:
        charge('waterfill_evaluations',1);z=zero_extremum(c,d);simple=equal_top_witness(c,d,charge)
        need(simple['probability']<=z['probability'],'Simple witness larger than sharp extremum')
        cases.append(dict(delta=record(d),sharp_all_zero_probability=record(z['probability']),active_counts=z['active_counts'],active_event_probabilities=[record(p) for p in z['probabilities']],tau_count_units=record(z['tau']),exceeds_primary_alpha=z['probability']>F(1,40),randomized_zero_rejection_upper=record(min(F(1),F(1,40)/z['probability'])) if z['probability'] else record(1),simple_top_k_witness=dict(k=simple['k'],count_total=simple['top_count_total'],event_probability=record(simple['event_probability']),all_zero_probability=record(simple['probability']),active_counts=simple['active_counts'])))
    roots={}
    for a in [F(1,40),F(1,20)]:
        lo,hi=sharp_zero_bracket(c,a,64,charge)
        roots[str(a)]=dict(lower=record(lo),upper=record(hi),width=record(hi-lo),steps=64)
    old=J*float(b)*(-math.expm1(math.log(.025)/J))
    need(float(F(roots['1/40']['upper']['numerator'])/F(roots['1/40']['upper']['denominator']))<=old+1e-12,'Full weights failed to tighten largest-cap reference')
    return dict(J=J,total_count=C,max_count=max(c),unlabelled_count_histogram={str(k):v for k,v in sorted(Counter(c).items())},largest_cap_zero_upper=old,sharp_zero_brackets=roots,cases=cases,not_general_positive_loss_CI=True)
