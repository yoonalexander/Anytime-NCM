"""Bounded synthetic-only tests; no saved outcome bodies or released weights."""
from copy import deepcopy
import json
import numpy as np
import pytest
import torch
from anytime_ncm.latency_diagnostic import (METHODS, LEVELS, observations, work, make_schedule,
    parity_cache, check_parity, cluster_draws, document_components, analyze)
from anytime_ncm.sparse_wmt import sparse_request
from anytime_ncm.forced_wmt import ForwardCounter, forced_request
from anytime_ncm.upstream_adapter import reconstruct_prefixes
from test_phase4 import tiny

def test_tiny_sparse_prefixes_independent_reconstruction_and_actual_work():
    torch.set_num_threads(1)
    model,context=tiny()
    counter=ForwardCounter(model,dict(inputs=100,generator_levels=1500,decoder=2000,encoder=0))
    try:
        counter.take('inputs')
        full=model.net.generate(None,context,**model.kwargs)
        expected=[]
        for d,latent in enumerate(reconstruct_prefixes(model.vq,full),1):
            ids=model.pick(model.tokenizer.vqvae.decoder(latent))[0].tolist()
            expected.append(dict(level=d,ids=ids,text=model.decode(ids)))
        row=dict(partition='E2_audit',identity='synthetic',prefix_ids=[1]*96,codes=full[0].tolist(),levels=expected)
        cache=parity_cache(row)
        seen=[];original=model.codes
        def capture(context,callback=None,maximum=None):
            if callback:
                original_callback=callback
                def wrapped(level,codes):
                    seen.append((level,codes.shape[1]))
                    return original_callback(level,codes)
                wrapped.inspection_levels=callback.inspection_levels
                callback=wrapped
            return original(context,callback,maximum)
        model.codes=capture
        for method,d in [('assigned_sparse',8),('assigned_sparse',10),('assigned_sparse',11),('fixed:8',8),('fixed:11',11)]:
            request=dict(method=method,depth=d);before=dict(counter.counts);counter.take('inputs')
            result=sparse_request(model,'synthetic',d) if method=='assigned_sparse' else forced_request(model,'synthetic',d,'terminal')
            assert {k:counter.counts[k]-before[k] for k in before}==work(request)
            check_parity(result,cache,request)
            assert torch.equal(result['codes'],full[:,:sum(LEVELS[:d])])
            assert model.net._cfg is None
        assert seen==[(d,sum(LEVELS[:d])) for d in (8,8,10,8,10,11)]
        for key in ('text','ids'):
            bad=deepcopy(result);bad[key]='tampered' if key=='text' else [999]*64
            with pytest.raises(ValueError):check_parity(bad,cache,request)
        bad=deepcopy(cache);bad['codes']['11']='bad'
        with pytest.raises(ValueError):check_parity(result,bad,request)
        assert counter.counts==dict(inputs=6,generator_levels=59,decoder=19,encoder=0)
        print('TOY_WORK_COUNTS '+json.dumps(counter.counts,sort_keys=True))
    finally:counter.close()

@pytest.mark.parametrize('depth,schedule',[(0,(8,10,11)),(9,(8,10,11)),(12,(8,10,11)),(True,(8,10,11)),(8.0,(8,10,11)),(8,None),(8,[8,10,11]),(8,(8,11))])
def test_invalid_sparse_inputs_before_any_forward(depth,schedule):
    model,_=tiny();counter=ForwardCounter(model,dict(inputs=0,generator_levels=0,decoder=0,encoder=0))
    try:
        with pytest.raises(ValueError):sparse_request(model,'synthetic',depth,schedule)
        assert not any(counter.counts.values())
    finally:counter.close()

def test_train_mode_and_exhausted_budget_fail_before_forward():
    model,_=tiny();counter=ForwardCounter(model,dict(inputs=0,generator_levels=0,decoder=0,encoder=0))
    try:
        model.net.train()
        with pytest.raises(ValueError):sparse_request(model,'synthetic',8)
        model.net.eval()
        with pytest.raises(RuntimeError,match='exhausted'):sparse_request(model,'synthetic',8)
        assert not any(counter.counts.values())
    finally:counter.close()

def test_schedule_paired_complete_deterministic_and_work_bounds():
    entries=[dict(index=i,identity=str(i)) for i in range(256)]
    exits=[(8,10,11)[i%3] for i in range(256)]
    a=make_schedule(entries,exits,0);b=make_schedule(entries,exits,1)
    assert a==make_schedule(entries,exits,0) and a!=b
    for plan in (a,b):
        assert len(plan)==6204 and sum(r['warmup'] for r in plan)==60
        keys={(r['position'],r['repeat'],r['method']) for r in plan if not r['warmup']}
        assert len(keys)==256*2*12
        assert all(sum(r['method']==m and r['warmup'] for r in plan)==5 for m in METHODS)
        totals={k:sum(work(r)[k] for r in plan) for k in work(plan[0])}
        assert totals['generator_levels']<=39809 and totals['decoder']<=7238 and totals['encoder']==0
        assert all(r['position']<16 for r in plan if r['warmup'])
    with pytest.raises(ValueError):make_schedule(entries,[9]*256,0)

def test_document_pairing_unequal_cluster_weights_and_null_boundary():
    cells=np.full((3,12),10.);cells[:,0]=[1.,1.,9.]
    groups=['a','a','b'];picks=np.array([[0,1],[0,0],[1,1]])
    actual=cluster_draws(cells,groups,picks)
    np.testing.assert_allclose(actual[:,0],[1-11/30,.9,.1])
    cells[:,0]=9.5
    np.testing.assert_allclose(cluster_draws(cells,groups,picks),.05)
    cells[:,0]=10.
    np.testing.assert_allclose(cluster_draws(cells,groups,picks),0.)
    cells[:,0]=11.
    assert (cluster_draws(cells,groups,picks)<0).all()

@pytest.mark.parametrize('groups,picks', [(['a']*3,[[0]]),(['a','a','b'],[[0]]),(['a','a','b'],[[0,2]])])
def test_bad_cluster_coverage_or_picks_rejected(groups,picks):
    with pytest.raises(ValueError):cluster_draws(np.ones((3,12)),groups,picks)

def test_document_alias_components_are_transitive():
    docs=[dict(index=i,document_sha256=d) for i,d in enumerate(['a','b','b','c','d'])]
    manifest={'partitions':{'x':[{'indices':[0,1]},{'indices':[2,3]},{'indices':[4]}]}}
    actual=document_components(docs,manifest)
    assert [r['document_sha256'] for r in actual]==['a','a','a','a','d']

def test_analysis_rejects_missing_cells_before_random_resampling():
    with pytest.raises(ValueError,match='Missing'):analyze([],list(range(16)),[],{})
    with pytest.raises(ValueError,match='Frozen'):analyze([],[],[],{},draws=1)

def test_analysis_rejects_inadequate_document_coverage_before_draws():
    entries=[dict(index=i) for i in range(16)]
    records=[]
    for s in range(2):
        for p in range(16):
            for r in range(2):
                for method in METHODS:
                    row=dict(session=s,position=p,repeat=r,method=method,depth=8 if method=='assigned_sparse' else int(method.split(':')[1]),warmup=False,parity=True,wall_ms=1.)
                    row['work']=work(row);records.append(row)
    docs=[dict(index=i,document_sha256='one') for i in range(16)]
    with pytest.raises(ValueError,match='Insufficient'):analyze(records,entries,docs,{})

def test_bad_method_depth_rejected():
    for m,d in [('future',8),('fixed:8',10),('assigned_sparse',9)]:
        with pytest.raises(ValueError):observations(m,d)
