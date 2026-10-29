"""Portable inspection, frozen aggregate claims and explicit checkout dispatch."""
import json,subprocess,sys
from pathlib import Path
from types import SimpleNamespace
import pytest
from anytime_ncm.cli import main,research_repository
from anytime_ncm.snapshot import load_snapshot
ROOT=Path(__file__).resolve().parents[1]

def test_status_json_preserves_the_negative_contract_and_exact_saved_values(capsys):
    assert main(['status','--json'])==0
    value=json.loads(capsys.readouterr().out);e=value['latest_evaluation']
    assert value['snapshot_version']=='0.1.0' and e['inputs']==1188 and e['early_exits']==315
    assert e['timing_screen_passed'] and not e['quality_point_screen_passed'] and not e['original_success_contract_established']
    assert e['quality_losses']['bleu']>.5 and e['quality_margins']['bleu']==.5
    for source in value['sources']:
        import hashlib
        assert hashlib.sha256((ROOT/source['path']).read_bytes()).hexdigest()==source['sha256']

def test_plain_status_explains_the_outcome(capsys):
    assert main(['status'])==0
    text=capsys.readouterr().out;assert 'research snapshot' in text and '5.076%' in text and 'fails' in text and 'confirmation is not ready' in text

def test_version_and_help(capsys):
    with pytest.raises(SystemExit) as e:main(['--version'])
    assert e.value.code==0 and capsys.readouterr().out.strip()=='0.1.0'
    assert main([])==0 and 'status' in capsys.readouterr().out

@pytest.mark.parametrize('command,args',[('collect',['--config','missing.json']),('validate-trajectories',['--metadata','missing.json'])])
def test_explicit_noncheckout_has_clear_error_before_research_import(tmp_path,command,args,capsys):
    with pytest.raises(SystemExit) as e:main(['--repository',str(tmp_path),command,*args])
    assert e.value.code==1 and 'research checkout' in capsys.readouterr().err

def test_explicit_repository_dispatch_is_independent_of_installed_module_location(tmp_path,monkeypatch,capsys):
    (tmp_path/'configs').mkdir();(tmp_path/'third_party/ncm').mkdir(parents=True);(tmp_path/'.gitmodules').write_text('fixture');calls=[]
    fake=SimpleNamespace(verify_run=lambda root,metadata:calls.append((root,metadata)) or dict(verified=True),run_collection=None)
    monkeypatch.setitem(sys.modules,'anytime_ncm.collect',fake)
    assert main(['--repository',str(tmp_path),'validate-trajectories','--metadata','m.json'])==0
    assert calls==[(tmp_path.resolve(),Path('m.json'))] and json.loads(capsys.readouterr().out)==dict(verified=True)

def test_base_snapshot_imports_no_research_libraries_in_fresh_process():
    code="import sys;sys.path.insert(0,'src');from anytime_ncm.cli import main;main(['status','--json']);assert not any(x.split('.')[0] in {'torch','transformers','numpy','scipy','sacrebleu'} for x in sys.modules)"
    subprocess.run([sys.executable,'-c',code],cwd=ROOT,check=True,capture_output=True,text=True)

def test_each_load_returns_independent_data():
    a=load_snapshot();a['latest_evaluation']['inputs']=0;assert load_snapshot()['latest_evaluation']['inputs']==1188
