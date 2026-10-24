"""Frozen S1 saved-WMT audit. No model libraries or final-output readers."""
from __future__ import annotations
import hashlib,itertools,json,math,os,re,resource,subprocess,sys,time
from pathlib import Path
import numpy as np
import sacrebleu
from sacrebleu.metrics import BLEU,CHRF
from anytime_ncm.wmt_data import StringRows,identity
from anytime_ncm.wmt_policy import diagnostics,simulate
from anytime_ncm.wmt_metrics import scores

OUT='results/stronger_research/s1'
PLAN='docs/studies/stronger-research-protocol.json'
INVENTORY='docs/studies/stronger-research-inventory.json'
SOURCES=['src/anytime_ncm/stronger_s1.py','scripts/run_stronger_s1.py','tests/test_stronger_s1.py',
         'src/anytime_ncm/wmt_metrics.py','src/anytime_ncm/wmt_policy.py','src/anytime_ncm/wmt_data.py']
WIDTHS=np.array([1,4,8,14,20,26,32,40,48,56,64]);PREFIX=np.cumsum(WIDTHS)
HEADER=re.compile(rb'^\{"identity":\s*"([a-f0-9]{64})",\s*"index":\s*(\d+),\s*"partition":\s*"([a-z0-9_]+)"')

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk)
    return h.hexdigest()
def save(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,ensure_ascii=True,allow_nan=False)+'\n',encoding='utf-8')
def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def need(value,message):
    if not value:raise ValueError(message)
def digest(a):return hashlib.sha256(json.dumps([int(x) for x in a],separators=(',',':')).encode()).hexdigest()
def source_hashes(root):return {p:sha(root/p) for p in SOURCES}

def validate_population(manifest,inventory):
    selected=inventory['s1_population'];seen=set()
    for part,count in [('exploration',128),('development',64)]:
        expected=sorted(manifest['partitions'][part],key=lambda e:e['index'])[:count]
        need(selected[part]==expected,'Allowlist differs from canonical manifest selection')
        for e in expected:
            need(e['identity'] not in seen,'Split identity collision');seen.add(e['identity'])
            need(e['index']==min(e['indices']),'Noncanonical group')
    forbidden={e['identity'] for p,rows in manifest['partitions'].items() if p not in selected for e in rows}
    need(not seen&forbidden,'Final/reserved overlap')
    return selected

def selective_rows(path,selected,active,all_selected):
    """Inspect identity header only before decoding active JSON bodies."""
    allow={(p,e['index'],e['identity']) for p,rows in all_selected.items() for e in rows}
    active_keys={(active,e['index'],e['identity']) for e in selected}
    rows=[];seen=set();skipped=0
    with Path(path).open('rb') as f:
        for line in f:
            m=HEADER.match(line);need(m is not None,'Noncanonical JSON identity header')
            key=(m[3].decode(),int(m[2]),m[1].decode())
            need(key in allow,'Unexpected or forbidden trajectory identity')
            need(key not in seen,'Duplicate trajectory identity');seen.add(key)
            if key not in active_keys:skipped+=1;continue
            row=json.loads(line)
            need((row['partition'],row['index'],row['identity'])==key,'Header/body disagreement')
            rows.append(row)
    need(seen==allow,'Missing saved trajectory identity')
    need(len(rows)==len(selected),'Active population incomplete')
    return sorted(rows,key=lambda e:e['index']),skipped

def validate_rows(rows):
    for row in rows:
        need(len(row['prefix_ids'])==96 and identity(row['prefix_ids'])==row['identity'],'Prefix identity mismatch')
        need(len(row['codes'])==313 and all(type(x)is int and 0<=x<4096 for x in row['codes']),'Invalid codes')
        need([s['level'] for s in row['levels']]==list(range(1,12)),'Missing/duplicate/out-of-order levels')
        for state in row['levels']:
            need(len(state['ids'])==64 and all(type(x)is int and 0<=x<151680 for x in state['ids']),'Invalid token IDs')
            need(isinstance(state['text'],str),'Nontext output')

