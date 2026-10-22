"""R3 exception scope, selective budgets, aggregate-only receipt, and stage controls."""
from pathlib import Path
from types import SimpleNamespace
import json

import pytest
import torch

from anytime_ncm.audit import config, parse_baseline_log, COLLECTION_LIMITS, PROFILE_LIMITS
from anytime_ncm.audit_inference import AuditBudget
from anytime_ncm.report import decision_gate


def test_official_receipt_is_aggregate_only_and_requires_full_coverage():
    receipt = parse_baseline_log("solved % solved cell % valid %\n 99.50 1990/2000 99.95 99.50\n")
    assert receipt["solved"] == 1990 and receipt["total"] == 2000
    assert not any(k in receipt for k in ("hyps", "refs", "raw_ids"))


@pytest.mark.parametrize("log", ["", "99.5 31/32 99.9 99.5\n",
    "99.5 1990/2000 99.9 99.5\n99.5 1990/2000 99.9 99.5\n"])
def test_missing_partial_or_ambiguous_official_result_cannot_be_a_full_baseline(log):
    with pytest.raises(ValueError):
        parse_baseline_log(log)


def test_fixed_r3_accounting_includes_parity_decodes_and_reused_screen():
    assert 2000 + COLLECTION_LIMITS["inputs"] + PROFILE_LIMITS["inputs"] == 4378
    assert 2000 + COLLECTION_LIMITS["decoder"] + PROFILE_LIMITS["decoder"] == 31536
    assert COLLECTION_LIMITS["inputs"] + 32 == 1400
    assert PROFILE_LIMITS["decoder"] == 1000 * 13 + 10 * 12
    assert 24000 + COLLECTION_LIMITS["generator_levels"] + PROFILE_LIMITS["generator_levels"] == 52536


@pytest.mark.parametrize("name", list(COLLECTION_LIMITS))
def test_stage_cap_rejects_extra_work_before_increment(name):
    budget = AuditBudget(COLLECTION_LIMITS)
    budget.counts[name] = COLLECTION_LIMITS[name]
    with pytest.raises(ValueError, match="budget exhausted"):
        budget.take(name)
    assert budget.counts[name] == COLLECTION_LIMITS[name]


def test_actual_module_hooks_refuse_encoder_and_cleanup():
    block, decoder, encoder = torch.nn.Identity(), torch.nn.Identity(), torch.nn.Identity()
    adapter = SimpleNamespace(generator=SimpleNamespace(transformer=SimpleNamespace(blocks=[block])),
                             tokenizer=SimpleNamespace(vqvae=SimpleNamespace(decoder=decoder, encoder=encoder)))
    budget = AuditBudget(COLLECTION_LIMITS)
    budget.attach(adapter)
    block(torch.zeros(1))
    decoder(torch.zeros(1))
    with pytest.raises(ValueError, match="encoder"):
        encoder(torch.zeros(1))
    assert budget.counts["generator_levels"] == budget.counts["decoder"] == 1
    budget.close()
    encoder(torch.zeros(1))


def test_input_reservation_persists_before_evaluation():
    persisted = []
    budget = AuditBudget(COLLECTION_LIMITS, lambda: persisted.append("reserved"))
    budget.take("inputs")
    assert budget.counts["inputs"] == 1 and persisted == ["reserved"]


def test_r3_config_explicitly_records_negative_r2_entry_exception():
    root = Path(__file__).resolve().parents[1]
    record = config(root)
    assert "negative R2" in record["entry_exception"] and record["candidate"] == "easy"
    assert record["reused_R2_exploration"] == 32


@pytest.mark.parametrize("field,value", [("candidate", "medium"), ("partitions", {"phase2_final": 300}),
                                        ("new_generation_budget", 4379), ("reused_R2_exploration", 0)])
def test_config_cannot_silently_change_setting_holdouts_or_budget(tmp_path, field, value):
    root = Path(__file__).resolve().parents[1]
    record = json.loads((root / "configs/r3_easy.json").read_text())
    record[field] = value
    (tmp_path / "configs").mkdir()
    (tmp_path / "configs/r3_easy.json").write_text(json.dumps(record))
    with pytest.raises(ValueError):
        config(tmp_path)


def test_negative_screen_is_not_relabelled_by_an_unfavorable_r3_estimate():
    assert decision_gate({"relative_mean_reduction": -.2,
                          "relative_mean_reduction_ci95": [-.3, -.1]}) == "no-go"
