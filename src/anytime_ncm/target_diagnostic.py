"""R1B selection, descriptive analysis, and model-free evidence verification."""

from collections import Counter
import json
from pathlib import Path

from anytime_ncm.dataset import load_examples, select_entries, sha256
from anytime_ncm.diagnosis import INPUTS as PHASE1_INPUTS, board_errors, transition_errors, distribution, csv_text
from anytime_ncm.sudoku import parse_board
from anytime_ncm.trajectories import decoded_text, label_output, validate_record, LEVEL_LENGTHS

PROTOCOL = "docs/studies/sudoku-target-encoding-protocol.md"
DEFAULT_OUTPUT = "results/followup/sudoku_target_encoding"
SOURCES = (
    PROTOCOL, "src/anytime_ncm/target_diagnostic.py", "src/anytime_ncm/target_encoding.py",
    "src/anytime_ncm/target_diagnostic_render.py", "scripts/diagnose_target_encoding.py",
    "tests/test_target_encoding.py", "src/anytime_ncm/diagnosis.py",
    "src/anytime_ncm/upstream_adapter.py", "src/anytime_ncm/dataset.py",
    "src/anytime_ncm/sudoku.py", "src/anytime_ncm/trajectories.py",
    "third_party/ncm/models/vqvae.py", "third_party/ncm/models/quant.py",
    "third_party/ncm/tokenization/vqvae_tokenizer.py", "third_party/ncm/scripts/eval_shard.py",
)
LIMITS = {"encoder": 32, "decoder": 384, "final_latent": 32}


def save_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def prepare_pilot(repository):
    repository = Path(repository)
    for name, expected in PHASE1_INPUTS.items():
        if sha256(repository / name) != expected:
            raise ValueError("Historical Phase 1 input changed: " + name)
    examples, access = load_examples(repository, {"exploration": 32})
    if tuple(e.index for e in examples) != tuple(range(32)) or any(e.partition != "exploration" for e in examples):
        raise ValueError("R1B requires exactly exploration indices 0–31.")
    metadata = json.loads((repository / "results/phase1/trajectories.metadata.json").read_text())
    manifest = json.loads((repository / "docs/partitions/sudoku-hard.json").read_text())
    selection = select_entries(manifest, {"exploration": 1000, "development": 400})
    if metadata["status"] != "complete" or metadata["selected_examples"] != list(selection):
        raise ValueError("Historical selection/collection contract changed.")
    if access["artifacts"] != metadata["checkpoint_artifacts"]:
        raise ValueError("Frozen artifact declarations disagree.")
    generated = []
    with (repository / "results/phase1/trajectories.jsonl").open(encoding="utf-8") as stream:
        for example in examples:
            line = stream.readline()
            if not line:
                raise ValueError("Missing cached pilot trajectory.")
            record = json.loads(line)
            validate_record(record, example, metadata["run_id"])
            generated.append(record)
    input_hashes = dict(PHASE1_INPUTS)
    input_hashes.update({r["path"]: r["sha256"] for r in access["artifacts"]})
    access = {"selected_puzzle_rows": 32, "selected_reference_rows": 32,
              "cached_generated_records_deserialized": 32, "development_records_deserialized": 0,
              "holdout_records_deserialized": 0, "sealed_rows_materialized": access["sealed_rows_materialized"]}
    return examples, generated, access, input_hashes


def check_target_record(record, example):
    if (record["dataset_index"], record["sample_id"], record["partition"]) != (example.index, example.identity, "exploration"):
        raise ValueError("Target-record selection mismatch.")
    codes = record["target_codes"]
    if len(codes) != sum(LEVEL_LENGTHS) or any(type(v) is not int or not 0 <= v < 16 for v in codes):
        raise ValueError("Malformed target code sequence.")
    if len(record["levels"]) != 12 or [s["level"] for s in record["levels"]] != list(range(1, 13)):
        raise ValueError("Target record must contain all 12 levels in order.")
    for state in record["levels"]:
        label_output(example, state["decoded_ids"], state["decoded_text"])
    checks = record["checks"]
    if checks["forward_counts"] != {"encoder": 1, "decoder": 12, "final_latent": 1}:
        raise ValueError("Target record exceeds or omits declared forwards.")
    if checks["prefix_shapes"] != [[1, 89, 256]] * 12 or not all(checks[k] is True for k in
            ("independent_prefix_storage", "final_latent_bitwise_equal", "encoded_codes_unchanged")):
        raise ValueError("Missing real prefix/parity declarations.")
    if checks["final_latent_max_abs_error"] != 0.0:
        raise ValueError("Final latent parity failed.")


