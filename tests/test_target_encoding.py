"""R1B encoding delegation, fixed budgets, paired labels, and retained failures."""

from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest
import torch
from omegaconf import OmegaConf

from anytime_ncm.target_encoding import ForwardBudget, encode_target_prefixes, model_fingerprint
from anytime_ncm.target_diagnostic import check_target_record, analyze_pilot
from anytime_ncm.upstream_adapter import _import_upstream, reconstruct_prefixes
from anytime_ncm.trajectories import decoded_text

UPSTREAM = Path(__file__).resolve().parents[1] / "third_party/ncm"
_import_upstream(UPSTREAM)
from models.vqvae import VQVAE

TEXT = "534678912672195348198342567859761423426853791713924856961537284287419635345286179"
TARGET = tuple(10 if v == "|" else int(v) for v in "|".join(TEXT[k:k+9] for k in range(0, 81, 9)))


def tiny_model():
    torch.manual_seed(19)
    return VQVAE(
        in_vocab_size=12, context_length=89, embed_dim=8, vqvae_vocab_size=[4, 4, 4],
        n_layers=2, compression_factor=1, dropout=.3, pre_quant_groupnorm=2,
        vector_quantizer_config=OmegaConf.create({
            "clss": "multiscale_residual_vector_quantizer",
            "levels": {"use_manual_levels": True, "manual_levels": [1, 2, 89]},
            "learned_l1_sampling": False,
            "quant_resi": {"enabled": True, "ratio": .5, "share_mode": 0},
        }),
    ).eval()


def test_encoder_uses_upstream_normalization_once_and_full_decode_matches(monkeypatch):
    model = tiny_model()
    target = torch.tensor([TARGET], dtype=torch.long)
    expected_codes = model.encode(target)
    expected_final = model.decode(expected_codes).argmax(-1)[0].tolist()
    before = model_fingerprint(model)
    calls, normalizations = [], []
    original = model.encode
    monkeypatch.setattr(model, "encode", lambda tensor: (calls.append(tensor.clone()), original(tensor))[1])
    handle = model.pre_quant_norm.register_forward_hook(lambda *args: normalizations.append(1))
    budget = ForwardBudget(1, 3, 1)
    budget.attach(model)
    try:
        record = encode_target_prefixes(model, target, lambda logits: logits.argmax(-1), decoded_text, budget)
    finally:
        budget.close()
        handle.remove()
    assert len(calls) == len(normalizations) == 1
    assert torch.equal(calls[0], target)
    assert record["target_codes"] == expected_codes[0].tolist()
    assert record["levels"][-1]["decoded_ids"] == expected_final
    assert record["checks"]["final_latent_bitwise_equal"]
    assert record["checks"]["prefix_shapes"] == [[1, 89, 8]] * 3
    assert budget.counts == {"encoder": 1, "decoder": 3, "final_latent": 1}
    assert model_fingerprint(model) == before


@pytest.mark.parametrize("kind,limit", [("encoder", 1), ("decoder", 3), ("final_latent", 1)])
def test_budget_refuses_an_extra_forward_before_increment(kind, limit):
    budget = ForwardBudget(1, 3, 1)
    for _ in range(limit):
        budget.take(kind)
    with pytest.raises(RuntimeError, match="budget exhausted"):
        budget.take(kind)
    assert budget.counts[kind] == limit


def test_budget_hooks_cleanup_does_not_leave_hidden_counting():
    model = tiny_model()
    budget = ForwardBudget(1, 3, 1)
    budget.attach(model)
    budget.close()
    model.encode(torch.tensor([TARGET]))
    assert budget.counts == {"encoder": 0, "decoder": 0, "final_latent": 0}


