"""Hash resolution must not silently forgive altered experimental evidence."""
import hashlib,importlib.util
from pathlib import Path
import pytest
P=Path(__file__).resolve().parents[1]/'scripts/audit_retained_evidence.py';spec=importlib.util.spec_from_file_location('delivery_artifact_audit',P);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
def h(b):return hashlib.sha256(b).hexdigest()
def test_current_hash_is_verified(tmp_path):
    (tmp_path/'result.json').write_bytes(b'original');assert mod.resolve_expected(tmp_path,{},'result.json',h(b'original'))=='current'
def test_only_declared_metadata_can_use_exact_original(tmp_path):
    (tmp_path/'README.md').write_bytes(b'new docs');assert mod.resolve_expected(tmp_path,{'README.md':b'old docs'},'README.md',h(b'old docs'))=='archived_metadata'
    with pytest.raises(ValueError):mod.resolve_expected(tmp_path,{'result.json':b'original'},'result.json',h(b'original'))
def test_wrong_archive_and_unsafe_paths_reject(tmp_path):
    with pytest.raises(ValueError):mod.resolve_expected(tmp_path,{'README.md':b'wrong'},'README.md',h(b'original'))
    with pytest.raises(ValueError):mod.resolve_expected(tmp_path,{},'../outside.json',h(b'x'))
