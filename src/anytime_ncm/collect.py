"""Offline full-depth collection with frozen partition access and provenance."""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess

from anytime_ncm.dataset import ALLOWED_PARTITIONS, load_examples, sha256
from anytime_ncm.trajectories import TIMING_COMPONENTS, make_record, validate_jsonl

CODE_PATHS = (
    "src/anytime_ncm/collect.py", "src/anytime_ncm/dataset.py",
    "src/anytime_ncm/trajectories.py", "src/anytime_ncm/features.py",
    "src/anytime_ncm/sudoku.py", "src/anytime_ncm/upstream_adapter.py",
    "src/anytime_ncm/cli.py", "scripts/collect_trajectories.py",
)
CONFIG_KEYS = {"schema_version", "task", "run_id", "partitions", "batch_size", "output_path", "smoke_metadata"}


def validate_config(config: dict) -> dict:
    if not isinstance(config, dict) or set(config) != CONFIG_KEYS:
        raise ValueError("Collection config has missing or unknown fields.")
    if type(config["schema_version"]) is not int or config["schema_version"] != 1 or config["task"] != "sudoku-hard":
        raise ValueError("Only schema 1 hard-Sudoku collection is supported.")
    if not isinstance(config["run_id"], str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", config["run_id"]):
        raise ValueError("run_id must be a short lowercase identifier.")
    counts = config["partitions"]
    if not isinstance(counts, dict) or not counts or set(counts) - ALLOWED_PARTITIONS.keys():
        raise ValueError("Collection cannot select sealed holdouts.")
    for name, count in counts.items():
        if type(count) is not int or not 1 <= count <= ALLOWED_PARTITIONS[name]:
            raise ValueError("Partition count is outside its frozen budget.")
    if type(config["batch_size"]) is not int or not 1 <= config["batch_size"] <= 128:
        raise ValueError("Batch size must be an integer in 1..128.")
    if not isinstance(config["output_path"], str) or not config["output_path"].endswith(".jsonl"):
        raise ValueError("Output must be a JSONL path.")
    if config["smoke_metadata"] is not None and not isinstance(config["smoke_metadata"], str):
        raise ValueError("smoke_metadata must be a metadata path or null.")
    if counts != {"exploration": 32} and config["smoke_metadata"] is None:
        raise ValueError("Expansion requires validated 32-input exploration smoke evidence.")
    return config


def output_path(repository: Path, value: str) -> Path:
    path = (repository / value).resolve()
    if not path.is_relative_to((repository / "results").resolve()):
        raise ValueError("Trajectory artifacts must stay beneath repository results/.")
    return path


def source_hashes(repository: Path) -> dict:
    return {name: sha256(repository / name) for name in CODE_PATHS}


def save_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8", newline="\n")


def verify_run(repository: Path, metadata_path: Path) -> dict:
    repository = Path(repository).resolve()
    metadata_path = output_path(repository, str(metadata_path))
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    config = validate_config(metadata["effective_config"])
    if metadata["status"] != "complete" or metadata["source_sha256"] != source_hashes(repository):
        raise ValueError("Collection is incomplete or its source version changed.")
    recorded_config = (repository / metadata["config_path"]).resolve()
    if not recorded_config.is_relative_to(repository) or sha256(recorded_config) != metadata["config_sha256"]:
        raise ValueError("Recorded collection configuration changed.")
    if sha256(repository / "third_party/ncm/config/eval/sudoku-hard.yaml") != metadata["official_config_sha256"]:
        raise ValueError("Official generation configuration changed.")
    path = output_path(repository, config["output_path"])
    if metadata_path != path.with_suffix(".metadata.json"):
        raise ValueError("Metadata path disagrees with its effective config.")
    examples, access = load_examples(repository, config["partitions"])
    if access["manifest_sha256"] != metadata["partition_manifest_sha256"] or access["protocol_sha256"] != metadata["protocol_sha256"]:
        raise ValueError("Recorded frozen identifiers disagree.")
    selected = [{"index": e.index, "partition": e.partition, "puzzle_sha256": e.identity} for e in examples]
    if metadata["selected_examples"] != selected:
        raise ValueError("Recorded selection differs from frozen manifest selection.")
    report = validate_jsonl(path, examples, config["run_id"])
    if metadata["trajectory_sha256"] != report["trajectory_sha256"]:
        raise ValueError("Trajectory checksum changed.")
    if metadata["record_count"] != report["record_count"]:
        raise ValueError("Recorded row count is inconsistent.")
    return dict(report, metadata_path=metadata_path.relative_to(repository).as_posix(),
                source_sha256=metadata["source_sha256"], run_id=config["run_id"],
                partition_manifest_sha256=access["manifest_sha256"],
                protocol_sha256=access["protocol_sha256"])


def write_records(adapter, examples, batch_size, device, run_id, stream) -> None:
    import torch

    for start in range(0, len(examples), batch_size):
        batch = examples[start:start + batch_size]
        context = torch.tensor([example.puzzle for example in batch], dtype=torch.long, device=device)
        codes = adapter.generate_codes(context)
        levels = adapter.decode_prefixes(codes)  # all generation has already finished
        rows = codes.tolist()
        for index, example in enumerate(batch):
            record = make_record(example, run_id, levels, rows[index], index)
            stream.write(json.dumps(record, separators=(",", ":"), allow_nan=False) + "\n")
        stream.flush()
        print(f"collected {min(start + batch_size, len(examples))}/{len(examples)} inputs", flush=True)


def run_collection(repository: Path, config_path: Path, *, overrides: dict | None = None) -> dict:
    from omegaconf import OmegaConf

    repository = Path(repository).resolve()
    config_path = (repository / config_path).resolve()
    if not config_path.is_relative_to(repository):
        raise ValueError("Collection configuration must be inside the repository.")
    config = OmegaConf.to_container(OmegaConf.load(config_path), resolve=True)
    if overrides:
        config.update(overrides)
    config = validate_config(config)
    path = output_path(repository, config["output_path"])
    metadata_path, validation_path = path.with_suffix(".metadata.json"), path.with_suffix(".validation.json")
    if any(p.exists() for p in (path, metadata_path, validation_path)):
        raise ValueError("Refusing to overwrite existing collection artifacts; choose a fresh output/run ID.")
    if config["smoke_metadata"] is not None:
        smoke_path = output_path(repository, config["smoke_metadata"])
        report = verify_run(repository, smoke_path)
        if report["record_count"] != 32 or report["partition_counts"] != {"exploration": 32}:
            raise ValueError("Expansion needs the validated exploration-only 32-input smoke run.")
    examples, access = load_examples(repository, config["partitions"])
    # The Phase 1B adapter must still be the implementation that passed real
    # official-output parity, not an unverified replacement.
    parity = json.loads((repository / "results/phase1/phase1b_verified/verification.json").read_text(encoding="utf-8"))
    if parity["status"] != "complete" or parity["final_decoded_text_matches"] != 32:
        raise ValueError("Successful Phase 1B parity evidence is required.")
    if sha256(repository / "src/anytime_ncm/upstream_adapter.py") != parity["source_sha256"]["src/anytime_ncm/upstream_adapter.py"]:
        raise ValueError("Adapter changed since Phase 1B parity verification.")

    os.environ.update(CUDA_VISIBLE_DEVICES="0", OMP_NUM_THREADS="4", MKL_NUM_THREADS="4", TOKENIZERS_PARALLELISM="false")
    import platform
    import torch
    from anytime_ncm.upstream_adapter import load_sudoku_adapter

    torch.set_num_threads(4)
    if not torch.cuda.is_available():
        raise RuntimeError("The validated collection path requires CUDA.")
    path.parent.mkdir(parents=True, exist_ok=True)
    metadata = {
        "schema_version": 1, "status": "running", "run_id": config["run_id"],
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "base_commit": subprocess.check_output(["git", "-c", f"safe.directory={repository}", "rev-parse", "HEAD"], cwd=repository, text=True).strip(),
        "source_sha256": source_hashes(repository),
        "config_path": config_path.relative_to(repository).as_posix(), "config_sha256": sha256(config_path),
        "effective_config": config, "sources": json.loads((repository / "configs/setup_sources.json").read_text()),
        "checkpoint_artifacts": access["artifacts"],
        "official_config_sha256": sha256(repository / "third_party/ncm/config/eval/sudoku-hard.yaml"),
        "partition_manifest_sha256": access["manifest_sha256"], "protocol_sha256": access["protocol_sha256"],
        "selected_examples": [{"index": e.index, "partition": e.partition, "puzzle_sha256": e.identity} for e in examples],
        "access": {"reader": "restricted protocol-4 token-list scanner; no pickle execution",
                   "file_bytes_traversed": "puzzles and solutions, including structural traversal of sealed rows",
                   "materialized_rows_per_file": len(examples), "sealed_rows_materialized": 0,
                   "holdout_predictions_or_references_inspected": False},
        "execution": {"python": platform.python_version(), "torch": str(torch.__version__),
                      "cuda_runtime": torch.version.cuda, "gpu": torch.cuda.get_device_name(0),
                      "gpu_total_bytes": torch.cuda.get_device_properties(0).total_memory,
                      "cpu_threads": 4, "device": "cuda:0", "precision": "float32, no autocast",
                      "torch_compile": False, "use_kv_cache": False, "warmup_requests": 0,
                      "sampling": {"temperature": 0.0, "top_k": 0, "top_p": 1.0, "cfg_scale": 0.0},
                      "batch_size": config["batch_size"], "batch_size_override_from_baseline": config["batch_size"] != 128,
                      "batch_sizes": [min(config["batch_size"], len(examples) - i) for i in range(0, len(examples), config["batch_size"])]},
        "timing": {"coverage": dict.fromkeys(TIMING_COMPONENTS, 0), "unit": "milliseconds",
                   "provenance": "unmeasured; no diagnostic profiling in Phase 1C",
                   "missing_value": None, "online_speedup_claim": False},
        "feature_scope": "current/past decoded tokens and current code counts; no reference, verifier, or future labels",
        "diagnostic_scope": "reference agreement and official metrics are offline labels, separate from features",
    }
    save_json(metadata_path, metadata)
    try:
        adapter = load_sudoku_adapter(repository)
        with path.open("x", encoding="utf-8", newline="\n") as stream:
            write_records(adapter, examples, config["batch_size"], "cuda", config["run_id"], stream)
        validation = validate_jsonl(path, examples, config["run_id"])
        metadata.update(status="complete", record_count=validation["record_count"], trajectory_sha256=validation["trajectory_sha256"])
        metadata["finished_utc"] = datetime.now(timezone.utc).isoformat()
        save_json(metadata_path, metadata)
        validation = verify_run(repository, metadata_path)
        save_json(validation_path, validation)
        return validation
    except Exception as error:
        metadata.update(status="failed", error=f"{type(error).__name__}: {error}",
                        finished_utc=datetime.now(timezone.utc).isoformat())
        save_json(metadata_path, metadata)
        raise
