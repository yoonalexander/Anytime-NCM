"""Synthetic prefix contracts against the actual pinned quantizer."""

from pathlib import Path
from types import SimpleNamespace

import pytest
import torch
from torch.nn import functional as F
from omegaconf import OmegaConf

from anytime_ncm.upstream_adapter import (
    SudokuAdapter, _import_upstream, reconstruct_prefixes,
)

UPSTREAM = Path(__file__).resolve().parents[1] / "third_party/ncm"
_import_upstream(UPSTREAM)
from models.quant import MultiscaleResidualVectorQuantizer
from tokenization.sudoku_tokenizer import SudokuTokenizer


def quantizer(*, learned=True, residual=True, all_sampling=False, cascade=False):
    torch.manual_seed(47)
    vq = MultiscaleResidualVectorQuantizer(
        vqvae_vocab_size=[4, 5, 6], embed_dim=8,
        levels=OmegaConf.create({"use_manual_levels": True, "manual_levels": [1, 2, 6]}),
        learned_l1_sampling=learned, learned_all_sampling=all_sampling,
        learned_l1_cascade=cascade,
        quant_resi=OmegaConf.create({"enabled": residual, "ratio": 0.5, "share_mode": 0}),
    ).eval()
    # Distinct nonzero learned transformations make interpolation-only and
    # residual-omission regressions visible; do not test just identity weights.
    with torch.no_grad():
        for name, parameter in vq.named_parameters():
            if "embedding" not in name:
                parameter.copy_(torch.randn_like(parameter) * 0.12)
    return vq


def codes():
    return torch.tensor([[0, 1, 2, 0, 1, 2, 3, 4, 5], [1, 2, 3, 5, 4, 3, 2, 1, 0]])


def independent_prefix(vq, ids, depth):
    """Test oracle: explicit conv/interpolation math, no adapter/private helpers."""
    total = torch.zeros(ids.shape[0], 6, 8)
    offset = 0
    for level, length in enumerate(vq.levels[:depth]):
        term = F.embedding(ids[:, offset:offset + length], vq.embeddings[level].weight)
        term = term.transpose(1, 2)
        if level == 0 and vq.learned_l1_sampling:
            layers = vq.learned_up_l1
            layers = list(layers) if isinstance(layers, torch.nn.Sequential) else [layers]
            for layer in layers:
                term = F.conv_transpose1d(term, layer.weight, layer.bias, stride=layer.stride)
        elif level != len(vq.levels) - 1:
            term = F.interpolate(term, size=6, mode="linear")
            if vq.learned_all_sampling:
                layer = vq.learned_up_refine[level]
                term = term + F.conv1d(term, layer.weight, layer.bias, padding=1)
        if vq.quant_resi_enabled:
            layer = vq.quant_resi[level / (len(vq.levels) - 1)]
            term = term * 0.5 + F.conv1d(term, layer.weight, layer.bias, padding=1) * 0.5
        total = total + term.transpose(1, 2)
        offset += length
    return total


@pytest.mark.parametrize("options", [
    {}, {"learned": False}, {"residual": False}, {"all_sampling": True}, {"cascade": True},
])
def test_every_prefix_matches_independent_accumulation(options):
    vq, ids = quantizer(**options), codes()
    prefixes = reconstruct_prefixes(vq, ids)
    assert len(prefixes) == 3
    for depth, latent in enumerate(prefixes, 1):
        assert latent.shape == (2, 6, 8)
        assert latent.dtype == torch.float32 and not latent.requires_grad
        torch.testing.assert_close(latent, independent_prefix(vq, ids, depth), rtol=0, atol=0)
    official, shortened = vq.idx_to_zhats(ids, return_zlevels=True)
    assert torch.equal(prefixes[-1], official[-1])
    assert torch.equal(prefixes[-1], shortened[-1])
    assert [p.shape[1] for p in shortened] == [1, 2, 6]


def test_snapshot_storage_is_independent_and_does_not_alias_upstream_bug():
    vq, ids = quantizer(), codes()
    prefixes = reconstruct_prefixes(vq, ids)
    assert len({p.untyped_storage().data_ptr() for p in prefixes}) == 3
    before = prefixes[1].clone()
    prefixes[0].fill_(999)
    assert torch.equal(prefixes[1], before)
    aliased, = vq.idx_to_zhats(ids, return_zlevels=False)
    assert len({p.untyped_storage().data_ptr() for p in aliased}) == 1


