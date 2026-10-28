"""One prospective exact math review; zero Monte Carlo and model work."""
import argparse,hashlib,json,os,resource,signal,subprocess,sys,time,zipfile
from pathlib import Path
os.environ['PYTHONDONTWRITEBYTECODE']='1'
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'docs/studies/quality-tolerant';OUT=ROOT/'results/quality_tolerant/final_math_review'
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf-8',newline='\n') as f:json.dump(v,f,indent=2,allow_nan=False);f.write('\n')
def git(*args):return subprocess.check_output(['git.exe',*args],cwd=ROOT,text=True,timeout=30).strip()
def verify():
    r=read(OUT/'execution.json');lock=read(BASE/'final-math-review-lock.json');checks=0
    for key,root in [('source_sha256',ROOT),('protected_sha256',ROOT),('artifact_sha256',OUT)]:
        for p,h in r[key].items():
            if sha(root/p)!=h:raise RuntimeError('Hash changed: '+p)
            checks+=1
    for k,n in r['counts'].items():
        if n>lock['limits'][k]:raise AssertionError('Counter exceeded '+k)
    d=read(OUT/'decision.json')
    if d['Q0_passed'] or d['Q2_authorized'] or d['reserved_outputs_released']:raise AssertionError('False scientific release')
    if r['MC_datasets'] or r['model_requests'] or r['corpus_or_reference_body_decodes']:raise AssertionError('Forbidden work')
    print(json.dumps(dict(verified=True,hash_checks=checks,new_profile_decodes=0,calculation_replays=0,counts=r['counts'])))
