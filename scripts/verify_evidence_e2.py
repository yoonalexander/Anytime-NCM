"""Separate E2 saved-record checker: no model imports or new outcome generation."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import zipfile
import numpy as np
from sacrebleu.metrics import BLEU,CHRF
from scipy.stats import binom,beta

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from anytime_ncm.wmt_data import StringRows
from anytime_ncm.wmt_policy import diagnostics
OUT=ROOT/'results/evidence_gaps/e2'


def read(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def vh(v):return hashlib.sha256(json.dumps(v,ensure_ascii=True,separators=(',',':')).encode()).hexdigest()
def need(v,message):
    if not v:raise ValueError(message)


def main():
    target=OUT/'independent-checks.json'
    if target.exists():raise FileExistsError('Preserve original verification')
    execution=read(OUT/'execution.json');started=read(OUT/'started.json');analysis=read(OUT/'analysis.json')
    for p,h in execution['artifact_sha256'].items():need(sha(OUT/p)==h,'Artifact hash: '+p)
    with zipfile.ZipFile(OUT/'execution-sources.zip') as z:
        for p,h in started['source_sha256'].items():
            need(sha(ROOT/p)==h and hashlib.sha256(z.read(p)).hexdigest()==h,'Source/archive hash: '+p)
    manifest=read(ROOT/'results/evidence_gaps/e0/input-manifest.json')
    entries=manifest['roles']['E2_audit'];allowed={e['index']:e['identity'] for e in entries}
    need(all(not e['outcome_access_released'] for e in entries),'E0 manifest mutated')
    rows=[json.loads(s) for s in (OUT/'trajectories.jsonl').read_text().splitlines()]
    need([(r['index'],r['identity']) for r in rows]==list(allowed.items()),'Audit allowlist/order')
    cache={r['index']:r for r in rows}
    # Only sixteen explicitly exposed warmup bodies; remaining historical bodies opaque.
    import re
    header=re.compile(rb'^\{"identity":\s*"([a-f0-9]{64})",\s*"index":\s*(\d+),\s*"partition":\s*"([a-z_]+)"')
    warm={e['index']:e['identity'] for e in manifest['E1_existing_exploration']}
    with (ROOT/'results/phase4/wmt14/trajectories.jsonl').open('rb') as stream:
        for raw in stream:
            m=header.match(raw);need(m is not None,'Historical header')
            index=int(m[2])
            if index in warm:
                need(m[1].decode()==warm[index] and m[3]==b'exploration','Warmup identity')
                cache[index]=json.loads(raw)
    need(set(cache)==set(allowed)|set(warm),'Unexpected output identity')
    depths={i:next(k+1 for k,l in enumerate(r['levels']) if l['text']==r['levels'][-1]['text']) for i,r in cache.items()}
    expected_counts=Counter(str(depths[i]) for i in allowed)
    need(analysis['exact_depth_counts']=={str(d):expected_counts[str(d)] for d in range(1,12)},'Exact-depth counts')
    schedule=read(OUT/'timing-schedule.json')
    records=[];total=dict(inputs=0,generator_levels=0,decoder=0,encoder=0)
    for stage in ('collection','0','1'):
        result=[json.loads(s) for s in (OUT/f'{stage}-requests.jsonl').read_text().splitlines()]
        ledger=[json.loads(s) for s in (OUT/f'{stage}-starts.jsonl').read_text().splitlines()]
        process=read(OUT/f'{stage}-execution.json');running=dict.fromkeys(total,0)
        need(len(result)==len(ledger)==(256 if stage=='collection' else 6204),'Request count')
        need(process['state_before']==process['state_after'],'Model state')
        for r,l in zip(result,ledger,strict=True):
            need(l['work_before']==running and l['request_count']==running['inputs']+1,'Start ledger')
            need(all(r[k]==v for k,v in l.items() if k not in ('work_before','request_count')),'Request-start identity')
            if stage!='collection':
                expected=schedule[r['request_id']]
                need(all(r[k]==v for k,v in expected.items()),'Derived schedule row')
                need(r['depth']==(depths[r['index']] if r['method']=='exact' else int(r['method'].split(':')[1])),'Assigned depth')
                need((r['index'] in warm)==(r['phase']=='warmup'),'Warmup/audit exclusion')
                records.append(r)
            delta=dict(inputs=1,generator_levels=r['depth'],decoder=r['depth'] if r['schedule']=='every_level' else 1,encoder=0)
            need(r['work']==delta and r['parity'],'Work/parity')
            running={k:running[k]+delta[k] for k in running}
            old=cache[r['index']];end=sum([1,4,8,14,20,26,32,40,48,56,64][:r['depth']])
            need(r['codes_sha256']==vh(old['codes'][:end]),'Code prefix')
            need(r['ids_sha256']==vh(old['levels'][r['depth']-1]['ids']) and r['text_sha256']==vh(old['levels'][r['depth']-1]['text']),'Exit output')
            expected_levels=[r['depth']] if r['schedule']=='terminal' else list(range(1,r['depth']+1))
            need([o['level'] for o in r['observations']]==expected_levels,'Inspection levels')
            for o in r['observations']:
                need(o['ids_sha256']==vh(old['levels'][o['level']-1]['ids']) and o['text_sha256']==vh(old['levels'][o['level']-1]['text']),'Observed output')
        need(running==process['counts'],'Process counts')
        total={k:total[k]+running[k] for k in total}
    need(total==execution['counts'],'Stage work')
    refs=StringRows((ROOT/'data/wmt14/reference_translations.pickle').read_bytes()).select(set(allowed))
    references=[refs[e['index']] for e in entries]
    methods=['exact']+[f'fixed:{d}' for d in range(1,12)]
    alpha=.05/118;rank=int(binom.ppf(.001/118,100000,alpha))
    metric_checks=0
    full_diagnostics=[diagnostics(r['levels'][-1]['text'],ref) for r,ref in zip(rows,references,strict=True)]
    for method in methods:
        hyps=[r['levels'][(depths[r['index']] if method=='exact' else int(method.split(':')[1]))-1]['text'] for r in rows]
        for name,metric in [('bleu',BLEU()),('chrf',CHRF())]:
            value=metric.corpus_score(hyps,[references]).score
            need(abs(value-analysis['quality'][method]['metrics'][name])<1e-10,'Direct corpus aggregation')
            metric_checks+=1
        ds=[diagnostics(h,r) for h,r in zip(hyps,references,strict=True)]
        nums=[d['numeric_reference_f1'] for d in ds if d['reference_has_digit_numbers']]
        numeric=float(np.mean(nums)) if nums else None
        need(numeric==analysis['quality'][method]['metrics']['numeric_reference_f1'],'Numeric aggregation')
        need(float(np.mean([d['negation_cue_mismatch'] for d in ds]))==analysis['quality'][method]['metrics']['negation_cue_mismatch_rate'],'Negation aggregation')
        for endpoint in ('numeric','negation'):
            differences=[]
            for a,b in zip(ds,full_diagnostics,strict=True):
                if endpoint=='numeric':
                    if a['reference_has_digit_numbers']:differences.append(a['numeric_reference_f1']-b['numeric_reference_f1'])
                else:differences.append(int(a['negation_cue_mismatch'])-int(b['negation_cue_mismatch']))
            interval=analysis['quality'][method]['intervals'][endpoint]
            need(interval['coverage']==len(differences),'Cue coverage')
            if method in ('exact','fixed:11'):
                need(all(d==0 for d in differences) and interval['lower']==interval['upper']==0,'Structural cue equality')
            elif differences:
                n=len(differences)
                upper=lambda k:1. if k==n else float(beta.isf(alpha,k+1,n-k))
                need(abs(interval['lower']+upper(sum(d<0 for d in differences)))<1e-12 and abs(interval['upper']-upper(sum(d>0 for d in differences)))<1e-12,'Signed sparse-cue envelope')
            else:need(interval['lower'] is None and interval['upper'] is None,'Undefined cue handling')
        intervals=analysis['quality'][method]['intervals'];margins={'bleu':.5,'chrf':1.,'numeric':.02,'negation':.02}
        passes=all(v['upper'] is not None and (v['upper']<=margins[k] if k=='negation' else v['lower']>=-margins[k]) for k,v in intervals.items())
        fails=any(v['lower'] is not None and (v['lower']>margins[k] if k=='negation' else v['upper']<-margins[k]) for k,v in intervals.items())
        need(analysis['quality'][method]['status']==('pass' if passes else 'fail' if fails else 'unresolved'),'Quality decision')
    positions={e['identity']:i for i,e in enumerate(entries)}
    data=np.full((256,2,2,12),np.nan)
    for r in records:
        if r['phase']=='timed':data[positions[r['identity']],r['block'],r['repeat'],methods.index(r['method'])]=r['wall_ms']
    need(np.isfinite(data).all(),'Complete timing grid')
    for j,m in enumerate(methods):need(abs(data[:,:,:,j].mean()-analysis['methods'][m]['mean_ms'])<1e-10,'Mean timing')
    rng=np.random.Generator(np.random.PCG64(20261026))
    ix=rng.integers(0,256,size=(100000,256),dtype=np.int32);blocks=rng.integers(0,2,size=(100000,2),dtype=np.int32)
    means=data.mean(axis=2)
    for j,m in enumerate(methods[1:],1):
        selected_exact=means[ix[:,:,None],blocks[:,None,:],0].mean(axis=(1,2))
        selected_fixed=means[ix[:,:,None],blocks[:,None,:],j].mean(axis=(1,2))
        distribution=np.sort(1-selected_exact/selected_fixed)
        saved=analysis['timing_exact_versus_fixed'][m]
        need(abs(saved['lower']-distribution[rank-1])<1e-12 and abs(saved['upper']-distribution[-rank])<1e-12,'Crossed paired interval')
    need(not analysis['controller_entry_released'] and execution['E3_inputs']==execution['E4_inputs']==execution['fits']==execution['target_encodings']==0,'Closed roles/work')
    receipt=dict(status='pass',request_rows_checked=12664,counts=total,metric_direct_corpus_checks=metric_checks,
        timing_contrasts_recomputed=11,bootstrap_vectors='same frozen 100000 identities/process indices; no additional draw set',
        numeric_reference_coverage=len(nums),audit_references_rematerialized_for_verification=256,new_reference_identities=0,
        E3_access=False,E4_access=False,model_calls=0,limitation='separate arithmetic implementation by the same assistant; not independent human scientific review')
    with target.open('x',encoding='utf-8') as f:json.dump(receipt,f,indent=2);f.write('\n')
    print(json.dumps(receipt),flush=True)


if __name__=='__main__':main()
