"""R2 float32 CUDA execution; released comparator body and frozen prefix adapter."""
import ast
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

import torch
from torch.nn import functional as F
from omegaconf import OmegaConf

from anytime_ncm.screening import (BASE, LIMITS, OUTPUT, SOURCE_PATHS, analyze_candidate,
    candidate_examples, require, require_candidate_allowed, save)
from anytime_ncm.dataset import sha256
from anytime_ncm.diagnosis import csv_text
from anytime_ncm.target_encoding import model_fingerprint
from anytime_ncm.trajectories import make_record, validate_record
from anytime_ncm.upstream_adapter import (PINNED_UPSTREAM, SUDOKU_LEVELS, SudokuAdapter,
    _import_upstream, reconstruct_prefixes)


class ScreenBudget:
    def __init__(self, persist=None):
        self.counts = dict.fromkeys(LIMITS, 0)
        self.handles = []
        self.persist = persist

    def take(self, name):
        require(name in LIMITS and self.counts[name] < LIMITS[name], "Screen budget exhausted: " + name)
        self.counts[name] += 1
        if name in ("official_inputs", "adapter_inputs") and self.persist:
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


def load_candidate(root, candidate):
    upstream = root / "third_party/ncm"
    command = ["git", "-c", f"safe.directory={upstream}", "-C", str(upstream)]
    require(subprocess.check_output(command + ["rev-parse", "HEAD"], text=True).strip() == PINNED_UPSTREAM,
            "Upstream pin changed.")
    require(not subprocess.check_output(command + ["-c", "core.autocrlf=true", "status", "--porcelain"], text=True).strip(),
            "Upstream checkout is dirty.")
    path = root / f"artifacts/sudoku/{candidate}/config.yaml"
    official = upstream / f"config/eval/sudoku-{candidate}.yaml"
    require(path.read_text() == official.read_text(), "Released/official config differs.")
    config = OmegaConf.load(path)
    require(config.task == "sudoku-" + candidate and config.model.prefix_len == 91
            and config.tokenizer.vqvae.context_length == 89 and config.tokenizer.vqvae.embed_dim == 256
            and list(config.model.vocab_size) == [16] * 12
            and dict(config.generation) == {"temperature": 0.0, "top_k": 0, "top_p": 1.0, "cfg_scale": 0.0},
            "Released inference contract differs.")
    _import_upstream(upstream)
    from tokenization.vqvae_tokenizer import VQVAETokenizer
    from models.next_concept import NextConceptTransformer
    checkpoint = root / f"artifacts/sudoku/{candidate}"
    config.tokenizer.vqvae.checkpoint_path = str(checkpoint / config.checkpoints.tokenizer)
    tokenizer = VQVAETokenizer.from_config(config.tokenizer)
    tokenizer.vqvae = tokenizer.vqvae.cuda().eval()
    generator = NextConceptTransformer(vqvae_local=tokenizer.vqvae, config=config.model).cuda()
    state = torch.load(checkpoint / config.checkpoints.generator, map_location="cpu", weights_only=False)
    generator.load_state_dict(state["model"], strict=True)
    del state
    generator.eval()
    adapter = SudokuAdapter(tokenizer, generator, upstream)
    require(tuple(adapter.vq.levels) == SUDOKU_LEVELS and len(generator.transformer.blocks) == 8
            and generator.query_level0 and not generator.l0_ar, "Candidate hierarchy/generator differs.")
    require(not adapter.vq.learned_all_sampling and adapter.vq.quant_resi_enabled
            and not adapter.vq.learned_l1_cascade_norm, "Independent reconstruction contract differs.")
    require(all(not m.training for model in (generator, tokenizer.vqvae) for m in model.modules())
            and all(p.dtype == torch.float32 for model in (generator, tokenizer.vqvae) for p in model.parameters()),
            "Require float32/eval for all models.")
    return adapter


def official_runner(adapter, upstream):
    """Compile verbatim pinned functions; skip evaluator CLI/data-loading side effects."""
    names = {"prefix", "pick_tokens", "dec", "run"}
    tree = ast.parse((upstream / "scripts/eval_shard.py").read_text())
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    require({n.name for n in nodes} == names, "Official comparator functions missing.")
    tk = adapter.tokenizer
    namespace = dict(torch=torch, net=adapter.generator, tk=tk, RAW=[], P=91, src_tok=None,
        EOS=tk.pre_tokenizer.eos_token_id, PAD=tk.pre_tokenizer.pad_token_id,
        CUT_AT_EOS=True, freq=0.0, ADJ=None, ALLOW=None, mu=0.0,
        temp=0.0, top_k=0, top_p=1.0, cfg=0.0)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(upstream / "scripts/eval_shard.py"), "exec"), namespace)
    return namespace


