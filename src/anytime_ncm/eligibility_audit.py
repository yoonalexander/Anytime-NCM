"""Source/reference metadata and synthetic cue bounds only; no model readers."""
from collections import Counter
import hashlib,html,itertools,json,math,re
import numpy as np
from scipy.special import xlogy,xlog1py
from scipy.stats import beta,binom
from anytime_ncm.wmt_data import identity
from anytime_ncm.wmt_policy import NUMBER

MARGIN=.02
ALPHA=.025

def need(v,message):
    if not v:raise ValueError(message)
def hash_text(s):return hashlib.sha256(s.encode('utf-8')).hexdigest()
def normalized(s):return re.sub(r'\s+',' ',html.unescape(s).strip())

def kl(x,p):
    x=np.asarray(x,dtype=float);p=np.asarray(p,dtype=float)
    with np.errstate(divide='ignore',invalid='ignore'):
        return xlogy(x,x)-xlogy(x,p)+xlog1py(1-x,-x)-xlog1py(1-x,-p)

def cue_upper(total_positive,counts,alpha=ALPHA):
    """Conservative KL inversion for fixed metadata weights and independent clusters."""
    c=np.asarray(counts,dtype=float);s=np.asarray(total_positive,dtype=float)
    need(c.ndim==1 and np.isfinite(c).all() and (c>=0).all() and np.all(c==np.floor(c)),'Invalid denominator counts')
    need(0<alpha<1 and np.isfinite(s).all() and (s>=0).all() and (s<=1+1e-12).all(),'Invalid statistic/alpha')
    c=c[c>0]
    if not len(c):return None
    j=len(c);b=float(c.max()/c.sum());h=j*b;x=np.clip(s/h,0,1);lo=x.copy();hi=np.full_like(x,1/h)
    threshold=math.log(1/alpha)
    # Upper bracket, not midpoint, is returned; no falsely low numerical root.
    for _ in range(72):
        mid=(lo+hi)/2;below=j*kl(x,mid)<threshold
        lo=np.where(below,mid,lo);hi=np.where(below,hi,mid)
    u=np.minimum(1,hi*h+1e-12)
    return u

def zero_upper(counts,alpha=ALPHA):
    c=np.asarray(counts,dtype=float);c=c[c>0]
    return None if not len(c) else min(1.,len(c)*float(c.max()/c.sum())*(-math.expm1(math.log(alpha)/len(c))))

def eb_ratio(positive_by_component,counts,M=128,alpha=ALPHA):
    a=np.asarray(positive_by_component,dtype=float);c=np.asarray(counts,dtype=float)
    need(a.shape[-1]==len(c) and (c>=0).all() and (c<=M).all() and (a>=0).all() and (a<=c).all(),'Invalid EB cluster totals')
    j=len(c)
    if j<2:return None
    log=math.log(4/alpha);y=a/M;v=c/M
    uy=np.minimum(1,y.mean(axis=-1)+np.sqrt(2*y.var(axis=-1,ddof=1)*log/j)+7*log/(3*(j-1)))
    lv=max(0,float(v.mean()-math.sqrt(2*v.var(ddof=1)*log/j)-7*log/(3*(j-1))))
    return None if lv<=0 else np.minimum(1,uy/lv)

def rate(events,n):
    k=int(events)
    return dict(events=k,trials=n,rate=k/n,ci99=[0. if not k else float(beta.ppf(.005,k,n-k+1)),1. if k==n else float(beta.isf(.005,k+1,n-k))])

