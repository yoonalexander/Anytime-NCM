"""Synthetic header access, sparse replay and cost-boundary tests; no fits."""
import json
import numpy as np
import pytest
from anytime_ncm.development_selection import select_private,replay_scores,estimated_cost
from anytime_ncm.quality_controller import Meter

def entries():return [dict(year=2015,index=i,role='development_fit' if i==0 else 'development_calibration') for i in (0,1)]

def test_trace_headers_skip_poisoned_fit_body_and_warmup_before_decode(tmp_path):
    es=entries();p=tmp_path/'trace.jsonl';lines=[]
    for e,warm in [(es[0],True),(es[0],False),(es[1],False)]:
        h=dict(e,warmup=warm);prefix=json.dumps(h)[:-1]
        lines.append(prefix+', "prefix_ids": '+('POISON NOT JSON' if e['index']==0 else '[1], "levels": []')+'}\n')
    p.write_text(''.join(lines));m=Meter(dict(trace_headers=3,calibration_trace_bodies=1));r=select_private(p,[es[1]],es,'trace',m,expected_warmups=1)
    assert list(r)==['2015:1'] and m.counts==dict(trace_headers=3,calibration_trace_bodies=1)

def test_reference_poison_skip_and_forbidden_missing_duplicate_headers(tmp_path):
    es=entries();p=tmp_path/'ref.jsonl';p.write_bytes((json.dumps(es[0])[:-1]+', "reference": ').encode()+b'"\xffPOISON"}\n'+(json.dumps(dict(es[1],reference='allowed'))+'\n').encode())
    m=Meter(dict(reference_headers=2,calibration_reference_bodies=1));r=select_private(p,[es[1]],es,'reference',m);assert r['2015:1']['reference']=='allowed'
    for raw in [json.dumps(dict(year=2015,index=99,role='development_evaluation',reference='bad'))+'\n',json.dumps(dict(es[0],reference='x'))+'\n',2*(json.dumps(dict(es[0],reference='x'))+'\n')]:
        p.write_text(raw)
        with pytest.raises(ValueError):select_private(p,[es[1]],es,'reference',Meter(dict(reference_headers=3,calibration_reference_bodies=1)))

def test_actual_inspection_schedules_threshold_equality_and_cue_veto():
    a=np.zeros((3,27));a[:,25:]=1;b=a.copy();b[2,25]=0
    s=dict(kind='development_joint',decision_levels=[8],threshold=.2,cue_guard=False,group='full')
    assert replay_scores(s,[.2,.3,.4],[.9,.1,.1],a,b)==[(8,[8]),(11,[8,11]),(11,[8,11])]
    s['decision_levels']=[8,10];s['cue_guard']=True
    assert replay_scores(s,[.2,.3,.4],[.9,.1,.1],a,b)==[(8,[8]),(10,[8,10]),(11,[8,10,11])]
    assert replay_scores(dict(kind='full'),None,None,a,b)==[(11,[11])]*3

def test_every_extra_observation_and_rich_decision_paid():
    spec=dict(kind='development_joint',group='cue',cue_guard=False)
    assert estimated_cost(spec,[(8,[8]),(11,[8,11])],{8:100,11:140},2,.5)==121.5
    spec['group']='cheap';assert estimated_cost(spec,[(8,[8]),(11,[8,11])],{8:100,11:140},2,.5)==121
    assert estimated_cost(dict(kind='full'),[],{11:140},2,.5)==140
