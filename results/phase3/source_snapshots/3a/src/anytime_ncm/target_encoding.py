"""Tokenizer-only released-checkpoint operations for the fixed R1B pilot."""

import hashlib
import subprocess
from pathlib import Path

import torch

from anytime_ncm.upstream_adapter import (
    CONFIG_SHA256, PINNED_UPSTREAM, SUDOKU_LEVELS,
    _import_upstream, _evaluator_helpers, reconstruct_prefixes,
)


class ForwardBudget:
    def __init__(self, encoder_limit=32, decoder_limit=384, parity_limit=32):
        self.limits = {"encoder": encoder_limit, "decoder": decoder_limit, "final_latent": parity_limit}
        self.counts = dict.fromkeys(self.limits, 0)
        self.handles = []

    def take(self, kind):
        if self.counts[kind] >= self.limits[kind]:
            raise RuntimeError("Frozen R1B forward budget exhausted: " + kind)
        self.counts[kind] += 1

    def attach(self, vae):
        if self.handles:
            raise RuntimeError("Budget hooks already attached.")
        self.handles = [
            vae.encoder.register_forward_pre_hook(lambda *args: self.take("encoder")),
            vae.decoder.register_forward_pre_hook(lambda *args: self.take("decoder")),
        ]

    def close(self):
        for handle in self.handles:
            handle.remove()
        self.handles = []


def model_fingerprint(model):
    digest = hashlib.sha256()
    for name, value in sorted(model.state_dict().items()):
        tensor = value.detach().cpu().contiguous()
        digest.update((name + str(tensor.dtype) + str(tuple(tensor.shape))).encode())
        digest.update(tensor.numpy().tobytes())
    return digest.hexdigest()


def load_tokenizer(repository, device="cuda"):
    from omegaconf import OmegaConf
    upstream = Path(repository).resolve() / "third_party/ncm"
    head = subprocess.check_output(["git", "-c", f"safe.directory={upstream}", "-C", str(upstream), "rev-parse", "HEAD"], text=True).strip()
    dirty = subprocess.check_output(["git", "-c", f"safe.directory={upstream}", "-c", "core.autocrlf=true", "-C", str(upstream), "status", "--porcelain"], text=True).strip()
    if head != PINNED_UPSTREAM or dirty:
        raise RuntimeError("Pinned upstream must be clean and unchanged.")
    config_path = upstream / "config/eval/sudoku-hard.yaml"
    if hashlib.sha256(config_path.read_text(encoding="utf-8").encode()).hexdigest() != CONFIG_SHA256:
        raise RuntimeError("Official configuration changed.")
    _import_upstream(upstream)
    from tokenization.vqvae_tokenizer import VQVAETokenizer
    config = OmegaConf.load(config_path)
    config.tokenizer.vqvae.checkpoint_path = str(Path(repository) / "artifacts/sudoku/hard/tokenizer.pt")
    tokenizer = VQVAETokenizer.from_config(config.tokenizer)
    vae = tokenizer.vqvae.to(device).eval()
    if tuple(vae.vq.levels) != SUDOKU_LEVELS or vae.context_length != 89 or vae.embed_dim != 256:
        raise RuntimeError("Unexpected hard-Sudoku tokenizer contract.")
    if any(p.dtype != torch.float32 for p in vae.parameters()):
        raise RuntimeError("Float32 tokenizer parameters required.")
    pick, decode = _evaluator_helpers(upstream, tokenizer)
    return vae, pick, decode


@torch.no_grad()
def encode_target_prefixes(vae, target, pick_tokens, decode_ids, budget):
    if any(module.training for module in vae.modules()):
        raise ValueError("The entire tokenizer must be in eval mode.")
    if getattr(vae.vq, "_stoch_encode", False):
        raise ValueError("Stochastic target encoding is outside R1B.")
    if target.shape != (1, 89) or target.dtype != torch.long:
        raise ValueError("Target must be a single 89-token torch.long reference.")
    separators = [i for i in range(89) if (i + 1) % 10 == 0]
    if any(int(target[0, i]) != 10 for i in separators) or any(
        not 1 <= int(target[0, i]) <= 9 for i in range(89) if i not in separators
    ):
        raise ValueError("Reference format requires 81 filled digits and eight row separators.")
    before = dict(budget.counts)
    codes = vae.encode(target)  # Normalized upstream entry point; exactly one encoding.
    saved_codes = codes.clone()
    prefixes = reconstruct_prefixes(vae.vq, codes)
    shapes = [list(latent.shape) for latent in prefixes]
    pointers = [latent.untyped_storage().data_ptr() for latent in prefixes]
    if len(set(pointers)) != len(prefixes) or any(tuple(s) != (1, 89, vae.embed_dim) for s in shapes):
        raise RuntimeError("Prefix storage/full-resolution contract failed.")
    if any(not bool(torch.isfinite(latent).all()) for latent in prefixes):
        raise RuntimeError("Nonfinite cumulative prefix.")
    budget.take("final_latent")
    official = vae.vq.idx_to_z_q(codes)  # Declared latent-only validation.
    if not torch.equal(prefixes[-1], official):
        raise RuntimeError("Final cumulative latent differs from upstream.")
    states = []
    for k, latent in enumerate(prefixes, 1):
        ids = pick_tokens(vae.decoder(official if k == len(prefixes) else latent))
        if ids.shape != (1, 89):
            raise RuntimeError("Selected target output has unexpected shape.")
        values = ids[0].cpu().tolist()
        states.append({"level": k, "decoded_ids": values, "decoded_text": decode_ids(values)})
    if not torch.equal(codes, saved_codes):
        raise RuntimeError("Decoding mutated encoded target codes.")
    delta = {kind: budget.counts[kind] - before[kind] for kind in before}
    if delta != {"encoder": 1, "decoder": len(prefixes), "final_latent": 1}:
        raise RuntimeError("Unexpected model-forward count for one reference.")
    return {
        "target_codes": codes[0].cpu().tolist(), "levels": states,
        "checks": {"independent_prefix_storage": True, "prefix_shapes": shapes,
                   "final_latent_bitwise_equal": True, "final_latent_max_abs_error": 0.0,
                   "encoded_codes_unchanged": True, "forward_counts": delta},
    }
