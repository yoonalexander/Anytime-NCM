"""Append-only resource accounting for the user-authorized 2026-10-29 campaign."""
import json
import math
from pathlib import Path
from anytime_ncm.evidence_preflight import sha,write_new

UNITS=('model_requests','model_orchestration_seconds','cpu_seconds','real_fits','controller_families','download_bytes','artifact_bytes','confirmation_evaluations','paid_dollars')

def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def usage_zero():return dict.fromkeys(UNITS,0)
def campaign_root(root):return Path(root)/'results/quality_tolerant/campaign_20261029'

def verify_campaign(root,additional=None):
    root=Path(root);base=campaign_root(root);lock=read(root/'docs/studies/quality-tolerant/campaign-20261029-lock.json');total=usage_zero();phases=[]
    for path in sorted((base/'accounting').glob('phase-*.json')):
        receipt=read(path);evidence=base/receipt['evidence_path']
        if sha(evidence)!=receipt['evidence_sha256']:raise ValueError('Campaign evidence changed: '+str(path))
        actual=read(evidence)
        if actual['campaign_usage']!=receipt['usage']:raise ValueError('Campaign usage not bound to execution')
        for k in UNITS:
            value=receipt['usage'][k]
            if not isinstance(value,(int,float)) or not math.isfinite(value) or value<0:raise ValueError('Invalid campaign usage')
            total[k]+=value
        phases.append(receipt['phase'])
    if len(set(phases))!=len(phases):raise ValueError('Duplicate campaign phase')
    if additional is not None:
        for k in UNITS:
            v=additional[k]
            if not isinstance(v,(int,float)) or not math.isfinite(v) or v<0:raise ValueError('Invalid proposed campaign charge')
            total[k]+=v
    if any(total[k]>lock['ceilings'][k] for k in UNITS):raise RuntimeError('Campaign ceiling exceeded')
    size=sum(p.stat().st_size for p in base.rglob('*') if p.is_file())
    if size>lock['ceilings']['artifact_bytes']:raise RuntimeError('Campaign physical storage ceiling')
    return dict(verified=True,completed_or_accounted_phases=phases,charged_usage=total,physical_artifact_bytes=size)

def record_phase(root,phase,evidence_path):
    root=Path(root);base=campaign_root(root);path=base/evidence_path;e=read(path)
    verify_campaign(root,e['campaign_usage'])
    write_new(base/'accounting'/('phase-'+phase+'.json'),dict(phase=phase,evidence_path=evidence_path,evidence_sha256=sha(path),usage=e['campaign_usage']))
    return verify_campaign(root)
