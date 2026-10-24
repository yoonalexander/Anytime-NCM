"""Independent S5 replay of saved claim calculations; no search/model imports."""
import os,sys,json,re,hashlib,math,time,resource
from pathlib import Path
for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[name]='4'
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
import numpy as np
from sacrebleu.metrics import BLEU,CHRF
from anytime_ncm.wmt_data import StringRows

def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dg(a):return hashlib.sha256(json.dumps([int(k) for k in a],separators=(',',':')).encode()).hexdigest()
NUM=re.compile(r'(?<!\w)\d+(?:[.,]\d+)*(?:%)?');NEG=re.compile(r"\b(?:no|not|never|neither|without)\b|n['\u2019]t\b",re.I)

def diagnostics(text,ref):
    x=set(NUM.findall(text));y=set(NUM.findall(ref))
    return (2*len(x&y)/(len(x)+len(y)) if y else None, int(bool(NEG.search(text))!=bool(NEG.search(ref))))
def direct(rows,refs,a):
    hyps=[r['levels'][k-1]['text'] for r,k in zip(rows,a,strict=True)]
    ds=[diagnostics(h,r) for h,r in zip(hyps,refs,strict=True)];nums=[d[0] for d in ds if d[0] is not None]
    return dict(bleu=BLEU().corpus_score(hyps,[refs]).score,chrf=CHRF().corpus_score(hyps,[refs]).score,
        numeric_reference_f1=float(np.mean(nums)) if nums else None,negation_cue_mismatch_rate=float(np.mean([d[1] for d in ds])))
def closemetrics(x,y):
    for k in ['bleu','chrf','numeric_reference_f1','negation_cue_mismatch_rate']:
        assert x[k] is None and y[k] is None or x[k] is not None and y[k] is not None and abs(x[k]-y[k])<1e-10,(k,x[k],y[k])
def cost(a,p,adaptive=True):
    prefixes=[1,5,13,27,47,73,105,145,193,249,313]
    return np.array([p['f']+(1-p['f'])*(p['tau']*k/11+(1-p['tau'])*prefixes[k-1]/313)+(p['h']*(k-1)+.2*p['h']*k if adaptive else 0) for k in a])
def okay(a,b):
    return a['bleu']>=b['bleu']-.5-1e-10 and a['chrf']>=b['chrf']-1-1e-10 and (b['numeric_reference_f1'] is None or a['numeric_reference_f1']>=b['numeric_reference_f1']-.02-1e-10) and a['negation_cue_mismatch_rate']<=b['negation_cue_mismatch_rate']+.02+1e-10

