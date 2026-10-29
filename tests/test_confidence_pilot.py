"""Synthetic-only confidence correctness, causal parity, timing and budget tests."""
import json
import math
import numpy as np
import pytest
import torch
from anytime_ncm.causal_confidence import confidence_features,cue_features,instrumented_request,RICH_NAMES
from anytime_ncm.confidence_pilot import schedule,analyze
from anytime_ncm.quality_controller import Meter
from anytime_ncm.controller_study import cache_row
from anytime_ncm.latency_diagnostic import check_parity
from anytime_ncm.forced_wmt import ForwardCounter
from anytime_ncm.upstream_adapter import reconstruct_prefixes
from anytime_ncm.quality_campaign import verify_campaign,usage_zero,UNITS
from test_phase4 import tiny

def test_entropy_margin_uniform_peaky_shift_and_no_mutation():
    logits=torch.zeros(1,64,4);before=logits.clone();ids=[0]*64
    v=confidence_features(logits,ids)
    np.testing.assert_allclose(v[:3],0.,atol=1e-7);np.testing.assert_allclose(v[3:],1.,atol=1e-6)
    assert torch.equal(logits,before)
    logits[:,:,0]=30.;a=confidence_features(logits,ids);b=confidence_features(logits+10.,ids)
    np.testing.assert_allclose(a,b,rtol=1e-5,atol=1e-6);np.testing.assert_allclose(a[:3],30.,atol=1e-6)
    assert a[3:].max()<1e-9

def test_eos_prefix_isolation_and_bad_shapes_nonfinite():
    x=torch.arange(256,dtype=torch.float32).reshape(1,64,4)/100;ids=[3,2]+[3]*62
    a=confidence_features(x,ids,eos=2);y=x.clone();y[:,2:,:]=float('nan')
    np.testing.assert_array_equal(a,confidence_features(y,ids,eos=2))
    with pytest.raises(ValueError):confidence_features(y,[3]*64)
    for shape in ((1,63,4),(2,64,4),(1,64,1)):
        with pytest.raises(ValueError):confidence_features(torch.zeros(shape),[0]*64)

def test_source_cues_are_literal_current_only_with_explicit_empty_cases():
    np.testing.assert_array_equal(cue_features('2 3','2'),[1,.5,1,0,1])
    np.testing.assert_array_equal(cue_features('kein Fehler','not wrong'),[0,1,1,1,1])
    np.testing.assert_array_equal(cue_features('plain','7'),[0,1,0,0,1])

def test_real_sparse_boundaries_independent_prefix_parity_and_work_on_tiny_cpu():
    torch.set_num_threads(1);model,context=tiny();counter=ForwardCounter(model,dict(inputs=5,generator_levels=1000,decoder=1000,encoder=0))
    meter=Meter(dict(cheap_features=4,confidence_features=2,cue_features=2));results={}
    try:
        counter.take('inputs');full=model.net.generate(None,context,**model.kwargs);levels=[]
        for d,z in enumerate(reconstruct_prefixes(model.vq,full),1):
            ids=model.pick(model.tokenizer.vqvae.decoder(z))[0].tolist();levels.append(dict(level=d,ids=ids,text=model.decode(ids)))
        cache=cache_row(dict(identity='synthetic',prefix_ids=[1]*96,codes=full[0].tolist(),levels=levels))
        for kind in ('cheap','rich'):
            counter.take('inputs');result=instrumented_request(model,'source 2',kind,meter);results[kind]=result
            check_parity(result,cache,dict(depth=11,method='assigned_sparse'))
            assert [v['level'] for v in result['features']]==[8,10] and model.net._cfg is None
            assert all(len(v['values'])==(19 if kind=='cheap' else len(RICH_NAMES)) for v in result['features'])
        for a,b in zip(results['cheap']['features'],results['rich']['features']):np.testing.assert_array_equal(a['values'],b['values'][:19])
        counter.take('inputs')
        with pytest.raises(ValueError):instrumented_request(model,'source','unknown')
        model.net.train();counter.take('inputs')
        with pytest.raises(ValueError):instrumented_request(model,'source','rich')
        assert counter.counts==dict(inputs=5,generator_levels=33,decoder=17,encoder=0)
        assert meter.counts==dict(cheap_features=4,confidence_features=2,cue_features=2)
        print('SYNTHETIC_PILOT_REQUESTS 5')
        print('SYNTHETIC_PILOT_FORWARDS '+json.dumps(counter.counts,sort_keys=True))
    finally:counter.close()

def synthetic_records(delta=.5,constant=False):
    out=[]
    for session in (0,1):
        for p in range(16):
            for repeat in (0,1):
                for kind in ('cheap','rich'):
                    fs=[]
                    for d in (8,10):
                        base=[p/100]*19;z=0 if constant else p
                        values=base if kind=='cheap' else base+[z+1,z+.5,z,.1+z/1000,.2+z/1000,.3+z/1000]+[0.]*5
                        fs.append(dict(level=d,values=values))
                    out.append(dict(session=session,position=p,index=p,repeat=repeat,kind=kind,warmup=False,parity=True,
                        wall_ms=100+p/100+(delta if kind=='rich' else 0),work=dict(inputs=1,generator_levels=11,decoder=3,encoder=0),features=fs,component_ms=dict(cheap=.1,extra=.5 if kind=='rich' else 0)))
    return out

def test_paired_gate_and_exact_boundary_without_simulation():
    a=analyze(synthetic_records());assert a['decision']=='pilot_passed'
    assert all(v['mean_added_ms']==pytest.approx(.5) for v in a['paired_sessions'].values())
    assert analyze(synthetic_records(1.))['decision']=='pilot_passed'
    assert analyze(synthetic_records(1.01))['decision']=='pilot_cost_screen_failed'

def test_missing_duplicate_inconsistent_features_and_constant_confidence_rejected():
    records=synthetic_records()
    with pytest.raises(ValueError):analyze(records[:-1])
    with pytest.raises(ValueError):analyze(records+[records[0]])
    records[1]['features'][0]['values'][0]=999
    with pytest.raises(ValueError):analyze(records)
    assert analyze(synthetic_records(constant=True))['decision']=='pilot_no_confidence_variation'

def test_counterbalanced_complete_schedule_including_charged_warmups():
    entries=[dict(index=i,identity=str(i)) for i in range(16)]
    for s in (0,1):
        rows=schedule(entries,s);assert len(rows)==74 and sum(r['warmup'] for r in rows)==10
        assert len({(r['position'],r['repeat'],r['kind']) for r in rows if not r['warmup']})==64
        for p in range(16):
            a=[r['kind'] for r in rows if not r['warmup'] and r['position']==p and r['repeat']==0]
            b=[r['kind'] for r in rows if not r['warmup'] and r['position']==p and r['repeat']==1]
            assert a==list(reversed(b))
    assert schedule(entries,0)!=schedule(entries,1)

def test_campaign_rejects_overbudget_or_negative_reservations(monkeypatch):
    import anytime_ncm.quality_campaign as c
    class Empty:
        def __truediv__(self,x):return self
        def glob(self,p):return []
        def rglob(self,p):return []
    monkeypatch.setattr(c,'campaign_root',lambda root:Empty())
    monkeypatch.setattr(c,'read',lambda p:dict(ceilings={k:100 for k in UNITS}))
    assert verify_campaign('/unused')['verified']
    a=usage_zero();a['model_requests']=101
    with pytest.raises(RuntimeError):verify_campaign('/unused',a)
    a['model_requests']=-1
    with pytest.raises(ValueError):verify_campaign('/unused',a)
