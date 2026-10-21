"""Run the unchanged official Sudoku evaluator with durable setup metadata."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, choices=(32, 2000), required=True)
    parser.add_argument("--output", required=True, help="New directory beneath results/.")
    parser.add_argument("--batch-size", type=int, default=None)
    args = parser.parse_args()
    output = (ROOT / args.output).resolve()
    if not output.is_relative_to(ROOT / "results"):
        parser.error("Output must be beneath this repository's results directory.")
    if output.exists() and any(output.iterdir()):
        parser.error("Refusing to reuse a nonempty evaluation directory.")
    manifest = ROOT / "docs/partitions/sudoku-hard.json"
    expected = (manifest.parent / "sudoku-hard.sha256").read_text().split()[0]
    manifest_hash = hashlib.sha256(manifest.read_bytes()).hexdigest()
    if manifest_hash != expected:
        raise RuntimeError("Partition manifest has changed since its recorded hash.")
    if not (ROOT / "results/setup/environment.json").exists():
        raise RuntimeError("Run CUDA/environment and artifact recording first.")
    config = ROOT / "third_party/ncm/config/eval/sudoku-hard.yaml"
    command = [sys.executable, "-u", "evaluate.py", "--config", str(config),
               "--checkpoint-dir", str(ROOT / "artifacts/sudoku/hard"),
               "--data-dir", str(ROOT / "data/sudoku/hard"), "--gpus", "0",
               "--n", str(args.n), "--out", str(output)]
    if args.batch_size is not None:
        if args.batch_size <= 0:
            parser.error("Batch size must be positive.")
        command.extend(["--bs", str(args.batch_size)])
    output.mkdir(parents=True, exist_ok=True)
    metadata = {
        "command": command, "cwd": str(ROOT / "third_party/ncm"),
        "sources": json.loads((ROOT / "configs/setup_sources.json").read_text()),
        "partition_manifest_sha256": manifest_hash,
        "protocol_sha256": hashlib.sha256((ROOT / "docs/experiment_protocol.md").read_bytes()).hexdigest(),
        "config_sha256": hashlib.sha256(config.read_bytes()).hexdigest(),
        "requested_examples": args.n, "gpu_ids": [0],
        "batch_size": args.batch_size or 128,
        "sampling": {"temperature": 0.0, "top_k": 0, "top_p": 1.0, "cfg_scale": 0.0},
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "descriptive official reproduction; no policy selection",
        "timing_note": "Process duration includes loading and scoring; not inference latency.",
        "status": "running",
    }
    metadata_path = output / "run.json"
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    started = time.perf_counter()
    environment = dict(os.environ, TOKENIZERS_PARALLELISM="false", OMP_NUM_THREADS="4", MKL_NUM_THREADS="4")
    with (output / "evaluate.log").open("w") as log:
        result = subprocess.Popen(command, cwd=ROOT / "third_party/ncm", env=environment,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        assert result.stdout is not None
        for line in result.stdout:
            log.write(line)
            log.flush()
            print(line, end="", flush=True)
        exit_code = result.wait()
    metadata.update({"status": "complete" if exit_code == 0 else "failed",
                     "exit_code": exit_code,
                     "finished_utc": datetime.now(timezone.utc).isoformat(),
                     "whole_evaluation_process_seconds": time.perf_counter() - started,
                     "environment_overrides": {"TOKENIZERS_PARALLELISM": "false", "OMP_NUM_THREADS": "4", "MKL_NUM_THREADS": "4"}})
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
