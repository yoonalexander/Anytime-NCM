"""Synthetic only: no repository datasets, references, timings or model imports."""
import json
import numpy as np
import pytest
from anytime_ncm.q1_exploratory import *

def metric(**kw):
    return dict(bleu=30.,chrf=50.,numeric_reference_f1=1.,negation_cue_mismatch_rate=0.,**kw) if not kw else {**metric(),**kw}

@pytest.mark.parametrize('key,margin',list(MARGINS.items()))
def test_margin_boundary(key,margin):
    f=metric();direction=1 if key=='negation_cue_mismatch_rate' else -1
    assert feasible({**f,key:f[key]+direction*margin},f)
    assert not feasible({**f,key:f[key]+direction*(margin+1e-5)},f)

@pytest.mark.parametrize('value',[None,float('nan'),float('inf')])
def test_inadequate_or_invalid_numeric(value):assert not feasible(metric(numeric_reference_f1=value),metric())

def test_schedule_visits():
    assert visits([8,10,11],'sparse_8_10_11').tolist()==[1,2,3]
    assert visits([9,10,11],'sparse_9_10_11').tolist()==[1,2,3]
    assert visits([10,11],'sparse_10_11').tolist()==[1,2]
    assert visits([1,11],'terminal_oracle').tolist()==[1,1]
    with pytest.raises(ValueError):visits([9],'sparse_8_10_11')

def test_observation_costs():
    p=np.arange(1,12,dtype=float)
    assert costs([10,11],'sparse_10_11',p,2).tolist()==pytest.approx([10.05,13.1])
    assert costs([10,11],'terminal_oracle',p,2).tolist()==[10,11]
    assert costs([11],'sparse_10_11',p,2,.2,2)[0]==pytest.approx(15.4)
    with pytest.raises(ValueError):costs([11],'sparse_10_11',p,-1)

class Fake:
    n=4
    def __init__(self,allowed=True):self.allowed=allowed;self.seen=[]
    def evaluate(self,a):
        self.seen.append(tuple(a));return (metric() if self.allowed or min(a)==11 else metric(bleu=0)),len(set(self.seen))<len(self.seen)
    def direct(self,a):return self.evaluate(a)[0]

def test_cap_and_deterministic_order():
    events=[];r=search(Fake(),'terminal_oracle',np.arange(1,12),0,events.append,cap=3)
    assert r['evaluations']==3 and len(events)==3 and r['termination']=='assignment_cap'
    assert r['exits']==[1,1,11,11] and r['certified_optimum'] is False

def test_no_improvement_and_no_cap_expansion():
    r=search(Fake(False),'sparse_10_11',np.arange(1,12),0,lambda e:None)
    assert r['exits']==[11]*4 and r['evaluations']==5 and r['termination']=='no_improving_coordinate_in_complete_pass'

def test_expensive_earlier_never_accepted():
    p=np.ones(11);p[9]=100
    r=search(Fake(),'sparse_10_11',p,1,lambda e:None)
    assert r['accepted_changes']==0

def test_header_rejects_before_body_decode(tmp_path):
    p=tmp_path/'bad';p.write_bytes(b'{"identity": "'+b'a'*64+b'", "index": 999, "partition": "E4_confirmation", NOT_JSON')
    charges=[]
    with pytest.raises(ValueError,match='before body decode'):read_rows(p,{'exploration':[]},lambda *a:charges.append(a))
    assert charges==[]

def test_corpus_aggregation_and_sparse_reference():
    refs=['There are 123 apples in the garden .','A short sentence .']
    rows=[dict(levels=[dict(level=k,text=(ref if k==11 else 'Nothing .'),ids=[k]*64) for k in range(1,12)]) for ref in refs]
    c=Corpus(rows,refs)
    assert c.covered.tolist()==[True,False]
    a=[11,10];s=c.direct(a)
    assert s['numeric_reference_coverage']==1 and s['numeric_reference_f1']==1
    assert c.parity_checks==1 and c.evaluate(a)[1]
    empty=Corpus([rows[1]],[refs[1]]);f=empty.direct([11]);assert not feasible(f,f)

def fixture():
    rows=[dict(index=i,identity=str(i),levels=[dict(text=str(k),ids=[k]) for k in range(1,12)]) for i in range(2)]
    entries=[dict(index=i,identity=str(i)) for i in range(2)];records=[]
    for i in range(2):
        for b in range(2):
            for rep in range(2):
                for m in range(12):
                    d=11 if m==0 else m;s=rows[i]['levels'][d-1]
                    records.append(dict(phase='timed',index=i,identity=str(i),block=b,repeat=rep,method='exact' if m==0 else f'fixed:{m}',depth=d,schedule='every_level' if m==0 else 'terminal',parity=True,work=dict(inputs=1,generator_levels=d,decoder=d if m==0 else 1,encoder=0),wall_ms=10.+d,text_sha256=value_hash(s['text']),ids_sha256=value_hash(s['ids'])))
    return entries,rows,records

def test_timing_complete():
    e,r,x=fixture();cells,n=timing_cells(e,r,x,[])
    assert cells.shape==(2,2,2,12) and n==0 and cells[0,0,0,10]==20

@pytest.mark.parametrize('fault',['missing','duplicate','identity','hash','work','block','depth','latency','method','warmup'])
def test_timing_validation(fault):
    e,r,x=fixture()
    if fault=='missing':x.pop()
    elif fault=='duplicate':x.append(dict(x[0]))
    elif fault=='identity':x[0]['identity']='sealed'
    elif fault=='hash':x[0]['text_sha256']='bad'
    elif fault=='work':x[0]['work']['encoder']=1
    elif fault=='block':x[0]['block']=-1
    elif fault=='depth':x[0]['depth']=1
    elif fault=='latency':x[0]['wall_ms']=float('nan')
    elif fault=='method':x[0]['method']='fixed:12'
    else:x.append(dict(phase='warmup',identity='sealed',index=999))
    with pytest.raises(ValueError):timing_cells(e,r,x,[])


def test_e2_header_is_recognized():
    line=b'{"identity": "'+b'a'*64+b'", "index": 3, "partition": "E2_audit"}'
    assert HEADER.match(line)[3]==b'E2_audit'
