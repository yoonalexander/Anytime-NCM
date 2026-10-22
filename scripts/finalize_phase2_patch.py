"""Format-only Phase 2 patch receipt correction; no model imports or evaluations."""
import ast
import difflib
import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from anytime_ncm.phase2 import save
from anytime_ncm.dataset import sha256

def main():
    out=ROOT/"results/phase2"
    path=out/"upstream_level_hook.patch.txt"
    initial=out/"upstream_level_hook.initial.patch.txt"
    if initial.exists():
        raise ValueError("Patch receipt already finalized.")
    initial.write_bytes(path.read_bytes())
    text=(ROOT/"src/anytime_ncm/online.py").read_text(encoding="utf-8")
    tree=ast.parse(text)
    helper=next(n for n in tree.body if isinstance(n,ast.Assign) and any(
        isinstance(t,ast.Name) and t.id=="BOUNDARY" for t in n.targets))
    function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=="patched_source")
    namespace={"BOUNDARY":ast.literal_eval(helper.value)}
    exec(compile(ast.Module(body=[function],type_ignores=[]),"pure-patch-transform","exec"),namespace)
    source=(ROOT/"third_party/ncm/models/next_concept.py").read_text(encoding="utf-8")
    changed=namespace["patched_source"](source)
    lines=difflib.unified_diff(source.splitlines(True),changed.splitlines(True),
        fromfile="a/models/next_concept.py",tofile="b/models/next_concept.py")
    corrected="".join(line if line.endswith("\n") else line+"\n\\ No newline at end of file\n" for line in lines)
    path.write_text(corrected,encoding="utf-8",newline="\n")
    subprocess.run(["git","-C",str(ROOT/"third_party/ncm"),"-c","core.autocrlf=true",
        "apply","--check","--ignore-space-change",str(path)],check=True)
    receipt=json.loads((out/"2a.json").read_text(encoding="utf-8"))
    receipt["artifacts_sha256"][initial.name]=sha256(initial)
    receipt["artifacts_sha256"][path.name]=sha256(path)
    receipt["patch_format_correction"]={"source_path":"scripts/finalize_phase2_patch.py",
        "sha256":sha256(Path(__file__)),"reason":"preserve Git no-newline marker in unified diff",
        "git_apply_check":True,"model_code_changed":False,"additional_model_calls":0}
    save(out/"2a.json",receipt)
    print("PASS: corrected patch applies cleanly; initial diff and execution receipts preserved.")
if __name__=="__main__":main()