def method_scenarios(charge):
    rng=np.random.Generator(np.random.PCG64(2026102601));results=[];validation=True
    # 3 sizes x2 frozen denominator profiles x4 risks x2000 =48000 datasets.
    for j in (128,512,1024):
        for shape in ('balanced8','skewed64'):
            sizes=np.full(j,8) if shape=='balanced8' else np.resize(np.array([1]*7+[64]),j)
            covered=np.full(j,2) if shape=='balanced8' else np.resize(np.array([1]*7+[16]),j)
            for p in (0.,.005,.02,.03):
                charge('synthetic_datasets',2000)
                z=rng.binomial(1,p,size=(2000,j)) # arbitrary dependence inside a component: all its inputs share z.
                endpoints={};joint=np.ones(2000,dtype=bool);joint_precision=np.ones(2000,dtype=bool)
                for name,counts in [('numeric',covered),('negation',sizes)]:
                    point=z@counts/counts.sum();upper=cue_upper(point,counts)
                    passed=upper<=MARGIN;precise=upper-point<=.01
                    noncoverage=upper<p-1e-12
                    if p>=MARGIN:
                        limit=int(binom.ppf(1-.001/24,2000,.025));validation=validation and int(passed.sum())<=limit
                    endpoints[name]=dict(point_mean=float(point.mean()),upper_mean=float(upper.mean()),NI=rate(passed.sum(),2000),NI_and_precision=rate((passed&precise).sum(),2000),noncoverage=rate(noncoverage.sum(),2000),max_cluster_weight=float(counts.max()/counts.sum()),zero_adverse_upper=zero_upper(counts))
                    joint&=passed;joint_precision&=passed&precise
                eb=eb_ratio(z*covered,covered)
                results.append(dict(J=j,shape=shape,risk=p,inputs=int(sizes.sum()),numeric_covered=int(covered.sum()),endpoints=endpoints,joint_two_cue_NI=rate(joint.sum(),2000),joint_two_cue_NI_and_precision=rate(joint_precision.sum(),2000),reference_EB_numeric_NI_events=0 if eb is None else int((eb<=MARGIN).sum()),reference_EB_unavailable=eb is None))
    # Exact two-point dependence counterexample, not more Monte Carlo datasets.
    u0=zero_upper([2]*512)
    negative=dict(distribution='all512 components share one Bernoulli(.02) adverse flag',zero_upper=u0,exact_false_NI_probability=.98 if u0<=.02 else 0.,valid_independent_cluster_model=False,adopted=False)
    return dict(scenarios=results,datasets=48000,seed=2026102601,null_sanity_checks_passed=bool(validation),dependence_negative_control=negative,whole_study_power_established=False,bootstrap_draws=0)

def parse_sgm(data,kind,charge,cap=20000):
    need(kind in ('source','reference'),'Invalid SGML role')
    text=data.decode('utf-8');doc=None;rows=[];seen=set();header=False
    for line in text.splitlines():
        line=line.strip()
        if re.match(r'<(?:srcset|refset)\b',line,re.I):
            attrs=dict(re.findall(r'([A-Za-z_]+)\s*=\s*["\x27]([^"\x27]*)["\x27]',line));attrs={k.lower():v for k,v in attrs.items()}
            need(attrs.get('srclang') in ('de','deu','ger'),'Wrong source language')
            if kind=='reference':need(attrs.get('trglang') in ('en','eng'),'Wrong reference language')
            header=True
        elif re.match(r'<doc\b',line,re.I):
            need(doc is None,'Nested/unclosed document')
            attrs=dict(re.findall(r'([A-Za-z_]+)\s*=\s*["\x27]([^"\x27]*)["\x27]',line));attrs={k.lower():v for k,v in attrs.items()}
            need(bool(attrs.get('docid')),'Missing document ID');doc=attrs
        elif re.match(r'</doc\s*>',line,re.I):need(doc is not None,'Unexpected document close');doc=None
        elif re.match(r'<seg\b',line,re.I):
            need(header and doc is not None,'Segment outside document/header')
            m=re.fullmatch(r'<seg\b([^>]*)>(.*)</seg>\s*',line,re.I);need(m is not None,'Invalid multiline/malformed segment')
            seg=re.search(r'\bid\s*=\s*["\x27]([^"\x27]+)["\x27]',m[1],re.I);need(seg is not None,'Missing segment ID')
            key=(doc['docid'],seg[1]);need(key not in seen,'Duplicate segment');seen.add(key)
            need(len(rows)<cap,'Member row cap');charge(kind+'_materializations',1)
            rows.append(dict(doc=doc['docid'],seg=seg[1],origlang=doc.get('origlang'),text=m[2]) if kind=='source' else dict(doc=doc['docid'],seg=seg[1],covered=bool(NUMBER.search(m[2]))))
    need(header and doc is None and len(rows)>0,'Incomplete/empty SGML')
    return rows

class Union:
    def __init__(self,n):self.p=list(range(n))
    def find(self,i):
        while self.p[i]!=i:self.p[i]=self.p[self.p[i]];i=self.p[i]
        return i
    def merge(self,a,b):
        a=self.find(a);b=self.find(b)
        if a!=b:self.p[max(a,b)]=min(a,b)

