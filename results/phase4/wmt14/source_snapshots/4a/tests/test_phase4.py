"""Phase 4 text isolation, exact corpus statistics and actual WMT-like generation tests."""
import pickle,subprocess,sys
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import pytest
import torch
from omegaconf import OmegaConf
from anytime_ncm.wmt_data import StringRows,make_manifest,select_entries,identity
from anytime_ncm.wmt_policy import Stability,cues,diagnostics,simulate
from anytime_ncm.wmt_metrics import scores,paired_quality,claim_gate,select_policies
from anytime_ncm.wmt_model import WmtModel,LEVELS,independent_prefixes
from anytime_ncm.online import build_generator,IncrementalLatent
from anytime_ncm.upstream_adapter import reconstruct_prefixes,_import_upstream
ROOT=Path(__file__).resolve().parents[1];UPSTREAM=ROOT/"third_party/ncm"
_import_upstream(UPSTREAM)
from models.vqvae import VQVAE
from models.next_concept import NextConceptTransformer

def tiny():
    torch.manual_seed(43)
    cfg=OmegaConf.load(UPSTREAM/"config/eval/wmt14.yaml")
    cfg.model.n_layer=1;cfg.model.n_head=2;cfg.model.n_embd=16
    cfg.model.vocab_size=[8]*10;cfg.model.prefix_pad_token_id=31
    vae=VQVAE(in_vocab_size=32,context_length=64,embed_dim=8,vqvae_vocab_size=[8]*11,
      n_layers=2,compression_factor=1,dropout=.1,dec_layers=1,pre_quant_groupnorm=2,
      vector_quantizer_config=OmegaConf.create({"clss":"multiscale_residual_vector_quantizer",
       "levels":{"use_manual_levels":True,"manual_levels":list(LEVELS)},"learned_l1_sampling":True,
       "learned_l1_cascade":True,"learned_l1_cascade_base":4,"learned_l1_cascade_norm":True,
       "learned_l1_cascade_norm_final":True,"quant_resi":{"enabled":True,"ratio":.5,"share_mode":0}})).eval()
    net=NextConceptTransformer(vqvae_local=vae,config=cfg.model).eval()
    model=WmtModel.__new__(WmtModel);model.net=net;model.vq=vae.vq;model.tokenizer=SimpleNamespace(vqvae=vae)
    model.generate,model.patch=build_generator(UPSTREAM)
    model.kwargs=dict(temperature=1.,top_k=1,top_p=0.,cfg_scale=0.,cfg_null_eos=31)
    model.pick=lambda logits:logits.argmax(-1)
    model.decode=lambda ids:" ".join(str(i) for i in ids)
    model.official={"prefix":lambda text:[1]*96}
    return model,torch.ones(1,96,dtype=torch.long)

def test_selective_string_reader_preserves_unicode_duplicates_and_skips_unselected_decode():
    text="duplicate-string-not-interned-"*2
    values=["GrÃ¼ÃŸe",text,text,"not selected"]
    raw=pickle.dumps(values,protocol=4)
    assert StringRows(raw).select({0,2},expected=4)=={0:values[0],2:text}
    invalid=pickle.dumps(["ok","BAD"],protocol=4).replace(b"BAD",b"\xff\xff\xff")
    assert StringRows(invalid).select({0},expected=2)=={0:"ok"}
    with pytest.raises(UnicodeDecodeError):StringRows(invalid).select({1},expected=2)

@pytest.mark.parametrize("payload",[b"\x80\x04cos\nsystem\n.",pickle.dumps([["nested"]],protocol=4),
    pickle.dumps(["ok"],protocol=4)[:-1],pickle.dumps(["ok"],protocol=4)+b"x"])
def test_string_reader_rejects_executable_nested_truncated_and_trailing_formats(payload):
    with pytest.raises(ValueError):StringRows(payload).select({0},expected=1)

def test_effective_prefix_aliases_never_cross_splits_and_manifest_is_deterministic():
    sources=[str(i) for i in range(1200)]+["0 same prefix"]
    tok=lambda text:{"input_ids":[int(text.split()[0])]}
    a=make_manifest(sources,tok);b=make_manifest(sources,tok)
    assert a==b and a["unique_effective_prefix_groups"]==1200
    assert len(a["partitions"]["exploration"])==512 and len(a["partitions"]["phase4_final"])==256
    all_ids=[r["identity"] for rows in a["partitions"].values() for r in rows]
    assert len(all_ids)==len(set(all_ids))
    group=next(r for r in a["partitions"]["exploration"] if r["index"]==0)
    assert group["indices"]==[0,1200]
    with pytest.raises(ValueError):select_entries(a,"final")
    assert len(select_entries(a,"final",True))==256

@pytest.mark.parametrize("depth",[1,5,11])
def test_wmt_predict_level_zero_hook_skips_actual_forward_calls(depth):
    model,context=tiny();full=model.net.generate(None,context,**model.kwargs)
    calls=[];h=model.net.transformer.blocks[0].register_forward_pre_hook(lambda *a:calls.append(1))
    actual=model.codes(context,maximum=depth);h.remove()
    assert len(calls)==depth and torch.equal(actual,full[:,:sum(LEVELS[:depth])])
    assert model.net.predict_level0 and not model.net.query_level0

