"""Actual pinned small-generator stopping, reconstruction and causal-isolation tests."""
from dataclasses import FrozenInstanceError
from pathlib import Path
from types import SimpleNamespace

import pytest
import torch
from omegaconf import OmegaConf

from anytime_ncm.online import OnlineRunner, IncrementalLatent, WorkCounter, patched_source
from anytime_ncm.online_policy import Observation, policy_spec, stable_decision
from anytime_ncm.upstream_adapter import _import_upstream, SudokuAdapter, SUDOKU_LEVELS, reconstruct_prefixes
from anytime_ncm.screening_inference import independent_prefixes

UPSTREAM=Path(__file__).resolve().parents[1]/"third_party/ncm"
_import_upstream(UPSTREAM)
from models.vqvae import VQVAE
from models.next_concept import NextConceptTransformer
from tokenization.sudoku_tokenizer import SudokuTokenizer

def tiny():
    torch.manual_seed(29)
    vae=VQVAE(in_vocab_size=12,context_length=89,embed_dim=8,vqvae_vocab_size=[4]*12,
        n_layers=2,compression_factor=1,dropout=.1,dec_layers=1,pre_quant_groupnorm=2,
        vector_quantizer_config=OmegaConf.create({"clss":"multiscale_residual_vector_quantizer",
          "levels":{"use_manual_levels":True,"manual_levels":list(SUDOKU_LEVELS)},
          "learned_l1_sampling":False,"quant_resi":{"enabled":True,"ratio":.5,"share_mode":0}})).eval()
    cfg=OmegaConf.load(UPSTREAM/"config/eval/sudoku-easy.yaml").model
    cfg.n_layer=1;cfg.n_head=2;cfg.n_embd=16;cfg.vocab_size=[4]*12
    net=NextConceptTransformer(vqvae_local=vae,config=cfg).eval()
    tokenizer=SimpleNamespace(vqvae=vae,pre_tokenizer=SudokuTokenizer())
    adapter=SudokuAdapter(tokenizer,net,UPSTREAM)
    context=torch.tensor([[11]+[10 if (i+1)%10==0 else 0 for i in range(89)]+[11]])
    return adapter,OnlineRunner(adapter,UPSTREAM),context

def test_disabled_hook_preserves_actual_upstream_codes_and_state():
    adapter,runner,context=tiny()
    expected=adapter.generate_codes(context)
    calls=[]
    handle=adapter.generator.transformer.blocks[0].register_forward_pre_hook(lambda *args:calls.append(1))
    actual=runner.codes(context)
    handle.remove()
    assert torch.equal(expected,actual) and len(calls)==12 and adapter.generator._cfg is None
    assert "level_callback" in runner.patch and "generated_idx.append" in runner.patch

@pytest.mark.parametrize("depth",[1,2,6,12])
def test_forced_boundaries_skip_actual_transformer_evaluations(depth):
    adapter,runner,context=tiny()
    full=adapter.generate_codes(context)
    calls=[]
    handle=adapter.generator.transformer.blocks[0].register_forward_pre_hook(lambda *args:calls.append(1))
    codes=runner.codes(context,maximum=depth)
    handle.remove()
    assert len(calls)==depth and codes.shape[1]==sum(SUDOKU_LEVELS[:depth])
    assert torch.equal(codes,full[:,:codes.shape[1]])

def test_callback_sees_only_available_prefix_and_stops_future_calls():
    adapter,runner,context=tiny()
    seen=[]
    def callback(level,codes):
        seen.append((level,codes.clone()))
        assert codes.shape[1]==sum(SUDOKU_LEVELS[:level])
        return level==3
    result=runner.codes(context,callback=callback)
    assert [x[0] for x in seen]==[1,2,3] and result.shape[1]==7

def test_mutating_callback_snapshot_cannot_modify_generator_prefix_state():
    adapter,runner,context=tiny()
    expected=adapter.generate_codes(context)
    def callback(level,codes):
        codes.fill_(0)
        return False
    assert torch.equal(runner.codes(context,callback=callback),expected)

def test_non_boolean_callback_fails_and_cleanup_preserves_next_request():
    adapter,runner,context=tiny()
    expected=adapter.generate_codes(context)
    with pytest.raises(TypeError):
        runner.codes(context,callback=lambda *args:1)
    assert adapter.generator._cfg is None
    assert torch.equal(runner.codes(context),expected)

@pytest.mark.parametrize("depth",[0,-1,13,True,2.0])
def test_invalid_boundaries_rejected_before_generation(depth):
    adapter,runner,context=tiny()
    calls=[]
    h=adapter.generator.transformer.blocks[0].register_forward_pre_hook(lambda *a:calls.append(1))
    with pytest.raises(ValueError):runner.codes(context,maximum=depth)
    h.remove()
    assert calls==[]

