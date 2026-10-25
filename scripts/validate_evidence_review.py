"""P1 source/PDF/link/hash bundle checks over aggregates only, never model data."""
import hashlib,json,re,subprocess,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];PAPER=ROOT/'paper/stronger-research-v4';OUT=ROOT/'results/evidence_gaps/p1'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(path,data):
    with path.open('x',encoding='utf-8') as f:json.dump(data,f,indent=2);f.write('\n')


def main():
    if (OUT/'completion.json').exists():raise FileExistsError('Preserve original P1 receipt')
    started=read(OUT/'started.json')
    mutable={'README.md','RESEARCH_ROADMAP.md','RESEARCH_SYNTHESIS.md','docs/studies/evidence-gaps/continuous-closure-plan.md'}
    checked=0
    for p,h in started['historical_worktree_sha256'].items():
        if p not in mutable:
            assert sha(ROOT/p)==h,('Historical bytes changed',p);checked+=1
    assert sha(PAPER/'history/RESEARCH_SYNTHESIS-v3.md')==started['historical_worktree_sha256']['RESEARCH_SYNTHESIS.md']
    e2=read(ROOT/'results/evidence_gaps/e2/analysis.json');screen=read(ROOT/'results/evidence_gaps/e2_terminal_screen/analysis.json')
    tex=(PAPER/'main.tex').read_text();pdftext=(OUT/'pdf-text.txt').read_text()
    expected=[f"{e2['methods']['exact']['mean_ms']:.3f}",f"{e2['methods']['fixed:11']['mean_ms']:.3f}",f"{screen['methods']['terminal_exact']['mean_ms']:.3f}",f"{100*screen['contrasts']['terminal_exact_versus_full']['relative_mean_reduction']:.3f}",'43/256','48/256','82,110','25,240','12,664','405','385','59']
    assert all(value in tex for value in expected),expected
    assert all(value in pdftext for value in expected),expected
    compact=re.sub(r'\s+','',pdftext)
    for value in ['-15.208','-11.310','1.735','3.729']:
        assert value in compact,value  # PDF extraction may wrap immediately after a minus sign.
    for value in ['post hoc','not a','Internal review draft']:assert value in pdftext,value
    assert e2['early_exact_inputs']==43 and not e2['controller_entry_released'] and not screen['E3_release'] and not screen['E4_release']
    plotted=read(PAPER/'figures/reviewed-data.json')
    assert plotted['exact_depth_counts']==e2['exact_depth_counts'] and plotted['exact_mean_ms']==e2['methods']['exact']['mean_ms']
    assert plotted['assembled_terminal_mean_ms']==screen['methods']['terminal_exact']['mean_ms']
    log=(OUT/'compile-polished.log').read_text(errors='replace')
    assert not re.search(r'Overfull|Underfull|undefined references|Citation .*undefined|Reference .*undefined',log)
    info=subprocess.check_output(['pdfinfo',str(PAPER/'main.pdf')],text=True)
    assert re.search(r'Pages:\s+8\b',info) and re.search(r'JavaScript:\s+no\b',info)
    pages=[ROOT/f'tmp/pdfs/stronger-v4/final-{n}.png' for n in range(1,9)]
    assert all(p.exists() for p in pages)
    pdfcheck=dict(status='pass',pages=8,all_pages_visually_inspected=list(range(1,9)),renderer='Poppler85DPI',native_compilation='success, MiKTeX; installer and shell escape disabled',codex_compilation='success on final source',layout_repairs=2,no_overfull_underfull_or_undefined_references=True,disabled_shell_warning_expected=True,embedded_javascript=False,pdf_sha256=sha(PAPER/'main.pdf'),source_sha256=sha(PAPER/'main.tex'),page_png_sha256=[sha(p) for p in pages],submission_ready=False)
    write(OUT/'pdf-validation.json',pdfcheck)
    # Package only explicit source/review/aggregate paths. Never enumerate raw outcome directories.
    source_files=[PAPER/'main.tex',*sorted(PAPER.glob('*.md')),*sorted((PAPER/'figures').glob('*')),*sorted((PAPER/'history').glob('*.md'))]
    with zipfile.ZipFile(PAPER/'manuscript-source.zip','x',compression=zipfile.ZIP_DEFLATED) as z:
        for p in source_files:z.writestr(p.relative_to(PAPER).as_posix(),p.read_bytes())
    protocol_names=['e0-protocol.md','e0-lock.json','e0-recovery-amendment.md','e1-protocol.md','e1-lock.json','e2-protocol.md','e2-lock.json','e2-terminal-screen-protocol.md','e2-terminal-screen-lock.json','m0-protocol.md','m0-lock.json','p1-protocol.md','continuous-closure-plan.md']
    aggregate_names={'e0':['summary.md','statistical-feasibility.json','completion.json'],
                     'e1':['summary.md','execution.json','independent-checks.json'],
                     'e2':['summary.md','analysis.json','execution.json','independent-checks.json'],
                     'e2_terminal_screen':['summary.md','analysis.json','execution.json','independent-checks.json'],
                     'm0':['summary.md','checks.json']}
    packet_files=[*source_files,PAPER/'main.pdf',ROOT/'RESEARCH_SYNTHESIS.md',ROOT/'RESEARCH_ROADMAP.md',OUT/'summary.md',OUT/'pdf-validation.json',ROOT/'scripts/build_evidence_review_figures.py',ROOT/'scripts/validate_evidence_review.py']
    packet_files += [ROOT/'docs/studies/evidence-gaps'/p for p in protocol_names]
    packet_files += [ROOT/'results/evidence_gaps'/stage/name for stage,names in aggregate_names.items() for name in names]
    packet_files += [ROOT/'results/evidence_gaps'/stage/'execution-sources.zip' for stage in ('e0','e1','e2') if (ROOT/'results/evidence_gaps'/stage/'execution-sources.zip').exists()]
    packet_files += [ROOT/'results/evidence_gaps/e2_terminal_screen/sources.zip']
    packet_files += [ROOT/'docs/studies/stronger-research-protocol.md',ROOT/'docs/studies/stronger-research-related-work.md']
    manifest={p.relative_to(ROOT).as_posix():sha(p) for p in packet_files}
    assert all(not any(fragment in p for fragment in ('trajectories.jsonl','requests.jsonl','selected-cells.json','pickle','safetensors')) for p in manifest)
    with zipfile.ZipFile(PAPER/'review-packet.zip','x',compression=zipfile.ZIP_DEFLATED) as z:
        for p in packet_files:z.writestr(p.relative_to(ROOT).as_posix(),p.read_bytes())
        z.writestr('manifest.json',json.dumps(dict(files_sha256=manifest,local_review_only=True,new_model_calls=0,raw_outcomes_included=False,submission_ready=False),indent=2))
    with zipfile.ZipFile(PAPER/'review-packet.zip') as z:
        for name,h in manifest.items():assert hashlib.sha256(z.read(name)).hexdigest()==h
    links=0
    doc_paths=[ROOT/'README.md',ROOT/'RESEARCH_ROADMAP.md',ROOT/'RESEARCH_SYNTHESIS.md',ROOT/'docs/studies/evidence-gaps/continuous-closure-plan.md',*PAPER.glob('*.md'),OUT/'summary.md']
    for p in doc_paths:
        for target in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf-8-sig')):
            if '://' in target or target.startswith('#'):continue
            if target.endswith(('pdf-validation.json','completion.json')) and p==OUT/'summary.md':continue
            assert (p.parent/target.split('#')[0]).resolve().exists(),(str(p),target)
            links+=1
    total=sum(p.stat().st_size for folder in (PAPER,OUT) for p in folder.rglob('*') if p.is_file())
    assert total<256*1024**2
    completion=dict(stage='P1',status='local_review_package_complete_human_tasks_open',protected_historical_files_checked=checked,prior_root_synthesis_archived_byte_exact=True,local_links_checked=links,pdf_pages=8,headline_aggregate_parity=True,review_packet_files=len(manifest),source_zip_sha256=sha(PAPER/'manuscript-source.zip'),review_zip_sha256=sha(PAPER/'review-packet.zip'),artifact_bytes_before_receipt=total,conservative_full_phase_wall_charge_seconds=14400,model_calls=0,new_source_reference_outcome_bodies=0,fits=0,target_encodings=0,paid_compute_dollars=0,E3_released=False,E4_released=False,independent_human_review=False,verified_human_authorship=False,rights_license_resolved=False,submission_ready=False,validator_sha256=sha(Path(__file__)))
    write(OUT/'completion.json',completion)
    print(json.dumps(completion))


if __name__=='__main__':main()