def run():
    start=time.monotonic();lock=read(BASE/'final-math-review-lock.json');limits=lock['limits']
    resource.setrlimit(resource.RLIMIT_AS,(2<<30,2<<30));resource.setrlimit(resource.RLIMIT_CPU,(1200,1200))
    def expired(*_):raise TimeoutError('Frozen wall cap')
    signal.signal(signal.SIGALRM,expired);signal.alarm(1800)
    head=git('rev-parse','HEAD');remote=git('ls-remote','origin','refs/heads/main').split()[0]
    if head!=remote or git('branch','--show-current')!='main' or git('status','--porcelain=v1','--untracked-files=all'):raise RuntimeError('Require clean matching live main')
    frozen=read(BASE/'final-math-review-source-lock.json');sources=dict(frozen['source_sha256']);sources['docs/studies/quality-tolerant/final-math-review-source-lock.json']=sha(BASE/'final-math-review-source-lock.json')
    for p,h in {**sources,**frozen['protected_sha256']}.items():
        if sha(ROOT/p)!=h:raise RuntimeError('Frozen input changed: '+p)
    save(OUT/'started.json',dict(source_commit=head,verified_live_main=remote,scope=lock['stage']))
    counts={k:0 for k in ['profile_decodes','profile_vectors','weight_values','waterfill_evaluations','top_k_evaluations','grid_points','grid_comparisons']};phase='invented_tests'
    try:
        with zipfile.ZipFile(OUT/'execution-sources.zip','x',compression=zipfile.ZIP_DEFLATED) as z:
            for p in sources:z.write(ROOT/p,p)
        test=subprocess.run([sys.executable,'-m','pytest','tests/test_final_math_review.py','-q','-p','no:cacheprovider','--junitxml=results/quality_tolerant/final_math_review/focused-tests.xml'],cwd=ROOT,capture_output=True,text=True,timeout=1800)
        (OUT/'test-output.txt').write_text(test.stdout+test.stderr,encoding='utf-8')
        if test.returncode:raise RuntimeError('Deterministic invented tests failed; no profile access')
        sys.path.insert(0,str(ROOT/'src'))
        from anytime_ncm.final_math_review import extract_profiles,review_profile,deterministic_grids,target_counterexamples,record,F,need
        with (OUT/'ledger.jsonl').open('x',encoding='utf-8') as stream:
            def charge(k,n):
                if type(n)is not int or n<=0 or counts[k]+n>limits[k]:raise RuntimeError('Allocation exhausted '+k)
                counts[k]+=n;stream.write(json.dumps(dict(kind=k,amount=n,total=counts[k]))+'\n')
                if sum(counts.values())%1024==0:stream.flush()
                if time.monotonic()-start>1800:raise TimeoutError('Deadline')
            phase='exact_validation';save(OUT/'deterministic-validation.json',dict(grids=deterministic_grids(charge),target_counterexamples=target_counterexamples(),MC_datasets=0))
            phase='metadata_profile_selection'
            path=ROOT/lock['profile_path']
            if path.stat().st_size>16<<20 or sha(path)!=lock['profile_sha256']:raise RuntimeError('Pinned profile file differs')
            charge('profile_decodes',1);profiles=extract_profiles(path.read_bytes());summary=read(ROOT/lock['aggregate_path']);results={};histograms={}
            for role in ['development','confirmation']:
                data=profiles[role];expected=summary['roles'][role]
                need(len(data['inputs'])==expected['components'] and sum(data['inputs'])==expected['inputs'],'Input profile/aggregate parity')
                need(sum(data['numeric'])==expected['numeric_covered'] and sum(x>0 for x in data['numeric'])==expected['covered_components'],'Numeric profile/aggregate parity')
                for endpoint in ['numeric','inputs']:
                    charge('profile_vectors',1);charge('weight_values',len(data[endpoint]));name=role+'_'+endpoint
                    results[name]=review_profile(data[endpoint],charge)
                    histograms[name]=results[name]['unlabelled_count_histogram']
            del profiles
            save(OUT/'weight-distributions.json',dict(profiles=histograms,component_identities_exported=False,per_input_reference_flags_decoded=False))
            save(OUT/'exact-results.json',results)
        phase='decision';confirmation={k:v for k,v in results.items() if k.startswith('confirmation_')};blocked=[]
        for name,value in confirmation.items():
            outside=next(c for c in value['cases'] if F(c['delta']['numerator'])/F(c['delta']['denominator'])==F(201,10000))
            if outside['exceeds_primary_alpha']:blocked.append(name)
        status='close_current_zero_loss_confirmatory_route' if blocked else 'zero_event_obstruction_removed_full_gate_still_unvalidated'
        save(OUT/'decision.json',dict(status=status,confirmation_zero_event_obstructions=blocked,full_weight_zero_event_optimum_reviewed=True,scope='Independent bounded heterogeneous component model, fixed metadata, all-zero certification; not universal impossibility for all signed observations/policies/targets',Q0_passed=False,Q2_authorized=False,reserved_outputs_released=False,model_benefit_evidence_added=False,unconditional_population_ratio_guarantee=False,operational_concentration_failure_preserved=True,next_action='End this final bounded review; no further execution follows. Any materially different inference model/population is a new study, not a repaired historical gate.'))
        for p,h in frozen['protected_sha256'].items():
            if sha(ROOT/p)!=h:raise RuntimeError('Protected historical evidence changed '+p)
        if any(m=='torch' or m.startswith('torch.') or m=='transformers' or m.startswith('transformers.') for m in sys.modules):raise RuntimeError('Forbidden model framework')
        storage=sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file());rss=max(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)*1024
        if storage>16<<20 or rss>2<<30:raise RuntimeError('Storage/RSS cap')
        save(OUT/'execution.json',dict(status='complete',source_commit=head,verified_live_main_before_execution=remote,wall_seconds=time.monotonic()-start,max_rss_bytes=rss,counts=counts,MC_datasets=0,bootstrap_draws=0,model_requests=0,corpus_or_reference_body_decodes=0,target_encodings=0,downloads=0,dollars=0,preparation_reporting_charge_seconds=7200,charged_seconds=7200+time.monotonic()-start,source_sha256=sources,protected_sha256=frozen['protected_sha256'],artifact_sha256={p.name:sha(p) for p in OUT.iterdir() if p.is_file()},python=sys.version))
        verify()
    except BaseException as error:
        save(OUT/'failure.json',dict(phase=phase,error=repr(error),counts=counts,retry_authorized=False));raise
    finally:signal.alarm(0)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['run','verify']);args=p.parse_args();run() if args.action=='run' else verify()
