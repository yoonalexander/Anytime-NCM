"""Execute once after the exploratory Q1 exception lock is pushed to main."""
import os
for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='1'
os.environ['PYTHONDONTWRITEBYTECODE']='1'
import argparse,hashlib,json,resource,signal,subprocess,sys,time,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/quality_tolerant/q1'
BASE=ROOT/'docs/studies/quality-tolerant'
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()
def read(p):return json.loads(p.read_text())
def save(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf-8',newline='\n') as f:json.dump(v,f,indent=2,allow_nan=False);f.write('\n')
def git(*a):return subprocess.check_output(['git.exe',*a],cwd=ROOT,text=True,timeout=30).strip()
def verify():
    r=read(OUT/'execution.json');lock=read(BASE/'q1-exploratory-lock.json');n=0
    for k,base in [('source_sha256',ROOT),('protected_sha256',ROOT),('artifact_sha256',OUT)]:
        for p,h in r[k].items():
            if sha(base/p)!=h:raise RuntimeError('Changed hash: '+p)
            n+=1
    for k,v in r['counts'].items():
        if v>lock['limits'][k]:raise AssertionError('Count exceeded')
    if r['status']!='complete' or r['max_rss_bytes']>lock['limits']['memory_bytes'] or r['wall_seconds']>lock['limits']['wall_seconds']:raise AssertionError('Execution status/resources')
    decision=read(OUT/'decision.json')
    if decision['Q0_passed'] or decision['Q2_authorized'] or decision['reserved_outputs_released']:raise AssertionError('Invalid phase release')
    print(json.dumps(dict(verified=True,hash_checks=n,new_outcome_body_reads=0,search_replays=0,counts=r['counts'])))
def run():
    start=time.monotonic();lock=read(BASE/'q1-exploratory-lock.json');limits=lock['limits'];counts={k:0 for k in ('reference_materializations','trajectory_bodies','request_bodies','assignment_evaluations','direct_parity_checks')}
    resource.setrlimit(resource.RLIMIT_AS,(limits['memory_bytes'],limits['memory_bytes']));resource.setrlimit(resource.RLIMIT_CPU,(limits['cpu_seconds'],limits['cpu_seconds']))
    def expired(*_):raise TimeoutError('Frozen Q1 wall cap')
    signal.signal(signal.SIGALRM,expired);signal.alarm(limits['wall_seconds'])
    def check():
        if time.monotonic()-start>limits['wall_seconds']:raise TimeoutError('Wall cap')
        if sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file())>limits['storage_bytes']:raise RuntimeError('Storage cap')
    head=git('rev-parse','HEAD');remote=git('ls-remote','origin','refs/heads/main').split()[0]
    if head!=remote or git('branch','--show-current')!='main' or git('status','--porcelain=v1','--untracked-files=all'):raise RuntimeError('Need clean live-equal main')
    frozen=read(BASE/'q1-exploratory-source-lock.json');sources=dict(frozen['source_sha256']);sources['docs/studies/quality-tolerant/q1-exploratory-source-lock.json']=sha(BASE/'q1-exploratory-source-lock.json')
    for p,h in sources.items():
        if sha(ROOT/p)!=h:raise RuntimeError('Source lock changed: '+p)
    protected=frozen['protected_sha256']
    for p,h in protected.items():
        if sha(ROOT/p)!=h:raise RuntimeError('Historical evidence changed: '+p)
    save(OUT/'started.json',dict(source_commit=head,verified_live_main=remote,exception=True,counts=counts))
    phase='synthetic_tests'
    try:
        with zipfile.ZipFile(OUT/'execution-sources.zip','x',compression=zipfile.ZIP_DEFLATED) as z:
            for p in sources:z.write(ROOT/p,p)
        test=subprocess.run([sys.executable,'-m','pytest','tests/test_q1_exploratory.py','tests/test_stronger_s1.py','-q','-p','no:cacheprovider','--junitxml=results/quality_tolerant/q1/focused-tests.xml'],cwd=ROOT,capture_output=True,text=True,timeout=limits['wall_seconds'])
        (OUT/'test-output.txt').write_text(test.stdout+test.stderr)
        if test.returncode:raise RuntimeError('Focused synthetic tests failed; no outcome access')
        phase='saved_data';sys.path.insert(0,str(ROOT/'src'))
        import numpy as np,sacrebleu
        from anytime_ncm.q1_exploratory import read_rows,Corpus,exact_depths,timing_cells,SCHEDULES,costs,search,describe,feasible
        from anytime_ncm.wmt_data import StringRows
        if sacrebleu.__version__!='2.6.0':raise RuntimeError('Metric version drift')
        inv=read(ROOT/'docs/studies/stronger-research-inventory.json');e0=read(ROOT/'results/evidence_gaps/e0/input-manifest.json');parent=read(ROOT/'docs/partitions/wmt14-phase4.json')
        groups={p:inv['s1_population'][p] for p in ('exploration','development')}
        for p,n in [('exploration',128),('development',64)]:
            if groups[p]!=sorted(parent['partitions'][p],key=lambda e:e['index'])[:n]:raise RuntimeError('S1 allowlist drift')
        groups['E2_audit']=sorted(e0['roles']['E2_audit'],key=lambda e:e['index'])
        allowed={e['index'] for es in groups.values() for e in es}
        if len(allowed)!=448:raise RuntimeError('Population overlap/count')
        save(OUT/'access-receipt.json',dict(source_commit=head,permitted_groups={p:len(es) for p,es in groups.items()},references=448,consumed_only=True,E3_E4_outputs_released=False,original_final_outputs_released=False))
        with (OUT/'ledger.jsonl').open('x') as stream:
            def charge(k,n):
                check()
                if counts[k]+n>limits[k]:raise RuntimeError('Budget exhausted '+k)
                counts[k]+=n;stream.write(json.dumps(dict(kind=k,amount=n,total=counts[k]))+'\n');stream.flush()
            charge('reference_materializations',448)
            refs=StringRows((ROOT/'data/wmt14/reference_translations.pickle').read_bytes()).select(allowed)
            rows=read_rows(ROOT/'results/phase4/wmt14/trajectories.jsonl',{p:groups[p] for p in ('exploration','development')},charge)
            rows.update(read_rows(ROOT/'results/evidence_gaps/e2/trajectories.jsonl',{'E2_audit':groups['E2_audit']},charge))
            def records():
                for b in (0,1):
                    with (ROOT/f'results/evidence_gaps/e2/{b}-requests.jsonl').open('rb') as f:
                        for line in f:
                            charge('request_bodies',1);r=json.loads(line)
                            if r['block']!=b:raise RuntimeError('Request file/block mismatch')
                            yield r
            cells,warm=timing_cells(groups['E2_audit'],rows['E2_audit'],records(),e0['E1_existing_exploration'])
            if warm!=120 or counts['request_bodies']!=12408:raise RuntimeError('Request/warmup count')
            exact=exact_depths(rows['E2_audit']);chosen=np.stack([cells[i,:,:,int(d)] for i,d in enumerate(exact)])
            denom=int(sum(exact-1))
            if denom<=0:raise RuntimeError('Observation proxy unidentified')
            raw=float((cells[:,:,:,0].mean(axis=(1,2))-chosen.mean(axis=(1,2))).sum()/denom);h=max(0.,raw)
            profile=cells[:,:,:,1:].mean(axis=(0,1,2))
            save(OUT/'cost-calibration.json',dict(terminal_depth_mean_ms=profile.tolist(),observation_step_proxy_ms=h,unclipped_proxy_ms=raw,extra_observations=denom,dense_exact_mean_ms=float(cells[:,:,:,0].mean()),matched_exact_terminal_mean_ms=float(chosen.mean()),warmup_records=warm,isolated_component_measurement=False,integrated_online_measurement=False))
            result={}
            for p,rs in rows.items():
                corpus=Corpus(rs,[refs[r['index']] for r in rs]);expected={'exploration':31,'development':13,'E2_audit':48}[p]
                if int(sum(corpus.covered))!=expected:raise RuntimeError('Coverage audit parity')
                full=None;baselines={};fixedcost=[]
                for d in (11,*range(1,11)):
                    charge('assignment_evaluations',1);a=[d]*corpus.n;charge('direct_parity_checks',1);s=corpus.direct(a)
                    if d==11:full=s
                    baselines[f'fixed:{d}']=dict(metrics=s,losses=__import__('anytime_ncm.q1_exploratory',fromlist=['losses']).losses(s,full),point_quality_pass=feasible(s,full),terminal_profile_ms=float(profile[d-1]))
                    if feasible(s,full):fixedcost.append(float(profile[d-1]))
                a=exact_depths(rs);charge('assignment_evaluations',1);charge('direct_parity_checks',1);corpus.direct(a)
                baselines['earliest_exact']=describe(corpus,a,full,'terminal_oracle',profile,h,cells if p=='E2_audit' else None)
                runs={}
                for schedule in SCHEDULES:
                    def emit(event):
                        charge('assignment_evaluations',1);stream.write(json.dumps(dict(cohort=p,schedule=schedule,**event))+'\n')
                    charge('direct_parity_checks',1)
                    run=search(corpus,schedule,profile,h,emit,cap=lock['search_cap'],passes=lock['passes']);a=run['exits']
                    run.update(describe(corpus,a,full,schedule,profile,h,cells if p=='E2_audit' else None))
                    run['projected_improvement_over_point_feasible_fixed']=float(1-run['projected_mean_ms']/min(fixedcost))
                    runs[schedule]=run
                result[p]=dict(n=corpus.n,numeric_covered=expected,baselines=baselines,searches=runs,cost_transfer_uncalibrated=p!='E2_audit')
            save(OUT/'results.json',result)
        qualified=[k for k,v in result['E2_audit']['searches'].items() if k!='terminal_oracle' and v['point_quality_pass'] and v['projected_full_savings']>=.05 and v['projected_improvement_over_point_feasible_fixed']>0]
        save(OUT/'decision.json',dict(status='exploratory_headroom_found' if qualified else 'bounded_search_insufficient_headroom',qualifying_E2_sparse_schedules=qualified,Q0_passed=False,Q2_authorized=False,reserved_outputs_released=False,independent_confirmation=False,integrated_online_speedup_demonstrated=False,statistically_excluded_fixed_depths=[],certified_optimum=False,next_step='Separate population and cluster-aware design only if pursued; no automatic execution.'))
        phase='preservation'
        for p,h0 in protected.items():
            if sha(ROOT/p)!=h0:raise RuntimeError('Historical file changed: '+p)
        if any(m=='torch' or m.startswith('torch.') or m=='transformers' or m.startswith('transformers.') for m in sys.modules):raise RuntimeError('Model import')
        check();rss=max(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)*1024
        if rss>limits['memory_bytes']:raise RuntimeError('RSS cap')
        save(OUT/'execution.json',dict(status='complete',source_commit=head,verified_live_main_before_access=remote,counts=counts,wall_seconds=time.monotonic()-start,max_rss_bytes=rss,preparation_reporting_charge_seconds=7200,charged_seconds=7200+time.monotonic()-start,cost_dollars=0,model_requests=0,new_fits=0,bootstrap_draws=0,reserved_output_bodies=0,source_sha256=sources,protected_sha256=protected,artifact_sha256={p.name:sha(p) for p in OUT.iterdir() if p.is_file()},python=sys.version,numpy=np.__version__,sacrebleu=sacrebleu.__version__))
        verify()
    except BaseException as e:
        save(OUT/'failure.json',dict(phase=phase,error=repr(e),counts=counts,retry_authorized=False));raise
    finally:signal.alarm(0)
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['run','verify']);args=parser.parse_args()
    run() if args.action=='run' else verify()
