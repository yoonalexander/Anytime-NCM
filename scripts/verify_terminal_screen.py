"""Separate saved-cell and bootstrap arithmetic check, with no new draw set."""
import hashlib,json,sys
from pathlib import Path
import numpy as np
from scipy.stats import binom
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/evidence_gaps/e2_terminal_screen'
read=lambda p:json.loads(p.read_text())


def main():
    target=OUT/'independent-checks.json'
    if target.exists():raise FileExistsError('Preserve first checker receipt')
    execution=read(OUT/'execution.json');report=read(OUT/'analysis.json')
    for p,h in execution['artifact_sha256'].items():assert hashlib.sha256((OUT/p).read_bytes()).hexdigest()==h,p
    selected=read(OUT/'selected-cells.json')
    trajectories=[json.loads(s) for s in (ROOT/'results/evidence_gaps/e2/trajectories.jsonl').read_text().splitlines()]
    assert [(r['index'],r['identity']) for r in selected]==[(r['index'],r['identity']) for r in trajectories]
    raw=[json.loads(s) for b in range(2) for s in (ROOT/f'results/evidence_gaps/e2/{b}-requests.jsonl').read_text().splitlines()]
    cells={(r['index'],r['block'],r['repeat'],r['method']):r['wall_ms'] for r in raw if r['phase']=='timed'}
    for r,t in zip(selected,trajectories,strict=True):
        assert r['depth']==next(k+1 for k,l in enumerate(t['levels']) if l['text']==t['levels'][-1]['text'])
        for field,method in [('terminal_ms',f"fixed:{r['depth']}"),('full_ms','fixed:11'),('dense_ms','exact')]:
            assert r[field]==[[cells[r['index'],b,repeat,method] for repeat in range(2)] for b in range(2)]
    data={method:np.array([r[field] for r in selected]) for method,field in [('terminal_exact','terminal_ms'),('full','full_ms'),('dense_exact','dense_ms')]}
    for m,v in data.items():assert abs(v.mean()-report['methods'][m]['mean_ms'])<1e-10
    rng=np.random.Generator(np.random.PCG64(20261026));ix=rng.integers(0,256,size=(100000,256),dtype=np.int32);blocks=rng.integers(0,2,size=(100000,2),dtype=np.int32)
    rank=int(binom.ppf(.001/4,100000,.0125));means={m:v.mean(axis=2) for m,v in data.items()}
    for candidate,base in [('terminal_exact','full'),('dense_exact','terminal_exact')]:
        a=means[candidate][ix[:,:,None],blocks[:,None,:]].mean(axis=(1,2));b=means[base][ix[:,:,None],blocks[:,None,:]].mean(axis=(1,2))
        values=np.sort(1-a/b);saved=report['contrasts'][candidate+'_versus_'+base]
        assert abs(values[rank-1]-saved['lower'])<1e-12 and abs(values[-rank]-saved['upper'])<1e-12
    assert report['contrasts']['terminal_exact_versus_full']['upper']<.05 and report['decision']=='do_not_budget_same_exact_family'
    receipt=dict(status='pass',selected_identities=256,selected_request_values=3072,reused_bootstrap_vectors=100000,cost_intervals_recomputed=2,new_reference_reads=0,model_calls=0,post_hoc=True,checker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),independent_human_review=False)
    with target.open('x') as f:json.dump(receipt,f,indent=2);f.write('\n')
    print(json.dumps(receipt))


if __name__=='__main__':main()
