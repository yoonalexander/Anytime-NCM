"""Bounded R2 Sudoku screen: pinned access, analysis, and model-free verification."""
import hashlib
import json
from pathlib import Path
import shutil
import urllib.request

from anytime_ncm.dataset import Example, MANIFEST_SHA256, PROTOCOL_SHA256, _TokenRows, puzzle_identity, sha256
from anytime_ncm.diagnosis import board_errors, csv_text, distribution
from anytime_ncm.sudoku import validate_solution
from anytime_ncm.trajectories import decoded_text, validate_record

BASE = "ff8adb713b668ee03a7bff916f2b42c9d2d5113c"
PROTOCOL = "docs/studies/sudoku-checkpoint-screen-protocol.md"
SOURCES_FILE = "configs/r2_sources.json"
OUTPUT = "results/followup/sudoku_checkpoint_screen"
ORDER = ("easy", "medium")
LIMITS = {"official_inputs": 32, "adapter_inputs": 32, "generator_levels": 768,
          "decoder": 416, "encoder": 0, "latent_parity": 32, "independent_prefix": 32}
SOURCE_PATHS = (PROTOCOL, SOURCES_FILE, "src/anytime_ncm/screening.py",
    "src/anytime_ncm/screening_inference.py", "src/anytime_ncm/screening_render.py",
    "scripts/screen_sudoku_checkpoints.py", "tests/test_screening.py",
    "src/anytime_ncm/dataset.py", "src/anytime_ncm/upstream_adapter.py",
    "src/anytime_ncm/trajectories.py", "src/anytime_ncm/diagnosis.py",
    "src/anytime_ncm/sudoku.py", "src/anytime_ncm/target_encoding.py",
    "third_party/ncm/models/next_concept.py", "third_party/ncm/models/quant.py",
    "third_party/ncm/models/vqvae.py", "third_party/ncm/scripts/eval_shard.py",
    "third_party/ncm/tokenization/vqvae_tokenizer.py")


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
                          encoding="utf-8", newline="\n")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def identity_only_hashes(raw, expected_count=2000):
    """Hash token operands incrementally, including reserved inputs; retain no rows."""
    reader = _TokenRows(raw)
    require(reader.data[:2].tobytes() == b"\x80\x04", "Unsupported pickle protocol.")
    reader.position = 2
    reader.expect(ord("]"))
    reader.expect(0x94)
    hashes = []
    while True:
        op = reader.op()
        if op == ord("."):
            break
        require(op == ord("("), "Expected root list batch.")
        while True:
            op = reader.op()
            if op == ord("e"):
                break
            require(op == ord("]") and len(hashes) < expected_count, "Unexpected puzzle row.")
            reader.expect(0x94)
            reader.expect(ord("("))
            digest, length = hashlib.sha256(b"["), 0
            while True:
                op = reader.op()
                if op == ord("e"):
                    break
                require(op == ord("K"), "Unsupported token operand.")
                token = reader.token()
                require(token <= 11 and length < 91, "Malformed puzzle token/length.")
                digest.update((("," if length else "") + str(token)).encode())
                length += 1
            require(length == 91, "Puzzle row must have 91 tokens.")
            digest.update(b"]")
            hashes.append(digest.hexdigest())
    require(len(hashes) == expected_count and reader.position == len(reader.data), "Dataset coverage differs.")
    return hashes


def make_manifest(candidate, hashes, original):
    require(candidate in ORDER, "Unknown candidate.")
    count = original["sample_count"]
    require(len(hashes) == count, "Candidate input count differs.")
    old_by_hash, by_index = {}, {}
    for partition, rows in original["partitions"].items():
        for entry in rows:
            require(entry["index"] not in by_index, "Original indices overlap.")
            by_index[entry["index"]] = partition
            old_by_hash[entry["puzzle_sha256"]] = partition
    require(set(by_index) == set(range(count)), "Original indices incomplete.")
    new_by_hash = dict(old_by_hash)
    for index, identity in enumerate(hashes):
        partition = by_index[index]
        require(identity not in new_by_hash or new_by_hash[identity] == partition,
                "Puzzle identity crosses an inherited reservation.")
        new_by_hash[identity] = partition
    partitions = {name: [{"index": e["index"], "puzzle_sha256": hashes[e["index"]]}
                         for e in sorted(rows, key=lambda r: r["index"])]
                  for name, rows in original["partitions"].items()}
    selected = partitions["exploration"][:32]
    require([e["index"] for e in selected] == list(range(32))
            and len({e["puzzle_sha256"] for e in selected}) == 32,
            "First 32 inputs must be unique exploration identities; no substitutions.")
    return {"schema_version": 1, "study": "R2", "candidate": candidate, "sample_count": count,
            "unique_puzzle_count": len(set(hashes)), "partitions": partitions,
            "inherited_manifest_sha256": MANIFEST_SHA256,
            "shared_solution_sha256": "b52de75f5e4642adca58b18967bcd4bbcafa699c61b21ac33ee0fd7389e0d576",
            "rule": "inherit aligned solution row partitions; reject cross-partition puzzle collisions",
            "selected_indices": list(range(32)), "identity_only_rows_hashed": count,
            "reference_rows_read_for_partitioning": 0}


