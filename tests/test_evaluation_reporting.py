"""Version-field repair and preserved cache invariants without model requests."""
import copy,json
import numpy as np
import pytest
from anytime_ncm.evaluation_reporting import native_environment,validated_cache
from anytime_ncm.development_reporting import plain
from anytime_ncm.quality_controller import Meter

def test_actual_torch_version_is_normalized_before_strict_report_and_failure_write(tmp_path):
    from torch.torch_version import TorchVersion
    version=TorchVersion('2.10.0+cu128')
    with pytest.raises(TypeError):plain(dict(torch=version))
    env=native_environment(dict(torch=version,physical_gpu_bytes=8546484224,tf32=False))
    assert type(env['torch']) is str and env['torch']=='2.10.0+cu128'
    for name,receipt in [('complete',dict(status='complete',environment=env)),('failure',dict(error='invented reporting failure',environment=env))]:
        p=tmp_path/(name+'.json');p.write_text(json.dumps(plain(receipt)));assert json.loads(p.read_text())==receipt

def test_version_repair_is_local_and_rejects_invalid_or_unrelated_objects():
    class Version(str):pass
    source=dict(torch=Version('x'),driver='d',memory=1);before=copy.deepcopy(source)
    assert native_environment(source)==before and source==before and type(source['torch']) is Version
    with pytest.raises(TypeError):native_environment(dict(torch=None))
    with pytest.raises(TypeError):native_environment(dict(torch='x',unsupported=object()))
    with pytest.raises(TypeError):plain(Version('x'))

def test_normalized_json_still_enforces_finite_scalars_and_string_keys():
    assert native_environment(dict(torch='x',count=np.int64(3),done=np.bool_(True)))==dict(torch='x',count=3,done=True)
    with pytest.raises(ValueError):native_environment(dict(torch='x',bad=float('nan')))
    with pytest.raises(ValueError):native_environment({'torch':'x',3:'bad'})

def test_cache_repair_rejects_missing_population_before_body_decode():
    class Poison:
        def __iter__(self):raise AssertionError('Body decoded before allocation rejection')
    with pytest.raises(ValueError):validated_cache([],[],[],Poison(),Meter(dict(native_trace_bodies=0)))
