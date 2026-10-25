"""Final metadata/artifact checks; never parses sealed outcome/reference bodies."""
import hashlib,json,re,subprocess,xml.etree.ElementTree as ET,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/evidence_gaps/closure'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    target=OUT/'completion.json'
    if target.exists():raise FileExistsError('Preserve closure receipt')
    p1=ROOT/'results/evidence_gaps/p1';started=read(p1/'started.json')
    mutable={'README.md','RESEARCH_ROADMAP.md','RESEARCH_SYNTHESIS.md','docs/studies/evidence-gaps/continuous-closure-plan.md','.gitignore'}
    unchanged=0
    for p,h in started['historical_worktree_sha256'].items():
        if p not in mutable:
            assert sha(ROOT/p)==h,('Historical artifact changed',p);unchanged+=1
    manifest=read(ROOT/'results/evidence_gaps/e0/input-manifest.json')
    assert sha(ROOT/'results/evidence_gaps/e0/input-manifest.json')==read(ROOT/'docs/studies/evidence-gaps/e2-lock.json')['E0_manifest_sha256']
    closed={name:len(manifest['roles'][name]) for name in ('E3_development','E4_confirmation','closed_unallocated')}
    assert closed==dict(E3_development=128,E4_confirmation=1024,closed_unallocated=571)
    assert all(not e['outcome_access_released'] for name in closed for e in manifest['roles'][name])
    release=read(ROOT/'results/evidence_gaps/e2/access-release.json');assert release['E3_released']==release['E4_released']==False
    assert not (ROOT/'results/evidence_gaps/e3').exists() and not (ROOT/'results/evidence_gaps/e4').exists()
    verified_hashes=0
    for stage in ('e1','e2','e2_terminal_screen'):
        receipt=read(ROOT/'results/evidence_gaps'/stage/'execution.json')
        for p,h in receipt['artifact_sha256'].items():
            assert sha(ROOT/'results/evidence_gaps'/stage/p)==h,(stage,p);verified_hashes+=1
    for stage in ('e1','e2','e2_terminal_screen'):
        snapshot=read(ROOT/'results/evidence_gaps'/stage/'started.json')
        for p,h in snapshot['source_sha256'].items():assert sha(ROOT/p)==h,('Executed source changed',p)
    e2=read(ROOT/'results/evidence_gaps/e2/analysis.json');screen=read(ROOT/'results/evidence_gaps/e2_terminal_screen/analysis.json')
    assert e2['decision']=='bounded_exact_no_go' and screen['decision']=='do_not_budget_same_exact_family'
    assert not e2['controller_entry_released'] and not screen['E3_release'] and not screen['E4_release']
    assert read(ROOT/'results/evidence_gaps/m0/checks.json')['cause_established']==False
    paper=ROOT/'paper/stronger-research-v4';pdfcheck=read(p1/'pdf-validation.json');p1done=read(p1/'completion.json');correction=read(p1/'access-bundle-correction.json')
    assert sha(paper/'main.pdf')==pdfcheck['pdf_sha256'] and sha(paper/'main.tex')==pdfcheck['source_sha256']
    assert pdfcheck['pages']==8 and pdfcheck['all_pages_visually_inspected']==list(range(1,9))
    assert sha(paper/'manuscript-source.zip')==p1done['source_zip_sha256']
    assert sha(paper/'review-packet.zip')==correction['original_sha256']==p1done['review_zip_sha256']
    assert sha(paper/'review-packet-with-access.zip')==correction['current_sha256']
    assert sha(paper/'history/RESEARCH_SYNTHESIS-v3.md')==started['historical_worktree_sha256']['RESEARCH_SYNTHESIS.md']
    for archive in ('review-packet.zip','review-packet-with-access.zip'):
        with zipfile.ZipFile(paper/archive) as z:
            internal=json.loads(z.read('manifest.json'))['files_sha256']
            for p,h in internal.items():assert hashlib.sha256(z.read(p)).hexdigest()==h
            if archive.endswith('with-access.zip'):
                assert len(internal)==56
                assert all(p in internal for p in correction['added_files'])
    suite=list(ET.parse(OUT/'tests.xml').getroot().iter('testsuite'))
    tests=sum(int(s.attrib['tests']) for s in suite)
    assert tests==103 and all(int(s.attrib['failures'])==int(s.attrib['errors'])==int(s.attrib['skipped'])==0 for s in suite)
    links=0
    paths=[ROOT/'README.md',ROOT/'RESEARCH_ROADMAP.md',ROOT/'RESEARCH_SYNTHESIS.md',*paper.glob('*.md'),ROOT/'docs/studies/evidence-gaps/continuous-closure-plan.md',ROOT/'docs/studies/evidence-gaps/continuous-closure.md',ROOT/'results/evidence_gaps/e2_terminal_screen/summary.md',ROOT/'results/evidence_gaps/m0/summary.md',p1/'summary.md']
    for p in paths:
        for link in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf-8-sig')):
            if '://' in link or link.startswith('#'):continue
            dest=(p.parent/link.split('#')[0]).resolve()
            if dest==target:continue
            assert dest.exists(),(str(p),link);links+=1
    # Generated TeX logs retain their original whitespace; only authored diffs must pass.
    subprocess.run(['git','-c','core.safecrlf=false','diff','--check','--','.gitignore','README.md','RESEARCH_ROADMAP.md','RESEARCH_SYNTHESIS.md','docs/studies/evidence-gaps/continuous-closure-plan.md'],cwd=ROOT,check=True)
    size=sum(p.stat().st_size for p in OUT.iterdir() if p.is_file());assert size<128*1024**2
    report=dict(status='complete_all_justified_local_work_human_tasks_open',preserved_baseline_files_checked=unchanged,current_status_and_ignore_exceptions=sorted(mutable),execution_artifact_hashes_checked=verified_hashes,closed_role_counts=closed,E0_manifest_byte_identical=True,new_closed_role_release=False,synthetic_cpu_tests_passed=tests,full_suite_rerun=False,real_checkpoint_calls_after_E2=0,new_source_reference_outcome_identities=0,fits=0,target_encodings=0,training_runs=0,paid_compute_dollars=0,local_markdown_links_checked=links,pdf_pages_verified=8,complete_review_bundle_sha256=correction['current_sha256'],initial_bundle_and_receipts_preserved=True,conservative_closure_wall_seconds_charged=3600,artifact_bytes_before_receipt=size,scientific_gate_dispositions=dict(E2='bounded_no_go',terminal_screen='post_hoc_budget_no_go',M0='complete_cause_unresolved',E3='blocked_unexecuted',E4='closed_unexecuted',S2B_M1_S4='deferred_unexecuted',P1='local_preparation_complete_human_decisions_open'),human_authorship_confirmed=False,rights_resolved=False,independent_researcher_review=False,paper_submitted=False,validator_sha256=sha(Path(__file__)))
    with target.open('x',encoding='utf-8') as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps(report))


if __name__=='__main__':main()