def provenance(root,lock):
    need(sacrebleu.__version__=='2.6.0','Metric version differs')
    need(sha(root/'docs/studies/stronger-research-protocol.md')==lock['protocol_sha256'],'Protocol hash differs')
    need(sha(root/INVENTORY)==lock['population']['selected_records_file_sha256'],'Population file hash differs')
    inventory=read(root/INVENTORY)
    # Historical evidence is immutable; the roadmap intentionally changes as phases complete.
    hashes={}
    for name,item in inventory['files'].items():
        if name in ('RESEARCH_ROADMAP.md',):continue
        need(sha(root/name)==item['sha256'],'Evidence hash differs: '+name);hashes[name]=item['sha256']
    for stage in ('4a','4b'):
        receipt=read(root/f'results/phase4/wmt14/{stage}.json')
        for name,h in receipt['source_sha256'].items():
            need(sha(root/receipt['source_snapshot']/name)==h,'Historical execution snapshot differs: '+name)
        need(receipt['state_before']==receipt['state_after'],'Historical model-state check failed')
    a=read(root/'results/phase4/wmt14/4a.json')
    need(a['full_resolution_checked_inputs']==192 and a['exact_official_parity_inputs']==32,'Historical reconstruction checks missing')
    sources=read(root/'configs/phase4_wmt_sources.json')
    need(sources['model_revision']=='d342ce8aaea58830eef3b8ad473664673e41f692','Model revision differs')
    need(sources['dataset_revision']=='6580ba41a4b0a976dde876fbe84d25327617b0e6','Data revision differs')
    for name in ('data/wmt14/sources.pickle','data/wmt14/reference_translations.pickle'):
        need(sha(root/name)==sources['files'][name]['sha256'],'Raw asset hash differs');hashes[name]=sources['files'][name]['sha256']
    return hashes

class Corpus:
    def __init__(self,rows,refs):
        self.rows=rows;self.refs=refs;self.n=len(rows);self.metric={'bleu':BLEU(),'chrf':CHRF()}
        self.stats={}
        for name,metric in self.metric.items():
            self.stats[name]=np.stack([np.asarray(metric._extract_corpus_statistics([r['levels'][k]['text'] for r in rows],[refs]),dtype=np.int64) for k in range(11)],axis=1)
        ds=[[diagnostics(s['text'],ref) for s in row['levels']] for row,ref in zip(rows,refs,strict=True)]
        self.covered=np.array([x[0]['reference_has_digit_numbers'] for x in ds],dtype=bool)
        self.numeric=np.array([[s['numeric_reference_f1'] if s['numeric_reference_f1'] is not None else 0 for s in x] for x in ds])
        self.negation=np.array([[int(s['negation_cue_mismatch']) for s in x] for x in ds])
        self.cache={};self.parity_checks=0
    def selected(self,a):return np.arange(self.n),np.asarray(a,dtype=int)-1
    def evaluate(self,a):
        key=tuple(int(x) for x in a);hit=key in self.cache
        if not hit:
            ix=self.selected(a)
            result={name:metric._compute_score_from_stats(self.stats[name][ix].sum(axis=0).tolist()).score for name,metric in self.metric.items()}
            result.update(numeric_reference_f1=float(self.numeric[ix][self.covered].mean()) if self.covered.any() else None,
                          numeric_reference_coverage=int(self.covered.sum()),negation_cue_mismatch_rate=float(self.negation[ix].mean()))
            self.cache[key]=result
        return dict(self.cache[key]),hit
    def direct(self,a):
        direct=scores([r['levels'][int(k)-1]['text'] for r,k in zip(self.rows,a,strict=True)],self.refs)
        cached,_=self.evaluate(a)
        for name in ('bleu','chrf','numeric_reference_f1','negation_cue_mismatch_rate'):
            need(cached[name] is None and direct[name] is None or cached[name] is not None and direct[name] is not None and abs(cached[name]-direct[name])<=1e-10,'Direct corpus parity failed: '+name)
        need(direct['bleu_signature']=='nrefs:1|case:mixed|eff:no|tok:13a|smooth:exp|version:2.6.0','BLEU signature differs')
        need(direct['chrf_signature']=='nrefs:1|case:mixed|eff:yes|nc:6|nw:0|space:no|version:2.6.0','chrF signature differs')
        self.parity_checks+=1;return direct