def release_sources(root):
    source = json.loads((root / SOURCES_FILE).read_text())
    require(source["upstream_commit"] == "c70274273f489abc73832b2b98584a8483b6b203"
            and source["model_revision"] == "d342ce8aaea58830eef3b8ad473664673e41f692"
            and source["dataset_revision"] == "6580ba41a4b0a976dde876fbe84d25327617b0e6"
            and source["candidate_order"] == list(ORDER), "Release pins/order differ.")
    return source


def require_candidate_allowed(root, candidate):
    require(candidate in ORDER, "Unknown candidate.")
    if candidate == "medium":
        easy = verify_candidate(root, "easy")
        require(not easy["qualifies_for_R3"], "Easy qualifies; medium is outside the stop rule.")


def prepare_candidate(root, candidate):
    """Download only active artifacts; freeze partitions before any output inspection."""
    root = Path(root).resolve()
    require_candidate_allowed(root, candidate)
    source = release_sources(root)
    out = root / OUTPUT / candidate
    manifest_path = root / f"docs/partitions/sudoku-{candidate}-r2.json"
    require(not out.exists() and not manifest_path.exists(), "Candidate preflight already exists.")
    require(sha256(root / "docs/partitions/sudoku-hard.json") == MANIFEST_SHA256
            and sha256(root / "docs/experiment_protocol.md") == PROTOCOL_SHA256, "Original reservations changed.")
    out.mkdir(parents=True)
    names = {name: info for name, info in source["files"].items() if f"/sudoku/{candidate}/" in name}
    require(len(names) == 5, "Expected exactly five selected artifacts.")
    record = {"study": "R2", "candidate": candidate, "status": "downloading",
              "source_inventory_sha256": sha256(root / SOURCES_FILE),
              "protocol_sha256": sha256(root / PROTOCOL),
              "disk_free_bytes_before": shutil.disk_usage(root).free,
              "declared_download_bytes": sum(i["size"] for i in names.values()), "files": names}
    save(out / "preflight.json", record)
    try:
        require(record["disk_free_bytes_before"] > 2 * 1024**3, "Insufficient declared disk headroom.")
        for name, info in names.items():
            path = root / name
            if not path.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                print("Downloading " + name, flush=True)
                with urllib.request.urlopen(info["url"], timeout=120) as remote, path.open("xb") as local:
                    shutil.copyfileobj(remote, local)
            require(path.stat().st_size == info["size"] and sha256(path) == info["sha256"],
                    "Pinned download mismatch: " + name)
        puzzle_path = root / f"data/sudoku/{candidate}/puzzles.pickle"
        hashes = identity_only_hashes(puzzle_path.read_bytes())
        original = json.loads((root / "docs/partitions/sudoku-hard.json").read_text())
        manifest = make_manifest(candidate, hashes, original)
        save(manifest_path, manifest)
        record.update(status="complete", manifest_path=manifest_path.relative_to(root).as_posix(),
                      manifest_sha256=sha256(manifest_path), identity_only_puzzle_rows_hashed=2000,
                      selected_rows_materialized=0, reference_rows_materialized=0,
                      generator_calls=0)
        save(out / "preflight.json", record)
        return record
    except Exception as error:
        record.update(status="failed", error=repr(error))
        save(out / "preflight.json", record)
        raise