def analyze_pilot(examples, generated, targets):
    if len(examples) != 32 or len(generated) != 32 or len(targets) != 32:
        raise ValueError("The fixed pilot must retain all 32 examples.")
    boards, changes, paths, observations = [], [], {}, {}
    for path, records in (("generated_saved", generated), ("target_encoded", targets)):
        histogram, per_input = Counter(), {}
        exact_failures, board_failures, primary_failures = [], [], []
        for example, record in zip(examples, records, strict=True):
            if example.partition != "exploration":
                raise ValueError("Only exploration may enter R1B analysis.")
            if path == "target_encoded":
                check_target_record(record, example)
            elif (record["dataset_index"], record["sample_id"], record["partition"]) != (example.index, example.identity, "exploration"):
                raise ValueError("Cached comparator identity mismatch.")
            rows = []
            header = {"path": path, "dataset_index": example.index, "sample_id": example.identity}
            for k, state in enumerate(record["levels"], 1):
                correctness, diagnostics, board = label_output(example, state["decoded_ids"], state["decoded_text"])
                measured = board_errors(example.puzzle, state["decoded_ids"], example.reference)
                metric = measured["metrics"]
                row = header | {"level": k, "parseable": measured["parseable"], "complete": measured["complete"],
                    "valid": measured["valid"], "reference_agreement": measured["reference_agreement"],
                    "exact_reference_tokens": state["decoded_ids"] == list(example.reference),
                    "official_solved": diagnostics["official_solved"], "official_valid_grid": diagnostics["official_valid_grid"],
                    "official_cell_accuracy": diagnostics["official_cell_accuracy"],
                    "given_cells": measured["given_cells"], "empty_cells": measured["empty_cells"]} | (metric or {})
                rows.append(row)
                if k > 1:
                    delta = transition_errors(example.puzzle, record["levels"][k - 2]["decoded_ids"], state["decoded_ids"], example.reference)
                    changes.append(header | {"from_level": k - 1, "to_level": k, "parseable": delta is not None} | (delta or {}))
            per_input[example.index] = rows
            boards.extend(rows)
            first = next((row["level"] for row in rows if row["valid"]), None)
            histogram[str(first) if first else "never"] += 1
            if not rows[-1]["exact_reference_tokens"]:
                exact_failures.append(example.index)
            if not rows[-1]["reference_agreement"]:
                board_failures.append(example.index)
            if not rows[-1]["valid"]:
                primary_failures.append(example.index)
        metric_names = list(board_errors(examples[0].puzzle, examples[0].reference, examples[0].reference)["metrics"])
        for row in boards:
            if row["path"] == path:
                for name in metric_names:
                    row.setdefault(name, None)
        levels = []
        for k in range(12):
            selected = [r[k] for r in per_input.values()]
            valid_rows = [r for r in selected if r["parseable"]]
            accuracy = [r["official_cell_accuracy"] for r in selected]
            given = sum(r["given_cells"] for r in valid_rows)
            empty = sum(r["empty_cells"] for r in valid_rows)
            levels.append({
                "level": k + 1, "inputs": 32,
                "parseable_count": len(valid_rows), "complete_count": sum(r["complete"] for r in selected),
                "valid_count": sum(r["valid"] for r in selected),
                "reference_agreement_count": sum(r["reference_agreement"] for r in selected),
                "exact_reference_token_count": sum(r["exact_reference_tokens"] for r in selected),
                "official_solved_count": sum(r["official_solved"] for r in selected),
                "official_valid_grid_count": sum(r["official_valid_grid"] for r in selected),
                "official_cell_accuracy_defined_count": sum(v is not None for v in accuracy),
                "official_cell_accuracy_mean": sum(accuracy) / 32 if all(v is not None for v in accuracy) else None,
                "given_cell_opportunities": given, "empty_cell_opportunities": empty,
                "metrics": {name: distribution([r[name] for r in selected]) for name in metric_names},
            })
        transition_rows = [r for r in changes if r["path"] == path]
        metric_changes = list(transition_errors(examples[0].puzzle, examples[0].reference, examples[0].reference, examples[0].reference))
        for row in transition_rows:
            for name in metric_changes:
                row.setdefault(name, None)
        paths[path] = {
            "inputs": 32, "levels": levels,
            "boundaries": [{"from_level": k, "to_level": k + 1,
                "metrics": {name: distribution([r[name] for r in transition_rows if r["from_level"] == k]) for name in metric_changes}}
                for k in range(1, 12)],
            "first_valid_counts": {str(k): histogram[str(k)] for k in range(1, 13)} | {"never": histogram["never"]},
            "early_valid_inputs": sum(histogram[str(k)] for k in range(1, 12)),
            "ever_valid_inputs": 32 - histogram["never"],
            "final_primary_failure_indices": primary_failures,
            "final_board_reference_mismatch_indices": board_failures,
            "final_token_mismatch_indices": exact_failures,
        }
        observations[path] = per_input
    paired, cases = [], {}
    for k in range(12):
        g, t = observations["generated_saved"], observations["target_encoded"]
        paired.append({"level": k + 1,
                       "target_valid_generated_invalid": sum(t[i][k]["valid"] and not g[i][k]["valid"] for i in t),
                       "generated_valid_target_invalid": sum(g[i][k]["valid"] and not t[i][k]["valid"] for i in t),
                       "target_minus_generated_wrong_cells": distribution([
                           t[i][k]["wrong_reference_cells"] - g[i][k]["wrong_reference_cells"]
                           if t[i][k]["parseable"] and g[i][k]["parseable"] else None for i in t])})
    for example, target, generated_record in zip(examples, targets, generated, strict=True):
        i = example.index
        target_rows, generated_rows = observations["target_encoded"][i], observations["generated_saved"][i]
        predicates = {
            "target_early_valid_generated_not_early": any(r["valid"] for r in target_rows[:-1]) and not any(r["valid"] for r in generated_rows[:-1]),
            "target_no_early_validity": not any(r["valid"] for r in target_rows[:-1]),
            "target_final_primary_failure": not target_rows[-1]["valid"],
            "target_final_token_mismatch": not target_rows[-1]["exact_reference_tokens"],
        }
        for name, applies in predicates.items():
            if applies and name not in cases:
                cases[name] = {"dataset_index": i, "sample_id": example.identity,
                    "puzzle": list(parse_board(example.puzzle).cells), "reference": list(parse_board(example.reference).cells),
                    "target_levels": [s["decoded_text"] for s in target["levels"]],
                    "generated_levels": [s["decoded_text"] for s in generated_record["levels"]]}
    names = ("target_early_valid_generated_not_early", "target_no_early_validity",
             "target_final_primary_failure", "target_final_token_mismatch")
    target_path = paths["target_encoded"]
    if target_path["final_primary_failure_indices"] or target_path["final_token_mismatch_indices"]:
        outcome = "final_round_trip_failures"
        next_action = "Investigate recorded target reconstruction failures before broadening the study; no automatic adapter-bug or causal conclusion."
    elif target_path["early_valid_inputs"]:
        outcome = "early_target_opportunity"
        next_action = "Scope a separate generated-code/target-prefix investigation; references are diagnostic, not a deployable policy."
    else:
        outcome = "no_early_target_opportunity"
        next_action = "Recommend R2 bounded easy-then-conditional-medium checkpoint screening under its own frozen protocol."
    return {"schema_version": 1, "study": "R1B", "paths": paths, "paired_by_level": paired,
            "representative_cases": {n: cases.get(n) for n in names},
            "outcome": outcome, "next_action": next_action}, boards, changes


