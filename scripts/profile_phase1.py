"""Run only the predeclared Phase 1D diagnostic budget; no online halting."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from anytime_ncm.collect import output_path, save_json, verify_run
from anytime_ncm.dataset import load_examples, sha256

SOURCE_PATHS = (
    "src/anytime_ncm/timing.py", "scripts/profile_phase1.py",
    "src/anytime_ncm/upstream_adapter.py", "src/anytime_ncm/sudoku.py",
    "src/anytime_ncm/features.py", "src/anytime_ncm/dataset.py",
    "docs/phase1d_analysis_plan.md",
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="results/phase1/profiles")
    args = parser.parse_args()
    output = output_path(ROOT, args.output)
    if output.exists():
        raise ValueError("Profile directory already exists; prior evidence is preserved.")
    validation = verify_run(ROOT, Path("results/phase1/trajectories.metadata.json"))
    examples, access = load_examples(ROOT, {"exploration": 100, "development": 100})
    os.environ.update(CUDA_VISIBLE_DEVICES="0", OMP_NUM_THREADS="4", MKL_NUM_THREADS="4", TOKENIZERS_PARALLELISM="false")
    import platform
    import torch
    from anytime_ncm.timing import calibrate_instrumentation, profile_request
    from anytime_ncm.upstream_adapter import load_sudoku_adapter
    torch.set_num_threads(4)
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA required.")
    output.mkdir(parents=True)
    metadata = {
        "schema_version": 1, "status": "running", "purpose": "offline diagnostic components, not headline online latency",
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "base_commit": subprocess.check_output(["git", "-c", f"safe.directory={ROOT}", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "source_sha256": {name: sha256(ROOT / name) for name in SOURCE_PATHS},
        "sources": json.loads((ROOT / "configs/setup_sources.json").read_text()),
        "collection_validation": validation, "protocol_sha256": access["protocol_sha256"],
        "partition_manifest_sha256": access["manifest_sha256"],
        "checkpoint_artifacts": access["artifacts"],
        "selected_examples": [{"index": e.index, "sample_id": e.identity, "partition": e.partition} for e in examples],
        "budget": {"exploration_inputs": 100, "development_inputs": 100, "warmup_requests": 10, "timed_repeats_per_input": 5},
        "execution": {"python": platform.python_version(), "torch": str(torch.__version__), "cuda": torch.version.cuda,
                      "gpu": torch.cuda.get_device_name(0), "gpu_total_bytes": torch.cuda.get_device_properties(0).total_memory,
                      "batch_size": 1, "batch_size_override_from_official_baseline": True, "cpu_threads": 4,
                      "precision": "float32; no autocast", "torch_compile": False, "kv_cache": False,
                      "sampling": {"temperature": 0.0, "top_k": 0, "top_p": 1.0, "cfg_scale": 0.0}},
        "measurement": {"generation": "CUDA events at start, 11 next-embedding prehooks, and final return; no interior synchronization",
                        "components": "isolated CUDA-event plus synchronized wall regions; host stages perf_counter_ns",
                        "excluded": ["model loading", "warmup", "reference scoring", "serialization"],
                        "feature_cost": "profiled, unused by the verifier-only candidate",
                        "assembly": "profiled at every depth; reused original concatenation at level 12 in estimates",
                        "latency_claim": "component-sum estimate only; no online inference measurement"},
        "access": {"sealed_rows_materialized": 0, "holdout_predictions_or_references_inspected": False},
    }
    path = output / "run.json"
    save_json(path, metadata)
    try:
        adapter = load_sudoku_adapter(ROOT)
        warmups = [e for e in examples if e.partition == "exploration"][:10]
        uninstrumented = {}
        print("Warming up ten exploration-only requests...", flush=True)
        for example in warmups:
            context = torch.tensor([example.puzzle], dtype=torch.long, device="cuda")
            codes = adapter.generate_codes(context)
            adapter.decode_prefixes(codes)
            uninstrumented[example.identity] = codes[0].tolist()
        torch.cuda.synchronize()
        metadata["warmup_indices"] = [e.index for e in warmups]
        metadata["instrumentation_calibration"] = calibrate_instrumentation()
        torch.cuda.reset_peak_memory_stats()
        parity_checks = repeat_checks = 0
        with (output / "components.jsonl").open("x", encoding="utf-8", newline="\n") as stream:
            for number, example in enumerate(examples, 1):
                prior_codes = None
                for repeat in range(5):
                    record = profile_request(adapter, example, repeat)
                    if example.identity in uninstrumented:
                        if record["generated_codes"] != uninstrumented[example.identity]:
                            raise RuntimeError("Observation hooks changed generated codes.")
                        parity_checks += 1
                    if prior_codes is not None:
                        if record["generated_codes"] != prior_codes:
                            raise RuntimeError("Greedy repeat output changed.")
                        repeat_checks += 1
                    prior_codes = record["generated_codes"]
                    stream.write(json.dumps(record, separators=(",", ":"), allow_nan=False) + "\n")
                stream.flush()
                if number % 10 == 0:
                    print(f"profiled {number}/200 identities, {number * 5}/1000 repeats", flush=True)
        metadata.update(status="complete", timed_records=1000, profiled_level_records=12000,
                        hook_vs_uninstrumented_code_parity_checks=parity_checks,
                        repeated_code_parity_checks=repeat_checks,
                        final_reconstruction_parity_checks=1000,
                        peak_allocated_bytes=torch.cuda.max_memory_allocated(),
                        components_sha256=sha256(output / "components.jsonl"),
                        finished_utc=datetime.now(timezone.utc).isoformat())
        save_json(path, metadata)
        print("PASS: 200 identities x 5 repeats; all diagnostic final reconstructions matched upstream.", flush=True)
    except Exception as error:
        metadata.update(status="failed", error=f"{type(error).__name__}: {error}",
                        finished_utc=datetime.now(timezone.utc).isoformat())
        save_json(path, metadata)
        raise


if __name__ == "__main__":
    main()