def candidate_examples(root, candidate):
    root = Path(root)
    require(candidate in ORDER, "Unknown candidate.")
    preflight = json.loads((root / OUTPUT / candidate / "preflight.json").read_text())
    require(preflight["status"] == "complete" and preflight["source_inventory_sha256"] == sha256(root / SOURCES_FILE)
            and preflight["protocol_sha256"] == sha256(root / PROTOCOL), "Preflight is incomplete/changed.")
    require(sha256(root / "docs/partitions/sudoku-hard.json") == MANIFEST_SHA256
            and sha256(root / "docs/experiment_protocol.md") == PROTOCOL_SHA256, "Original reservation changed.")
    expected_files = {n: i for n, i in release_sources(root)["files"].items() if f"/sudoku/{candidate}/" in n}
    require(preflight["files"] == expected_files, "Preflight artifact declarations differ.")
    inputs = {"docs/partitions/sudoku-hard.json": MANIFEST_SHA256,
              "docs/experiment_protocol.md": PROTOCOL_SHA256}
    for name, info in expected_files.items():
        require(sha256(root / name) == info["sha256"], "Candidate artifact changed: " + name)
        inputs[name] = info["sha256"]
    manifest_path = root / preflight["manifest_path"]
    require(sha256(manifest_path) == preflight["manifest_sha256"], "Candidate manifest changed.")
    manifest = json.loads(manifest_path.read_text())
    original = json.loads((root / "docs/partitions/sudoku-hard.json").read_text())
    hashes = identity_only_hashes((root / f"data/sudoku/{candidate}/puzzles.pickle").read_bytes())
    require(manifest == make_manifest(candidate, hashes, original), "Candidate reservations/identities differ.")
    inputs[preflight["manifest_path"]] = sha256(manifest_path)
    inputs[f"{OUTPUT}/{candidate}/preflight.json"] = sha256(root / OUTPUT / candidate / "preflight.json")
    indices = set(manifest["selected_indices"])
    selected = []
    for filename, length in (("puzzles.pickle", 91), ("solutions.pickle", 89)):
        selected.append(_TokenRows((root / f"data/sudoku/{candidate}/{filename}").read_bytes()).select(indices, length, 2000))
    examples = []
    for index in sorted(indices):
        puzzle, reference = selected[0][index], selected[1][index]
        require(puzzle_identity(puzzle) == hashes[index], "Selected puzzle identity differs.")
        require(len(puzzle) == 91 and puzzle[0] == puzzle[-1] == 11
                and decoded_text(puzzle[1:-1]) == decoded_text(puzzle), "Puzzle BOS contract differs.")
        require(all(reference[i] == 10 if (i + 1) % 10 == 0 else 1 <= reference[i] <= 9 for i in range(89)),
                "Reference target format differs.")
        require(validate_solution(puzzle, reference, reference=reference).is_valid_solution, "Invalid reference.")
        examples.append(Example(index, "exploration", hashes[index], puzzle, reference))
    return tuple(examples), inputs


def analyze_candidate(candidate, examples, records):
    require(candidate in ORDER and len(examples) == len(records) == 32, "Incomplete fixed screen.")
    require([e.index for e in examples] == list(range(32)) and all(e.partition == "exploration" for e in examples)
            and len({e.identity for e in examples}) == 32, "Screen selection differs.")
    boards, first_levels = [], []
    for example, record in zip(examples, records, strict=True):
        require(record["dataset_index"] == example.index and record["sample_id"] == example.identity,
                "Paired identity/order differs.")
        trajectory, official = record["trajectory"], record["comparator"]
        validate_record(trajectory, example, "R2-" + candidate)
        require(official["decoded_text"] == decoded_text(official["decoded_ids"]), "Comparator text differs.")
        require(len(official["decoded_ids"]) == 89 and all(type(t) is int and 0 <= t <= 11 for t in official["decoded_ids"]),
                "Malformed comparator tokens.")
        final = trajectory["levels"][-1]
        require(final["decoded_ids"] == official["decoded_ids"] and final["decoded_text"] == official["decoded_text"],
                "Full-depth official/adapter parity failed.")
        checks = record["checks"]
        for key in ("final_latent_bitwise_equal", "independent_prefix_equal", "independent_storage", "finite"):
            require(checks[key] is True, "Recorded reconstruction check failed.")
        require(checks["prefix_shapes"] == [[1, 89, 256]] * 12, "Prefix shape differs.")
        require(record["forward_counts"] == {"official_inputs": 1, "adapter_inputs": 1,
            "generator_levels": 24, "decoder": 13, "encoder": 0, "latent_parity": 1, "independent_prefix": 1},
            "Per-input forward declarations differ.")
        flags = []
        for state in trajectory["levels"]:
            errors = board_errors(example.puzzle, state["decoded_ids"], example.reference)
            require(errors["valid"] == state["correctness"]["is_valid_solution"], "Independent validity differs.")
            flags.append(errors["valid"])
            boards.append({"dataset_index": example.index, "sample_id": example.identity, "level": state["level"],
                "parseable": errors["parseable"], "complete": errors["complete"], "valid": errors["valid"],
                "reference_agreement": errors["reference_agreement"], "given_cells": errors["given_cells"],
                "empty_cells": errors["empty_cells"], **{k: state["diagnostics"][k] for k in
                    ("official_solved", "official_valid_grid", "official_cell_accuracy")},
                **(errors["metrics"] or dict.fromkeys(board_errors(example.puzzle, example.reference, example.reference)["metrics"]))})
        first_levels.append(next((i + 1 for i, flag in enumerate(flags) if flag), None))
    levels = []
    for level in range(1, 13):
        rows = [r for r in boards if r["level"] == level]
        metrics = [k for k in rows[0] if k not in {"dataset_index", "sample_id", "level"}]
        summary = {k: distribution([int(r[k]) if type(r[k]) is bool else r[k] for r in rows]) for k in metrics}
        levels.append({"level": level, "valid_count": sum(r["valid"] for r in rows),
                       "reference_match_count": sum(r["reference_agreement"] for r in rows),
                       "metrics": summary})
    early = [e.index for e, first in zip(examples, first_levels) if first is not None and first < 12]
    never = [e.index for e, first in zip(examples, first_levels) if first is None]
    analysis = {"study": "R2", "candidate": candidate, "inputs": 32, "states": 384,
        "final_parity_inputs": 32, "levels": levels,
        "first_valid_histogram": {str(k): first_levels.count(k) for k in range(1, 13)} | {"never": len(never)},
        "first_valid_by_index": {str(e.index): first for e, first in zip(examples, first_levels)},
        "early_valid_indices": early, "never_valid_indices": never,
        "final_valid_count": levels[-1]["valid_count"], "qualifies_for_R3": bool(early),
        "decision": "qualifies_for_R3" if early else "negative_at_fixed_budget",
        "new_Phase2_go": False, "timed_requests": 0,
        "access": {"identity_only_puzzle_rows_hashed": 2000, "puzzle_rows_materialized": 32,
                   "reference_rows_materialized": 32, "development_rows_materialized": 0,
                   "final_holdout_rows_materialized": 0}}
    return analysis, boards