def feasible(a,b):
    return (a['bleu']>=b['bleu']-.5-1e-10 and a['chrf']>=b['chrf']-1-1e-10 and
        (b['numeric_reference_f1'] is None or a['numeric_reference_f1']>=b['numeric_reference_f1']-.02-1e-10) and
        a['negation_cue_mismatch_rate']<=b['negation_cue_mismatch_rate']+.02+1e-10)
def costs(a,f=.25,tau=.5,h=0,adaptive=True):
    a=np.asarray(a);v=f+(1-f)*(tau*a/11+(1-tau)*PREFIX[a-1]/313)
    return v+(h*(a-1)+.2*h*a if adaptive else 0)
def better(candidate,current,point):
    if current is None:return True
    x=float(costs(candidate,**point).mean());y=float(costs(current,**point).mean())
    if abs(x-y)>1e-12:return x<y
    return (int(PREFIX[np.asarray(candidate)-1].sum()),tuple(candidate))<(int(PREFIX[np.asarray(current)-1].sum()),tuple(current))

def search(corpus,point,baselines,emit,checkpoint,cap=10000,deadline=math.inf):
    p={k:point[k] for k in ('f','tau','h')};a=np.full(corpus.n,11,dtype=int);full,_=corpus.evaluate(a)
    count=0;accepted=0;terminated=None;start=time.monotonic()
    def evaluate(v,kind,change=None):
        nonlocal count
        count+=1;s,hit=corpus.evaluate(v)
        emit({'sequence':count,'kind':kind,'change':change,'assignment_sha256':digest(v),'metrics':s,
              'cost':float(costs(v,**p).mean()),'feasible':feasible(s,full),'cache_hit':hit,'selection_status':'baseline' if kind!='neighbor' else 'pending_sweep_see_acceptance_ledger','elapsed_seconds':time.monotonic()-start})
        return s
    for name,v in baselines:
        need(count<cap,'Budget too small for declared baselines');evaluate(v,name)
    checkpoint(a,count,accepted)
    while count<cap:
        winner=None;interrupted=False
        for i in range(corpus.n):
            for k in range(1,int(a[i])):
                if count>=cap or time.monotonic()>=deadline:interrupted=True;break
                v=a.copy();v[i]=k;s=evaluate(v,'neighbor',{'input_position':i,'old':int(a[i]),'new':k,'parent_sha256':digest(a)})
                if feasible(s,full) and float(costs(v,**p).mean())<float(costs(a,**p).mean())-1e-12 and better(v,winner,p):winner=v
            if interrupted:break
        if winner is not None:
            a=winner;accepted+=1;corpus.direct(a);checkpoint(a,count,accepted)
        if interrupted:
            terminated='assignment_cap_incomplete_sweep' if count>=cap else 'wall_time_incomplete_sweep';break
        if winner is None:terminated='no_improving_feasible_coordinate_neighbor';break
    if terminated is None:terminated='assignment_cap_at_sweep_boundary'
    return {'exits':[int(x) for x in a],'assignment_sha256':digest(a),'evaluations':count,'accepted_changes':accepted,
            'termination':terminated,'certified_optimum':False,'optimality_gap':None,'metrics':corpus.direct(a),
            'scenario':p,'mean_cost':float(costs(a,**p).mean()),'mean_levels':float(a.mean()),
            'mean_codes':float(PREFIX[a-1].mean()),'mean_surrogate_decodes':float(a.mean()),
            'exit_distribution':{str(k):int((a==k).sum()) for k in range(1,12)},'early_inputs':int((a<11).sum())}

def interval(v):
    v=np.asarray(v,dtype=float);good=v[np.isfinite(v)]
    return {'ci95':np.percentile(good,[2.5,97.5]).tolist() if len(good) else None,
            'lower95':float(np.percentile(good,5)) if len(good) else None,'undefined':int(len(v)-len(good))}

