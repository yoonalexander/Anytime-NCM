"""Outcome-free allocation of previously audited DEVELOPMENT components only."""
from collections import Counter,defaultdict
import hashlib,math,re
SEED='campaign20261029-development-v1'
ROLES=('development_fit','development_calibration','development_evaluation')

def allocate(records):
    identities=set();keys=set();old_roles=defaultdict(set);development=defaultdict(list);confirmation=set()
    for r in records:
        if set(r)!={'year','index','identity','component','role'} or type(r['year']) is not int or r['year'] not in range(2015,2021) or type(r['index']) is not int or r['index']<0 or r['role'] not in ('development','confirmation') or any(re.fullmatch('[a-f0-9]{64}',r[k]) is None for k in ('identity','component')):raise ValueError('Invalid source-only manifest record')
        key=(r['year'],r['index'])
        if key in keys or r['identity'] in identities:raise ValueError('Duplicate canonical key/identity')
        keys.add(key);identities.add(r['identity']);old_roles[r['component']].add(r['role'])
        if r['role']=='development':development[r['component']].append(r)
        else:confirmation.add(r['component'])
    if any(len(v)!=1 for v in old_roles.values()) or confirmation&set(development):raise ValueError('Prior component crossed development/confirmation')
    components=sorted(development,key=lambda c:(hashlib.sha256((SEED+'|'+c).encode()).hexdigest(),c));g=len(components)
    cuts=(math.floor(.6*g),math.floor(.6*g)+math.floor(.2*g));parts={role:[] for role in ROLES}
    for i,c in enumerate(components):
        if len(development[c])>128:raise ValueError('Prior component cap violated')
        role=ROLES[0] if i<cuts[0] else ROLES[1] if i<cuts[1] else ROLES[2]
        parts[role].extend(dict(r,role=role,prior_role='development') for r in sorted(development[c],key=lambda r:(r['year'],r['index'])))
    return dict(seed=SEED,allocation='whole audited development components; hash order; floor60%fit/floor20%calibration/remainder evaluation',parts=parts,confirmation_reallocated=False)

def summarize(allocation):
    summary={}
    for role,rows in allocation['parts'].items():
        sizes=Counter(r['component'] for r in rows)
        summary[role]=dict(inputs=len(rows),components=len(sizes),largest_component=max(sizes.values(),default=0),year_inputs=dict(sorted(Counter(str(r['year']) for r in rows).items())),numeric_coverage='not inspected by role',negation_change_support='unknown until authorized model collection')
    return summary

def feasible(summary,charged,ceilings):
    f,c,t=(summary[k] for k in ROLES)
    metadata_ready=(f['inputs']>=2000 and c['inputs']>=500 and t['inputs']>=500 and f['components']>=120 and c['components']>=40 and t['components']>=40)
    # Prospective capacity envelope, not a release or actual work. Includes later evaluation cache and warmups/toy-attempt allowance.
    requests=f['inputs']+c['inputs']+5+t['inputs']+5+2*(2*t['inputs']*12+60)+192
    planned=dict(model_requests=requests,model_orchestration_seconds=21600,cpu_seconds=10000,real_fits=16,controller_families=1,download_bytes=0,artifact_bytes=536870912,confirmation_evaluations=0,paid_dollars=0)
    resource_ready=all(charged[k]+v<=ceilings[k] for k,v in planned.items())
    return dict(status='development_extension_metadata_supported' if metadata_ready and resource_ready else 'development_extension_not_supported',metadata_ready=metadata_ready,resource_capacity_ready=resource_ready,planned_future_envelope=planned,actual_new_model_requests=0,rare_adverse_supervision_established=False,new_quality_evidence=False,Q0_passed=False,confirmation_ready=False,next_branch='prospectively_lock_fit_calibration_collection' if metadata_ready and resource_ready else 'bounded_family2_existing_data_or_closeout')
