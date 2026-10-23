"""Isolated pinned-function online generation; no vendored source mutation."""
import ast
import difflib
import importlib
from pathlib import Path
import torch

from anytime_ncm.online_policy import Observation, stable_decision
from anytime_ncm.sudoku import validate_solution

BOUNDARY = '''
def _phase2_boundary(level, parts, callback, limit):
    active = callback is not None and (not hasattr(callback, "inspection_levels") or level in callback.inspection_levels)
    if not active and (limit is None or level < limit):
        return None
    current = torch.cat(parts, dim=1)
    if active:
        decision = callback(level, current)
        if type(decision) is not bool:
            raise TypeError("A stopping callback must return a Boolean.")
        if decision:
            return current
    if limit is not None and level >= limit:
        return current
    return None
'''

def patched_source(source):
    signature = "cfg_null_eos=50256):"
    first = "        generated_idx = [idx]\n"
    later = "                generated_idx.append(idx_next)\n"
    if any(source.count(anchor) != 1 for anchor in (signature, first, later)):
        raise RuntimeError("Pinned generation boundary changed.")
    result = source.replace(signature, "cfg_null_eos=50256, level_callback=None, level_limit=None):")
    def inserted(indent, level):
        return (indent + f"_phase2_exit = _phase2_boundary({level}, generated_idx, level_callback, level_limit)\n"
                + indent + "if _phase2_exit is not None:\n"
                + indent + "    self._cfg = None\n"
                + indent + "    return _phase2_exit\n")
    result = result.replace(first, first + inserted("        ", "1"))
    result = result.replace(later, later + inserted("                ", "level_idx + 2"))
    return result.rstrip() + "\n" + BOUNDARY

def build_generator(upstream):
    source = (Path(upstream) / "models/next_concept.py").read_text(encoding="utf-8")
    changed = patched_source(source)
    tree = ast.parse(changed)
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "NextConceptTransformer")
    method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "generate")
    helper = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_phase2_boundary")
    method.name = "_phase2_generate"
    namespace = dict(importlib.import_module("models.next_concept").__dict__)
    exec(compile(ast.Module(body=[helper, method], type_ignores=[]), "phase2-isolated-pinned-generate", "exec"), namespace)
    patch = "".join(difflib.unified_diff(source.splitlines(True), changed.splitlines(True),
        fromfile="a/models/next_concept.py", tofile="b/models/next_concept.py"))
    return namespace["_phase2_generate"], patch

class IncrementalLatent:
    def __init__(self, vq):
        self.vq, self.depth, self.total = vq, 0, None

    @torch.no_grad()
    def snapshot(self, codes, depth):
        if type(depth) is not int or not self.depth < depth <= len(self.vq.levels):
            raise ValueError("Incremental reconstruction needs increasing legal depths.")
        if codes.ndim != 2 or codes.shape[0] != 1 or codes.dtype != torch.long or codes.shape[1] != sum(self.vq.levels[:depth]):
            raise ValueError("Only the current complete code prefix may be supplied.")
        if self.total is None:
            self.total = torch.zeros(1, self.vq.levels[-1], self.vq.embed_dim, device=codes.device, dtype=torch.float32)
        for level in range(self.depth, depth):
            start = sum(self.vq.levels[:level]); length = self.vq.levels[level]
            term = self.vq.embeddings[level](codes[:, start:start + length])
            if level != len(self.vq.levels) - 1:
                term = self.vq._up_to_full(term, level, self.vq.levels[-1])
            self.total.add_(self.vq._apply_quant_resi(term, level))
        self.depth = depth
        return self.total.clone()