def bootstraps(corpus,vectors,draws,deadline):
    result={}
    for name,a in vectors.items():
        need(time.monotonic()<deadline,'Split wall-time limit reached during bootstrap')
        ix=corpus.selected(a);data={}
        for metric,obj in corpus.metric.items():
            stats=corpus.stats[metric][ix];values=[]
            for begin in range(0,len(draws),128):
                sums=stats[draws[begin:begin+128]].sum(axis=1)
                values.extend(obj._compute_score_from_stats(s.tolist()).score for s in sums)
            data[metric]=np.array(values)
        denom=corpus.covered[draws].sum(axis=1);num=corpus.numeric[ix][draws]*corpus.covered[draws]
        data['numeric_reference_f1']=np.divide(num.sum(axis=1),denom,out=np.full(len(draws),np.nan),where=denom!=0)
        data['negation_cue_mismatch_rate']=corpus.negation[ix][draws].mean(axis=1)
        result[name]=data
    return result

def analyze(corpus,results,fixed_depth,split,deadline):
    n=corpus.n;fixed=np.full(n,fixed_depth);full=np.full(n,11)
    vectors={k:np.array(v['exits']) for k,v in results.items()};vectors.update(fixed=fixed,full=full)
    rng=np.random.Generator(np.random.PCG64(20261023 if split=='exploration' else 20261024));draws=rng.integers(0,n,size=(10000,n))
    boots=bootstraps(corpus,vectors,draws,deadline);comparisons={}
    for name in ('O0','O1','O2','fixed'):
        for base in (('full','fixed') if name!='fixed' else ('full',)):
            point=results[name]['scenario'] if name!='fixed' else dict(f=.25,tau=.5,h=.005)
            a=vectors[name];b=vectors[base];ma,_=corpus.evaluate(a);mb,_=corpus.evaluate(b)
            qa={key:{'difference':None if ma.get(key) is None else ma[key]-mb[key],**interval(boots[name][key]-boots[base][key])} for key in boots[name]}
            ca=costs(a,**point,adaptive=name!='fixed');cb=costs(b,**point,adaptive=False)
            samples=1-ca[draws].mean(axis=1)/cb[draws].mean(axis=1)
            comparisons[name+'_vs_'+base]={'quality':qa,'point_guardrails_pass':feasible(ma,mb),
                  'estimated_reduction':1-float(ca.mean()/cb.mean()),'conditional_reduction':interval(samples)}
    sensitivity=[]
    for name,a in vectors.items():
        if name in ('full','fixed'):continue
        for f,tau,h in itertools.product((0,.25,.5),(.25,.5,.75),(0,.005,.01,.02,.05)):
            c=costs(a,f,tau,h);b=costs(fixed,f,tau,h,False)
            denom=float(((a-1)+.2*a).mean());zero=float(costs(a,f,tau,0).mean())
            sensitivity.append({'point':name,'f':f,'tau':tau,'h':h,'mean_cost':float(c.mean()),'reduction_vs_full':1-float(c.mean()),
                'reduction_vs_fixed':1-float(c.mean()/b.mean()),'h_break_even_0':(1-zero)/denom if denom else None,
                'h_break_even_5pct':(.95-zero)/denom if denom else None})
    primary=comparisons['O1_vs_full'];fixedcmp=comparisons['O1_vs_fixed']
    quality=lambda r: all(r['quality'][k]['lower95']>=-margin for k,margin in [('bleu',.5),('chrf',1.)])
    point_pass=primary['estimated_reduction']>=.05 and fixedcmp['estimated_reduction']>0
    conditional_pass=point_pass and quality(primary) and quality(fixedcmp) and primary['conditional_reduction']['ci95'][0]>0 and fixedcmp['point_guardrails_pass']
    return {'comparisons':comparisons,'sensitivity':sensitivity,'bootstrap':{'resamples':10000,'seed':20261023 if split=='exploration' else 20261024,'reoptimized':False,'selection_uncertainty_accounted_for':False},
        'primary_point_thresholds_pass':point_pass,'primary_conditional_gate_pass':conditional_pass,
        'scenario_result':'supported_conditionally' if conditional_pass else 'not_supported_by_frozen_primary_search',
        'practical_headroom':'inconclusive','practical_reason':'No saved WMT arbitrary-exit generator/terminal/monitoring decomposition identifies the uncalibrated surrogate. No actual early-exit latency measured.'}

