"""Frozen hard-Sudoku loading and offline full-resolution prefix decoding.

Private upstream dependencies: MultiscaleResidualVectorQuantizer._up_to_full
and ._apply_quant_resi at PINNED_UPSTREAM. No generation callbacks or halting.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
import importlib
from pathlib import Path
import subprocess
import sys
from typing import Any

import torch

PINNED_UPSTREAM = "c70274273f489abc73832b2b98584a8483b6b203"
CONFIG_SHA256 = "8d58c49e6fe52e60191e06df4061937d5bb84f97c5ffbcd93ed9830c32f8df2f"
SUDOKU_LEVELS = (1, 2, 4, 6, 9, 13, 18, 26, 37, 50, 67, 89)


def _import_upstream(upstream: Path) -> None:
    """Expose the vendored absolute imports, rejecting namespace collisions."""
    upstream = upstream.resolve()
    for name, module in tuple(sys.modules.items()):
        if name.split(".")[0] in {"models", "tokenization", "utils"}:
            filename = getattr(module, "__file__", None)
            if filename is None or not Path(filename).resolve().is_relative_to(upstream):
                raise RuntimeError(f"Upstream import namespace collision: {name}")
    if str(upstream) not in sys.path:
        sys.path.insert(0, str(upstream))
    importlib.invalidate_caches()


def _evaluator_helpers(upstream: Path, tokenizer: Any) -> tuple[Any, Any]:
    """Compile only actual pinned pick_tokens/dec definitions, never CLI I/O.

    Sudoku uses the evaluator's default zero frequency/adjacency penalties.
    Importing eval_shard normally would parse argv and run the evaluator.
    """
    source = upstream / "scripts/eval_shard.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    names = {"pick_tokens", "dec"}
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    if {n.name for n in nodes} != names:
        raise RuntimeError("Pinned evaluator helpers are missing.")
    namespace = {
        "torch": torch, "freq": 0.0, "ADJ": None, "ALLOW": None, "mu": 0.0,
        "CUT_AT_EOS": True, "EOS": tokenizer.pre_tokenizer.eos_token_id,
        "PAD": tokenizer.pre_tokenizer.pad_token_id, "tk": tokenizer,
    }
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), "exec"), namespace)
    return namespace["pick_tokens"], namespace["dec"]


def _check_codes(vq: Any, codes: torch.Tensor) -> None:
    if codes.ndim != 2 or codes.shape[0] == 0 or codes.shape[1] != sum(vq.levels):
        raise ValueError("Expected a nonempty batch of complete multilevel code sequences.")
    if codes.dtype != torch.long:
        raise ValueError("Code IDs must have dtype torch.long.")
    offset = 0
    for length, embedding in zip(vq.levels, vq.embeddings, strict=True):
        chunk = codes[:, offset:offset + length]
        if bool(((chunk < 0) | (chunk >= embedding.num_embeddings)).any()):
            raise ValueError("Code ID is outside its level's codebook.")
        offset += length


@torch.no_grad()
def reconstruct_prefixes(vq: Any, codes: torch.Tensor) -> tuple[torch.Tensor, ...]:
    """Snapshot each cumulative prefix at full length, after full generation.

    The float32 accumulator and operation order deliberately match upstream
    idx_to_zhats. Clones happen inside the loop, before subsequent add_ calls.
    """
    _check_codes(vq, codes)
    accumulator = torch.zeros(
        codes.shape[0], vq.levels[-1], vq.embed_dim, device=codes.device,
        dtype=torch.float32,
    )
    snapshots = []
    offset = 0
    for level, length in enumerate(vq.levels):
        contribution = vq.embeddings[level](codes[:, offset:offset + length])
        if level != len(vq.levels) - 1:
            contribution = vq._up_to_full(contribution, level, vq.levels[-1])
        contribution = vq._apply_quant_resi(contribution, level)
        if contribution.shape != accumulator.shape:
            raise RuntimeError("Upstream reconstruction no longer has full resolution.")
        accumulator.add_(contribution)
        snapshots.append(accumulator.clone())
        offset += length
    return tuple(snapshots)


@dataclass(frozen=True)
class DecodedPrefix:
    level: int                     # one-based
    code_length: int
    cumulative_codes: int
    token_ids: torch.Tensor        # [batch, 89], remains on inference device
    texts: tuple[str, ...]


class SudokuAdapter:
    """Offline adapter for the released deterministic hard-Sudoku configuration."""

    def __init__(self, tokenizer: Any, generator: Any, upstream: Path):
        self.tokenizer = tokenizer
        self.generator = generator
        self.vq = tokenizer.vqvae.vq
        self.pick_tokens, self.decode_ids = _evaluator_helpers(upstream, tokenizer)

    def _require_eval(self) -> None:
        if self.generator.training or self.tokenizer.vqvae.training:
            raise RuntimeError("Generator and VQ-VAE must both be in eval mode.")

    @torch.no_grad()
    def generate_codes(self, context: torch.Tensor) -> torch.Tensor:
        self._require_eval()
        if context.ndim != 2 or context.shape[0] == 0 or context.shape[1] != 91:
            raise ValueError("Hard-Sudoku context must have shape [nonempty batch, 91].")
        if context.dtype != torch.long or bool(((context < 0) | (context > 11)).any()):
            raise ValueError("Context must contain torch.long Sudoku IDs in 0..11.")
        # Identical to eval_shard.run: no explicit KV-cache override or callback.
        codes = self.generator.generate(
            None, context, temperature=0.0, top_k=0, top_p=1.0,
            cfg_scale=0.0, cfg_null_eos=self.tokenizer.pre_tokenizer.eos_token_id,
        )
        _check_codes(self.vq, codes)
        return codes

    @torch.no_grad()
    def decode_latent(self, latent: torch.Tensor) -> tuple[torch.Tensor, tuple[str, ...]]:
        self._require_eval()
        if latent.ndim != 3 or tuple(latent.shape[1:]) != (89, self.vq.embed_dim):
            raise ValueError("Decoder requires a full-resolution [batch, 89, channels] latent.")
        ids = self.pick_tokens(self.tokenizer.vqvae.decoder(latent))
        return ids, tuple(self.decode_ids(row) for row in ids.tolist())

    @torch.no_grad()
    def decode_prefixes(self, codes: torch.Tensor) -> tuple[DecodedPrefix, ...]:
        self._require_eval()
        snapshots = reconstruct_prefixes(self.vq, codes)
        result = []
        cumulative = 0
        for level, (length, latent) in enumerate(zip(self.vq.levels, snapshots, strict=True), 1):
            cumulative += length
            ids, texts = self.decode_latent(latent)
            result.append(DecodedPrefix(level, length, cumulative, ids, texts))
        return tuple(result)


def load_sudoku_adapter(repository: Path, *, device: str = "cuda") -> SudokuAdapter:
    """Load pinned local artifacts exactly as eval_shard does, in float32 eval mode.

    No downloads. Reject changed upstream/config rather than silently adapting
    the reconstruction contract. Artifact digests are checked by the parity run.
    """
    import hashlib
    from omegaconf import OmegaConf

    repository = Path(repository).resolve()
    upstream = repository / "third_party/ncm"
    actual = subprocess.check_output(["git", "-c", f"safe.directory={upstream}", "-C", str(upstream), "rev-parse", "HEAD"], text=True).strip()
    dirty = subprocess.check_output(["git", "-c", f"safe.directory={upstream}", "-c", "core.autocrlf=true", "-C", str(upstream), "status", "--porcelain"], text=True).strip()
    if actual != PINNED_UPSTREAM or dirty:
        raise RuntimeError("The pinned upstream checkout must be unchanged and clean.")
    config_path = upstream / "config/eval/sudoku-hard.yaml"
    if hashlib.sha256(config_path.read_text(encoding='utf-8').encode()).hexdigest() != CONFIG_SHA256:
        raise RuntimeError("Official hard-Sudoku configuration has changed.")
    _import_upstream(upstream)
    from models.next_concept import NextConceptTransformer
    from tokenization.vqvae_tokenizer import VQVAETokenizer

    config = OmegaConf.load(config_path)
    checkpoint = repository / "artifacts/sudoku/hard"
    config.tokenizer.vqvae.checkpoint_path = str(checkpoint / config.checkpoints.tokenizer)
    tokenizer = VQVAETokenizer.from_config(config.tokenizer)
    tokenizer.vqvae = tokenizer.vqvae.to(device).eval()
    generator = NextConceptTransformer(vqvae_local=tokenizer.vqvae, config=config.model).to(device)
    state = torch.load(checkpoint / config.checkpoints.generator, map_location="cpu", weights_only=False)
    generator.load_state_dict(state["model"], strict=True)
    generator.eval()
    if tuple(tokenizer.vqvae.vq.levels) != SUDOKU_LEVELS:
        raise RuntimeError("Unexpected hard-Sudoku hierarchy.")
    if any(p.dtype != torch.float32 for model in (generator, tokenizer.vqvae) for p in model.parameters()):
        raise RuntimeError("Released inference requires float32 parameters.")
    return SudokuAdapter(tokenizer, generator, upstream)