def test_eval_required_for_all_modules():
    adapter,runner,context=tiny()
    adapter.tokenizer.vqvae.train()
    with pytest.raises(ValueError):runner.codes(context)

def test_incremental_skipped_inspection_depths_equal_independent_and_offline_arithmetic():
    adapter,runner,context=tiny()
    codes=adapter.generate_codes(context)
    expected=reconstruct_prefixes(adapter.vq,codes)
    independent=independent_prefixes(adapter.vq,codes)
    accumulator=IncrementalLatent(adapter.vq)
    snapshots=[]
    for depth in (1,6,10,12):
        current=codes[:,:sum(SUDOKU_LEVELS[:depth])]
        actual=accumulator.snapshot(current,depth)
        torch.testing.assert_close(actual,expected[depth-1],rtol=0,atol=0)
        torch.testing.assert_close(actual,independent[depth-1],rtol=0,atol=0)
        snapshots.append(actual)
    assert len({x.untyped_storage().data_ptr() for x in snapshots})==4
    snapshots[0].fill_(999)
    assert not torch.equal(snapshots[0],accumulator.total)

def test_future_suffix_cannot_enter_an_earlier_incremental_observation():
    adapter,runner,context=tiny()
    codes=adapter.generate_codes(context)
    limit=sum(SUDOKU_LEVELS[:3])
    altered=codes.clone();altered[:,limit:]=(altered[:,limit:]+1)%4
    a=IncrementalLatent(adapter.vq).snapshot(codes[:,:limit],3)
    b=IncrementalLatent(adapter.vq).snapshot(altered[:,:limit],3)
    assert torch.equal(a,b)
    with pytest.raises(ValueError):IncrementalLatent(adapter.vq).snapshot(codes,3)

def test_never_valid_verified_policy_falls_back_to_exact_full_output():
    adapter,runner,context=tiny()
    original=runner.request(context[0].tolist(),policy_spec("full"))
    verified=runner.request(context[0].tolist(),policy_spec("verified",levels=list(range(1,13))))
    assert verified["exit_level"]==12 and len(verified["inspected_levels"])==12
    assert verified["decoded_ids"]==original["decoded_ids"]
    assert torch.equal(verified["generated_codes"],original["generated_codes"])

def test_causal_observation_is_frozen_and_contains_no_reference_or_future():
    assert set(Observation.__dataclass_fields__)=={"level","cumulative_codes","decoded_ids"}
    observation=Observation(1,1,(0,)*89)
    with pytest.raises(FrozenInstanceError):observation.level=12
    stop,previous,count=stable_decision(observation,None,0,1)
    assert not stop and count==0
    assert stable_decision(Observation(2,3,(0,)*89),previous,count,1)[0]

def test_work_counter_forbids_encoder_and_cleans_up():
    adapter,runner,context=tiny()
    counter=WorkCounter(adapter,{"inputs":1,"generator_levels":1,"decoder":1,"encoder":0})
    counter.take("inputs")
    runner.codes(context,maximum=1)
    with pytest.raises(RuntimeError):runner.codes(context,maximum=1)
    with pytest.raises(RuntimeError):adapter.tokenizer.vqvae.encoder(context[:,:89])
    counter.close()

def test_changed_upstream_boundary_is_rejected():
    with pytest.raises(RuntimeError):patched_source("def generate(): pass")

def test_full_request_does_not_time_offline_adapter_debug_synchronizations(monkeypatch):
    adapter,runner,context=tiny()
    monkeypatch.setattr(adapter,"generate_codes",lambda *args:(_ for _ in ()).throw(
        AssertionError("Offline debug validation must stay outside the headline baseline.")))
    result=runner.request(context[0].tolist(),policy_spec("full"))
    assert result["exit_level"]==12 and result["inspected_levels"]==[]

def test_deferred_schedule_avoids_unscheduled_prefix_assembly(monkeypatch):
    adapter,runner,context=tiny()
    helper=runner.generate.__wrapped__.__globals__["_phase2_boundary"] if hasattr(runner.generate,"__wrapped__") else runner.generate.__globals__["_phase2_boundary"]
    calls=[];seen=[]
    original=torch.cat
    monkeypatch.setattr(torch,"cat",lambda *a,**kw:(calls.append(1),original(*a,**kw))[1])
    def callback(level,codes):
        seen.append(level)
        return False
    callback.inspection_levels=frozenset({12})
    parts=[]
    for level,length in enumerate(SUDOKU_LEVELS,1):
        parts.append(torch.zeros(1,length,dtype=torch.long))
        helper(level,parts,callback,12)
    assert len(calls)==1 and seen==[12]
