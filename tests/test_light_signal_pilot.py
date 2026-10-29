"""Synthetic light-logit measurement, parity, accounting and gate tests."""
import json
import numpy as np
import pytest
import torch
from anytime_ncm.causal_light import logit_summary,instrumented_request,FEATURE_NAMES
from anytime_ncm.light_signal_pilot import schedule,analyze,KINDS
from anytime_ncm.quality_controller import Meter
from anytime_ncm.controller_study import cache_row
from anytime_ncm.latency_diagnostic import LEVELS,check_parity,value_hash
from anytime_ncm.forced_wmt import ForwardCounter
from anytime_ncm.upstream_adapter import reconstruct_prefixes
from test_phase4 import tiny

def test_margin_shift_invariance_selected_logit_shift_and_no_mutation():
    x=torch.arange(256,dtype=torch.float32).reshape(1,64,4)/100;before=x.clone();picked=x.argmax(-1);ids=picked[0].tolist()
    a=logit_summary(x,ids,'margin',picked_ids=picked);b=logit_summary(x+10,ids,'margin',picked_ids=picked)
    np.testing.assert_allclose(a,b,rtol=1e-4,atol=1e-6)
    a=logit_summary(x,ids,'selected_logit',picked_ids=picked);b=logit_summary(x+10,ids,'selected_logit',picked_ids=picked)
    np.testing.assert_allclose(b-a,10,atol=1e-6);assert torch.equal(x,before)
    np.testing.assert_array_equal(a,logit_summary(x,ids,'selected_logit'))

def test_eos_tail_isolation_ties_empty_and_nonfinite_failures():
    x=torch.zeros(1,64,4);ids=[0,2]+[0]*62
    np.testing.assert_array_equal(logit_summary(x,ids,'margin'),[0,0,0])
    y=x.clone();y[:,2:,:]=float('nan')
    for kind in ('margin','selected_logit'):
        np.testing.assert_array_equal(logit_summary(x,ids,kind,eos=2),logit_summary(y,ids,kind,eos=2))
        with pytest.raises(ValueError):logit_summary(y,[0]*64,kind)
    with pytest.raises(ValueError):logit_summary(x[:,:0],[],'margin')
    with pytest.raises(ValueError):logit_summary(x,ids,'unknown')

def test_tiny_current_prefix_hashes_independent_outputs_and_exact_work():
    torch.set_num_threads(1);model,context=tiny();counter=ForwardCounter(model,dict(inputs=6,generator_levels=1000,decoder=1000,encoder=0))
    meter=Meter(dict(cheap_features=6,margin_features=2,selected_logit_features=2,cue_features=4));results={}
    try:
        counter.take('inputs');full=model.net.generate(None,context,**model.kwargs);levels=[]
        for d,z in enumerate(reconstruct_prefixes(model.vq,full),1):
            ids=model.pick(model.tokenizer.vqvae.decoder(z))[0].tolist();levels.append(dict(level=d,ids=ids,text=model.decode(ids)))
        cache=cache_row(dict(identity='synthetic',prefix_ids=[1]*96,codes=full[0].tolist(),levels=levels))
        for kind in KINDS:
            counter.take('inputs');r=instrumented_request(model,'source 2',kind,meter);results[kind]=r
            check_parity(r,cache,dict(depth=11,method='assigned_sparse'))
            assert all(value_hash(v['codes'])==cache['codes'][str(v['level'])] for v in r['prefix_codes'])
            assert all(len(f['values'])==len(FEATURE_NAMES[kind]) for f in r['features']) and model.net._cfg is None
        for kind in ('margin','selected_logit'):
            for a,b in zip(results['cheap']['features'],results[kind]['features']):np.testing.assert_array_equal(a['values'],b['values'][:19])
        counter.take('inputs')
        with pytest.raises(ValueError):instrumented_request(model,'source','unknown')
        model.net.train();counter.take('inputs')
        with pytest.raises(ValueError):instrumented_request(model,'source','margin')
        assert counter.counts==dict(inputs=6,generator_levels=44,decoder=20,encoder=0)
        assert meter.counts==dict(cheap_features=6,margin_features=2,selected_logit_features=2,cue_features=4)
        print('SYNTHETIC_LIGHT_REQUESTS 6');print('SYNTHETIC_LIGHT_FORWARDS '+json.dumps(counter.counts,sort_keys=True))
    finally:counter.close()

def synthetic_records(margin_cost=.5,selected_cost=.2,ready_penalty=.5,oscillation=0.):
    rows=[]
    for s in (0,1):
        for p in range(16):
            for repeat in range(8):
                for kind in KINDS:
                    fs=[]
                    for d in (8,10):
                        base=[p/100]*19;v=base if kind=='cheap' else base+[p+1,p+.5,p]+[0.]*5
                        fs.append(dict(level=d,values=v))
                    extra=0 if kind=='cheap' else margin_cost if kind=='margin' else selected_cost
                    delta=0 if kind=='cheap' else ready_penalty+oscillation*(1 if repeat%2 else -1)
                    rows.append(dict(session=s,position=p,index=p,repeat=repeat,kind=kind,warmup=False,parity=True,wall_ms=100+p/100+delta,
                        work=dict(inputs=1,generator_levels=11,decoder=3,encoder=0),features=fs,component_ms=dict(cheap=.1,extra=extra)))
    return rows

def test_explicit_component_gate_priority_and_original_whole_path_failure_preserved():
    a=analyze(synthetic_records(oscillation=10))
    assert a['selected_signal']=='margin' and a['decision']=='light_signal_collection_supported'
    assert a['original_entropy_pilot_whole_request_gate_still_failed'] and not a['whole_controller_speedup_established']
    assert a['signals']['margin']['sessions']['0']['p95_added_ready_ms']>3
    assert analyze(synthetic_records(margin_cost=1.01))['selected_signal']=='selected_logit'
    assert analyze(synthetic_records(margin_cost=1.01,selected_cost=1.01))['decision']=='no_light_signal_qualified'
    assert analyze(synthetic_records(ready_penalty=100))['decision']=='no_light_signal_qualified'

def test_missing_duplicate_inconsistent_timing_or_features_rejected():
    a=synthetic_records()
    with pytest.raises(ValueError):analyze(a[:-1])
    with pytest.raises(ValueError):analyze(a+[a[0]])
    a[1]['features'][0]['values'][0]=999
    with pytest.raises(ValueError):analyze(a)

def test_eight_repeat_three_method_order_balanced_and_all_work_charged():
    entries=[dict(index=i,identity=str(i)) for i in range(16)]
    for s in (0,1):
        rows=schedule(entries,s);assert len(rows)==399 and sum(r['warmup'] for r in rows)==15
        assert len({(r['position'],r['repeat'],r['kind']) for r in rows if not r['warmup']})==384
        for p in range(16):
            orders=[[r['kind'] for r in rows if not r['warmup'] and r['position']==p and r['repeat']==i] for i in range(8)]
            assert len({tuple(v) for v in orders[:6]})==6
            for kind in KINDS:
                counts=[sum(v[j]==kind for v in orders) for j in range(3)];assert max(counts)-min(counts)<=1
    assert schedule(entries,0)!=schedule(entries,1)
