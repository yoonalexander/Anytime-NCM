"""R3 finite CUDA stages; no new policy or online stopping implementation."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys

import torch

from anytime_ncm.audit import (OUTPUT, RUN_ID, COLLECTION_LIMITS, PROFILE_LIMITS,
    config, examples, parse_baseline_log, source_hashes, verify_stage)
from anytime_ncm.dataset import sha256
from anytime_ncm.screening import require, save
from anytime_ncm.screening_inference import load_candidate, checked_prefixes
from anytime_ncm.target_encoding import model_fingerprint
from anytime_ncm.trajectories import make_record, validate_record


class AuditBudget:
    def __init__(self, limits, persist=None):
        self.limits = dict(limits)
        self.counts = dict.fromkeys(limits, 0)
        self.persist = persist
        self.handles = []

    def take(self, name):
        require(name in self.limits and self.counts[name] < self.limits[name], "R3 stage budget exhausted: " + name)
        self.counts[name] += 1
        if name == "inputs" and self.persist:
            self.persist()

    def attach(self, adapter):
        for module, name in ((adapter.generator.transformer.blocks[0], "generator_levels"),
                             (adapter.tokenizer.vqvae.decoder, "decoder"),
                             (adapter.tokenizer.vqvae.encoder, "encoder")):
            self.handles.append(module.register_forward_pre_hook(lambda *args, key=name: self.take(key)))

    def close(self):
        for handle in self.handles:
            handle.remove()
        self.handles.clear()


def begin(root, stage, limits=None):
    root = Path(root).resolve()
    out = root / OUTPUT
    out.mkdir(parents=True, exist_ok=True)
    path = out / (stage + ".json")
    require(not path.exists(), "R3 stage already attempted; no silent retry.")
    _, inputs = examples(root, {"exploration": 32})
    for name in ("records.jsonl", "provenance.json"):
        relative = "results/followup/sudoku_checkpoint_screen/easy/" + name
        inputs[relative] = sha256(root / relative)
    record = {"study": "R3", "stage": stage, "status": "started",
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "base_commit": config(root)["base_commit"], "entry_exception": config(root)["entry_exception"],
        "source_sha256": source_hashes(root), "inputs_sha256": inputs, "artifacts_sha256": {}}
    budget = AuditBudget(limits, lambda: save(path, record)) if limits else None
    if budget:
        record.update(limits=budget.limits, counts=budget.counts)
    save(path, record)
    return out, path, record, budget


def load(root):
    os.environ.update(OMP_NUM_THREADS="4", MKL_NUM_THREADS="4", TOKENIZERS_PARALLELISM="false")
    torch.set_num_threads(4)
    require(torch.cuda.is_available(), "Validated CUDA environment required.")
    return load_candidate(root, "easy")


def state(adapter):
    return {"generator": model_fingerprint(adapter.generator),
            "tokenizer": model_fingerprint(adapter.tokenizer.vqvae)}


def finish(out, path, record, artifacts):
    record.update(status="complete", finished_utc=datetime.now(timezone.utc).isoformat(),
                  artifacts_sha256={name: sha256(out / name) for name in artifacts})
    save(path, record)


def fail(path, record, error):
    record.update(status="failed", error=repr(error), finished_utc=datetime.now(timezone.utc).isoformat())
    save(path, record)


def baseline(root):
    root = Path(root).resolve()
    out, path, record, _ = begin(root, "baseline")
    raw = out / "raw/official_baseline"
    command = [sys.executable, "-u", "evaluate.py",
        "--config", str(root / "third_party/ncm/config/eval/sudoku-easy.yaml"),
        "--checkpoint-dir", str(root / "artifacts/sudoku/easy"),
        "--data-dir", str(root / "data/sudoku/easy"), "--gpus", "0",
        "--n", "2000", "--bs", "1", "--out", str(raw)]
    record.update(command=command, reserved_input_generations=2000, completed_input_generations=0,
        batch_size=1, warmups=0, count_measurement="exact unchanged CLI --n; no module prehooks in official process",
        access="official evaluator internally scores all rows; analyst reads aggregate stdout only; raw pickles ignored")
    save(path, record)
    try:
        env = dict(os.environ, OMP_NUM_THREADS="4", MKL_NUM_THREADS="4", TOKENIZERS_PARALLELISM="false")
        with (out / "baseline.log").open("x", encoding="utf-8", newline="\n") as log:
            process = subprocess.Popen(command, cwd=root / "third_party/ncm", env=env,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in process.stdout:
                log.write(line)
                log.flush()
                print(line, end="", flush=True)
            code = process.wait()
        require(code == 0, "Official R3 baseline process failed.")
        metrics = parse_baseline_log((out / "baseline.log").read_text())
        save(out / "baseline_metrics.json", metrics)
        record.update(completed_input_generations=2000, exit_code=code, raw_predictions_opened_by_analyst=False)
        finish(out, path, record, ["baseline.log", "baseline_metrics.json"])
    except Exception as error:
        fail(path, record, error)
        raise


def collect(root):
    root = Path(root).resolve()
    verify_stage(root, "baseline")
    selected, _ = examples(root, {"exploration": 1000, "development": 400})
    out, path, record, budget = begin(root, "collection", COLLECTION_LIMITS)
    record.update(completed_inputs=0, reused_inputs=32, new_completed_inputs=0, batch_size=1,
                  final_rows_materialized=0, timed_requests=0, warmups=0)
    try:
        adapter = load(root)
        record["state_before"] = state(adapter)
        budget.attach(adapter)
        inherited = [json.loads(line) for line in (root / "results/followup/sudoku_checkpoint_screen/easy/records.jsonl").read_text().splitlines()]
        reused = {row["dataset_index"]: row for row in inherited}
        with (out / "trajectories.jsonl").open("x", encoding="utf-8", newline="\n") as stream, \
             (out / "prefix_checks.jsonl").open("x", encoding="utf-8", newline="\n") as checks_stream:
            for number, example in enumerate(selected, 1):
                if example.index in reused:
                    trajectory = dict(reused[example.index]["trajectory"], run_id=RUN_ID)
                else:
                    budget.take("inputs")
                    context = torch.tensor([example.puzzle], dtype=torch.long, device="cuda")
                    codes = adapter.generate_codes(context)
                    levels, checks = checked_prefixes(adapter, codes, budget)
                    trajectory = make_record(example, RUN_ID, levels, codes[0].tolist(), 0)
                    checks_stream.write(json.dumps({"dataset_index": example.index, "sample_id": example.identity,
                                                    **checks}, separators=(",", ":")) + "\n")
                    checks_stream.flush()
                    record["new_completed_inputs"] += 1
                validate_record(trajectory, example, RUN_ID)
                stream.write(json.dumps(trajectory, separators=(",", ":"), allow_nan=False) + "\n")
                stream.flush()
                record["completed_inputs"] = number
                save(path, record)
                if number % 50 == 0:
                    print(f"R3 collection {number}/1400; new generations {budget.counts['inputs']}/1368", flush=True)
        record["state_after"] = state(adapter)
        require(record["state_before"] == record["state_after"] and budget.counts == COLLECTION_LIMITS
                and record["new_completed_inputs"] == 1368, "R3 collection state/budget differs.")
        finish(out, path, record, ["trajectories.jsonl", "prefix_checks.jsonl"])
    except Exception as error:
        fail(path, record, error)
        raise
    finally:
        budget.close()


def profile(root):
    from anytime_ncm.timing import calibrate_instrumentation, profile_request
    root = Path(root).resolve()
    verify_stage(root, "collection")
    selected, _ = examples(root, {"exploration": 100, "development": 100})
    out, path, record, budget = begin(root, "profiles", PROFILE_LIMITS)
    folder = out / "profiles"
    folder.mkdir()
    metadata = {"schema_version": 1, "status": "running", "timed_records": 0,
        "budget": {"exploration_inputs": 100, "development_inputs": 100, "warmup_requests": 10, "timed_repeats_per_input": 5},
        "source_sha256": source_hashes(root),
        "selected_examples": [{"index": e.index, "sample_id": e.identity, "partition": e.partition} for e in selected],
        "measurement": "unchanged tested timing.py; component-sum diagnostics; no actual online latency"}
    save(folder / "run.json", metadata)
    record.update(timed_records=0, completed_warmups=0, final_rows_materialized=0)
    try:
        adapter = load(root)
        record["state_before"] = state(adapter)
        budget.attach(adapter)
        uninstrumented = {}
        for e in [e for e in selected if e.partition == "exploration"][:10]:
            budget.take("inputs")
            codes = adapter.generate_codes(torch.tensor([e.puzzle], dtype=torch.long, device="cuda"))
            adapter.decode_prefixes(codes)
            uninstrumented[e.identity] = codes[0].tolist()
            record["completed_warmups"] += 1
            save(path, record)
        torch.cuda.synchronize()
        metadata["warmup_indices"] = [e.index for e in selected if e.identity in uninstrumented]
        metadata["instrumentation_calibration"] = calibrate_instrumentation(100)
        torch.cuda.reset_peak_memory_stats()
        hook_checks = repeats = 0
        with (folder / "components.jsonl").open("x", encoding="utf-8", newline="\n") as stream:
            for number, example in enumerate(selected, 1):
                previous = None
                for repeat in range(5):
                    budget.take("inputs")
                    budget.take("latent_parity")
                    row = profile_request(adapter, example, repeat)
                    if example.identity in uninstrumented:
                        require(row["generated_codes"] == uninstrumented[example.identity], "Timing hook code parity failed.")
                        hook_checks += 1
                    if previous is not None:
                        require(row["generated_codes"] == previous, "Greedy repeat changed.")
                        repeats += 1
                    previous = row["generated_codes"]
                    stream.write(json.dumps(row, separators=(",", ":"), allow_nan=False) + "\n")
                    stream.flush()
                    record["timed_records"] += 1
                    save(path, record)
                if number % 10 == 0:
                    print(f"R3 profiled {number}/200 identities, {record['timed_records']}/1000 repeats", flush=True)
        record["state_after"] = state(adapter)
        require(record["state_before"] == record["state_after"] and budget.counts == PROFILE_LIMITS
                and record["completed_warmups"] == 10 and record["timed_records"] == 1000, "R3 profile state/budget differs.")
        metadata.update(status="complete", timed_records=1000, profiled_level_records=12000,
            hook_vs_uninstrumented_code_parity_checks=hook_checks, repeated_code_parity_checks=repeats,
            final_reconstruction_parity_checks=1000, components_sha256=sha256(folder / "components.jsonl"),
            peak_allocated_bytes=torch.cuda.max_memory_allocated(),
            execution={"python": sys.version.split()[0], "torch": torch.__version__, "cuda": torch.version.cuda,
                       "gpu": torch.cuda.get_device_name(), "batch_size": 1, "cpu_threads": 4, "precision": "float32/eval",
                       "compile": False, "autocast": False, "kv_cache": False})
        save(folder / "run.json", metadata)
        finish(out, path, record, ["profiles/run.json", "profiles/components.jsonl"])
    except Exception as error:
        metadata.update(status="failed", error=repr(error))
        save(folder / "run.json", metadata)
        fail(path, record, error)
        raise
    finally:
        budget.close()