def verify_candidate(root, candidate):
    root = Path(root).resolve()
    out = root / OUTPUT / candidate
    provenance = json.loads((out / "provenance.json").read_text())
    require(provenance["study"] == "R2" and provenance["candidate"] == candidate, "Provenance identity differs.")
    for group in ("source_sha256", "inputs_sha256"):
        for name, expected in provenance[group].items():
            require(sha256(root / name) == expected, "Source/input hash differs: " + name)
    for name, expected in provenance["artifacts_sha256"].items():
        require(sha256(out / name) == expected, "Output hash differs: " + name)
    examples, inputs = candidate_examples(root, candidate)
    require(inputs == provenance["inputs_sha256"], "Input coverage differs.")
    records = [json.loads(line) for line in (out / "records.jsonl").read_text().splitlines()]
    comparators = [json.loads(line) for line in (out / "comparators.jsonl").read_text().splitlines()]
    require(comparators == [{"dataset_index": r["dataset_index"], "sample_id": r["sample_id"],
                            **r["comparator"]} for r in records], "Raw comparator pairing differs.")
    require(set(provenance["source_sha256"]) == set(SOURCE_PATHS), "Source hash coverage differs.")
    analysis, rows = analyze_candidate(candidate, examples, records)
    require(analysis == json.loads((out / "analysis.json").read_text()), "Recomputed analysis differs.")
    require((out / "board_metrics.csv").read_text() == csv_text(rows), "Recomputed CSV differs.")
    attempt = json.loads((out / "attempt.json").read_text())
    require(attempt["status"] == "complete" and attempt["limits"] == LIMITS and attempt["forward_counts"] == LIMITS
            and attempt["completed_inputs"] == 32, "Incomplete/expanded screen budget.")
    require(attempt["state_before"] == attempt["state_after"], "Recorded model state changed.")
    require(attempt["peak_cuda_allocated_bytes"] <= 6 * 1024**3 and attempt["timed_requests"] == 0
            and attempt["warmups"] == attempt["training_steps"] == 0,
            "Resource/time boundary differs.")
    require(attempt["source_sha256"] == provenance["source_sha256"]
            and attempt["inputs_sha256"] == inputs, "Attempt provenance differs.")
    return analysis


def verify_report(root, analyses):
    path = root / OUTPUT / "report_provenance.json"
    if not path.exists():
        return
    report = json.loads(path.read_text())
    require(report["study"] == "R2", "Report study differs.")
    require(report["candidate_provenance_sha256"] == {
        a["candidate"]: sha256(root / OUTPUT / a["candidate"] / "provenance.json") for a in analyses},
        "Report candidate coverage differs.")
    for name, expected in report["artifacts_sha256"].items():
        require(sha256(root / OUTPUT / name) == expected, "Report artifact changed: " + name)


def verify_screen(root):
    root = Path(root)
    easy = verify_candidate(root, "easy")
    medium_path = root / OUTPUT / "medium"
    if easy["qualifies_for_R3"]:
        require(not medium_path.exists(), "Medium ran after easy qualified.")
        verify_report(root, [easy])
        return [easy]
    require(medium_path.exists(), "Negative easy requires the declared medium screen.")
    medium = verify_candidate(root, "medium")
    easy_attempt = json.loads((root / OUTPUT / "easy/attempt.json").read_text())
    medium_attempt = json.loads((medium_path / "attempt.json").read_text())
    require(easy_attempt["finished_utc"] <= medium_attempt["started_utc"], "Candidate order differs.")
    verify_report(root, [easy, medium])
    return [easy, medium]