def inventory(rows,historical):
    """Only hashed source metadata and cue presence; never accepts model outcomes."""
    need(len({(r['year'],r['index']) for r in rows})==len(rows),'Duplicate year/index')
    docs=sorted({(r['year'],r['doc_hash']) for r in rows});positions={d:i for i,d in enumerate(docs)}
    du=Union(len(docs));ru=Union(len(rows));lookup={};stories={}
    for i,r in enumerate(rows):
        d=positions[r['year'],r['doc_hash']]
        for kind in ('raw_hash','normalized_hash','prefix_hash'):
            key=(kind,r[kind])
            if key in lookup:
                old=lookup[key];ru.merge(i,old);du.merge(d,positions[rows[old]['year'],rows[old]['doc_hash']])
            else:lookup[key]=i
        if r.get('story_hash'):
            if r['story_hash'] in stories:du.merge(d,stories[r['story_hash']])
            else:stories[r['story_hash']]=d
    aliases={}
    for i,r in enumerate(rows):aliases.setdefault(ru.find(i),[]).append(i)
    canonical={root:min(ix,key=lambda i:(rows[i]['year'],rows[i]['index'])) for root,ix in aliases.items()}
    components={}
    for i,r in enumerate(rows):components.setdefault(du.find(positions[r['year'],r['doc_hash']]),[]).append(i)
    eligible=[];excluded=Counter();manifest=[];private=[];aliases_removed=0
    for ix in components.values():
        ds=sorted({(rows[i]['year'],rows[i]['doc_hash']) for i in ix})
        component=hash_text(json.dumps(ds,separators=(',',':')))
        reps=sorted({canonical[ru.find(i)] for i in ix},key=lambda i:(rows[i]['year'],rows[i]['index']))
        aliases_removed+=len(ix)-len(reps)
        overlap=any(any(rows[i][kind] in historical[kind] for kind in ('raw_hash','normalized_hash','prefix_hash','doc_hash')) for i in ix)
        reason='historical_overlap' if overlap else 'component_over128' if len(reps)>128 else None
        if reason:excluded[reason]+=len(reps)
        c=dict(component=component,hash_order=hash_text('2026102507|'+component),indices=reps,input_count=len(reps),covered_count=sum(rows[i]['covered'] for i in reps),document_count=len(ds),reason=reason)
        private.append(c)
        if reason is None:eligible.append(c)
    eligible.sort(key=lambda c:(c['hash_order'],c['component']));cut=math.floor(.4*len(eligible))
    profiles={};roles={}
    for role,cs in [('development',eligible[:cut]),('confirmation',eligible[cut:])]:
        n=[c['input_count'] for c in cs];m=[c['covered_count'] for c in cs]
        total=sum(n);covered=sum(m)
        roles[role]=dict(components=len(cs),inputs=total,numeric_covered=covered,covered_components=sum(x>0 for x in m),max_input_component_fraction=max(n,default=0)/total if total else None,max_numeric_component_fraction=max(m,default=0)/covered if covered else None,input_n_eff=total**2/sum(x*x for x in n) if total else None,numeric_n_eff=covered**2/sum(x*x for x in m) if covered else None,numeric_zero_adverse_KL_upper=zero_upper(m),negation_zero_adverse_KL_upper=zero_upper(n),year_inputs=dict(Counter(str(rows[i]['year']) for c in cs for i in c['indices'])))
        profiles[role]=dict(inputs=n,numeric=m)
        for c in cs:
            for i in c['indices']:
                r=rows[i];manifest.append(dict(year=r['year'],index=r['index'],identity=r['prefix_hash'],component=c['component'],role=role))
    d=roles['development'];c=roles['confirmation']
    screening=bool(d['components']>=200 and d['numeric_covered']>=300 and c['components']>=400 and c['numeric_covered']>=1000 and c['covered_components']>=200 and c['max_input_component_fraction']<=.01 and c['max_numeric_component_fraction']<=.02)
    return dict(candidate_rows=len(rows),candidate_documents=len(docs),eligible_components=len(eligible),aliases_removed=aliases_removed,excluded_canonical_inputs=dict(excluded),roles=roles,operational_screen_passed=screening,statistical_feasibility_passed=False,story_independence_proven=False,checkpoint_training_overlap='unknown'),manifest,dict(components=private,profiles=profiles)