@pytest.mark.parametrize("depth", [1, 2])
def test_later_codes_cannot_change_earlier_snapshots(depth):
    vq, ids = quantizer(), codes()
    changed = ids.clone()
    offset = sum(vq.levels[:depth])
    cursor = offset
    for level in range(depth, len(vq.levels)):
        length = vq.levels[level]
        changed[:, cursor:cursor + length] = (changed[:, cursor:cursor + length] + 1) % vq.embeddings[level].num_embeddings
        cursor += length
    before, after = reconstruct_prefixes(vq, ids), reconstruct_prefixes(vq, changed)
    for left, right in zip(before[:depth], after[:depth]):
        assert torch.equal(left, right)
    assert not torch.equal(before[-1], after[-1])  # guaranteed by this synthetic fixture


def test_zero_later_contribution_can_legitimately_leave_snapshots_equal():
    vq = quantizer(learned=False, residual=False)
    with torch.no_grad():
        vq.embeddings[-1].weight.zero_()
    prefixes = reconstruct_prefixes(vq, codes())
    assert torch.equal(prefixes[-1], prefixes[-2])
    assert prefixes[-1].data_ptr() != prefixes[-2].data_ptr()


@pytest.mark.parametrize("bad", [
    torch.zeros(9, dtype=torch.long), torch.zeros(2, 8, dtype=torch.long),
    torch.zeros(2, 10, dtype=torch.long), torch.zeros(0, 9, dtype=torch.long),
    torch.zeros(2, 9), torch.full((2, 9), -1, dtype=torch.long),
    torch.full((2, 9), 4, dtype=torch.long),
])
def test_malformed_code_sequences_are_rejected(bad):
    with pytest.raises(ValueError):
        reconstruct_prefixes(quantizer(), bad)


def adapter_fixture():
    vq = quantizer()
    vq.levels = [1, 2, 89]
    calls = []

    class Generator:
        training = False

        def generate(self, level0, context, **kwargs):
            calls.append((level0, context.clone(), kwargs))
            return torch.zeros(context.shape[0], 92, dtype=torch.long)

    def decoder(latent):
        logits = torch.zeros(latent.shape[0], 89, 12)
        logits[:, :, 3] = 2
        logits[:, 0, 11] = 4
        return logits

    tokenizer = SimpleNamespace(
        vqvae=SimpleNamespace(vq=vq, decoder=decoder, training=False),
        pre_tokenizer=SudokuTokenizer(),
    )
    return SudokuAdapter(tokenizer, Generator(), UPSTREAM), calls


def test_generation_delegates_once_with_exact_released_sampling_arguments():
    adapter, calls = adapter_fixture()
    context = torch.zeros(2, 91, dtype=torch.long)
    output = adapter.generate_codes(context)
    assert output.shape == (2, 92) and len(calls) == 1
    assert calls[0][0] is None and torch.equal(calls[0][1], context)
    assert calls[0][2] == dict(temperature=0.0, top_k=0, top_p=1.0, cfg_scale=0.0, cfg_null_eos=None)


@pytest.mark.parametrize("bad", [
    torch.zeros(91, dtype=torch.long), torch.zeros(2, 89, dtype=torch.long),
    torch.zeros(0, 91, dtype=torch.long), torch.zeros(2, 91),
    torch.full((2, 91), 12, dtype=torch.long),
])
def test_invalid_context_is_rejected_before_generation(bad):
    adapter, calls = adapter_fixture()
    with pytest.raises(ValueError):
        adapter.generate_codes(bad)
    assert calls == []


def test_decode_uses_actual_upstream_selection_and_special_token_rules():
    adapter, _ = adapter_fixture()
    ids, texts = adapter.decode_latent(torch.zeros(2, 89, 8))
    assert ids.shape == (2, 89) and ids[0, 0] == 11
    assert texts == ("3" * 88,) * 2
    assert adapter.decode_ids([11, 0, 10, 2, 11]) == "_|2"


def test_shortened_latents_are_rejected():
    adapter, _ = adapter_fixture()
    with pytest.raises(ValueError):
        adapter.decode_latent(torch.zeros(2, 2, 8))


@pytest.mark.parametrize("component", ["generator", "vqvae"])
def test_train_mode_is_rejected(component):
    adapter, calls = adapter_fixture()
    target = adapter.generator if component == "generator" else adapter.tokenizer.vqvae
    target.training = True
    with pytest.raises(RuntimeError):
        adapter.generate_codes(torch.zeros(2, 91, dtype=torch.long))
    assert calls == []
