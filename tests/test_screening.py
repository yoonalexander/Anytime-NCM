"""R2 shared-solution reservations, bounded execution, actual reconstruction, and gates."""
from pathlib import Path
import pickle
from types import SimpleNamespace

import pytest
import torch
from omegaconf import OmegaConf

import anytime_ncm.screening as screening
from anytime_ncm.screening import (LIMITS, analyze_candidate, identity_only_hashes, make_manifest,
    require_candidate_allowed)
from anytime_ncm.screening_inference import ScreenBudget, independent_prefixes, official_runner
from anytime_ncm.dataset import Example, puzzle_identity
from anytime_ncm.trajectories import LEVEL_LENGTHS, decoded_text, make_record
from anytime_ncm.upstream_adapter import DecodedPrefix, _import_upstream, reconstruct_prefixes

UPSTREAM = Path(__file__).resolve().parents[1] / "third_party/ncm"
_import_upstream(UPSTREAM)
from models.quant import MultiscaleResidualVectorQuantizer
from tokenization.sudoku_tokenizer import SudokuTokenizer

TEXT = "534678912672195348198342567859761423426853791713924856961537284287419635345286179"
TARGET = tuple(10 if v == "|" else int(v) for v in "|".join(TEXT[k:k+9] for k in range(0, 81, 9)))


def puzzle(index):
    row = list(TARGET)
    for i in range(5):
        if index & (1 << i):
            row[i] = 0
    return (11, *row, 11)


def original_manifest(count=40):
    names = ["exploration"] * 32 + ["development"] * 2 + ["phase2_final"] * 3 + ["phase3_final"] * (count - 37)
    return {"sample_count": count, "partitions": {
        name: [{"index": i, "puzzle_sha256": "old-" + str(i)} for i, n in enumerate(names) if n == name]
        for name in ("exploration", "development", "phase2_final", "phase3_final")}}


def test_identity_only_scanner_matches_canonical_hashes_without_pickle_execution():
    rows = [puzzle(i) for i in range(32)]
    raw = pickle.dumps([list(row) for row in rows], protocol=4)
    assert identity_only_hashes(raw, 32) == [puzzle_identity(row) for row in rows]


@pytest.mark.parametrize("raw", [b"", b"\x80\x05", pickle.dumps([["bad"]], protocol=4),
                                  pickle.dumps([[1] * 91], protocol=4) + b"trailing"])
def test_identity_scanner_rejects_unsupported_structures(raw):
    with pytest.raises((ValueError, IndexError)):
        identity_only_hashes(raw, 1)


def test_manifest_inherits_reference_row_reservations_before_row_materialization():
    original = original_manifest()
    hashes = ["new-" + str(i) for i in range(40)]
    manifest = make_manifest("easy", hashes, original)
    assert manifest["selected_indices"] == list(range(32))
    for name, entries in original["partitions"].items():
        assert [r["index"] for r in manifest["partitions"][name]] == [r["index"] for r in entries]
    assert manifest["reference_rows_read_for_partitioning"] == 0
    assert manifest["shared_solution_sha256"].startswith("b52de75")


@pytest.mark.parametrize("source,destination", [(0, 34), (34, 0), (32, 37)])
def test_cross_difficulty_puzzle_collision_cannot_promote_an_inherited_row(source, destination):
    original = original_manifest()
    hashes = ["new-" + str(i) for i in range(40)]
    hashes[destination] = "old-" + str(source)
    with pytest.raises(ValueError, match="reservation"):
        make_manifest("medium", hashes, original)


@pytest.mark.parametrize("a,b", [(0, 34), (32, 37)])
def test_new_duplicate_hashes_cannot_cross_partitions(a, b):
    hashes = ["new-" + str(i) for i in range(40)]
    hashes[b] = hashes[a]
    with pytest.raises(ValueError, match="reservation"):
        make_manifest("easy", hashes, original_manifest())


def test_duplicate_first32_is_rejected_without_substitution():
    hashes = ["new-" + str(i) for i in range(40)]
    hashes[1] = hashes[0]
    with pytest.raises(ValueError, match="no substitutions"):
        make_manifest("easy", hashes, original_manifest())


