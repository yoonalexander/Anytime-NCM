"""Exact schema adapter for the committed cheap19/ridge/8-only policy."""
from copy import deepcopy
import numpy as np

def runtime_spec(spec):
    if (spec.get('kind')!='development_joint' or spec.get('method')!='ridge' or spec.get('group')!='cheap' or spec.get('columns')!=list(range(19)) or spec.get('decision_levels')!=[8] or spec.get('cue_guard') is not False or spec.get('threshold')!=.6 or spec.get('name')!='ridge:cheap:8:guard0:0.6' or set(spec.get('models',{}))!={'8'}):raise ValueError('Only the committed selected policy schema is supported')
    m=spec['models']['8'];mean=np.asarray(m['mean']);scale=np.asarray(m['scale']);coef=np.asarray(m['coef'])
    if m.get('status')!='fitted' or m.get('method')!='ridge' or mean.shape!=(19,) or scale.shape!=(19,) or coef.shape!=(20,) or np.any(scale<=0) or not all(np.isfinite(v).all() for v in (mean,scale,coef)):raise ValueError('Invalid frozen selected coefficients')
    return dict(name=spec['name'],kind='joint_ridge',group='cheap',decision_levels=[8],cue_guard=False,threshold=.6,models=deepcopy(spec['models']))