def timed_development(root,selected,rows,methods):
    active={(e['index'],e['identity']) for e in selected};observed={};offline={r['identity']:r for r in rows}
    with (root/'results/phase4/wmt14/4b_requests.jsonl').open('rb') as f:
        for line in f:
            m=HEADER.match(line);need(m is not None,'Timing identity header differs')
            need(m[3]==b'development' and (int(m[2]),m[1].decode()) in active,'Forbidden/non-timed request row')
            row=json.loads(line);key=(row['identity'],row['method'],row['repeat'])
            need(key not in observed and row['repeat'] in (0,1,2) and row['method'] in methods,'Timing duplicate/method/repeat mismatch')
            expected=simulate(methods[row['method']],offline[row['identity']]['levels'])
            need(row['exit_level']==expected and row['ids']==offline[row['identity']]['levels'][expected-1]['ids'],'Saved online/output replay differs')
            need(math.isfinite(row['wall_ms']) and row['wall_ms']>=0,'Invalid timing')
            observed[key]=row['wall_ms']
    need(len(observed)==len(selected)*4*3,'Timing coverage differs')
    summary={name:{'requests':len(selected)*3,'mean_ms':float(np.mean([v for (i,m,r),v in observed.items() if m==name])),
        'median_ms':float(np.median([v for (i,m,r),v in observed.items() if m==name])),
        'p95_ms':float(np.percentile([v for (i,m,r),v in observed.items() if m==name],95)),
        'identity_repeat_mean_ms':{e['identity']:float(np.mean([observed[e['identity'],name,r] for r in range(3)])) for e in selected}}
        for name in methods}
    draws=np.random.Generator(np.random.PCG64(20261024)).integers(0,len(selected),size=(10000,len(selected)))
    for name in methods:
        x=np.array([summary[name]['identity_repeat_mean_ms'][e['identity']] for e in selected])
        summary[name]['paired']={}
        for base in ('full','fixed'):
            y=np.array([summary[base]['identity_repeat_mean_ms'][e['identity']] for e in selected])
            summary[name]['paired'][base]={'relative_mean_reduction':1-float(x.mean()/y.mean()),**interval(1-x[draws].mean(axis=1)/y[draws].mean(axis=1))}
    return summary

