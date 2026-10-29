"""Fixed family1ablations and one bounded nonlinear family; no implicit fitting."""
import numpy as np
from anytime_ncm.signal_discrimination import fit_ridge,predict as ridge_predict
COLUMNS=dict(cheap=tuple(range(19)),logit=tuple(range(22)),cue=tuple(range(19))+tuple(range(22,27)),full=tuple(range(27)))

def fit_tree(x,y,meter):
    x=np.asarray(x,dtype=float);y=np.asarray(y,dtype=float)
    if x.ndim!=2 or y.shape!=(len(x),) or not np.isfinite(x).all() or not np.isin(y,[0.,1.]).all():raise ValueError('Invalid tree fit arrays')
    counts=[int((y==v).sum()) for v in (0,1)]
    if min(counts)<20:return dict(status='insufficient_classes',class_counts=counts,method='tree')
    meter.take('fits')
    def grow(a,b,depth):
        n=len(b);p=float(b.mean());node=dict(n=n,positive=int(b.sum()),probability=p)
        if depth>=3 or n<64 or p in (0.,1.):return node
        base=2*p*(1-p);best=None;best_gain=0.
        for j in range(a.shape[1]):
            thresholds=sorted(set(np.quantile(a[:,j],np.arange(.1,1.,.1)).tolist()))
            for threshold in thresholds:
                meter.take('tree_thresholds');left=a[:,j]<=threshold;nl=int(left.sum());nr=n-nl
                if min(nl,nr)<32:continue
                pl=float(b[left].mean());pr=float(b[~left].mean());gain=base-(nl*2*pl*(1-pl)+nr*2*pr*(1-pr))/n
                if gain>best_gain+1e-12:best=(j,float(threshold),left);best_gain=gain
        if best is None:return node
        j,t,left=best;node.update(feature=j,threshold=t,gain=float(best_gain),left=grow(a[left],b[left],depth+1),right=grow(a[~left],b[~left],depth+1));return node
    return dict(status='fitted',method='tree',n_features=x.shape[1],class_counts=counts,max_depth=3,min_leaf=32,quantile_grid=[i/10 for i in range(1,10)],root=grow(x,y,0))

def fit_model(x,y,method,meter):
    if method=='ridge':return dict(fit_ridge(x,y,meter),method='ridge')
    if method=='tree':return fit_tree(x,y,meter)
    raise ValueError('Unknown frozen model family')

def predict_model(model,x):
    if model['method']=='ridge':return ridge_predict(model,x)
    if model['method']!='tree' or model['status']!='fitted':raise ValueError('Unsupported frozen model')
    x=np.asarray(x,dtype=float)
    if x.ndim!=2 or x.shape[1]!=model['n_features'] or not np.isfinite(x).all():raise ValueError('Invalid tree prediction array')
    out=[]
    for row in x:
        node=model['root'];depth=0
        while 'feature' in node:
            j=node['feature']
            if type(j)is not int or not 0<=j<len(row) or depth>=3 or not np.isfinite(node['threshold']):raise ValueError('Invalid frozen tree path')
            node=node['left'] if row[j]<=node['threshold'] else node['right'];depth+=1
        p=node['probability']
        if not 0<=p<=1 or not np.isfinite(p):raise ValueError('Invalid frozen leaf score')
        out.append(p)
    return np.asarray(out,dtype=float)

def candidate_specs(models):
    result=[dict(name='full',kind='full')]
    for method,groups in [('ridge',('cheap','logit','cue','full')),('tree',('cheap','full'))]:
        for group in groups:
            for levels in ([8],[8,10]):
                if any(models[method][str(d)][group]['status']!='fitted' for d in levels):continue
                for guard in (False,True):
                    for threshold in (i/10 for i in range(10)):
                        result.append(dict(name=method+':'+group+':'+','.join(map(str,levels))+':guard'+str(int(guard))+':'+str(threshold),kind='development_joint',method=method,group=group,columns=list(COLUMNS[group]),decision_levels=levels,cue_guard=guard,threshold=threshold,models={str(d):models[method][str(d)][group] for d in levels}))
    return result

def decide(spec,level,vector):
    if level not in spec['decision_levels'] or tuple(spec['columns'])!=COLUMNS[spec['group']]:raise ValueError('Unscheduled/malformed decision')
    x=np.asarray(vector,dtype=float)
    if x.shape!=(27,) or not np.isfinite(x).all():raise ValueError('Require finite current causal vector')
    if spec['cue_guard'] and (x[25]!=1 or x[26]!=1):return False
    score=float(predict_model(spec['models'][str(level)],x[list(spec['columns'])][None,:])[0]);return score<=spec['threshold']