def test_inherited_final_row_cannot_be_moved_into_first32():
    original = original_manifest()
    moved = original["partitions"]["exploration"].pop(1)
    reserved = original["partitions"]["phase2_final"].pop(0)
    original["partitions"]["exploration"].append(reserved)
    original["partitions"]["phase2_final"].append(moved)
    with pytest.raises(ValueError, match="no substitutions"):
        make_manifest("easy", ["new-" + str(i) for i in range(40)], original)


def test_medium_requires_completed_negative_easy_and_stops_on_positive(monkeypatch, tmp_path):
    monkeypatch.setattr(screening, "verify_candidate", lambda *args: {"qualifies_for_R3": True})
    with pytest.raises(ValueError, match="outside the stop rule"):
        require_candidate_allowed(tmp_path, "medium")
    monkeypatch.setattr(screening, "verify_candidate", lambda *args: {"qualifies_for_R3": False})
    require_candidate_allowed(tmp_path, "medium")
    require_candidate_allowed(tmp_path, "easy")


@pytest.mark.parametrize("kind", list(LIMITS))
def test_budget_refuses_extra_operations_before_forward(kind):
    budget = ScreenBudget()
    budget.counts[kind] = LIMITS[kind]
    with pytest.raises(ValueError, match="budget exhausted"):
        budget.take(kind)
    assert budget.counts[kind] == LIMITS[kind]


def test_block_decoder_encoder_hooks_and_cleanup():
    block, decoder, encoder = torch.nn.Identity(), torch.nn.Identity(), torch.nn.Identity()
    adapter = SimpleNamespace(generator=SimpleNamespace(transformer=SimpleNamespace(blocks=[block])),
        tokenizer=SimpleNamespace(vqvae=SimpleNamespace(decoder=decoder, encoder=encoder)))
    budget = ScreenBudget()
    budget.attach(adapter)
    block(torch.zeros(1))
    decoder(torch.zeros(1))
    with pytest.raises(ValueError, match="encoder"):
        encoder(torch.zeros(1))
    assert budget.counts["generator_levels"] == budget.counts["decoder"] == 1
    assert budget.counts["encoder"] == 0
    budget.close()
    encoder(torch.zeros(1))
    assert budget.counts["encoder"] == 0


@pytest.mark.parametrize("cascade,residual", [(False, False), (False, True), (True, True)])
def test_independent_functional_prefixes_match_actual_quantizer_and_isolate_suffix(cascade, residual):
    torch.manual_seed(7)
    vq = MultiscaleResidualVectorQuantizer(vqvae_vocab_size=[4, 5, 6], embed_dim=8,
        levels=OmegaConf.create({"use_manual_levels": True, "manual_levels": [1, 2, 6]}),
        learned_l1_sampling=True, learned_l1_cascade=cascade,
        quant_resi=OmegaConf.create({"enabled": residual, "ratio": .5, "share_mode": 0})).eval()
    ids = torch.tensor([[0, 1, 2, 0, 1, 2, 3, 4, 5]])
    actual, independent = reconstruct_prefixes(vq, ids), independent_prefixes(vq, ids)
    for a, b in zip(actual, independent, strict=True):
        torch.testing.assert_close(a, b, rtol=0, atol=0)
    changed = ids.clone()
    changed[:, 3:] = (changed[:, 3:] + 1) % 6
    altered = independent_prefixes(vq, changed)
    assert torch.equal(independent[0], altered[0]) and torch.equal(independent[1], altered[1])
    assert not torch.equal(independent[-1], altered[-1])
    assert len({p.untyped_storage().data_ptr() for p in independent}) == 3


def test_comparator_executes_actual_released_run_and_sampling_arguments():
    calls = []
    def generate(level0, context, **kwargs):
        calls.append((level0, context.clone(), kwargs))
        return torch.zeros(1, 322, dtype=torch.long)
    final = torch.zeros(1, 89, 8)
    vae = SimpleNamespace(vq=SimpleNamespace(idx_to_zhats=lambda codes, return_zlevels:
                                            ((final,), (final,))),
                         decoder=lambda latent: torch.zeros(1, 89, 12))
    adapter = SimpleNamespace(generator=SimpleNamespace(generate=generate),
                              tokenizer=SimpleNamespace(vqvae=vae, pre_tokenizer=SudokuTokenizer()))
    official = official_runner(adapter, UPSTREAM)
    context = torch.tensor([official["prefix"](puzzle(0))])
    text = official["run"](context)
    assert len(calls) == 1 and calls[0][0] is None
    assert calls[0][2] == dict(temperature=0.0, top_k=0, top_p=1.0, cfg_scale=0.0, cfg_null_eos=None)
    assert len(official["RAW"]) == 1 and len(official["RAW"][0]) == 89
    assert text == [decoded_text(official["RAW"][0])]