@pytest.mark.parametrize("mode", ["training", "stochastic"])
def test_encoding_rejects_training_or_stochastic_mode_before_forward(mode):
    model = tiny_model()
    if mode == "training":
        model.train()
    else:
        model.vq.set_stochastic_encode(True)
    budget = ForwardBudget(1, 3, 1)
    budget.attach(model)
    try:
        with pytest.raises(ValueError):
            encode_target_prefixes(model, torch.tensor([TARGET]), lambda x: x.argmax(-1), decoded_text, budget)
    finally:
        budget.close()
    assert budget.counts["encoder"] == budget.counts["decoder"] == 0


@pytest.mark.parametrize("bad", [
    torch.tensor([TARGET], dtype=torch.float32),
    torch.tensor([TARGET[:-1]], dtype=torch.long),
    torch.tensor([TARGET, TARGET], dtype=torch.long),
    torch.full((1, 89), 11, dtype=torch.long),
    torch.zeros((1, 89), dtype=torch.long),
])
def test_bad_reference_tensor_is_rejected_without_consuming_budget(bad):
    model = tiny_model()
    budget = ForwardBudget(1, 3, 1)
    budget.attach(model)
    try:
        with pytest.raises(ValueError):
            encode_target_prefixes(model, bad, lambda x: x.argmax(-1), decoded_text, budget)
    finally:
        budget.close()
    assert budget.counts["encoder"] == 0


def test_encoded_prefix_storage_and_suffix_isolation_with_actual_quantizer():
    model = tiny_model()
    codes = model.encode(torch.tensor([TARGET]))
    changed = codes.clone()
    changed[:, 3:] = (changed[:, 3:] + 1) % 4
    a, b = reconstruct_prefixes(model.vq, codes), reconstruct_prefixes(model.vq, changed)
    assert len({t.untyped_storage().data_ptr() for t in a}) == 3
    assert torch.equal(a[0], b[0]) and torch.equal(a[1], b[1])
    saved = a[1].clone()
    a[0].fill_(999)
    assert torch.equal(a[1], saved)


def fixtures():
    bad = list(TARGET)
    bad[0] = 3
    examples, generated, targets = [], [], []
    for i in range(32):
        clues = [0] * 81
        clues[0] = 5
        example = SimpleNamespace(index=i, identity=f"id{i}", partition="exploration",
                                  puzzle=tuple(clues), reference=TARGET)
        examples.append(example)
        header = {"dataset_index": i, "sample_id": example.identity, "partition": "exploration"}
        def state(k, ids):
            return {"level": k, "decoded_ids": list(ids), "decoded_text": decoded_text(ids)}
        generated.append(header | {"levels": [state(k, TARGET if k == 12 and i < 24 else bad) for k in range(1, 13)]})
        targets.append(header | {
            "target_codes": [0] * 322,
            "levels": [state(k, TARGET if k == 12 else bad) for k in range(1, 13)],
            "checks": {"forward_counts": {"encoder": 1, "decoder": 12, "final_latent": 1},
                       "prefix_shapes": [[1, 89, 256]] * 12, "independent_prefix_storage": True,
                       "final_latent_bitwise_equal": True, "encoded_codes_unchanged": True,
                       "final_latent_max_abs_error": 0.},
        })
    return tuple(examples), generated, targets


def test_paired_analysis_preserves_all_inputs_and_distinguishes_final_accuracy():
    examples, generated, targets = fixtures()
    a, boards, changes = analyze_pilot(examples, generated, targets)
    assert len(boards) == 768 and len(changes) == 704
    assert a["outcome"] == "no_early_target_opportunity"
    assert a["paths"]["target_encoded"]["levels"][-1]["valid_count"] == 32
    assert a["paths"]["generated_saved"]["levels"][-1]["valid_count"] == 24
    assert a["paths"]["target_encoded"]["first_valid_counts"]["12"] == 32
    assert a["representative_cases"]["target_early_valid_generated_not_early"] is None
    assert a["representative_cases"]["target_no_early_validity"]["dataset_index"] == 0


