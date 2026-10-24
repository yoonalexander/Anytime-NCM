"""Synthetic-only scientific contract tests: no historical outcome access."""
import json
import numpy as np
import pytest
from anytime_ncm.stronger_s1 import Corpus,selective_rows,search,costs,feasible,better,validate_rows

def rows_for(texts):
    return [{'index':i,'levels':[{'level':k+1,'text':text} for k,text in enumerate(levels)]} for i,levels in enumerate(texts)]

def test_mixed_corpus_statistics_match_direct_not_sentence_average():
    refs=['the long sentence has a total of 12 words in it today','not here']
    rows=rows_for([['the long sentence has words']*10+[refs[0]],['not at this place']*10+[refs[1]]])
    c=Corpus(rows,refs);a=np.array([3,11]);v=c.direct(a)
    assert abs(v['bleu']-c.evaluate(a)[0]['bleu'])<1e-10
    assert v['numeric_reference_coverage']==1

def test_no_numeric_coverage_is_unavailable():
    c=Corpus(rows_for([['no digits here']*11]),['some reference'])
    assert c.evaluate([11])[0]['numeric_reference_f1'] is None
    assert feasible(c.evaluate([11])[0],c.evaluate([11])[0])

def test_reader_filters_forbidden_body_before_json_decode(tmp_path):
    a={'identity':'a'*64,'index':0,'indices':[0]};b={'identity':'b'*64,'index':1,'indices':[1]}
    path=tmp_path/'rows.jsonl'
    path.write_bytes((json.dumps(dict(identity=a['identity'],index=0,partition='exploration',levels=[]))+'\n').encode()+b'{"identity":"'+b'b'*64+b'","index":1,"partition":"development","poison":BROKEN}\n')
    rows,skipped=selective_rows(path,[a],'exploration',{'exploration':[a],'development':[b]})
    assert len(rows)==1 and skipped==1
    with pytest.raises(json.JSONDecodeError):selective_rows(path,[b],'development',{'exploration':[a],'development':[b]})

@pytest.mark.parametrize('kind',['duplicate','missing','final'])
def test_reader_rejects_duplicate_missing_and_final(tmp_path,kind):
    e={'identity':'a'*64,'index':0};line=json.dumps(dict(identity=e['identity'],index=0,partition='exploration'))+'\n'
    if kind=='duplicate':line+=line
    if kind=='missing':line=''
    if kind=='final':line=line.replace('exploration','phase4_final')
    path=tmp_path/'rows';path.write_text(line)
    with pytest.raises(ValueError):selective_rows(path,[e],'exploration',{'exploration':[e],'development':[]})

class FakeCorpus:
    n=2
    def __init__(self,allow=True):self.allow=allow;self.calls=0
    def evaluate(self,a):
        self.calls+=1;v=20 if self.allow or all(k==11 for k in a) else 0
        return dict(bleu=v,chrf=v,numeric_reference_f1=None,negation_cue_mismatch_rate=0),False
    def direct(self,a):return self.evaluate(a)[0]

def test_search_charges_baselines_and_stops_exactly_at_cap_incomplete_sweep():
    c=FakeCorpus();events=[];checks=[]
    r=search(c,dict(f=.25,tau=.5,h=0),[('baseline',np.array([11,11]))]*13,events.append,lambda *x:checks.append(x),cap=16)
    assert r['evaluations']==len(events)==16
    assert r['termination']=='assignment_cap_incomplete_sweep'
    assert r['exits']==[1,11] and r['certified_optimum'] is False
    assert r['accepted_changes']==1

def test_search_retains_full_if_no_feasible_neighbor():
    r=search(FakeCorpus(False),dict(f=.25,tau=.5,h=0),[('baseline',np.array([11,11]))]*13,lambda x:None,lambda *x:None,cap=100)
    assert r['exits']==[11,11] and r['evaluations']==33
    assert r['termination']=='no_improving_feasible_coordinate_neighbor'

