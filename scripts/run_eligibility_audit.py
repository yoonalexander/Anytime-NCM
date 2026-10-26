"""One locked metadata + synthetic methods audit; no model execution."""
import os
for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','RAYON_NUM_THREADS'):os.environ[k]='1'
os.environ['TOKENIZERS_PARALLELISM']='false'
import argparse,gzip,hashlib,io,json,resource,signal,subprocess,sys,tarfile,time,urllib.request,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/quality_tolerant/eligibility_audit';PRIVATE=ROOT/'data/wmt_metadata_audit_20261026';BASE=ROOT/'docs/studies/quality-tolerant'
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf-8',newline='\n') as f:json.dump(v,f,indent=2,allow_nan=False);f.write('\n')
def git(*a):return subprocess.check_output(['git.exe',*a],cwd=ROOT,text=True,timeout=30).strip()

def verify():
    e=read(OUT/'execution.json');lock=read(BASE/'eligibility-audit-lock.json');checks=0
    for name,root in [('source_sha256',ROOT),('protected_sha256',ROOT),('artifact_sha256',OUT)]:
        for p,h in e[name].items():
            if sha(root/p)!=h:raise RuntimeError('Changed hash '+p)
            checks+=1
    for k,n in e['counts'].items():
        if n>lock['limits'][k]:raise AssertionError('Count exceeded '+k)
    if e['counts']['synthetic_datasets']!=48000 or not read(OUT/'method-results.json')['null_sanity_checks_passed']:raise AssertionError('Methods audit incomplete/invalid')
    d=read(OUT/'decision.json')
    if d['Q2_authorized'] or d['Q0_passed'] or d['reserved_outputs_released']:raise AssertionError('Scientific gate falsely released')
    if e['model_requests'] or e['target_encodings'] or e['real_outcome_body_reads']:raise AssertionError('Forbidden work')
    print(json.dumps(dict(verified=True,hash_checks=checks,new_dataset_body_decodes=0,simulation_replays=0,status=e['status'],counts=e['counts'])))