def run(root,split):
    start=time.monotonic();deadline=start+7200;out=root/OUT/split
    need(not out.exists(),'Split already attempted: no silent rerun')
    lock=read(root/PLAN)
    if split=='development':
        release=read(root/OUT/'exploration_release.json');need(release['local_head']==release['github_main'],'Exploration not remote-verified')
        need(release['sources']==source_hashes(root),'Exploration source lock changed')
        need(sha(root/OUT/'exploration/result.json')==release['result_sha256'],'Exploration result changed')
        commit=release['local_head'];need(subprocess.check_output(['git','show',commit+':'+OUT+'/exploration/result.json'],cwd=root)==(root/OUT/'exploration/result.json').read_bytes(),'Released result differs from commit')
    out.mkdir(parents=True)
    status={'split':split,'status':'started','started_unix':time.time(),'new_model_calls':0,'new_fits':0,'new_final_outcomes':0,'sources':source_hashes(root)};save(out/'execution.json',status)
    try:
        hashes=provenance(root,lock);population=validate_population(read(root/'docs/partitions/wmt14-phase4.json'),read(root/INVENTORY));selected=population[split]
        rows,skipped=selective_rows(root/'results/phase4/wmt14/trajectories.jsonl',selected,split,population);validate_rows(rows)
        refs_by_index=StringRows((root/'data/wmt14/reference_translations.pickle').read_bytes()).select({e['index'] for e in selected})
        refs=[refs_by_index[r['index']] for r in rows]
        save(out/'access.json',{'active_split':split,'identities':selected,'references_materialized':len(refs),'rows_materialized':len(rows),'other_split_bodies_skipped':skipped,'final_outcomes_materialized':0})
        corpus=Corpus(rows,refs);full,_=corpus.evaluate(np.full(len(rows),11));fixed=[]
        for k in range(1,12):
            a=np.full(len(rows),k);metric=corpus.direct(a);fixed.append({'depth':k,'metrics':metric,'feasible':feasible(metric,full)})
        chosen=min(x['depth'] for x in fixed if x['feasible']);methods=read(root/'results/phase4/wmt14/policy_lock.json')['methods']
        baseline=[('fixed_'+str(k),np.full(len(rows),k)) for k in range(1,12)]
        replay={name:[simulate(methods[name],r['levels']) for r in rows] for name in ('stability','adaptive')}
        baseline.extend((name,np.array(a)) for name,a in replay.items());results={}
        for point in lock['search']['points']:
            name=point['name'];stream=(out/(name+'_search.jsonl')).open('x',encoding='utf-8')
            def emit(r):
                r.update(split=split,point=name);stream.write(json.dumps(r,allow_nan=False,separators=(',',':'))+'\n')
                if r['sequence']%100==0:stream.flush()
            def checkpoint(a,count,accepted):
                stream.flush();entry={'exits':[int(x) for x in a],'evaluations':count,'accepted_changes':accepted,'assignment_sha256':digest(a),'selection_status':'accepted_incumbent'}
                save(out/(name+'_checkpoint.json'),entry)
                with (out/(name+'_acceptances.jsonl')).open('a',encoding='utf-8') as accepted_stream:accepted_stream.write(json.dumps(entry)+'\n')
                need(sum(p.stat().st_size for p in (root/OUT).rglob('*') if p.is_file())<=512*1024*1024,'Storage cap exceeded')
            try:results[name]=search(corpus,point,baseline,emit,checkpoint,deadline=deadline)
            finally:stream.close()
            save(out/(name+'_assignment.json'),dict(results[name],identities=selected))
            print(split,name,results[name]['termination'],results[name]['evaluations'],'cost',results[name]['mean_cost'],flush=True)
        analysis=analyze(corpus,results,chosen,split,deadline)
        examples=[]
        if split=='exploration':
            metric=CHRF();a=results['O1']['exits'];changes=[metric.sentence_score(r['levels'][k-1]['text'],[ref]).score-metric.sentence_score(r['levels'][-1]['text'],[ref]).score for r,k,ref in zip(rows,a,refs)]
            indices=list(range(3))
            for sign in (1,-1):
                choices=[i for i,d in enumerate(changes) if sign*d>1e-12]
                if choices:indices.append(min(choices,key=lambda i:(-sign*changes[i],rows[i]['index'],a[i])))
            for i in dict.fromkeys(indices):examples.append({'identity':rows[i]['identity'],'index':rows[i]['index'],'exit_level':a[i],'reference':refs[i],'early_text':rows[i]['levels'][a[i]-1]['text'],'full_text':rows[i]['levels'][-1]['text'],'sentence_chrf_difference':changes[i]})
        timing=timed_development(root,selected,rows,methods) if split=='development' else None
        result={'split':split,'inputs':len(rows),'fixed_depths':fixed,'selected_fixed_depth':chosen,'saved_policy_exits':replay,'assignments':results,'analysis':analysis,'examples':examples,'saved_timing':timing,'corpus_parity_checks':corpus.parity_checks,'evidence_hashes':hashes,'sources':source_hashes(root),
            'environment':{'python':sys.version,'numpy':np.__version__,'sacrebleu':sacrebleu.__version__,'platform':sys.platform,'compute_threads':4},'certified_optimum':False,'new_model_calls':0,'new_fits':0,'new_final_outcomes':0}
        need(sum(v['evaluations'] for v in results.values())<=30000,'Split budget exceeded')
        need(time.monotonic()<deadline,'Split time cap exceeded')
        need(sum(p.stat().st_size for p in (root/OUT).rglob('*') if p.is_file())<=512*1024*1024,'Storage cap exceeded')
        need('torch' not in sys.modules,'Unexpected model library import')
        save(out/'result.json',result);status.update(status='complete',seconds=time.monotonic()-start,assignments_evaluated=sum(v['evaluations'] for v in results.values()),max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        need(status['max_rss_kib']<8*1024*1024,'Memory cap exceeded')
    except Exception as error:
        status.update(status='failed',error=repr(error),seconds=time.monotonic()-start);raise
    finally:save(out/'execution.json',status)
    print('Completed',split,'saved-data analysis; zero model work.',flush=True)
