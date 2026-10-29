"""Saved-cache validation and explicitly normalized environment version fields."""
import math
from anytime_ncm.controller_study import cache_row
from anytime_ncm.development_evaluation_data import key
from anytime_ncm.development_reporting import plain
from anytime_ncm.wmt_data import identity

def native_environment(environment):
    result=dict(environment)
    version=result.get('torch')
    if not isinstance(version,str):raise TypeError('Torch version must be a version string')
    result['torch']=str(version)
    return plain(result)

def validated_cache(entries,plan,public,private_lines,meter):
    allowed={key(e):e for e in entries}
    if len(allowed)!=1188 or len(plan)!=1193 or len(public)!=1193:raise ValueError('Incomplete saved evaluation allocation')
    rows={};counts=dict(inputs=0,generator_levels=0,decoder=0,encoder=0);seen=0
    for number,line in enumerate(private_lines):
        if number>=1193:raise ValueError('Extra saved native trace')
        meter.take('native_trace_bodies');p=plan[number];v=public[number];a=__import__('json').loads(line);seen+=1;k=key(a)
        if k not in allowed or any(v[f]!=x or a[f]!=x for f,x in p.items()) or any(a[f]!=allowed[k][f] for f in ('identity','component','role')):raise ValueError('Saved native allocation mismatch')
        if v['work']!=dict(inputs=1,generator_levels=11,decoder=12,encoder=0) or v['feature_work']!=dict(cheap_features=2,selected_logit_features=2,cue_features=2) or not v['native_final_parity'] or not a['native_final_parity']:raise ValueError('Saved native work/parity mismatch')
        if len(a['prefix_ids'])!=96 or identity(a['prefix_ids'])!=a['identity'] or len(a['codes'])!=313 or [o['level'] for o in a['levels']]!=list(range(1,12)) or any(len(o['ids'])!=64 for o in a['levels']):raise ValueError('Saved native shape/identity mismatch')
        if cache_row(a)!=v['hashes'] or a['features']!=v['features'] or [f['level'] for f in a['features']]!=[8,10] or any(len(f['values'])!=27 or not all(math.isfinite(x) for x in f['values']) for f in a['features']):raise ValueError('Saved native private/public binding failed')
        if not a['warmup']:
            if k in rows:raise ValueError('Duplicate saved native evaluation')
            rows[k]=a
        for f,x in v['work'].items():counts[f]+=x
    if seen!=1193 or set(rows)!=set(allowed) or sum(p['warmup'] for p in plan)!=5 or counts!=dict(inputs=1193,generator_levels=13123,decoder=14316,encoder=0):raise ValueError('Missing saved native work/population')
    return rows,counts