def test_early_target_validity_is_separate_from_deployable_generation():
    examples, generated, targets = fixtures()
    targets[3]["levels"][9].update(decoded_ids=list(TARGET), decoded_text=decoded_text(TARGET))
    a, _, _ = analyze_pilot(examples, generated, targets)
    assert a["outcome"] == "early_target_opportunity"
    assert a["paths"]["target_encoded"]["early_valid_inputs"] == 1
    assert a["paths"]["generated_saved"]["early_valid_inputs"] == 0
    assert a["representative_cases"]["target_early_valid_generated_not_early"]["dataset_index"] == 3


def test_final_roundtrip_failure_is_retained_not_dropped_or_hidden():
    examples, generated, targets = fixtures()
    targets[4]["levels"][-1].update(decoded_ids=list(generated[4]["levels"][0]["decoded_ids"]),
                                   decoded_text=generated[4]["levels"][0]["decoded_text"])
    a, boards, _ = analyze_pilot(examples, generated, targets)
    assert len(boards) == 768 and a["outcome"] == "final_round_trip_failures"
    for name in ("final_primary_failure_indices", "final_board_reference_mismatch_indices", "final_token_mismatch_indices"):
        assert a["paths"]["target_encoded"][name] == [4]
    assert a["representative_cases"]["target_final_primary_failure"]["dataset_index"] == 4


def test_unparseable_final_output_has_undefined_error_coverage_and_is_retained():
    examples, generated, targets = fixtures()
    targets[4]["levels"][-1].update(decoded_ids=[11] * 89, decoded_text="")
    a, _, _ = analyze_pilot(examples, generated, targets)
    row = a["paths"]["target_encoded"]["levels"][-1]
    assert row["parseable_count"] == 31
    assert row["metrics"]["wrong_reference_cells"]["undefined_count"] == 1
    assert row["official_cell_accuracy_mean"] is None
    assert a["paths"]["target_encoded"]["final_primary_failure_indices"] == [4]


@pytest.mark.parametrize("corruption", ["partition", "identity", "codes", "level", "shape", "budget", "parity"])
def test_native_record_checks_reject_changed_selection_or_contract(corruption):
    examples, _, targets = fixtures()
    record = deepcopy(targets[0])
    if corruption == "partition":
        record["partition"] = "phase2_final"
    elif corruption == "identity":
        record["sample_id"] = "other"
    elif corruption == "codes":
        record["target_codes"][0] = 16
    elif corruption == "level":
        record["levels"].pop()
    elif corruption == "shape":
        record["checks"]["prefix_shapes"][0] = [1, 1, 256]
    elif corruption == "budget":
        record["checks"]["forward_counts"]["encoder"] = 2
    else:
        record["checks"]["final_latent_bitwise_equal"] = False
    with pytest.raises(ValueError):
        check_target_record(record, examples[0])


def test_analysis_rejects_missing_input_and_development_reference():
    examples, generated, targets = fixtures()
    with pytest.raises(ValueError):
        analyze_pilot(examples[:-1], generated, targets)
    changed = list(examples)
    changed[0] = SimpleNamespace(**(vars(examples[0]) | {"partition": "development"}))
    with pytest.raises(ValueError):
        analyze_pilot(changed, generated, targets)


def test_report_renders_synthetic_roundtrip_failures_and_consistent_tables(tmp_path):
    import re
    from anytime_ncm.target_diagnostic_render import render_report
    examples, generated, targets = fixtures()
    targets[4]["levels"][-1].update(decoded_ids=[11] * 89, decoded_text="")
    a, _, _ = analyze_pilot(examples, generated, targets)
    root = tmp_path
    out = root / "results/followup/test"
    out.mkdir(parents=True)
    render_report(root, out, a)
    text = (out / "summary.md").read_text(encoding="utf-8")
    assert "[4]" in text and "undefined" in text and (out / "prefix_comparison.png").exists()
    width = None
    for line in text.splitlines():
        if line.startswith("|"):
            n = len(line.split("|")) - 2
            width = n if width is None else width
            assert n == width
        else:
            width = None
