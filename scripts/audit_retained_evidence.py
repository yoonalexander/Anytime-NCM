"""Read-only audit of retained research hashes plus explicitly archived metadata."""
import argparse,hashlib,json,subprocess,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
C=ROOT/'results/quality_tolerant/campaign_20261029'
MUTABLE_METADATA={'README.md','ROADMAP.md','RESEARCH_ROADMAP.md','AGENTS.md','.gitattributes','pyproject.toml','src/anytime_ncm/__init__.py','src/anytime_ncm/__main__.py','src/anytime_ncm/cli.py'}
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda:f.read(1<<20),b''):h.update(block)
    return h.hexdigest()
def resolve_expected(root,originals,path,expected):
    if Path(path).is_absolute() or '..' in Path(path).parts:raise ValueError('Unsafe evidence path')
    target=(root/path).resolve()
    if not target.is_relative_to(root.resolve()):raise ValueError('Evidence path escaped checkout')
    if target.is_file() and sha(target)==expected:return 'current'
    if path in MUTABLE_METADATA and path in originals and hashlib.sha256(originals[path]).hexdigest()==expected:return 'archived_metadata'
    raise ValueError('Changed/missing research artifact: '+path)

def audit(private=False):
    history=ROOT/'docs/history/pre-delivery-03e3e70';m=read(history/'manifest.json');archive=history/'original-bytes.zip'
    if set(m['files'])!=MUTABLE_METADATA:raise ValueError('Unexpected historical metadata allowlist')
    if sha(archive)!=m['binary_archive_sha256']:raise ValueError('Historical byte archive changed')
    with zipfile.ZipFile(archive) as z:
        originals={p:z.read(v['byte_member']) for p,v in m['files'].items()}
    if any(hashlib.sha256(originals[p]).hexdigest()!=v['sha256'] for p,v in m['files'].items()):raise ValueError('Invalid archived metadata')
    resolved=set();current=set()
    def check(path,expected):
        (current if resolve_expected(ROOT,originals,path,expected)=='current' else resolved).add(path)
    source=read(ROOT/'docs/studies/quality-tolerant/campaign-closeout-source-lock.json')
    pairs=set()
    for field in ('source_sha256','protected_sha256'):
        pairs.update(source[field].items())
    for p,h in sorted(pairs):check(p,h)
    if private:
        for p,h in source['private_sha256'].items():check(p,h)
    lock=read(ROOT/'docs/studies/quality-tolerant/campaign-20261029-lock.json');totals={k:0 for k in lock['ceilings']};phases=[];artifacts=0
    for path in sorted((C/'accounting').glob('phase-*.json')):
        a=read(path);e=C/a['evidence_path'];check(e.relative_to(ROOT).as_posix(),a['evidence_sha256']);v=read(e)
        if a['usage']!=v['campaign_usage']:raise ValueError('Ledger/evidence mismatch')
        for k,value in a['usage'].items():totals[k]+=value
        for rel,h in v.get('artifact_sha256',{}).items():check((e.parent/rel).relative_to(ROOT).as_posix(),h);artifacts+=1
        phases.append(a['phase'])
    if len(phases)!=13 or any(totals[k]>limit for k,limit in lock['ceilings'].items()):raise ValueError('Campaign accounting changed')
    e=read(C/'closeout/execution.json');check('docs/studies/quality-tolerant/campaign-20261029-final-report.md',e['report_sha256']);check('docs/studies/quality-tolerant/campaign-20261029-verification.md',e['runbook_sha256'])
    decision=read(C/'closeout/decision.json');quality=read(C/'development_evaluation_reporting/quality-points.json');timing=read(C/'first_timing_diagnostic/analysis.json')
    if decision['original_success_contract_established'] or quality['controller']['point_pass'] or decision['confirmation_released'] or totals['confirmation_evaluations']:raise ValueError('Scientific boundary changed')
    value=1-timing['methods']['controller']['mean_ms']/timing['methods']['fixed:11']['mean_ms']
    if abs(value-timing['mean_saving'])>1e-12 or quality['controller']['losses']['bleu']<=.5:raise ValueError('Aggregate result changed')
    commit=subprocess.check_output(['git','-C',str(ROOT/'third_party/ncm'),'rev-parse','HEAD'],text=True).strip()
    if commit!=source['upstream_commit'] or subprocess.check_output(['git','-C',str(ROOT/'third_party/ncm'),'status','--porcelain'],text=True).strip():raise ValueError('Pinned upstream changed')
    packaged=read(ROOT/'src/anytime_ncm/snapshot.json')
    for item in packaged['sources']:check(item['path'],item['sha256'])
    return dict(status='verified_with_explicit_historical_metadata_resolution',baseline_research_commit=m['baseline_commit'],public_expected_hash_pairs=len(pairs),current_paths_verified=len(current),archived_metadata_paths=sorted(resolved),executed_artifact_hashes=artifacts,private_hashes_checked=len(source['private_sha256']) if private else 0,private_corpus_or_trajectory_bodies_decoded=0,real_checkpoint_loads=0,new_model_requests=0,new_fits=0,new_reference_scores=0,new_resampling=0,phases=phases,unchanged_charged_usage=totals,original_receipt_gaps_preserved=True,original_full_matrix_incomplete=True,quality_and_latency_success_established=False,confirmation_still_sealed=True,strict_current_tree_legacy_verifier_claimed=False,upstream_commit=commit)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--private',action='store_true');p.add_argument('--output',type=Path);a=p.parse_args();result=audit(a.private)
    if a.output:
        a.output.parent.mkdir(parents=True,exist_ok=True)
        with a.output.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(result))