def main():
    start=time.monotonic();out=ROOT/'results/stronger_research/s5a';assert not (out/'independent-checks.json').exists(),'No silent verification replay';out.mkdir(parents=True,exist_ok=True)
    inv=load(ROOT/'docs/studies/stronger-research-inventory.json');manifest=load(ROOT/'docs/partitions/wmt14-phase4.json');checks={};nmetrics=0;count=0
    for split,n in [('exploration',128),('development',64)]:
        selected=inv['s1_population'][split];assert selected==sorted(manifest['partitions'][split],key=lambda e:e['index'])[:n]
        keys={(e['identity'],e['index']) for e in selected};rows=[]
        # Independently filter identity metadata before parsing active outcome bodies.
        with (ROOT/'results/phase4/wmt14/trajectories.jsonl').open('rb') as f:
            for line in f:
                m=re.match(rb'^\{"identity":"([a-f0-9]{64})","index":(\d+),"partition":"([a-z0-9_]+)"',line);assert m
                if m[3].decode()!=split:continue
                assert (m[1].decode(),int(m[2])) in keys
                rows.append(json.loads(line))
        rows.sort(key=lambda r:r['index']);assert len(rows)==n and len({r['identity'] for r in rows})==n
        refmap=StringRows((ROOT/'data/wmt14/reference_translations.pickle').read_bytes()).select({e['index'] for e in selected});refs=[refmap[r['index']] for r in rows]
        r=load(ROOT/f'results/stronger_research/s1/{split}/result.json');full=direct(rows,refs,[11]*n);nmetrics+=1
        for fixed in r['fixed_depths']:
            closemetrics(direct(rows,refs,[fixed['depth']]*n),fixed['metrics']);nmetrics+=1
        ledger_count=0;incumbent_count=0
        for point,final in r['assignments'].items():
            base=ROOT/f'results/stronger_research/s1/{split}';accepted=[json.loads(x) for x in (base/(point+'_acceptances.jsonl')).read_text().splitlines()]
            parents={dg(e['exits']):e for e in accepted};previous=math.inf
            for entry in accepted:
                a=entry['exits'];metric=direct(rows,refs,a);nmetrics+=1
                assert okay(metric,full);assert float(cost(a,final['scenario']).mean())<=previous+1e-12
                previous=float(cost(a,final['scenario']).mean());incumbent_count+=1
            closemetrics(direct(rows,refs,final['exits']),final['metrics']);nmetrics+=1
            for i,event in enumerate((base/(point+'_search.jsonl')).open(),1):
                e=json.loads(event);assert e['sequence']==i
                if e['kind'].startswith('fixed_'):a=[int(e['kind'].split('_')[1])]*n
                elif e['kind'] in ('stability','adaptive'):a=r['saved_policy_exits'][e['kind']]
                else:
                    change=e['change'];parent=parents[change['parent_sha256']];assert parent['evaluations']<=i
                    a=list(parent['exits']);j=change['input_position'];assert a[j]==change['old'] and 1<=change['new']<change['old'];a[j]=change['new']
                assert dg(a)==e['assignment_sha256'];assert abs(float(cost(a,final['scenario']).mean())-e['cost'])<1e-12
                assert okay(e['metrics'],full)==e['feasible'];ledger_count+=1
            assert i==10000 and final['evaluations']==10000 and final['certified_optimum'] is False
        count+=ledger_count
        # New implementation of fixed-vector bootstrap, with direct corpus-statistics parity.
        vectors={p:v['exits'] for p,v in r['assignments'].items()};vectors.update(full=[11]*n,fixed=[r['selected_fixed_depth']]*n)
        draws=np.random.Generator(np.random.PCG64(20261023 if split=='exploration' else 20261024)).integers(0,n,size=(10000,n));bootstrap={}
        for name,a in vectors.items():
            hyps=[row['levels'][k-1]['text'] for row,k in zip(rows,a,strict=True)];values={}
            for metric,obj in [('bleu',BLEU()),('chrf',CHRF())]:
                stats=np.array(obj._extract_corpus_statistics(hyps,[refs]),dtype=np.int64)
                assert abs(obj._compute_score_from_stats(stats.sum(axis=0).tolist()).score-obj.corpus_score(hyps,[refs]).score)<1e-10
                values[metric]=np.array([obj._compute_score_from_stats(x.tolist()).score for begin in range(0,10000,100) for x in stats[draws[begin:begin+100]].sum(axis=1)])
            bootstrap[name]=values
        for pair,old in r['analysis']['comparisons'].items():
            name,base=pair.split('_vs_');point=r['assignments'][name]['scenario'] if name!='fixed' else dict(f=.25,tau=.5,h=.005)
            for k in ['bleu','chrf']:
                v=bootstrap[name][k]-bootstrap[base][k]
                assert np.max(np.abs(np.percentile(v,[2.5,97.5])-old['quality'][k]['ci95']))<1e-10
                assert abs(float(np.percentile(v,5))-old['quality'][k]['lower95'])<1e-10
            ca=cost(vectors[name],point,name!='fixed');cb=cost(vectors[base],point,False)
            reduction=1-ca[draws].mean(axis=1)/cb[draws].mean(axis=1)
            assert np.max(np.abs(np.percentile(reduction,[2.5,97.5])-old['conditional_reduction']['ci95']))<1e-10
        s2=load(ROOT/f'results/stronger_research/s2a/{split}.json');metric=CHRF();early_text=0;early_ids=0;damaged=0
        for row,ref in zip(rows,refs,strict=True):
            early_text+=any(s['text']==row['levels'][-1]['text'] for s in row['levels'][:-1]);early_ids+=any(s['ids']==row['levels'][-1]['ids'] for s in row['levels'][:-1])
            vals=[metric.sentence_score(s['text'],[ref]).score for s in row['levels']];damaged+=sum(y-x< -1e-12 for x,y in zip(vals,vals[1:]))
        assert early_text==s2['ever_early_final_text_match'] and early_ids==s2['ever_early_final_ids_match'];assert damaged==sum(x['damaged'] for x in s2['adjacent'])
        checks[split]={'inputs':n,'fixed_points_verified':11,'retained_assignments_verified':3,'accepted_incumbents_verified':incumbent_count,'ledger_records_verified':ledger_count,'paired_comparisons_verified':7,'bootstrap_resamples_reproduced':10000,'early_final_visible_matches':early_text,'early_final_ids_matches':early_ids,'adjacent_chrF_decreases':damaged}
    assert count==60000 and nmetrics<=256
    immutable={}
    for name,item in inv['files'].items():
        if name=='RESEARCH_ROADMAP.md':continue
        assert sha(ROOT/name)==item['sha256'];immutable[name]=item['sha256']
    result={'status':'passed','independence':'Separate calculation implementation by the same assistant; no independent researcher or hardware replication','checks':checks,'direct_corpus_replays':nmetrics,'historical_digests_unchanged':immutable,'new_candidates_searched':0,'new_model_calls':0,'new_fits':0,'new_final_outcomes':0,'seconds':time.monotonic()-start,'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'source_sha256':sha(Path(__file__)),'protocol_sha256':sha(ROOT/'docs/studies/stronger-research-s5-verification-plan.md')}
    assert result['seconds']<7200 and result['max_rss_kib']<4*1024*1024 and 'torch' not in sys.modules
    (out/'independent-checks.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='historical_digests_unchanged'},indent=2))
if __name__=='__main__':main()
