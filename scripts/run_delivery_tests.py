"""Run synthetic software regressions without real model/data reads or GPU use (WSL)."""
import argparse,json,os,resource,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
GUARD=r'''import atexit,json,os,socket,sys
from pathlib import Path
root=Path(os.environ['NCM_DELIVERY_ROOT']).resolve();work=Path(os.environ['NCM_DELIVERY_WORK']).resolve();counts=dict(real_data_reads_blocked=0,repository_writes_blocked=0,external_connections_blocked=0,text_tokenizer_metadata_reads_allowed=0)
def audit(event,args):
    if event=='open':
        name=args[0]
        if not isinstance(name,(str,bytes,os.PathLike)):return
        p=Path(os.fsdecode(name)).resolve();flags=args[2] if len(args)>2 and isinstance(args[2],int) else 0;mode=args[1] if len(args)>1 else '';writing=bool(flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND)) or isinstance(mode,str) and any(x in mode for x in 'wax+')
        tokenizer_metadata=(p.is_relative_to(root/'artifacts/wmt14/text_tokenizer') and p.suffix in ('.json','.txt') and not writing)
        if tokenizer_metadata:counts['text_tokenizer_metadata_reads_allowed']+=1
        if any(p.is_relative_to(root/d) for d in ('data','artifacts')) and not tokenizer_metadata:
            counts['real_data_reads_blocked']+=1;raise PermissionError('Delivery test blocked real research data/artifact access')
        if writing and p.is_relative_to(root) and not p.is_relative_to(work):
            counts['repository_writes_blocked']+=1;raise PermissionError('Delivery test writes must stay in temporary delivery workspace')
    elif event=='socket.connect':
        address=args[1]
        if isinstance(address,tuple) and address and address[0] not in ('127.0.0.1','::1','localhost'):
            counts['external_connections_blocked']+=1;raise PermissionError('Delivery tests have no external network')
sys.addaudithook(audit)
def finish():
    (work/('guard-'+str(os.getpid())+'.json')).write_text(json.dumps(dict(pid=os.getpid(),gpu_visible=os.environ.get('CUDA_VISIBLE_DEVICES'),**counts)),encoding='utf-8')
atexit.register(finish)
'''
def main():
    p=argparse.ArgumentParser();p.add_argument('label');p.add_argument('--group',choices=('all','main','q0'),default='all');a=p.parse_args();work=ROOT/'build/delivery'/a.label;work.mkdir(parents=True,exist_ok=False);guard=work/'guard';guard.mkdir();(guard/'sitecustomize.py').write_text(GUARD,encoding='utf-8')
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(guard)+os.pathsep+str(ROOT/'src'),NCM_DELIVERY_ROOT=str(ROOT),NCM_DELIVERY_WORK=str(work),CUDA_VISIBLE_DEVICES='',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',TOKENIZERS_PARALLELISM='false',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
    selected=['tests'] if a.group=='all' else ['tests','--ignore=tests/test_q0_multiplicity.py','--ignore=tests/test_q0_population.py'] if a.group=='main' else ['tests/test_q0_multiplicity.py','tests/test_q0_population.py'];started=time.monotonic();log=work/'pytest.log';args=[sys.executable,'-m','pytest',*selected,'-q','-p','no:cacheprovider','--basetemp='+str(work/'tmp'),'--junitxml='+str(work/'tests.xml')]
    def cap():resource.setrlimit(resource.RLIMIT_CPU,(600,600))
    with log.open('x') as f:result=subprocess.run(args,cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=1200,preexec_fn=cap)
    guards=[json.loads(x.read_text()) for x in work.glob('guard-*.json')];receipt=dict(label=a.label,group=a.group,exit_code=result.returncode,wall_seconds=time.monotonic()-started,python=sys.version,command=args,guard_reports=guards,real_checkpoint_loads=0,experiment_reruns=0,gpu_disabled=True,scope='software tests on invented fixtures; pinned text-tokenizer JSON allowed for decoder compatibility; not research performance evidence')
    out=ROOT/'results/delivery/20261029';(out/(a.label+'.json')).write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8');(out/(a.label+'.log')).write_bytes(log.read_bytes())
    if (work/'tests.xml').exists():(out/(a.label+'.xml')).write_bytes((work/'tests.xml').read_bytes())
    print(log.read_text()[-10000:]);print(json.dumps(receipt));return result.returncode
if __name__=='__main__':raise SystemExit(main())