@torch.no_grad()
def independent_prefixes(vq, codes):
    """Functional arithmetic oracle; no adapter/private upsample/residual helpers."""
    total = torch.zeros(codes.shape[0], vq.levels[-1], vq.embed_dim, device=codes.device)
    result, offset = [], 0
    for level, length in enumerate(vq.levels):
        term = F.embedding(codes[:, offset:offset + length], vq.embeddings[level].weight).transpose(1, 2)
        if level == 0 and vq.learned_l1_sampling:
            layers = list(vq.learned_up_l1) if isinstance(vq.learned_up_l1, torch.nn.Sequential) else [vq.learned_up_l1]
            for layer in layers:
                require(isinstance(layer, torch.nn.ConvTranspose1d), "Unsupported independent cascade operation.")
                term = F.conv_transpose1d(term, layer.weight, layer.bias, layer.stride, layer.padding,
                                          layer.output_padding, layer.groups, layer.dilation)
        elif level != len(vq.levels) - 1:
            term = F.interpolate(term, size=vq.levels[-1], mode="linear")
        term = term.contiguous()
        if vq.quant_resi_enabled:
            layer = vq.quant_resi[level / max(len(vq.levels) - 1, 1)]
            ratio = layer.resi_ratio
            term = term * (1 - ratio) + F.conv1d(term, layer.weight, layer.bias,
                stride=layer.stride, padding=layer.padding, dilation=layer.dilation, groups=layer.groups) * ratio
        total.add_(term.transpose(1, 2).contiguous())
        result.append(total.clone())
        offset += length
    return tuple(result)


@torch.no_grad()
def checked_prefixes(adapter, codes, budget):
    from anytime_ncm.upstream_adapter import DecodedPrefix
    snapshots = reconstruct_prefixes(adapter.vq, codes)
    budget.take("independent_prefix")
    independent = independent_prefixes(adapter.vq, codes)
    equal = all(torch.equal(a, b) for a, b in zip(snapshots, independent, strict=True))
    budget.take("latent_parity")
    _, official = adapter.vq.idx_to_zhats(codes, return_zlevels=True)
    final_equal = torch.equal(snapshots[-1], official[-1])
    storage = len({p.untyped_storage().data_ptr() for p in snapshots}) == 12
    finite = all(bool(torch.isfinite(p).all()) for p in snapshots)
    shapes = [list(p.shape) for p in snapshots]
    require(equal and final_equal and storage and finite and shapes == [[1, 89, 256]] * 12,
            "Candidate prefix reconstruction/parity failed.")
    prefixes, cumulative = [], 0
    for level, (length, latent) in enumerate(zip(adapter.vq.levels, snapshots, strict=True), 1):
        cumulative += length
        ids, texts = adapter.decode_latent(latent)
        prefixes.append(DecodedPrefix(level, length, cumulative, ids, texts))
    return tuple(prefixes), {"final_latent_bitwise_equal": final_equal, "independent_prefix_equal": equal,
        "independent_storage": storage, "finite": finite, "prefix_shapes": shapes}


