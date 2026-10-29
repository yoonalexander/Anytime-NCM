"""Build from an sdist and test wheel/sdist installs in clean environments (no ML)."""
import argparse,hashlib,json,os,platform,subprocess,sys,tarfile,tempfile,venv,zipfile
from email.parser import Parser
from pathlib import Path,PurePosixPath

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def python_at(root):return root/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
def run(args,cwd,env):
    p=subprocess.run([str(x) for x in args],cwd=cwd,env=env,capture_output=True,text=True,encoding='utf-8',timeout=180)
    if p.returncode:raise RuntimeError('Command failed: '+str(args[:3])+'\n'+p.stdout[-3000:]+p.stderr[-3000:])
    return p.stdout

def safe_member(name):
    p=PurePosixPath(name)
    if p.is_absolute() or '..' in p.parts or any(':' in x for x in p.parts):raise ValueError('Unsafe archive path')
    return p

def check_archives(sdist,wheel):
    forbidden={'.pt','.pth','.ckpt','.safetensors','.pkl','.pickle','.npy','.npz','.pem','.key'}
    with zipfile.ZipFile(wheel) as z:
        for name in z.namelist():
            p=safe_member(name)
            if p.suffix in forbidden or p.parts[0]!='anytime_ncm' and not p.parts[0].endswith('.dist-info'):raise ValueError('Unexpected wheel member: '+name)
        meta=Parser().parsestr(z.read(next(n for n in z.namelist() if n.endswith('.dist-info/METADATA'))).decode())
        if meta['Version']!='0.1.0' or meta.get_all('Requires-Dist'):raise ValueError('Unexpected version/runtime dependencies')
        if 'anytime_ncm/snapshot.json' not in z.namelist() or 'anytime_ncm/upstream-NCM-LICENSE.txt' not in z.namelist():raise ValueError('Snapshot/notice missing')
    with tarfile.open(sdist,'r:gz') as tar:
        for m in tar.getmembers():
            p=safe_member(m.name);parts=p.parts[1:]
            if m.issym() or m.islnk() or p.suffix in forbidden:raise ValueError('Forbidden sdist member')
            if not parts:continue
            if parts[0] not in {'src','scripts','examples','docs','README.md','pyproject.toml','NOTICE.md','RIGHTS.md','MANIFEST.in','PKG-INFO','setup.cfg'}:raise ValueError('Unexpected sdist member: '+m.name)
            if parts[0]=='scripts' and len(parts)>1 and parts[1]!='verify_distribution.py':raise ValueError('Unexpected build script')
            if parts[0]=='docs' and parts[1:] not in [(),('delivery',),('delivery','INSTALL.md')]:raise ValueError('Unexpected bundled documentation')
    return dict(wheel_sha256=sha(wheel),sdist_sha256=sha(sdist),runtime_dependencies=[],checkpoint_dataset_credentials_included=False)

def main():
    p=argparse.ArgumentParser();p.add_argument('--sdist',type=Path,required=True);p.add_argument('--work-dir',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--python',type=Path);a=p.parse_args();sdist=a.sdist.resolve();work=a.work_dir.resolve();work.mkdir(parents=True,exist_ok=False)
    env=dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1');env.pop('PYTHONPATH',None);env.pop('PYTHONHOME',None)
    extracted=work/'source';extracted.mkdir()
    with tarfile.open(sdist,'r:gz') as tar:
        for m in tar.getmembers():
            path=safe_member(m.name)
            if m.issym() or m.islnk():raise ValueError('Unsafe source archive')
            dest=extracted.joinpath(*path.parts)
            if m.isdir():dest.mkdir(parents=True,exist_ok=True)
            elif m.isfile():dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(tar.extractfile(m).read())
            else:raise ValueError('Unsupported source archive member')
    source=next(extracted.iterdir());run([sys.executable,'-m','build','--wheel','--no-isolation','--outdir',work/'wheels'],source,env);wheel=next((work/'wheels').glob('*.whl'));checks=check_archives(sdist,wheel);runtime=str(a.python or sys.executable);results=[]
    with tempfile.TemporaryDirectory(prefix='ncm-installed-') as outside:
        cwd=Path(outside)
        for kind,artifact in [('wheel',wheel),('sdist',sdist)]:
            v=work/('venv-'+kind);run([runtime,'-m','venv',v],cwd,env);py=python_at(v);run([py,'-m','pip','install','--no-deps','--no-cache-dir',artifact],cwd,env);pip_check=run([py,'-m','pip','check'],cwd,env).strip();entry=v/('Scripts/anytime-ncm.exe' if os.name=='nt' else 'bin/anytime-ncm');count=0
            for command in ([entry,'--version'],[py,'-m','anytime_ncm','--version']):
                assert run(command,cwd,env).strip()=='0.1.0';count+=1
            for command in ([entry,'status','--json'],[py,'-m','anytime_ncm','status','--json']):
                value=json.loads(run(command,cwd,env));e=value['latest_evaluation'];assert e['inputs']==1188 and e['early_exits']==315 and not e['original_success_contract_established'] and e['quality_losses']['bleu']>.5;assert abs((1-e['controller_mean_ms']/e['full_mean_ms'])-e['mean_saving'])<1e-12;count+=1
            assert 'fails' in run([entry,'status'],cwd,env);count+=1
            for command in ([entry,'--help'],[py,'-m','anytime_ncm','--help']):assert 'validate-trajectories' in run(command,cwd,env);count+=1
            code="import sys;from anytime_ncm.cli import main;main(['status','--json']);assert not any(x.split('.')[0] in {'torch','transformers','numpy','scipy','sacrebleu'} for x in sys.modules)";run([py,'-c',code],cwd,env);count+=1
            for command in ([entry,'collect','--config','missing.json'],[entry,'validate-trajectories','--metadata','missing.json']):
                failed=subprocess.run([str(x) for x in command],cwd=cwd,env=env,capture_output=True,text=True,encoding='utf-8');assert failed.returncode==1 and 'research checkout' in failed.stderr and 'Traceback' not in failed.stderr;count+=1
            example=source/'examples/inspect_snapshot.py';assert 'False' in run([py,example],cwd,env);count+=1
            location=run([py,'-c','import anytime_ncm;print(anytime_ncm.__file__)'],cwd,env).strip();assert str(v) in location and '/src/' not in location.replace('\\','/');count+=1
            results.append(dict(artifact=kind,checks=count,pip_check=pip_check,python=run([py,'--version'],cwd,env).strip(),outside_checkout=True,no_research_libraries_imported=True))
    report=dict(status='passed',package='anytime-ncm',version='0.1.0',platform=platform.platform(),build_python=platform.python_version(),wheel_built_from_sdist=True,archive_checks=checks,installations=results,real_model_requests=0,research_experiments_rerun=0,package_registries_published=False)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report))
if __name__=='__main__':main()