class OnlineRunner:
    def __init__(self, adapter, upstream):
        self.adapter = adapter
        self.generate, self.patch = build_generator(upstream)

    @torch.no_grad()
    def codes(self, context, *, callback=None, maximum=None):
        generator = self.adapter.generator
        count = len(self.adapter.vq.levels)
        if maximum is not None and (type(maximum) is not int or not 1 <= maximum <= count):
            raise ValueError("Maximum depth outside hierarchy.")
        if context.shape != (1, 91) or context.dtype != torch.long:
            raise ValueError("Online experiment requires one 91-token context.")
        if generator.training or self.adapter.tokenizer.vqvae.training:
            raise ValueError("All models must be in eval mode.")
        if not generator.query_level0 or generator.l0_ar:
            raise ValueError("Only the released query-level-zero eager configuration is supported.")
        try:
            return self.generate(generator, None, context, temperature=0.0, top_k=0, top_p=1.0,
                use_kv_cache=False, cfg_scale=0.0, cfg_null_eos=self.adapter.tokenizer.pre_tokenizer.eos_token_id,
                level_callback=callback, level_limit=maximum)
        finally:
            generator._cfg = None

    @torch.no_grad()
    def request(self, puzzle, spec):
        adapter = self.adapter
        if any(m.training for model in (adapter.generator, adapter.tokenizer.vqvae) for m in model.modules()):
            raise ValueError("All models must be in eval mode.")
        context = torch.tensor([puzzle], dtype=torch.long, device=next(adapter.generator.parameters()).device)
        latest = {}
        previous, unchanged = None, 0
        inspected = []
        monitor = IncrementalLatent(adapter.vq)
        def callback(level, prefix):
            nonlocal previous, unchanged
            if level not in spec["levels"]:
                return False
            latent = monitor.snapshot(prefix, level)
            ids = adapter.pick_tokens(adapter.tokenizer.vqvae.decoder(latent))[0].cpu().tolist()
            text = adapter.decode_ids(ids)
            frame = Observation(level, prefix.shape[1], tuple(ids))
            if spec["kind"] == "verified":
                stop = validate_solution(puzzle, frame.decoded_ids).is_valid_solution
            else:
                stop, previous, unchanged = stable_decision(frame, previous, unchanged, spec["patience"])
            latest.update(ids=ids, text=text, level=level)
            inspected.append(level)
            return bool(stop)
        callback.inspection_levels = frozenset(spec["levels"])
        kind = spec["kind"]
        if kind == "full":
            # Exact released generation without the offline adapter's debug range-check synchronizations.
            codes = adapter.generator.generate(None, context, temperature=0.0, top_k=0, top_p=1.0,
                cfg_scale=0.0, cfg_null_eos=adapter.tokenizer.pre_tokenizer.eos_token_id)
        elif kind == "fixed":
            codes = self.codes(context, maximum=spec["depth"])
        else:
            codes = self.codes(context, callback=callback, maximum=12)
        depth = next(i for i in range(1, len(adapter.vq.levels) + 1) if sum(adapter.vq.levels[:i]) == codes.shape[1])
        if not latest or latest["level"] != depth:
            if depth == len(adapter.vq.levels):
                latent = adapter.vq.idx_to_z_q(codes)
            else:
                latent = monitor.snapshot(codes, depth)
            ids = adapter.pick_tokens(adapter.tokenizer.vqvae.decoder(latent))[0].cpu().tolist()
            latest.update(ids=ids, text=adapter.decode_ids(ids), level=depth)
        return {"decoded_ids": latest["ids"], "decoded_text": latest["text"], "exit_level": depth,
                "generated_codes": codes, "inspected_levels": inspected}

class WorkCounter:
    def __init__(self, adapter, limits):
        self.counts = {"inputs": 0, "generator_levels": 0, "decoder": 0, "encoder": 0}
        self.limits = limits
        self.handles = []
        for module, key in ((adapter.generator.transformer.blocks[0], "generator_levels"),
                            (adapter.tokenizer.vqvae.decoder, "decoder"),
                            (adapter.tokenizer.vqvae.encoder, "encoder")):
            self.handles.append(module.register_forward_pre_hook(lambda *args, name=key: self.take(name)))
    def take(self, key):
        if self.counts[key] >= self.limits[key]:
            raise RuntimeError("Phase 2 work budget exhausted: " + key)
        self.counts[key] += 1
    def close(self):
        for handle in self.handles: handle.remove()
        self.handles.clear()
