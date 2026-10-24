"""S5 independent retained-timing and source-lock checks; no models."""
import json,sys,hashlib,re
from pathlib import Path
import numpy as np
root=Path(__file__).resolve().parents[1]
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
s1=root/'results/stronger_research/s1';dev=read(s1/'development/result.json');pop=read(root/'docs/studies/stronger-research-inventory.json')['s1_population']['development']
for split in ['exploration','development']:
    for n,v in read(s1/split/'result.json')['sources'].items():assert h(root/n)==v,n
keys={e['identity'] for e in pop};values={}
with (root/'results/phase4/wmt14/4b_requests.jsonl').open('rb') as f:
    for line in f:
        m=re.match(rb'^\{"identity":"([a-f0-9]{64})","index":(\d+),"partition":"development"',line);assert m and m[1].decode() in keys
        r=json.loads(line);key=(r['identity'],r['method'],r['repeat']);assert key not in values;values[key]=r['wall_ms'];assert r['exit_level']==11
assert len(values)==768
ids=[e['identity'] for e in pop];draws=np.random.Generator(np.random.PCG64(20261024)).integers(0,64,size=(10000,64))
for method,old in dev['saved_timing'].items():
    v=np.array([values[i,method,k] for i in ids for k in range(3)]);means=np.array([np.mean([values[i,method,k] for k in range(3)]) for i in ids])
    assert abs(v.mean()-old['mean_ms'])<1e-10 and abs(np.percentile(v,95)-old['p95_ms'])<1e-10
    for base in ['full','fixed']:
        b=np.array([np.mean([values[i,base,k] for k in range(3)]) for i in ids]);ci=np.percentile(1-means[draws].mean(axis=1)/b[draws].mean(axis=1),[2.5,97.5]);assert max(abs(ci-old['paired'][base]['ci95']))<1e-10
result={'status':'passed','timed_development_rows':768,'identities':64,'repeats':3,'methods':4,'s1_source_locks_match':True,'mean_p95_paired_intervals':'independently reproduced','new_models_or_final_outcomes':0,'source_sha256':h(Path(__file__))}
p=root/'results/stronger_research/s5a/timing-source-checks.json';assert not p.exists();p.write_text(json.dumps(result,indent=2)+'\n');print(result)