def test_coordinate_ties_are_deterministic():
    assert better([1,11],[11,1],dict(f=.25,tau=.5,h=0))
    assert not better([11,1],[1,11],dict(f=.25,tau=.5,h=0))

def test_terminal_and_controller_costs_not_free():
    assert costs([11],h=0,adaptive=False)[0]==1
    assert costs([11],h=.005)[0]==pytest.approx(1+.005*10+.001*11)
    assert costs([1],h=.005)[0]>costs([1],h=0)[0]

def test_guardrail_and_corpus_losses_all_apply():
    b=dict(bleu=20,chrf=40,numeric_reference_f1=.8,negation_cue_mismatch_rate=.1)
    for k,v in [('bleu',19.4),('chrf',38.9),('numeric_reference_f1',.77),('negation_cue_mismatch_rate',.13)]:
        assert not feasible(dict(b,**{k:v}),b)

def test_duplicate_levels_rejected_before_scoring():
    from anytime_ncm.wmt_data import identity
    row={'prefix_ids':[1]*96,'identity':identity([1]*96),'codes':[0]*313,'levels':[{'level':1,'ids':[0]*64,'text':''}]*11}
    with pytest.raises(ValueError,match='levels'):validate_rows([row])


def test_provenance_protocol_mismatch_fails_before_any_outcome_read(tmp_path):
    from anytime_ncm.stronger_s1 import provenance
    path=tmp_path/'docs/studies/stronger-research-protocol.md';path.parent.mkdir(parents=True);path.write_text('wrong protocol')
    with pytest.raises(ValueError,match='Protocol hash'):provenance(tmp_path,{'protocol_sha256':'wrong'})

def test_development_requires_release_before_materializing_data(tmp_path):
    from anytime_ncm.stronger_s1 import run
    path=tmp_path/'docs/studies/stronger-research-protocol.json';path.parent.mkdir(parents=True);path.write_text('{}')
    with pytest.raises(FileNotFoundError,match='exploration_release'):run(tmp_path,'development')
    assert not (tmp_path/'results/stronger_research/s1/development').exists()

def test_cached_baseline_attempts_still_consume_slots():
    c=Corpus(rows_for([['same words for all levels']*11]),['same words for all levels'])
    events=[]
    r=search(c,dict(f=.25,tau=.5,h=0),[('same',np.array([11]))]*13,events.append,lambda *x:None,cap=13)
    assert r['evaluations']==13 and len(events)==13 and all(x['cache_hit'] for x in events)


def test_retained_timing_is_identity_paired_with_all_repeats(tmp_path):
    from anytime_ncm.stronger_s1 import timed_development
    selected=[{'index':i,'identity':str(i)*64} for i in range(2)]
    rows=[dict(e,levels=[{'level':k,'ids':[0]*64,'text':'text'} for k in range(1,12)]) for e in selected]
    methods={'full':{'kind':'full'},'fixed':{'kind':'fixed','depth':11},'stability':{'kind':'stability','minimum':10,'patience':1,'epsilon':0},'adaptive':{'kind':'guarded','minimum':10,'patience':1,'epsilon':0}}
    p=tmp_path/'results/phase4/wmt14/4b_requests.jsonl';p.parent.mkdir(parents=True)
    with p.open('w') as f:
        for e in selected:
            for name in methods:
                for repeat in range(3):
                    r=dict(identity=e['identity'],index=e['index'],partition='development',method=name,repeat=repeat,exit_level=11,ids=[0]*64,wall_ms=(e['index']+1)*(2 if name=='full' else 1))
                    f.write(json.dumps(r)+'\n')
    result=timed_development(tmp_path,selected,rows,methods)
    assert result['fixed']['paired']['full']['relative_mean_reduction']==.5
    assert result['fixed']['paired']['full']['ci95']==[.5,.5]
    assert result['full']['requests']==6
