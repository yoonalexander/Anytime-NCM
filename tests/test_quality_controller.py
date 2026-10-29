"""Bounded synthetic controller validation; no real outcomes/checkpoints."""
from copy import deepcopy
import json
import numpy as np
import pytest
import torch
from anytime_ncm.quality_controller import (FEATURES,Meter,Controller,features,replay,fit_models,candidates,point_pass)
from anytime_ncm.controller_study import selected_rows,schedule,sum_work,timing_analysis,cache_row
from anytime_ncm.latency_diagnostic import LEVELS,check_parity,cluster_draws
from anytime_ncm.controller_wmt import controller_request
from anytime_ncm.forced_wmt import ForwardCounter
from anytime_ncm.upstream_adapter import reconstruct_prefixes
from anytime_ncm.wmt_data import identity
from test_phase4 import tiny

def spec_exit(depth):
    models={}
    for d in (8,10):
        coef=np.zeros((20,4));coef[-1,:]=-1 if d==depth else 1
        models[str(d)]=dict(mean=[0.]*19,scale=[1.]*19,coef=coef.tolist())
    return dict(kind='ridge',threshold=0.,models=models)

def synthetic_row(i=0):
    prefix=[i+1]*96
    return dict(identity=identity(prefix),index=i,partition='exploration',prefix_ids=prefix,codes=[j%8 for j in range(313)],
        levels=[dict(level=d,ids=[d%4]*64,text='number 2' if d>=10 else 'number 3') for d in range(1,12)])

def test_live_callbacks_stop_at_real_boundary_and_match_independent_prefixes():
    torch.set_num_threads(1);model,context=tiny();counter=ForwardCounter(model,dict(inputs=64,generator_levels=1000,decoder=1000,encoder=0))
    try:
        counter.take('inputs');full=model.net.generate(None,context,**model.kwargs);levels=[]
        for d,z in enumerate(reconstruct_prefixes(model.vq,full),1):
            ids=model.pick(model.tokenizer.vqvae.decoder(z))[0].tolist();levels.append(dict(level=d,ids=ids,text=model.decode(ids)))
        row=dict(partition='exploration',identity=identity([1]*96),index=0,prefix_ids=[1]*96,codes=full[0].tolist(),levels=levels);cache=cache_row(row)
        specs=[spec_exit(8),spec_exit(10),spec_exit(11),dict(kind='stability',epsilon=0.),dict(kind='full')]
        for spec in specs:
            meter=Meter(dict(decisions=20,features=20));ctrl=Controller(spec,meter);d,visits=replay(ctrl,'synthetic',row)
            before=dict(counter.counts);counter.take('inputs');result=controller_request(model,'synthetic',ctrl)
            assert result['exit_level']==d and [o['level'] for o in result['observations']]==visits
            assert {k:counter.counts[k]-before[k] for k in before}==dict(inputs=1,generator_levels=d,decoder=len(visits),encoder=0)
            method='fixed:11' if spec['kind']=='full' else 'assigned_sparse'
            check_parity(result,cache,dict(depth=d,method=method));assert model.net._cfg is None
        assert counter.counts['inputs']==6 and counter.counts['generator_levels']<=62 and counter.counts['decoder']<=21
        model.net.train()
        with pytest.raises(ValueError):controller_request(model,'synthetic',Controller(spec_exit(8)))
        model.net.eval()
        print('TOY_CONTROLLER_FORWARD_COUNTS '+json.dumps(counter.counts,sort_keys=True))
    finally:counter.close()

def test_first_observation_is_not_stability_and_only_real_history_counts():
    r=synthetic_row();c=Controller(dict(kind='stability',epsilon=0.))
    ids=[1]*64
    assert not c.observe('text',8,[],ids,'same',None)
    assert c.observe('text',10,[],ids,'same',dict(level=8,ids=ids,text='same'))
    with pytest.raises(ValueError):c.observe('text',10,[],ids,'same',dict(level=7,ids=ids,text='same'))

def test_current_features_isolate_future_suffix_final_text_references_and_identity():
    r=synthetic_row();o=r['levels'][7]
    x=features('source 2',8,r['codes'][:sum(LEVELS[:8])],o['ids'],o['text'])
    poisoned=deepcopy(r);poisoned['codes'][sum(LEVELS[:8]):]=[999]*len(poisoned['codes'][sum(LEVELS[:8]):]);poisoned['levels'][10]['text']='SECRET FUTURE';poisoned['identity']='unused'
    xx=features('source 2',8,poisoned['codes'][:sum(LEVELS[:8])],o['ids'],o['text'])
    np.testing.assert_array_equal(x,xx);assert len(x)==len(FEATURES)==19 and x[13]==0
    assert replay(Controller(spec_exit(8)),'source 2',r)==replay(Controller(spec_exit(8)),'source 2',poisoned)
    with pytest.raises(ValueError):features('source',8,r['codes'],o['ids'],o['text'])
    with pytest.raises(ValueError):features('source',8,r['codes'][:sum(LEVELS[:8])],o['ids'],o['text'],dict(level=8,ids=o['ids'],text=o['text']))

