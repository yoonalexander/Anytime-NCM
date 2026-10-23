"""Apply a narrow reporting clarification without changing frozen Phase 4 execution."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"results/phase4/wmt14"
OLD="Whole baseline duration includes loading/processing and is not warm request latency."
NEW="The recorded baseline process_seconds covers the batch loop and scoring after model/data loading; separate model-load time was not recorded. It is not warm request latency."
NOTE="""

## Report-only clarification and resampling limits

Frozen execution sources, policies and quantitative results are unchanged. The [original renderer output](summary.initial.md) is retained. The [report finalizer](../../../scripts/finalize_phase4_report.py) corrects only the baseline elapsed-clock description and adds these limitations; it performs zero model calls.

Effective-prefix grouping prevents identical model-input leakage. Original news-document group IDs are not supplied in the selected two-string-list release. Sentence-identity bootstrap intervals are conditional on that unit and this benchmark process; they do not establish document-level or across-process replication.

If intentionally regenerating the report from saved records, run the report stage and then this finalizer:

~~~powershell
.\\scripts\\wsl_python.ps1 -PythonArguments @('scripts/run_phase4.py','report')
python scripts/finalize_phase4_report.py
~~~

The usual saved-data verify command checks the amended report, retained original and finalizer hashes.
"""
def main():
    summary=OUT/"summary.md";initial=OUT/"summary.initial.md";current=summary.read_text(encoding="utf-8")
    original=initial.read_text(encoding="utf-8") if initial.exists() else current
    if original.count(OLD)!=1:raise ValueError("Expected exactly one original baseline timing description.")
    corrected=original.replace(OLD,NEW)+NOTE
    if current not in (original,corrected):raise ValueError("Unexpected report edits; refusing to overwrite.")
    if not initial.exists():initial.write_text(original,encoding="utf-8",newline="\n")
    summary.write_text(corrected,encoding="utf-8",newline="\n")
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    path=OUT/"report_provenance.json";prov=json.loads(path.read_text(encoding="utf-8"))
    prov["artifacts"].update({"summary.md":sha(summary),"summary.initial.md":sha(initial),
                             "../../../scripts/finalize_phase4_report.py":sha(Path(__file__))})
    prov["report_only_correction"]={"scope":"baseline clock wording and resampling limitations",
        "original_summary_sha256":sha(initial),"corrected_summary_sha256":sha(summary),
        "finalizer_sha256":sha(Path(__file__)),"additional_model_calls":0,
        "policies_execution_and_quantitative_results_unchanged":True}
    path.write_text(json.dumps(prov,indent=2,sort_keys=True)+"\n",encoding="utf-8",newline="\n")
    print("Phase 4 report-only clarification complete; quantitative results unchanged.")
if __name__=="__main__":main()