def test_wmt_disabled_hook_and_never_stop_fallback_match_original():
    model,context=tiny();full=model.net.generate(None,context,**model.kwargs)
    assert torch.equal(model.codes(context),full)
    expected=model.request("synthetic",{"kind":"full"})
    result=model.request("synthetic",{"kind":"guarded","minimum":10,"patience":2,"epsilon":0.})
    assert result["exit_level"]==11 and result["ids"]==expected["ids"] and torch.equal(result["codes"],full)
    assert result["inspections"]==[10,11] and model.net._cfg is None

def test_wmt_cascade_groupnorm_independent_reconstruction_and_future_isolation():
    model,context=tiny();codes=model.net.generate(None,context,**model.kwargs)
    actual=reconstruct_prefixes(model.vq,codes);other=independent_prefixes(model.vq,codes)
    for a,b in zip(actual,other):torch.testing.assert_close(a,b,rtol=0,atol=0)
    assert len({a.untyped_storage().data_ptr() for a in actual})==11
    suffix=codes.clone();end=sum(LEVELS[:5]);suffix[:,end:]=(suffix[:,end:]+1)%8
    a=IncrementalLatent(model.vq).snapshot(codes[:,:end],5)
    b=IncrementalLatent(model.vq).snapshot(suffix[:,:end],5)
    assert torch.equal(a,b)

@pytest.mark.parametrize("depth",[0,12,True,1.0])
def test_invalid_wmt_boundaries_fail_before_generation(depth):
    model,context=tiny()
    with pytest.raises(ValueError):model.codes(context,maximum=depth)

def test_training_mode_refused_for_online_wmt():
    model,context=tiny();model.net.train()
    with pytest.raises(ValueError):model.request("synthetic",{"kind":"full"})

def test_guards_block_number_or_negation_changes_without_references():
    basic=Stability(dict(kind="stability",epsilon=.02,patience=1))
    guard=Stability(dict(kind="guarded",epsilon=.02,patience=1))
    for tracker in (basic,guard):assert not tracker.observe(8,[1]*64,"There are 10 people.")[0]
    changed=[1]*63+[2]
    assert basic.observe(9,changed,"There are not 11 people.")[0]
    assert not guard.observe(9,changed,"There are not 11 people.")[0]
    assert guard.observe(10,changed,"There are not 11 people.")[0]

def test_heuristic_diagnostics_retain_coverage_and_do_not_assert_semantic_truth():
    assert cues("It isn't 1,000 or 2.5%.")==(("1,000","2.5%"),True)
    d=diagnostics("There are 10 people.","There are 20 people.")
    assert d["numeric_reference_f1"]==0 and d["reference_has_digit_numbers"]
    assert diagnostics("This is fine.","Everything is fine.")["numeric_reference_f1"] is None

def test_future_labels_cannot_change_an_earlier_stability_exit():
    states=[{"level":k,"ids":[1]*64,"text":"constant"} for k in range(1,12)]
    other=deepcopy(states)
    for s in other[7:]:s["ids"]=[2]*64;s["text"]="future";s["reference"]="secret";s["oracle"]=True
    spec=dict(kind="guarded",minimum=5,patience=1,epsilon=0.)
    assert simulate(spec,states)==simulate(spec,other)==6

def test_exact_corpus_quality_and_paired_statistics_identity_case():
    refs=["the small black cat sat on the mat","a second long example has several words"]
    q=scores(refs,refs)
    assert q["bleu"]==pytest.approx(100) and q["chrf"]==pytest.approx(100)
    paired=paired_quality(refs,refs,refs)
    assert all(v["difference"]==0 and v["ci95"]==[0.,0.] for v in paired.values())

def test_quality_noninferiority_gate_preserves_uncertainty_and_speed_requirement():
    good={"relative_mean_reduction":.08,"relative_mean_reduction_ci95":[.05,.12]}
    q={m:{"ci95":[-.1,.1]} for m in ("bleu","chrf")}
    assert claim_gate(good,q,True)=="go"
    q["bleu"]["ci95"]=[-.8,.1];assert claim_gate(good,q,True)=="inconclusive"
    q["bleu"]["ci95"]=[-2.,-1.];assert claim_gate(good,q,True)=="no-go"
    assert claim_gate({"relative_mean_reduction":0.,"relative_mean_reduction_ci95":[-.1,.01]},q,True)=="no-go"

def test_rust_decode_matches_pinned_hf_decoder_without_importing_models():
    from transformers import AutoTokenizer
    from anytime_ncm.phase4 import decode_ids
    tok=AutoTokenizer.from_pretrained(ROOT/"artifacts/wmt14/text_tokenizer",local_files_only=True)
    ids=tok.encode("No, it isn't 1,000 euros.")+[151645,123]
    expected=tok.decode(ids[:ids.index(151645)],skip_special_tokens=True)
    assert decode_ids(ROOT,ids)==expected

def test_verification_imports_no_torch_or_transformers_in_fresh_process():
    code="import sys;sys.path.insert(0,'src');import anytime_ncm.phase4;assert 'torch' not in sys.modules;assert 'transformers' not in sys.modules"
    subprocess.run([sys.executable,"-c",code],cwd=ROOT,check=True)

def test_development_catalog_contains_every_candidate_and_a_strong_fixed_comparator():
    reference="the same long sentence contains several ordinary words"
    rows=[{"levels":[{"level":i,"ids":[1]*64,"text":reference} for i in range(1,12)]} for _ in range(2)]
    selected=select_policies(rows,[reference]*2)
    assert len(selected["fixed_candidates"])==11
    assert sum(len(v) for v in selected["adaptive_candidates"].values())==36
    assert selected["methods"]["fixed"]["depth"]==1
    assert simulate(selected["methods"]["adaptive"],rows[0]["levels"])==6
