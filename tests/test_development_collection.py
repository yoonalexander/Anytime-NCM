"""Selective corpus access and native/prefix feature correctness on invented cases."""
import numpy as np
import pytest
import torch
from anytime_ncm.development_data import selected_segments
from anytime_ncm.development_trace import trace_request,current_logits
from anytime_ncm.forced_wmt import ForwardCounter,forced_request
from anytime_ncm.quality_controller import Meter,features
from anytime_ncm.latency_diagnostic import LEVELS
from test_phase4 import tiny

def blob(kind='source',payloads=(b'keep',b'\xffPOISON'),segments=(b'1',b'2')):
    tag=b'srcset' if kind=='source' else b'refset';extra=b'' if kind=='source' else b' trglang="en"'
    return b'<'+tag+b' setid="newstest2015" srclang="any"'+extra+b'>\n<doc docid="d">\n'+b''.join(b'<seg id="'+i+b'">'+p+b'</seg>\n' for p,i in zip(payloads,segments))+b'</doc>\n</'+tag+b'>\n'
def member(kind):return 'test/newstest2015-deen-src.de.sgm' if kind=='source' else 'test/newstest2015-deen-ref.en.sgm'
def meter(s=1,r=1):return Meter(dict(source_segment_headers=2,reference_segment_headers=2,source_body_decodes=s,reference_body_decodes=r))

def test_skip_unallocated_poison_payload_before_utf8_decode():
    m=meter();s,h=selected_segments(blob(),'source',member('source'),{0},2,m)
    r,_=selected_segments(blob('reference'),'reference',member('reference'),{0},2,m,h)
    assert s==r=={0:'keep'} and m.counts==dict(source_segment_headers=2,reference_segment_headers=2,source_body_decodes=1,reference_body_decodes=1)

def test_exact_audited_whitespace_entities_unicode_and_no_implicit_cleaning():
    text='  Grüße &amp;  &quot;42&quot;  '
    s,_=selected_segments(blob(payloads=(text.encode(),b'other')),'source',member('source'),{0},2,meter())
    assert s[0]==text

def test_alignment_rejects_before_selected_reference_body_decode():
    m=meter();_,h=selected_segments(blob(),'source',member('source'),{0},2,m)
    with pytest.raises(ValueError,match='before body decode'):selected_segments(blob('reference',segments=(b'wrong',b'2')),'reference',member('reference'),{0},2,m,h)
    assert m.counts['reference_body_decodes']==0

def test_duplicate_missing_extra_header_and_invalid_selected_payload():
    with pytest.raises(ValueError,match='duplicate'):selected_segments(blob(segments=(b'1',b'1')),'source',member('source'),{0},2,meter())
    with pytest.raises(ValueError,match='Incomplete'):selected_segments(blob(),'source',member('source'),{0},3,Meter(dict(source_segment_headers=3,source_body_decodes=1)))
    with pytest.raises(UnicodeDecodeError):selected_segments(blob(),'source',member('source'),{1},2,meter())
    with pytest.raises(ValueError):selected_segments(blob(),'source',member('source'),{3},2,meter())

def test_empty_active_set_does_not_decode_any_body():
    m=meter(0,0);s,_=selected_segments(blob(payloads=(b'\xff',b'\xfe')),'source',member('source'),set(),2,m)
    assert not s and not m.counts['source_body_decodes']

def test_wrong_language_and_member_attestation_reject():
    for data,name in [(blob().replace(b'"any"',b'"fr"'),member('source')),(blob(),'test/wrong.sgm')]:
        with pytest.raises(ValueError):selected_segments(data,'source',name,{0},2,meter())

def test_tiny_native_generation_suffix_isolation_features_final_parity_and_exact_work():
    torch.set_num_threads(1);model,_=tiny();counter=ForwardCounter(model,dict(inputs=3,generator_levels=22,decoder=15,encoder=0));m=Meter(dict(cheap_features=2,selected_logit_features=2,cue_features=2));before={name:{k:v.detach().clone() for k,v in net.state_dict().items()} for name,net in [('g',model.net),('t',model.tokenizer.vqvae)]}
    try:
        counter.take('inputs');row=trace_request(model,'source 2',m)
        counter.take('inputs');full=forced_request(model,'source 2',11,'terminal')
        assert row['codes']==full['codes'][0].tolist() and row['levels'][-1]['ids']==full['ids'] and row['native_final_parity']
        codes=torch.tensor([row['codes']],dtype=torch.long);bad=codes.clone();bad[:,sum(LEVELS[:8]):]=10**6
        a=current_logits(model,codes,8);b=current_logits(model,bad,8);assert torch.equal(a,b)
        previous=None
        for v in row['features']:
            d=v['level'];o=row['levels'][d-1];expected=features('source 2',d,row['codes'][:sum(LEVELS[:d])],o['ids'],o['text'],previous)
            np.testing.assert_array_equal(v['values'][:19],expected);previous=dict(level=d,ids=o['ids'],text=o['text'])
        assert m.counts==dict(cheap_features=2,selected_logit_features=2,cue_features=2) and model.net._cfg is None
        for name,net in [('g',model.net),('t',model.tokenizer.vqvae)]:assert all(torch.equal(v,before[name][k]) for k,v in net.state_dict().items())
        counter.take('inputs');model.net.train()
        with pytest.raises(ValueError):trace_request(model,'source',m)
        assert counter.counts==dict(inputs=3,generator_levels=22,decoder=15,encoder=0)
        print('SYNTHETIC_DEVELOPMENT_REQUESTS 3')
    finally:counter.close()
