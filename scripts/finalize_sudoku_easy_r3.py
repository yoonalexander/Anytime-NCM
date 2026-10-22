"""Finalize R3 report-only cohort labeling; verify original, amendment and report sources."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from anytime_ncm.audit import OUTPUT, verify
from anytime_ncm.dataset import sha256
from anytime_ncm.screening import require, save

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    out = ROOT / OUTPUT
    provenance = json.loads((out / "report_provenance.json").read_text())
    spec = importlib.util.spec_from_file_location("r3_amendment", ROOT / "scripts/resume_sudoku_easy_r3.py")
    amendment = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(amendment)
    amendment.verify_amendment(ROOT)
    if args.verify:
        require(provenance["report_only_source_sha256"] == {
            "scripts/finalize_sudoku_easy_r3.py": sha256(Path(__file__))}, "Report-only source changed.")
        require(provenance["execution_amendment_sha256"] == amendment.extra_hashes(ROOT),
                "Amendment source changed.")
        analysis = verify(ROOT)
        require("torch" not in sys.modules and "matplotlib" not in sys.modules,
                "Model-free verification imported model/plot libraries.")
        print("PASS: R3 original execution sources, amended execution, original byte prefixes, report sources and recomputed analysis.")
        print("Decision:", analysis["decision"])
        print(analysis["profile_costs"]["development"]["paired"])
        return
    # Format-only correction: one common profile cohort on the cost-quality panel.
    # Preserve the original frozen renderer and measured data; record this source separately.
    original = ROOT / "src/anytime_ncm/audit_render.py"
    source = original.read_text()
    old = '[100 * f["collection_valid_rate"] for f in fixed]'
    new = '[100 * f["profile_valid_rate"] for f in fixed]'
    require(source.count(old) == 1, "Original plot expression changed.")
    namespace = {"__name__": "r3_report_only_renderer"}
    exec(compile(source.replace(old, new), str(original) + ":report-only-profile-cohort", "exec"), namespace)
    summary = (out / "summary.md").read_text()
    marker = "\n## Recorded execution interruption"
    require(summary.count(marker) == 1, "Expected recorded interruption note.")
    note = marker + summary.split(marker, 1)[1]
    analysis = json.loads((out / "analysis.json").read_text())
    namespace["render"](ROOT, analysis)
    text = (out / "summary.md").read_text().replace(
        ".\\scripts\\wsl_python.ps1 -PythonArguments @('scripts/audit_sudoku_easy.py','verify')",
        ".\\scripts\\wsl_python.ps1 -PythonArguments @('scripts/finalize_sudoku_easy_r3.py','--verify')")
    text += note
    text += ("\nThe cost-quality figure uses the same 100 development profiling identities for both fixed-depth "
             "and verified quality. The full 400-input development validity is reported separately in the table. "
             "This report-only correction changes no outputs, measurements, analysis or decision.\n")
    (out / "summary.md").write_text(text, encoding="utf-8", newline="\n")
    provenance["report_only_source_sha256"] = {"scripts/finalize_sudoku_easy_r3.py": sha256(Path(__file__))}
    for name in ("summary.md", "audit_comparison.png"):
        provenance["artifacts_sha256"][name] = sha256(out / name)
    save(out / "report_provenance.json", provenance)

if __name__ == "__main__":
    main()