def collect_pilot(repository, output):
    import datetime
    import sys
    import torch
    from anytime_ncm.target_encoding import ForwardBudget, load_tokenizer, encode_target_prefixes, model_fingerprint
    repository, output = Path(repository).resolve(), Path(output).resolve()
    if not output.is_relative_to(repository / "results/followup") or output.exists():
        raise ValueError("Use a fresh output directory inside results/followup/.")
    examples, generated, access, inputs = prepare_pilot(repository)
    source_hashes = {n: sha256(repository / n) for n in SOURCES}
    output.mkdir(parents=True)
    budget = ForwardBudget()
    attempt = {"study": "R1B", "status": "started", "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
               "limits": LIMITS, "forward_counts": budget.counts, "completed_inputs": 0,
               "source_sha256": source_hashes, "inputs_sha256": inputs, "access": access,
               "generator_calls": 0, "generator_constructed": False, "timed_requests": 0}
    save_json(output / "attempt.json", attempt)
    targets = []
    try:
        torch.set_num_threads(4)
        if not torch.cuda.is_available():
            raise RuntimeError("The declared CUDA environment is unavailable.")
        vae, pick, decode = load_tokenizer(repository)
        budget.attach(vae)
        before = model_fingerprint(vae)
        attempt["model_state_before_sha256"] = before
        with (output / "targets.jsonl").open("x", encoding="utf-8", newline="") as stream:
            for example in examples:
                tensor = torch.tensor([example.reference], dtype=torch.long, device="cuda")
                record = {"dataset_index": example.index, "sample_id": example.identity, "partition": "exploration"} | encode_target_prefixes(vae, tensor, pick, decode, budget)
                check_target_record(record, example)
                stream.write(json.dumps(record, separators=(",", ":")) + "\n")
                stream.flush()
                targets.append(record)
                attempt["completed_inputs"] = len(targets)
                save_json(output / "attempt.json", attempt)
        after = model_fingerprint(vae)
        attempt["model_state_after_sha256"] = after
        if before != after or budget.counts != LIMITS:
            raise RuntimeError("Model state changed or pilot budget coverage differs.")
        attempt["execution"] = {"python": sys.version.split()[0], "torch": torch.__version__,
            "cuda_runtime": torch.version.cuda, "gpu": torch.cuda.get_device_name(),
            "batch_size": 1, "cpu_threads": 4, "precision": "float32; no autocast",
            "compile": False, "warmups": 0, "generator_module_loaded": "models.next_concept" in sys.modules}
        if attempt["execution"]["generator_module_loaded"]:
            raise RuntimeError("Generator module was unexpectedly loaded.")
        analysis, boards, changes = analyze_pilot(examples, generated, targets)
        save_json(output / "analysis.json", analysis)
        (output / "board_metrics.csv").write_text(csv_text(boards), encoding="utf-8", newline="\n")
        (output / "transition_metrics.csv").write_text(csv_text(changes), encoding="utf-8", newline="\n")
        from anytime_ncm.target_diagnostic_render import render_report
        render_report(repository, output, analysis)
        attempt["status"] = "complete"
        attempt["finished_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        save_json(output / "attempt.json", attempt)
        names = ["targets.jsonl", "attempt.json", "analysis.json", "board_metrics.csv",
                 "transition_metrics.csv", "summary.md", "prefix_comparison.png"]
        save_json(output / "provenance.json", {"study": "R1B", "status": "complete",
            "base_commit": "ee043228ede0a95a82bf6033211a2168d7ec3add",
            "inputs_sha256": inputs, "source_sha256": source_hashes,
            "artifacts_sha256": {n: sha256(output / n) for n in names},
            "coverage": {"references": 32, "target_states": 384, "cached_generated_states": 384,
                         "board_rows": len(boards), "transition_rows": len(changes)},
            "forward_counts": dict(budget.counts), "access": access})
        return analysis
    except Exception as error:
        attempt["status"] = "failed"
        attempt["error"] = repr(error)
        save_json(output / "attempt.json", attempt)
        raise
    finally:
        budget.close()


def verify_pilot(repository, output):
    repository, output = Path(repository).resolve(), Path(output).resolve()
    if not output.is_relative_to(repository / "results/followup"):
        raise ValueError("Report must be inside results/followup/.")
    provenance = json.loads((output / "provenance.json").read_text())
    for kind in ("inputs_sha256", "source_sha256"):
        for name, expected in provenance[kind].items():
            if sha256(repository / name) != expected:
                raise ValueError("Frozen input/source changed: " + name)
    for name, expected in provenance["artifacts_sha256"].items():
        if sha256(output / name) != expected:
            raise ValueError("Stored artifact changed: " + name)
    examples, generated, access, inputs = prepare_pilot(repository)
    if access != provenance["access"] or inputs != provenance["inputs_sha256"]:
        raise ValueError("Pilot access/input declarations differ.")
    with (output / "targets.jsonl").open(encoding="utf-8") as stream:
        targets = [json.loads(line) for line in stream]
    attempt = json.loads((output / "attempt.json").read_text())
    if attempt["status"] != "complete" or attempt["forward_counts"] != LIMITS or attempt["completed_inputs"] != 32:
        raise ValueError("Incomplete or expanded pilot execution.")
    if attempt["model_state_before_sha256"] != attempt["model_state_after_sha256"]:
        raise ValueError("Recorded tokenizer state changed.")
    if attempt["generator_calls"] != 0 or attempt["generator_constructed"] or attempt["timed_requests"] != 0:
        raise ValueError("Out-of-scope model activity.")
    if attempt["execution"]["generator_module_loaded"]:
        raise ValueError("Generator module unexpectedly loaded.")
    analysis, boards, changes = analyze_pilot(examples, generated, targets)
    if analysis != json.loads((output / "analysis.json").read_text()):
        raise ValueError("Recomputed R1B analysis differs.")
    for name, rows in (("board_metrics.csv", boards), ("transition_metrics.csv", changes)):
        if (output / name).read_text(encoding="utf-8") != csv_text(rows):
            raise ValueError("Recomputed table differs: " + name)
    return analysis