def test_fit_budget_eight_endpoint_models_and_fixed_candidate_family():
    rows=[synthetic_row(i) for i in range(16)];sources={i:'source 2 '+str(i) for i in range(16)};refs={i:'number 2' for i in range(16)}
    meter=Meter(dict(features=32,sentence_label_pairs=48,fits=8));models=fit_models(rows,sources,refs,meter)
    assert meter.counts==dict(features=32,sentence_label_pairs=48,fits=8)
    assert [models[str(d)]['label_counts'] for d in (8,10)]==[[16]*4,[16]*4]
    assert len(candidates(models))==9
    for c in candidates(models):replay(Controller(c),sources[0],rows[0])
    print('SYNTHETIC_FIT_COUNTS '+json.dumps(meter.counts,sort_keys=True))

def test_insufficient_covered_training_labels_rejected():
    rows=[synthetic_row(i) for i in range(12)]
    m=Meter(dict(features=24,sentence_label_pairs=36,fits=8))
    with pytest.raises(ValueError,match='Insufficient'):fit_models(rows,{i:'source' for i in range(12)},{i:'no digits' for i in range(12)},m)
    assert m.counts['fits']==2

@pytest.mark.parametrize('kind',['bad','ridge'])
def test_unknown_or_malformed_policies_fail(kind):
    with pytest.raises((ValueError,KeyError)):Controller(dict(kind=kind,models={}))

def test_budget_rejects_before_work():
    m=Meter(dict(features=0,decisions=0))
    with pytest.raises(RuntimeError):Controller(spec_exit(8),m).observe('source',8,[],[],'',None)
    assert m.counts==dict(features=0,decisions=0)

def test_header_scanner_skips_unreleased_body_without_json_decode(tmp_path):
    a=synthetic_row(0);b=synthetic_row(1);entries=[dict(index=r['index'],identity=r['identity'],origin='exploration') for r in (a,b)]
    p=tmp_path/'rows.jsonl'
    raw=json.dumps(a)+'\n'+json.dumps(b).split(', "prefix_ids"')[0]+', POISON NON JSON\n'
    p.write_text(raw,encoding='utf-8');m=Meter(dict(trajectory_bodies=1))
    assert selected_rows(p,[entries[0]],entries,m)==[a] and m.counts['trajectory_bodies']==1
    with pytest.raises(ValueError,match='Forbidden'):selected_rows(p,[entries[0]],[entries[0]],Meter(dict(trajectory_bodies=1)))

def test_paired_schedule_complete_with_true_online_exit_expectations():
    entries=[dict(index=i,identity=str(i)) for i in range(87)];pred=[(d,[v for v in (8,10,11) if v<=d]) for d in [(8,10,11)[i%3] for i in range(87)]]
    for s in (0,1):
        p=schedule(entries,pred,s);assert len(p)==2148 and sum(r['warmup'] for r in p)==60
        assert len({(r['position'],r['repeat'],r['method']) for r in p if not r['warmup']})==2088
        counts=sum_work(p);assert counts['generator_levels']<=13783 and counts['decoder']<=2506
        assert all(r['position']<16 for r in p if r['warmup'])
    assert schedule(entries,pred,0)==schedule(entries,pred,0) and schedule(entries,pred,0)!=schedule(entries,pred,1)

def test_point_margins_boundary_and_missing_numeric_never_silently_pass():
    full=dict(bleu=20.,chrf=50.,numeric_reference_f1=.8,negation_cue_mismatch_rate=.1)
    edge=dict(bleu=19.5,chrf=49.,numeric_reference_f1=.78,negation_cue_mismatch_rate=.12)
    assert point_pass(edge,full)
    edge['bleu']-=1e-5;assert not point_pass(edge,full)
    edge['numeric_reference_f1']=None;assert not point_pass(edge,full)

def test_pairing_preserves_unequal_cluster_weights_null_and_five_percent_boundary():
    cells=np.full((3,12),10.);cells[:,0]=[1.,1.,9.];picks=np.array([[0,1],[0,0],[1,1]])
    np.testing.assert_allclose(cluster_draws(cells,['a','a','b'],picks)[:,0],[1-11/30,.9,.1])
    cells[:,0]=9.5;np.testing.assert_allclose(cluster_draws(cells,['a','a','b'],picks),.05)
    cells[:,0]=10.;np.testing.assert_allclose(cluster_draws(cells,['a','a','b'],picks),0.)

def test_missing_and_inadequately_clustered_timings_reject_before_bootstrap():
    with pytest.raises(ValueError,match='Missing'):timing_analysis([],list(range(16)),{},'fixed:11',0)
    rows=[]
    for s in (0,1):
        for p in range(16):
            for repeat in range(2):
                for m in ('controller',)+tuple('fixed:%d'%i for i in range(1,12)):
                    d=11 if m=='controller' else int(m.split(':')[1]);visits=[11] if m=='controller' else [d]
                    rows.append(dict(session=s,position=p,repeat=repeat,method=m,depth=d,visits=visits,warmup=False,parity=True,wall_ms=1.,work=dict(inputs=1,generator_levels=d,decoder=1,encoder=0)))
    with pytest.raises(ValueError,match='Inadequate'):timing_analysis(rows,[dict(component='same') for _ in range(16)],{},'fixed:11',0)