def collect_candidate(root, candidate):
    root = Path(root).resolve()
    require_candidate_allowed(root, candidate)
    examples, inputs = candidate_examples(root, candidate)
    out = root / OUTPUT / candidate
    require(not (out / "attempt.json").exists(), "Candidate attempt already exists; no silent retries.")
    sources = {name: sha256(root / name) for name in SOURCE_PATHS}
    budget = ScreenBudget()
    attempt = {"study": "R2", "candidate": candidate, "base_commit": BASE, "status": "started",
        "started_utc": datetime.now(timezone.utc).isoformat(), "completed_inputs": 0,
        "limits": LIMITS, "forward_counts": budget.counts, "source_sha256": sources,
        "inputs_sha256": inputs, "timed_requests": 0, "warmups": 0, "training_steps": 0}
    save(out / "attempt.json", attempt)
    budget.persist = lambda: save(out / "attempt.json", attempt)
    records = []
    try:
        torch.set_num_threads(4)
        require(torch.cuda.is_available(), "Declared CUDA environment unavailable.")
        torch.cuda.reset_peak_memory_stats()
        adapter = load_candidate(root, candidate)
        comparator = official_runner(adapter, root / "third_party/ncm")
        attempt["state_before"] = {"generator": model_fingerprint(adapter.generator),
                                   "tokenizer": model_fingerprint(adapter.tokenizer.vqvae)}
        budget.attach(adapter)
        save(out / "attempt.json", attempt)
        with (out / "comparators.jsonl").open("x", encoding="utf-8", newline="\n") as official_stream, \
             (out / "records.jsonl").open("x", encoding="utf-8", newline="\n") as stream:
            for example in examples:
                before = dict(budget.counts)
                context = torch.tensor([comparator["prefix"](example.puzzle)], dtype=torch.long, device="cuda")
                budget.take("official_inputs")
                texts = comparator["run"](context)
                official = {"decoded_ids": comparator["RAW"][-1], "decoded_text": texts[0]}
                official_stream.write(json.dumps({"dataset_index": example.index, "sample_id": example.identity,
                                                   **official}, separators=(",", ":")) + "\n")
                official_stream.flush()
                budget.take("adapter_inputs")
                codes = adapter.generate_codes(context)
                outputs, checks = checked_prefixes(adapter, codes, budget)
                trajectory = make_record(example, "R2-" + candidate, outputs, codes[0].tolist(), 0)
                validate_record(trajectory, example, "R2-" + candidate)
                record = {"dataset_index": example.index, "sample_id": example.identity, "comparator": official,
                    "trajectory": trajectory, "checks": checks,
                    "forward_counts": {k: budget.counts[k] - before[k] for k in LIMITS}}
                # Retain both raw paths even if their final outputs fail parity.
                stream.write(json.dumps(record, separators=(",", ":"), allow_nan=False) + "\n")
                stream.flush()
                require(official["decoded_ids"] == trajectory["levels"][-1]["decoded_ids"]
                        and official["decoded_text"] == trajectory["levels"][-1]["decoded_text"], "Final comparator parity failed.")
                records.append(record)
                attempt["completed_inputs"] = len(records)
                save(out / "attempt.json", attempt)
                print(candidate + ": " + str(len(records)) + "/32 paired inputs complete", flush=True)
        attempt["state_after"] = {"generator": model_fingerprint(adapter.generator),
                                  "tokenizer": model_fingerprint(adapter.tokenizer.vqvae)}
        attempt["peak_cuda_allocated_bytes"] = torch.cuda.max_memory_allocated()
        attempt["execution"] = {"python": sys.version.split()[0], "torch": torch.__version__,
            "cuda_runtime": torch.version.cuda, "gpu": torch.cuda.get_device_name(),
            "batch_size": 1, "precision": "float32; no autocast", "cpu_threads": 4,
            "compile": False, "kv_cache_override": None, "warmups": 0,
            "generator_level_counter": "first transformer block prehook",
            "comparator": "verbatim pinned eval_shard prefix/pick_tokens/dec/run; selected rows only"}
        require(attempt["state_before"] == attempt["state_after"] and budget.counts == LIMITS,
                "Model state changed or budget incomplete.")
        require(attempt["peak_cuda_allocated_bytes"] <= 6 * 1024**3, "Declared memory fit ceiling exceeded.")
        analysis, boards = analyze_candidate(candidate, examples, records)
        save(out / "analysis.json", analysis)
        (out / "board_metrics.csv").write_text(csv_text(boards), encoding="utf-8", newline="\n")
        attempt.update(status="complete", finished_utc=datetime.now(timezone.utc).isoformat())
        save(out / "attempt.json", attempt)
        save(out / "provenance.json", {"study": "R2", "candidate": candidate, "base_commit": BASE,
            "source_sha256": sources, "inputs_sha256": inputs,
            "artifacts_sha256": {name: sha256(out / name) for name in
                ("attempt.json", "comparators.jsonl", "records.jsonl", "analysis.json", "board_metrics.csv")},
            "access": analysis["access"], "forward_counts": dict(budget.counts)})
        print(json.dumps({"candidate": candidate, "early": analysis["early_valid_indices"],
                          "final_valid": analysis["final_valid_count"], "decision": analysis["decision"]}), flush=True)
        return analysis
    except Exception as error:
        attempt.update(status="failed", error=repr(error), finished_utc=datetime.now(timezone.utc).isoformat())
        save(out / "attempt.json", attempt)
        raise
    finally:
        budget.close()
