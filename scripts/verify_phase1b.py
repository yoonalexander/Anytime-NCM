"""Verify Phase 1B against a fresh unchanged official 32-input evaluator run.

Exploration-only parity evidence; no trajectory-quality analysis or timing claim.
"""

from datetime import datetime, timezone
import argparse
import hashlib
import json
import os
from pathlib import Path
import pickle
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import torch
from anytime_ncm.upstream_adapter import load_sudoku_adapter, reconstruct_prefixes

# Exact frozen digest (kept explicit so a changed manifest cannot authorize access).
MANIFEST_SHA256 = "ed7a6b3c102fe4713a3f80f8f02b53afe37a44b53da80964936467617799bdb7"
PROTOCOL_SHA256 = "557cf1377fe49b6c8515f506856ff0a395f8aaabe32adc79c25a8f2d9a3929ef"


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def smoke_inputs(manifest, puzzles):
    """Only the predetermined first 32 exploration identities may be returned."""
    allowed = {entry["index"]: entry["puzzle_sha256"] for entry in manifest["partitions"]["exploration"]}
    selected = []
    for index in range(32):
        if index not in allowed:
            raise RuntimeError(f"Smoke input {index} is not in exploration.")
        item = [int(value) for value in puzzles[index]]
        identity = hashlib.sha256(json.dumps(item, separators=(",", ":")).encode()).hexdigest()
        if identity != allowed[index]:
            raise RuntimeError(f"Smoke input identity mismatch at {index}.")
        if len(item) != 91:
            raise RuntimeError("Official Sudoku input is not 91 tokens.")
        selected.append(item)
    return selected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="results/phase1/phase1b", help="Fresh directory beneath results/.")
    args = parser.parse_args()
    output = (ROOT / args.output).resolve()
    if not output.is_relative_to(ROOT / "results"):
        parser.error("Output must be beneath results/.")
    os.environ.update(OMP_NUM_THREADS="4", MKL_NUM_THREADS="4", TOKENIZERS_PARALLELISM="false",
                      CUDA_VISIBLE_DEVICES="0")
    torch.set_num_threads(4)
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required for matched official parity.")
    if output.exists() and any(output.iterdir()):
        raise RuntimeError("Use a fresh evidence directory; previous results are never overwritten.")
    manifest_path = ROOT / "docs/partitions/sudoku-hard.json"
    protocol_path = ROOT / "docs/experiment_protocol.md"
    if digest(manifest_path) != MANIFEST_SHA256 or digest(protocol_path) != PROTOCOL_SHA256:
        raise RuntimeError("Frozen manifest/protocol mismatch.")
    artifacts = json.loads((ROOT / "results/setup/artifacts.json").read_text())
    for artifact in artifacts:
        # Includes the reference file's checksum only, with no unpickling here.
        if digest(ROOT / artifact["path"]) != artifact["sha256"]:
            raise RuntimeError(f"Artifact checksum mismatch: {artifact['path']}")
    manifest = json.loads(manifest_path.read_text())
    with (ROOT / "data/sudoku/hard/puzzles.pickle").open("rb") as stream:
        puzzles = pickle.load(stream)
    items = smoke_inputs(manifest, puzzles)
    del puzzles
    output.mkdir(parents=True, exist_ok=True)
    record = {
        "schema_version": 1, "milestone": "Phase 1B", "status": "running",
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "base_commit": subprocess.check_output(["git", "-c", f"safe.directory={ROOT}", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "sources": json.loads((ROOT / "configs/setup_sources.json").read_text()),
        "protocol_sha256": PROTOCOL_SHA256, "partition_manifest_sha256": MANIFEST_SHA256,
        "input_indices": list(range(32)), "partition": "exploration",
        "batch_size_setting": 128, "effective_batch_size": 32,
        "sampling": {"temperature": 0.0, "top_k": 0, "top_p": 1.0, "cfg_scale": 0.0},
        "precision": "float32, no autocast", "torch_compile": False, "use_kv_cache": False,
        "environment": {"python": platform.python_version(), "torch": str(torch.__version__),
                        "cuda": torch.version.cuda, "gpu": torch.cuda.get_device_name(0),
                        "cpu_threads": torch.get_num_threads()},
        "access": {
            "inputs": "puzzles.pickle deserialized; only indices 0..31 selected and identity-checked",
            "references": "official evaluator internally loads reference pickle; output restricted to first 32 exploration inputs",
            "comparison": "only first 32 exploration hypotheses from fresh official output; reference fields not inspected",
            "holdout_predictions_or_references_inspected": False,
            "intermediate_quality_analysis": False,
        },
        "timing_claim": "None; this is correctness/parity verification, not latency measurement.",
    }
    evidence = output / "verification.json"
    def save():
        evidence.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")

    save()
    try:
        # Match loading, batching, sampling, precision, and input order in a
        # completely independent invocation of the unchanged official evaluator.
        command = [sys.executable, "-u", str(ROOT / "scripts/run_upstream_baseline.py"),
                   "--n", "32", "--output", (output / "official").relative_to(ROOT).as_posix()]
        record["official_command"] = command
        save()
        print("Running unchanged official smoke evaluator...", flush=True)
        subprocess.run(command, cwd=ROOT, check=True)
        adapter = load_sudoku_adapter(ROOT)
        context = torch.tensor(items, dtype=torch.long, device="cuda")
        codes = adapter.generate_codes(context)
        original_codes = codes.clone()
        snapshots = reconstruct_prefixes(adapter.vq, codes)
        expected_shape = (32, 89, 256)
        if len(snapshots) != 12 or any(tuple(z.shape) != expected_shape for z in snapshots):
            raise AssertionError("Not all 12 prefixes have full resolution.")
        if len({z.untyped_storage().data_ptr() for z in snapshots}) != 12:
            raise AssertionError("Prefix storage aliases.")
        official_hats, official_levels = adapter.vq.idx_to_zhats(codes, return_zlevels=True)
        if not torch.equal(snapshots[-1], official_levels[-1]):
            raise AssertionError("Final latent differs from official reconstruction.")
        del official_hats, official_levels

        # Perturb every code strictly after k and compare all prefixes <= k.
        # This verifies isolation for each of the 11 proper prefixes on real
        # generated codes; no future output is used as a policy feature.
        isolation = []
        for depth in range(1, 12):
            changed = codes.clone()
            cursor = sum(adapter.vq.levels[:depth])
            for level in range(depth, 12):
                length = adapter.vq.levels[level]
                changed[:, cursor:cursor + length] = (
                    changed[:, cursor:cursor + length] + 1
                ) % adapter.vq.embeddings[level].num_embeddings
                cursor += length
            altered = reconstruct_prefixes(adapter.vq, changed)
            if not all(torch.equal(a, b) for a, b in zip(snapshots[:depth], altered[:depth])):
                raise AssertionError(f"Future-code leakage at depth {depth}.")
            isolation.append(depth)
        decoded = adapter.decode_prefixes(codes)
        if [tuple(result.token_ids.shape) for result in decoded] != [(32, 89)] * 12:
            raise AssertionError("Decoded prefixes do not all have 89 positions.")
        final_ids, final_text = adapter.decode_latent(snapshots[-1])
        if not torch.equal(final_ids, decoded[-1].token_ids):
            raise AssertionError("Public prefix API disagrees with final decoding.")
        with (output / "official/shard_0.pkl").open("rb") as stream:
            official = pickle.load(stream)
        if official["idxs"] != list(range(32)):
            raise AssertionError("Official comparator contains unexpected inputs.")
        matches = [left == right for left, right in zip(final_text, official["hyps"], strict=True)]
        if len(matches) != 32 or not all(matches):
            raise AssertionError(f"Official final-text parity failed: {sum(matches)}/32.")
        if not torch.equal(codes, original_codes):
            raise AssertionError("Reconstruction changed the generated codes.")
        if any(p.requires_grad for p in snapshots):
            raise AssertionError("Inference reconstruction retained an autograd graph.")
        record.update({
            "status": "complete", "generated_code_shape": list(codes.shape),
            "levels": list(adapter.vq.levels), "prefix_latent_shape": list(expected_shape),
            "prefix_count": len(snapshots), "decoded_token_shape_per_level": [32, 89],
            "independent_storage": True, "later_code_isolation_depths_passed": isolation,
            "final_latent_bitwise_equal_to_upstream": True,
            "final_decoded_text_matches": sum(matches), "compared_inputs": len(matches),
            "input_codes_unchanged": True,
            "official_score_log": (output / "official/evaluate.log").relative_to(ROOT).as_posix(),
            "artifacts_verified": artifacts,
        })
        print("PASS: all 12 full-resolution prefixes; isolation at depths 1..11; final-text parity 32/32.", flush=True)
    except Exception as error:
        record.update(status="failed", error=f"{type(error).__name__}: {error}")
        raise
    finally:
        record["finished_utc"] = datetime.now(timezone.utc).isoformat()
        paths = [
            "src/anytime_ncm/upstream_adapter.py", "tests/test_partial_decoder.py",
            "tests/test_full_depth_equivalence.py", "scripts/verify_phase1b.py",
            "third_party/ncm/models/quant.py", "third_party/ncm/scripts/eval_shard.py",
            "third_party/ncm/config/eval/sudoku-hard.yaml",
        ]
        record["source_sha256"] = {name: digest(ROOT / name) for name in paths}
        save()


if __name__ == "__main__":
    main()
