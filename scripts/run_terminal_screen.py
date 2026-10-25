"""Single saved-data terminal screen; refuses overwrite and imports no model."""
import os
for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[name]='4'
import argparse,json,subprocess,sys,time,zipfile,resource
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from anytime_ncm.evidence_preflight import sha,write_new
from anytime_ncm.terminal_screen import assemble,calculate
LOCK=ROOT/'docs/studies/evidence-gaps/e2-terminal-screen-lock.json'
OUT=ROOT/'results/evidence_gaps/e2_terminal_screen'
FILES=['scripts/run_terminal_screen.py','src/anytime_ncm/terminal_screen.py','tests/test_terminal_screen.py','docs/studies/evidence-gaps/e2-terminal-screen-protocol.md',
       'src/anytime_ncm/evidence_preflight.py','src/anytime_ncm/evidence_timing.py','docs/studies/evidence-gaps/e2-terminal-screen-lock.json']
read=lambda p:json.loads(p.read_text())


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--prepare',action='store_true');parser.add_argument('--remote-head');args=parser.parse_args()
    if args.prepare:
        protocol=FILES[3]
        write_new(LOCK,dict(base_commit='d84b2a4a3aaec9b427ba91fe51cdc32de4110227',protocol=protocol,protocol_sha256=sha(ROOT/protocol),
            E2_execution_sha256=sha(ROOT/'results/evidence_gaps/e2/execution.json'),E0_manifest_sha256=sha(ROOT/'results/evidence_gaps/e0/input-manifest.json'),
            analysis_seconds=900,preparation_seconds=3600,report_seconds=2700,rss_bytes=4294967296,artifact_bytes=134217728,model_calls=0,draws=100000))
        print('Locked post hoc saved-data screen; zero selected-terminal calculations.');return
    if not args.remote_head:parser.error('Supply verified source-lock commit')
    git=lambda *a:subprocess.check_output(['git','-c','safe.directory='+str(ROOT),'-c','safe.directory='+str(ROOT/'third_party/ncm'),'-c','core.autocrlf=true','-c','core.safecrlf=false',*a],cwd=ROOT,text=True).strip()
    if git('rev-parse','HEAD')!=args.remote_head or git('status','--porcelain') or git('branch','--show-current')!='main' or git('ls-remote','origin','refs/heads/main').split()[0]!=args.remote_head:raise ValueError('Need clean source-lock main/remote equality')
    lock=read(LOCK)
    if sha(ROOT/lock['protocol'])!=lock['protocol_sha256'] or sha(ROOT/'results/evidence_gaps/e2/execution.json')!=lock['E2_execution_sha256'] or sha(ROOT/'results/evidence_gaps/e0/input-manifest.json')!=lock['E0_manifest_sha256']:raise ValueError('Frozen dependency differs')
    OUT.mkdir(parents=True,exist_ok=False);start=time.monotonic()
    started=dict(source_commit=args.remote_head,source_sha256={p:sha(ROOT/p) for p in FILES},post_hoc=True,new_outcome_access=False)
    write_new(OUT/'started.json',started)
    with zipfile.ZipFile(OUT/'sources.zip','x',compression=zipfile.ZIP_DEFLATED) as z:
        for p in FILES:z.writestr(p,(ROOT/p).read_bytes())
    try:
        e2=ROOT/'results/evidence_gaps/e2';execution=read(e2/'execution.json')
        names=['trajectories.jsonl','timing-schedule.json','0-requests.jsonl','1-requests.jsonl','0-starts.jsonl','1-starts.jsonl']
        for p in names:
            if sha(e2/p)!=execution['artifact_sha256'][p]:raise ValueError('E2 artifact differs: '+p)
        entries=read(ROOT/'results/evidence_gaps/e0/input-manifest.json')['roles']['E2_audit']
        rows=[json.loads(s) for s in (e2/'trajectories.jsonl').read_text().splitlines()]
        records=[json.loads(s) for b in range(2) for s in (e2/f'{b}-requests.jsonl').read_text().splitlines()]
        data,depths=assemble(entries,rows,records);report=calculate(data,lock['draws'])
        write_new(OUT/'analysis.json',report)
        selected=[dict(identity=e['identity'],index=e['index'],depth=depths[e['index']],terminal_ms=data['terminal_exact'][i].tolist(),full_ms=data['full'][i].tolist(),dense_ms=data['dense_exact'][i].tolist()) for i,e in enumerate(entries)]
        write_new(OUT/'selected-cells.json',selected)
        seconds=time.monotonic()-start;rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024;size=sum(p.stat().st_size for p in OUT.iterdir() if p.is_file())
        if seconds>lock['analysis_seconds'] or rss>lock['rss_bytes'] or size>lock['artifact_bytes']:raise RuntimeError('Resource limit')
        write_new(OUT/'execution.json',dict(status='complete',source_commit=args.remote_head,analysis_seconds=seconds,peak_rss_bytes=rss,artifact_bytes=size,
            conservative_preparation_reporting_seconds=6300,deterministic_selections=256,reused_bootstrap_vectors=100000,new_references=0,new_inputs=0,model_calls=0,fits=0,target_encodings=0,paid_compute_dollars=0,
            decision=report['decision'],artifact_sha256={p.name:sha(p) for p in OUT.iterdir() if p.is_file()}))
        print(json.dumps(report),flush=True)
    except Exception as error:
        write_new(OUT/'failure.json',dict(error=type(error).__name__+': '+str(error),automatic_retry=False,wall_seconds=time.monotonic()-start));raise


if __name__=='__main__':main()