def run():
    start=time.monotonic();lock=read(BASE/'eligibility-audit-lock.json');limits=lock['limits']
    import importlib.metadata
    if any(importlib.metadata.version(k)!=v for k,v in lock['versions'].items()):raise RuntimeError('Pinned package version drift')
    resource.setrlimit(resource.RLIMIT_AS,(2<<30,4<<30));resource.setrlimit(resource.RLIMIT_CPU,(1200,1200))
    def expired(*a):raise TimeoutError('Frozen phase deadline')
    signal.signal(signal.SIGALRM,expired);signal.alarm(1800)
    head=git('rev-parse','HEAD');remote=git('ls-remote','origin','refs/heads/main').split()[0]
    if head!=remote or git('branch','--show-current')!='main' or git('status','--porcelain=v1','--untracked-files=all'):raise RuntimeError('Need clean matching live main')
    frozen=read(BASE/'eligibility-audit-source-lock.json');sources=dict(frozen['source_sha256']);sources['docs/studies/quality-tolerant/eligibility-audit-source-lock.json']=sha(BASE/'eligibility-audit-source-lock.json')
    for absolute,h in frozen.get('installed_sha256',{}).items():
        if sha(Path(absolute))!=h:raise RuntimeError('Installed metadata source changed')
    for p,h in {**sources,**frozen['protected_sha256']}.items():
        if sha(ROOT/p)!=h:raise RuntimeError('Frozen provenance changed: '+p)
    save(OUT/'started.json',dict(source_commit=head,verified_live_main=remote,scope=lock['stage']))
    if PRIVATE.exists():raise RuntimeError('Private audit directory already exists; no silent reuse')
    counts={k:0 for k in limits if k not in ('metadata_wall_seconds','methods_wall_seconds','memory_bytes','public_storage_bytes','private_storage_bytes')};phase='synthetic_tests';unit_start=start
    ledger=(OUT/'ledger.jsonl').open('x',encoding='utf-8')
    def check():
        if time.monotonic()-unit_start>1800:raise TimeoutError('Unit wall cap')
        for directory,cap in [(OUT,limits['public_storage_bytes']),(PRIVATE,limits['private_storage_bytes'])]:
            if sum(p.stat().st_size for p in directory.rglob('*') if p.is_file())>cap:raise RuntimeError('Storage cap')
    def charge(k,n):
        if type(n) is not int or n<=0 or k not in counts or counts[k]+n>limits[k]:raise RuntimeError('Invalid/exhausted allocation '+k)
        counts[k]+=n;ledger.write(json.dumps(dict(kind=k,amount=n,total=counts[k]))+'\n')
        if counts[k]%1024==0:ledger.flush();check()
    try:
        with zipfile.ZipFile(OUT/'execution-sources.zip','x',compression=zipfile.ZIP_DEFLATED) as z:
            for p in sources:z.write(ROOT/p,p)
            for i,p in enumerate(frozen.get('installed_sha256',{})):z.write(p,f'installed/{i}-'+Path(p).name)
        tests=subprocess.run([sys.executable,'-m','pytest','tests/test_eligibility_audit.py','-q','-p','no:cacheprovider','--junitxml=results/quality_tolerant/eligibility_audit/focused-tests.xml'],cwd=ROOT,capture_output=True,text=True,timeout=1800)
        (OUT/'test-output.txt').write_text(tests.stdout+tests.stderr,encoding='utf-8')
        if tests.returncode:raise RuntimeError('Synthetic tests failed before data access')
        sys.path.insert(0,str(ROOT/'src'))
        import numpy as np,scipy
        from anytime_ncm.eligibility_audit import method_scenarios,parse_sgm,inventory,hash_text,normalized,identity,zero_upper
        phase='synthetic_methods';methods=method_scenarios(charge);save(OUT/'method-results.json',methods)
        if not methods['null_sanity_checks_passed']:raise RuntimeError('Frozen null checks failed; no acquisition')
        methods_seconds=time.monotonic()-start;check();phase='metadata';unit_start=time.monotonic();signal.alarm(1800);resource.setrlimit(resource.RLIMIT_AS,(4<<30,4<<30));PRIVATE.mkdir(parents=True,exist_ok=False)
        metadata_status='not_completed';metadata_error=None;acquisitions=[];aggregate=None;rows=[];private_artifacts={}
        try:
            from tokenizers import Tokenizer
            from anytime_ncm.wmt_data import StringRows
            tokenizer=Tokenizer.from_file(str(ROOT/'artifacts/wmt14/text_tokenizer/tokenizer.json'))
            if tokenizer.padding is not None or tokenizer.truncation is not None:raise RuntimeError('Unexpected tokenizer configuration')
            parent=read(ROOT/'docs/partitions/wmt14-phase4.json');old_entries={e['index']:e['identity'] for es in parent['partitions'].values() for e in es}
            old_docs={x['document_sha256'] for x in read(ROOT/'results/quality_tolerant/q0_population/document-map.json')}
            charge('historical_source_materializations',3003);old=StringRows((ROOT/'data/wmt14/sources.pickle').read_bytes()).select(set(range(3003)))
            charge('source_tokenizations',3003);encoded=tokenizer.encode_batch([old[i] for i in range(3003)],add_special_tokens=True)
            def prefix(e):return identity((e.ids[:96]+[151643]*96)[:96])
            if len(old_entries)!=3003 or any(prefix(e)!=old_entries[i] for i,e in enumerate(encoded)):raise RuntimeError('Bare tokenizer/historical effective-prefix parity failed')
            historical=dict(raw_hash={hash_text(x) for x in old.values()},normalized_hash={hash_text(normalized(x)) for x in old.values()},prefix_hash=set(old_entries.values()),doc_hash=old_docs)
            del old,encoded
            save(OUT/'access-receipt.json',dict(source_commit=head,authorization='User approved bounded data-eligibility and statistical-method audit',candidate_years=list(range(2015,2021)),references='Machine-only cue presence and alignment; no model scoring; flags private',source_tokenization_only=True,historical_source_prefix_parity=3003,historical_references_read=0,reserved_model_outputs_released=False))
            class Redirect(urllib.request.HTTPRedirectHandler):
                def redirect_request(self,req,fp,code,msg,headers,newurl):
                    from urllib.parse import urlparse
                    p=urlparse(newurl)
                    if p.scheme!='https' or p.hostname not in ('statmt.org','www.statmt.org','data.statmt.org') or p.path!=urllib.parse.urlparse(req.full_url).path:raise RuntimeError('Unapproved redirect')
                    charge('GETs',1);return super().redirect_request(req,fp,code,msg,headers,newurl)
            opener=urllib.request.build_opener(Redirect)
            for item in lock['archives']:
                check();year=item['year'];archive=PRIVATE/f'{year}.tgz';charge('GETs',1)
                request=urllib.request.Request(item['url'],headers={'User-Agent':'Anytime-NCM-bounded-metadata-audit','Accept-Encoding':'identity'})
                with opener.open(request,timeout=30) as response,archive.open('xb') as f:
                    length=response.headers.get('Content-Length')
                    if length and int(length)>limits['download_bytes']-counts['download_bytes']:raise RuntimeError('Content-Length cap')
                    while True:
                        remaining=limits['download_bytes']-counts['download_bytes']
                        if remaining<=0:raise RuntimeError('Transport budget exhausted before EOF')
                        b=response.read(min(65536,remaining))
                        if not b:break
                        charge('download_bytes',len(b));f.write(b)
                if hashlib.md5(archive.read_bytes(),usedforsecurity=False).hexdigest()!=item['md5']:raise RuntimeError('Pinned archive MD5 differs')
                remaining=limits['decompressed_bytes']-counts['decompressed_bytes']
                if remaining<=0:raise RuntimeError('Decompression budget exhausted')
                with gzip.open(archive,'rb') as f:payload=f.read(remaining)
                charge('decompressed_bytes',len(payload))
                if len(payload)==remaining:raise RuntimeError('Decompression cap boundary; no extra probe')
                members={}
                with tarfile.open(fileobj=io.BytesIO(payload),mode='r:') as tar:
                    for kind,name in [('source',item['source_member']),('reference',item['reference_member'])]:
                        matches=[m for m in tar.getmembers() if m.name==name]
                        if len(matches)!=1 or not matches[0].isfile() or matches[0].size>16<<20:raise RuntimeError('Missing/oversize/ambiguous allowed member')
                        stream=tar.extractfile(matches[0]);members[kind]=stream.read();stream.close()
                del payload
                src=parse_sgm(members['source'],'source',charge);ref=parse_sgm(members['reference'],'reference',charge)
                if [(x['doc'],x['seg']) for x in src]!=[(x['doc'],x['seg']) for x in ref]:raise RuntimeError('Source/reference document/segment alignment')
                charge('source_tokenizations',len(src));encoded=tokenizer.encode_batch([r['text'] for r in src],add_special_tokens=True)
                for i,(s,r,e) in enumerate(zip(src,ref,encoded,strict=True)):
                    rows.append(dict(year=year,index=i,doc_hash=hash_text(html_unescape(s['doc'])),raw_hash=hash_text(s['text']),normalized_hash=hash_text(normalized(s['text'])),prefix_hash=prefix(e),covered=r['covered'],origlang=s['origlang'],story_hash=hash_text(html_unescape(s['doc'])) if s['doc'].startswith(('https://','http://')) else None))
                acquisitions.append(dict(year=year,url=item['url'],archive_sha256=sha(archive),archive_md5=item['md5'],archive_bytes=archive.stat().st_size,source_member=item['source_member'],reference_member=item['reference_member'],source_sha256=hashlib.sha256(members['source']).hexdigest(),reference_sha256=hashlib.sha256(members['reference']).hexdigest(),rows=len(src)))
                del src,ref,encoded,members
            aggregate,manifest,private=inventory(rows,historical)
            save(OUT/'population-summary.json',aggregate);save(OUT/'split-manifest.json',manifest)
            save(PRIVATE/'private-metadata.json',dict(rows=rows,components=private['components'],profiles=private['profiles']))
            private_artifacts={p.name:sha(p) for p in PRIVATE.iterdir() if p.is_file()}
            metadata_status='six_year_frame_audited'
        except Exception as error:
            metadata_error=repr(error);save(OUT/'metadata-failure.json',dict(stage=phase,error=metadata_error,completed_archives=len(acquisitions),new_source_rows_materialized=counts['source_materializations'],new_reference_rows_materialized=counts['reference_materializations'],retry_authorized=False))
            metadata_status='blocked_incomplete_audit'
        private_artifacts={p.name:sha(p) for p in PRIVATE.iterdir() if p.is_file()}
        save(OUT/'acquisition.json',dict(status=metadata_status,archives=acquisitions,error=metadata_error,raw_corpus_committed=False,other_member_body_decodes=0))
        ledger.flush();ledger.close();check()
        power_cases=[dict(J=s['J'],shape=s['shape'],lower99=s['joint_two_cue_NI_and_precision']['ci99'][0]) for s in methods['scenarios'] if s['risk']==.005]
        save(OUT/'decision.json',dict(status='audit_complete_no_model_release',method_implementation_validated_conditionally=True,conditional_independent_cluster_bound=True,metadata_status=metadata_status,operational_metadata_screen_passed=None if aggregate is None else aggregate['operational_screen_passed'],method_power_scenarios=power_cases,whole_study_power_established=False,population_independence_established=False,Q0_passed=False,Q2_authorized=False,reserved_outputs_released=False,model_benefit_evidence_added=False))
        for p,h in frozen['protected_sha256'].items():
            if sha(ROOT/p)!=h:raise RuntimeError('Historical evidence changed '+p)
        if any(m=='torch' or m.startswith('torch.') or m=='transformers' or m.startswith('transformers.') for m in sys.modules):raise RuntimeError('Model framework import')
        rss=max(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)*1024
        check()
        save(OUT/'execution.json',dict(status='audit_complete',source_commit=head,verified_live_main_before_access=remote,counts=counts,methods_seconds=methods_seconds,metadata_seconds=time.monotonic()-unit_start,wall_seconds=time.monotonic()-start,max_rss_bytes=rss,cost_dollars=0,model_requests=0,target_encodings=0,real_outcome_body_reads=0,bootstrap_draws=0,source_sha256=sources,protected_sha256=frozen['protected_sha256'],artifact_sha256={p.name:sha(p) for p in OUT.iterdir() if p.is_file()},private_artifact_sha256=private_artifacts,python=sys.version,numpy=np.__version__,scipy=scipy.__version__))
        verify()
    except BaseException as error:
        if not ledger.closed:ledger.flush();ledger.close()
        save(OUT/'failure.json',dict(phase=phase,error=repr(error),counts=counts,retry_authorized=False));raise
    finally:signal.alarm(0)

def html_unescape(s):
    import html
    return html.unescape(s)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['run','verify']);a=p.parse_args();run() if a.action=='run' else verify()
