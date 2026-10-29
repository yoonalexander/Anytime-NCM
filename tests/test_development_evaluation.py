"""Selected-runtime equivalence, actual stopping, selective extraction and pairing."""
import copy,gzip,hashlib,io,tarfile
import numpy as np
import pytest
import torch
from anytime_ncm.development_evaluation_adapter import runtime_spec
from anytime_ncm.development_evaluation_data import extract_corpus
from anytime_ncm.development_models import decide
from anytime_ncm.joint_risk_controller import decision
from anytime_ncm.joint_risk_wmt import joint_request
from anytime_ncm.forced_wmt import ForwardCounter,forced_request
from anytime_ncm.development_trace import current_logits
from anytime_ncm.quality_controller import Meter
from anytime_ncm.controller_study import schedule,sum_work
from anytime_ncm.latency_diagnostic import LEVELS,cluster_draws
from test_phase4 import tiny

def spec(intercept=.2):return dict(name='ridge:cheap:8:guard0:0.6',kind='development_joint',method='ridge',group='cheap',columns=list(range(19)),decision_levels=[8],cue_guard=False,threshold=.6,models={'8':dict(status='fitted',method='ridge',mean=[0]*19,scale=[1]*19,coef=[0]*19+[intercept])})

def test_schema_adapter_exact_single_row_math_and_no_unused_feature_dependency():
    p=spec();p['models']['8']['coef'][1]=.3;p['models']['8']['coef'][4]=-.2;before=copy.deepcopy(p);adapted=runtime_spec(p)
    values=np.arange(128*27,dtype=float).reshape(128,27)/100
    for row in values:
        assert decide(p,8,row)==decision(adapted,8,row)
        changed=row.copy();changed[19:]=1e9;assert decision(adapted,8,row)==decision(adapted,8,changed)
    assert p==before

def test_adapter_rejects_policy_replacement_or_bad_coefficients():
    for field,value in [('threshold',.7),('columns',[1]*19),('method','tree'),('cue_guard',True),('decision_levels',[8,10])]:
        p=spec();p[field]=value
        with pytest.raises(ValueError):runtime_spec(p)
    p=spec();p['models']['8']['scale'][0]=0
    with pytest.raises(ValueError):runtime_spec(p)

def test_tiny_actual_selected_shape_skips_generation_current_parity_state_and_exact_work():
    torch.set_num_threads(1);model,_=tiny();counter=ForwardCounter(model,dict(inputs=4,generator_levels=30,decoder=5,encoder=0));m=Meter(dict(cheap_features=2,selected_logit_features=0,cue_features=0,decisions=2));states={name:{k:v.detach().clone() for k,v in net.state_dict().items()} for name,net in [('g',model.net),('t',model.tokenizer.vqvae)]}
    try:
        counter.take('inputs');full=forced_request(model,'source 2',11,'terminal')
        counter.take('inputs');early=joint_request(model,'source 2',runtime_spec(spec(.2)),m)
        counter.take('inputs');late=joint_request(model,'source 2',runtime_spec(spec(1.)),m)
        with torch.no_grad():independent=model.pick(current_logits(model,full['codes'],8))[0].tolist()
        assert early['exit_level']==8 and [o['level'] for o in early['observations']]==[8] and early['ids']==independent
        assert late['exit_level']==11 and [o['level'] for o in late['observations']]==[8,11] and late['ids']==full['ids']
        assert torch.equal(early['codes'],full['codes'][:,:sum(LEVELS[:8])]) and torch.equal(late['codes'],full['codes'])
        assert early['features'][0]['values']==late['features'][0]['values'] and early['features'][0]['values'][19:]==[0.]*8 and model.net._cfg is None
        for name,net in [('g',model.net),('t',model.tokenizer.vqvae)]:assert all(torch.equal(v,states[name][k]) for k,v in net.state_dict().items())
        counter.take('inputs');model.net.train()
        with pytest.raises(ValueError):joint_request(model,'source',runtime_spec(spec()),m)
        assert counter.counts==dict(inputs=4,generator_levels=30,decoder=5,encoder=0) and m.counts==dict(cheap_features=2,selected_logit_features=0,cue_features=0,decisions=2)
        print('SYNTHETIC_DEVELOPMENT_EVALUATION_REQUESTS 4')
    finally:counter.close()

def test_pinned_archive_extracts_only_selected_eval_payload_and_rejects_other_role(tmp_path):
    def blob(kind):
        tag=b'srcset' if kind=='source' else b'refset';extra=b'' if kind=='source' else b' trglang="en"'
        return b'<'+tag+b' srclang="any"'+extra+b'>\n<doc docid="d">\n<seg id="1">\xffPOISON</seg>\n<seg id="2">  allowed &amp; 42  </seg>\n</doc>\n</'+tag+b'>\n'
    members={'source':'test/newstest2015-deen-src.de.sgm','reference':'test/newstest2015-deen-ref.en.sgm'};data=io.BytesIO()
    with tarfile.open(fileobj=data,mode='w:') as tar:
        for kind,name in members.items():
            payload=blob(kind);info=tarfile.TarInfo(name);info.size=len(payload);info.mtime=0;tar.addfile(info,io.BytesIO(payload))
    raw=gzip.compress(data.getvalue(),mtime=0);p=tmp_path/'test.tgz';p.write_bytes(raw);item=dict(year=2015,path='test.tgz',bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),rows=2,**{kind+'_member':v for kind,v in members.items()},**{kind+'_sha256':hashlib.sha256(blob(kind)).hexdigest() for kind in members})
    entry=dict(year=2015,index=1,role='development_evaluation');m=Meter(dict(decompressed_bytes=1<<20,source_segment_headers=2,reference_segment_headers=2,source_body_decodes=1,reference_body_decodes=1));s,r,receipt=extract_corpus(tmp_path,[entry],[item],m,1<<20)
    assert s==r=={'2015:1':'  allowed &amp; 42  '} and receipt[0]['selected_payloads_each']==1
    with pytest.raises(ValueError):extract_corpus(tmp_path,[dict(entry,role='confirmation')],[item],m,1<<20)

def test_full_pairing_counts_and_cluster_weight_null_boundary():
    entries=[dict(index=i,identity=str(i)) for i in range(1188)];pred=[(8,[8]) if i%4==0 else (11,[8,11]) for i in range(1188)]
    for session in (0,1):
        plan=schedule(entries,pred,session);assert len(plan)==28572 and sum(r['warmup'] for r in plan)==60
        assert len({(r['position'],r['repeat'],r['method']) for r in plan if not r['warmup']})==28512
        work=sum_work(plan);assert work['generator_levels']<=183337 and work['decoder']<=30953
    cells=np.full((3,12),100.);cells[:,0]=[10,10,90];picks=np.array([[0,1],[0,0],[1,1]])
    np.testing.assert_allclose(cluster_draws(cells,['a','a','b'],picks)[:,0],[1-110/300,.9,.1]);cells[:,0]=95;np.testing.assert_allclose(cluster_draws(cells,['a','a','b'],picks),.05);cells[:,0]=100;np.testing.assert_allclose(cluster_draws(cells,['a','a','b'],picks),0)
