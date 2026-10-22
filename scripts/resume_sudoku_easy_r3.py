"""Amendment-1 R3 continuation: preserve completed work; retry metadata I/O only."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from anytime_ncm.audit import OUTPUT, COLLECTION_LIMITS, RUN_ID, examples, source_hashes
from anytime_ncm.dataset import sha256
from anytime_ncm.screening import require

AMENDMENT = "docs/studies/sudoku-easy-r3-resumption-amendment.md"
EXTRA = (AMENDMENT, "scripts/resume_sudoku_easy_r3.py", "tests/test_audit_resume.py")


def extra_hashes(root=ROOT):
    return {name: sha256(root / name) for name in EXTRA}


def atomic_save(path, value):
    """Retry only bounded filesystem writes/replaces, never the wrapped model work."""
    path = Path(path)
    if isinstance(value, dict) and value.get("study") == "R3" and "stage" in value:
        value["execution_amendment_sha256"] = extra_hashes()
    data = json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
    for attempt in range(10):
        temporary = None
        try:
            fd, name = tempfile.mkstemp(prefix=".r3-write-", suffix=".tmp", dir=path.parent)
            temporary = Path(name)
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
                stream.write(data)
            os.replace(temporary, path)
            return
        except OSError:
            if attempt == 9:
                raise
            time.sleep(.05)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)


def verify_failed_prefix(root=ROOT):
    out = root / OUTPUT
    snapshot = json.loads((out / "failed_collection_snapshot.json").read_text())
    require(sha256(out / "collection.failed_attempt_1.json") == snapshot["failed_metadata_sha256"],
            "Failed-attempt receipt changed.")
    require(sha256(out / "tests.pre_resume.xml") == snapshot["initial_tests_sha256"], "Initial test receipt changed.")
    for name, info in snapshot["prefixes"].items():
        with (out / name).open("rb") as stream:
            prefix = stream.read(info["bytes"])
        require(hashlib.sha256(prefix).hexdigest() == info["sha256"], "Completed pre-resumption bytes changed.")
    return snapshot


def check_resume_counts(record, rows, checks):
    new = len(rows) - 32
    expected = {"inputs": new + 1, "generator_levels": new * 12, "decoder": new * 12,
                "encoder": 0, "latent_parity": new, "independent_prefix": new}
    require(record["status"] == "failed" and record["counts"] == expected
            and record["completed_inputs"] == len(rows) and record["new_completed_inputs"] == new
            and len(checks) == new, "Interrupted work is not exactly one pre-generation pending slot.")
    require(len(rows) == 499 and new == 467, "Amendment 1 applies only to the recorded 499-row interruption.")


def resume_collection(root=ROOT):
    import torch
    import anytime_ncm.audit_inference as ai
    from anytime_ncm.screening_inference import checked_prefixes
    from anytime_ncm.trajectories import make_record, validate_record
    out = root / OUTPUT
    path = out / "collection.json"
    require(not (out / "collection.failed_attempt_1.json").exists(), "Resumption already attempted.")
    record = json.loads(path.read_text())
    rows = [json.loads(line) for line in (out / "trajectories.jsonl").read_text().splitlines()]
    checks = [json.loads(line) for line in (out / "prefix_checks.jsonl").read_text().splitlines()]
    check_resume_counts(record, rows, checks)
    require(record["source_sha256"] == source_hashes(root), "Original R3 sources changed.")
    selected, _ = examples(root, {"exploration": 1000, "development": 400})
    for example, row in zip(selected, rows):
        validate_record(row, example, RUN_ID)
    require([r["dataset_index"] for r in checks] == [r["dataset_index"] for r in rows[32:]],
            "Pre-resumption check coverage differs.")
    (out / "collection.failed_attempt_1.json").write_bytes(path.read_bytes())
    (out / "tests.pre_resume.xml").write_bytes((out / "tests.xml").read_bytes())
    snapshot = {"failed_metadata_sha256": sha256(out / "collection.failed_attempt_1.json"),
        "initial_tests_sha256": sha256(out / "tests.pre_resume.xml"),
        "completed_rows": len(rows), "completed_new_generations": len(checks),
        "pending_reserved_dataset_index": selected[len(rows)].index, "prefixes": {}}
    for name in ("trajectories.jsonl", "prefix_checks.jsonl"):
        p = out / name
        snapshot["prefixes"][name] = {"bytes": p.stat().st_size, "sha256": sha256(p)}
    atomic_save(out / "failed_collection_snapshot.json", snapshot)
    ai.save = atomic_save
    budget = ai.AuditBudget(COLLECTION_LIMITS, lambda: atomic_save(path, record))
    budget.counts.update(record["counts"])
    record["counts"] = budget.counts
    record["prior_error"] = record.pop("error")
    record.update(status="resuming", resumption_started_utc=datetime.now(timezone.utc).isoformat(),
        resumption_remaining_inputs=len(selected) - len(rows), reused_pending_input_slot=True,
        interruption_end_state_fingerprint_available=False)
    atomic_save(path, record)
    try:
        adapter = ai.load(root)
        require(ai.state(adapter) == record["state_before"], "Reloaded checkpoint differs from original starting state.")
        record["resumed_state_before"] = ai.state(adapter)
        budget.attach(adapter)
        with (out / "trajectories.jsonl").open("a", encoding="utf-8", newline="\n") as stream, \
             (out / "prefix_checks.jsonl").open("a", encoding="utf-8", newline="\n") as checks_stream:
            for number, example in enumerate(selected[len(rows):], len(rows) + 1):
                if number != len(rows) + 1:
                    budget.take("inputs")
                # First resumed identity uses its already reserved, never executed slot.
                context = torch.tensor([example.puzzle], dtype=torch.long, device="cuda")
                codes = adapter.generate_codes(context)
                levels, checked = checked_prefixes(adapter, codes, budget)
                trajectory = make_record(example, RUN_ID, levels, codes[0].tolist(), 0)
                validate_record(trajectory, example, RUN_ID)
                checks_stream.write(json.dumps({"dataset_index": example.index, "sample_id": example.identity,
                                                 **checked}, separators=(",", ":")) + "\n")
                checks_stream.flush()
                stream.write(json.dumps(trajectory, separators=(",", ":"), allow_nan=False) + "\n")
                stream.flush()
                record["new_completed_inputs"] += 1
                record["completed_inputs"] = number
                atomic_save(path, record)
                if number % 50 == 0:
                    print(f"R3 resumed collection {number}/1400; total new generations {budget.counts['inputs']}/1368", flush=True)
        record["state_after"] = ai.state(adapter)
        require(record["resumed_state_before"] == record["state_after"] == record["state_before"]
                and budget.counts == COLLECTION_LIMITS and record["completed_inputs"] == 1400,
                "Resumed collection state/budget differs.")
        verify_failed_prefix(root)
        ai.finish(out, path, record, ["trajectories.jsonl", "prefix_checks.jsonl",
            "collection.failed_attempt_1.json", "failed_collection_snapshot.json", "tests.pre_resume.xml"])
    except Exception as error:
        ai.fail(path, record, error)
        raise
    finally:
        budget.close()


def verify_amendment(root=ROOT):
    out = root / OUTPUT
    expected = extra_hashes(root)
    for name in ("collection", "profiles"):
        record = json.loads((out / (name + ".json")).read_text())
        require(record["execution_amendment_sha256"] == expected, "Execution amendment source changed.")
    verify_failed_prefix(root)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("collect", "profile", "analyze", "verify"))
    args = parser.parse_args()
    if args.stage == "collect":
        resume_collection()
    elif args.stage == "profile":
        import anytime_ncm.audit_inference as ai
        ai.save = atomic_save
        ai.profile(ROOT)
    elif args.stage == "analyze":
        from anytime_ncm.audit import analyze
        analyze(ROOT)
        out = ROOT / OUTPUT
        path = out / "summary.md"
        note = ("\n## Recorded execution interruption\n\n"
            "The first collection process stopped on a metadata filesystem-write error after 499 saved trajectories "
            "(467 new generations). The next input was reserved but had not executed. "
            "A dated [resumption amendment](../../../" + AMENDMENT + ") retained all completed bytes and completed "
            "the 901 unrun inputs using the same total budget, with no repeated model evaluation. "
            "The [failed attempt](collection.failed_attempt_1.json) and "
            "[pre-resumption byte receipts](failed_collection_snapshot.json) are preserved. "
            "The interrupted process has no measured end-state fingerprint; the resumed process reloaded the exact "
            "starting state and matched it at completion. Profiling used bounded atomic metadata I/O outside timed regions.\n")
        path.write_text(path.read_text() + note, encoding="utf-8", newline="\n")
        prov = json.loads((out / "report_provenance.json").read_text())
        prov["artifacts_sha256"]["summary.md"] = sha256(path)
        prov["execution_amendment_sha256"] = extra_hashes()
        atomic_save(out / "report_provenance.json", prov)
    else:
        from anytime_ncm.audit import verify
        verify_amendment()
        result = verify(ROOT)
        prov = json.loads((ROOT / OUTPUT / "report_provenance.json").read_text())
        require(prov["execution_amendment_sha256"] == extra_hashes(), "Report amendment source changed.")
        print("R3 easy verified: " + result["decision"])
        print(result["profile_costs"]["development"]["paired"])
        require("torch" not in sys.modules and "matplotlib" not in sys.modules,
                "Saved-data verification imported model/plot libraries.")
        print("PASS: original sources, amendment, retained prefixes and model-free analysis.")


if __name__ == "__main__":
    main()