def fixture_records(*, early=False, final_invalid=False):
    examples, records = [], []
    empty = [10 if t == 10 else 0 for t in TARGET]
    for index in range(32):
        p = puzzle(index)
        example = Example(index, "exploration", puzzle_identity(p), p, TARGET)
        examples.append(example)
        outputs = []
        for level, length in enumerate(LEVEL_LENGTHS, 1):
            ids = list(TARGET) if (level == 12 and not final_invalid) or (early and index == 3 and level == 11) else empty
            outputs.append(DecodedPrefix(level, length, sum(LEVEL_LENGTHS[:level]),
                                         torch.tensor([ids]), (decoded_text(ids),)))
        trajectory = make_record(example, "R2-easy", outputs, [0] * 322, 0)
        records.append({"dataset_index": index, "sample_id": example.identity, "trajectory": trajectory,
            "comparator": {"decoded_ids": trajectory["levels"][-1]["decoded_ids"],
                           "decoded_text": trajectory["levels"][-1]["decoded_text"]},
            "checks": {"final_latent_bitwise_equal": True, "independent_prefix_equal": True,
                "independent_storage": True, "finite": True, "prefix_shapes": [[1, 89, 256]] * 12},
            "forward_counts": {"official_inputs": 1, "adapter_inputs": 1, "generator_levels": 24,
                "decoder": 13, "encoder": 0, "latent_parity": 1, "independent_prefix": 1}})
    return tuple(examples), records


@pytest.mark.parametrize("early,final_invalid,expected", [(False, False, False), (True, False, True),
                                                        (False, True, False), (True, True, True)])
def test_screen_gate_counts_actual_early_validity_and_retains_never_valid(early, final_invalid, expected):
    examples, records = fixture_records(early=early, final_invalid=final_invalid)
    analysis, rows = analyze_candidate("easy", examples, records)
    assert len(rows) == 384 and analysis["qualifies_for_R3"] is expected
    assert analysis["early_valid_indices"] == ([3] if early else [])
    assert analysis["final_valid_count"] == (0 if final_invalid else 32)
    assert analysis["first_valid_histogram"]["never"] == ((31 if early else 32) if final_invalid else 0)
    assert analysis["new_Phase2_go"] is False
    assert analysis["access"]["final_holdout_rows_materialized"] == 0


@pytest.mark.parametrize("kind", ["comparator", "identity", "parity", "shape", "budget", "labels", "partition"])
def test_analysis_refuses_incorrect_or_unpaired_evidence(kind):
    examples, records = fixture_records()
    if kind == "comparator":
        records[0]["comparator"] = {"decoded_ids": [0] * 89, "decoded_text": "_" * 89}
    elif kind == "identity":
        records[0]["dataset_index"] = 5
    elif kind == "parity":
        records[0]["checks"]["independent_prefix_equal"] = False
    elif kind == "shape":
        records[0]["checks"]["prefix_shapes"][0] = [1, 1, 256]
    elif kind == "budget":
        records[0]["forward_counts"]["adapter_inputs"] = 2
    elif kind == "labels":
        records[0]["trajectory"]["levels"][0]["correctness"]["is_valid_solution"] = True
    else:
        examples = (Example(0, "phase2_final", examples[0].identity, examples[0].puzzle, TARGET), *examples[1:])
    with pytest.raises(ValueError):
        analyze_candidate("easy", examples, records)


def test_incomplete_fixed_screen_cannot_be_interpreted():
    examples, records = fixture_records()
    with pytest.raises(ValueError, match="Incomplete"):
        analyze_candidate("easy", examples[:-1], records[:-1])
