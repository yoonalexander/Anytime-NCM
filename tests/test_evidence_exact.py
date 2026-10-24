"""E2 synthetic tests; never read new empirical outcomes."""
from collections import Counter
import copy
import numpy as np
import pytest
from anytime_ncm.evidence_exact import exact_depth,make_schedule,quality_gate,FAMILY,TAIL,METHODS,analyze
from anytime_ncm.evidence_preflight import minimum_coverage,mc_precision,cue_interval


def row(index,early=7):
    return dict(index=index,identity=f'{index:064x}',levels=[dict(level=d,text='Final text 7' if d in (early,11) else f'Partial {d}',ids=[d]) for d in range(1,12)])


def test_first_exact_string_not_raw_ids_or_normalized_matching():
    r=row(0)
    r['levels'][2]['text']='final text 7'
    r['levels'][3]['text']='Final text 7 '
    assert exact_depth(r)==7
    r['levels'][6]['text']='Other'
    assert exact_depth(r)==11
    r['levels'][0]['text']='Final text 7'
    assert exact_depth(r)==1
    r['levels'].pop()
    with pytest.raises(ValueError):exact_depth(r)


def fixture():
    entries=[dict(identity=f'{i:064x}',index=i) for i in range(256)]
    warm=[dict(identity=f'{i:064x}',index=i) for i in range(256,272)]
    rows={i:row(i) for i in range(272)}
    return entries,warm,rows


def test_schedule_pairing_populations_caps_and_determinism():
    entries,warm,rows=fixture()
    plan=make_schedule(entries,warm,rows)
    assert plan==make_schedule(entries,warm,rows)
    assert len(plan)==12408
    assert sum(r['phase']=='warmup' for r in plan)==120
    assert sum(r['depth'] for r in plan)<=79618
    assert sum(r['depth'] if r['method']=='exact' else 1 for r in plan)<=22748
    for b in range(2):
        selected=[r for r in plan if r['block']==b]
        assert len(selected)==6204
        assert set(Counter((r['identity'],r['repeat'],r['method']) for r in selected if r['phase']=='timed').values())=={1}
        assert Counter(r['method'] for r in selected if r['phase']=='warmup')==Counter({m:5 for m in METHODS})
    assert all(r['index']>=256 for r in plan if r['phase']=='warmup')
    assert all(r['index']<256 for r in plan if r['phase']=='timed')


@pytest.mark.parametrize('problem',['extra','missing','overlap','count'])
def test_access_mismatch_fails_before_schedule(problem):
    entries,warm,rows=fixture()
    if problem=='extra':rows[999]=row(999)
    if problem=='missing':rows.pop(1)
    if problem=='overlap':warm[0]=entries[0]
    if problem=='count':entries.pop()
    with pytest.raises(ValueError):make_schedule(entries,warm,rows)


def test_conservative_family_and_no_degenerate_cue_pass():
    assert FAMILY==59 and TAIL==.05/118
    assert minimum_coverage(TAIL)>256
    assert mc_precision(100000,TAIL,FAMILY)['quantile_resolved']
    intervals={k:dict(lower=0.,upper=0.) for k in ('bleu','chrf','numeric','negation')}
    assert quality_gate(intervals)=='pass'
    intervals['numeric']=cue_interval(np.zeros(256),TAIL)
    assert quality_gate(intervals)=='unresolved'
    intervals['bleu']=dict(lower=-3.,upper=-.6)
    assert quality_gate(intervals)=='fail'
    intervals['bleu']=dict(lower=0.,upper=0.)
    intervals['numeric']=cue_interval([],TAIL)
    assert quality_gate(intervals)=='unresolved'


def test_analysis_refuses_missing_schedule_before_metric_work():
    with pytest.raises(ValueError):analyze({},[],[],[],[dict(request_id=0)],draws=1)


def test_full_exact_constructed_case_corpus_and_paired_work():
    entries,warm,rows=fixture()
    # Restrict first test to text-equivalent controls. Even then finite cue equality for fixed early is unresolved.
    for r in rows.values():
        for level in r['levels']:level['text']='Final text 7'
    plan=make_schedule(entries,warm,rows)
    records=[dict(r,wall_ms=float(r['depth']+1),parity=True,work=dict(inputs=1,generator_levels=r['depth'],decoder=r['depth'] if r['method']=='exact' else 1,encoder=0)) for r in plan]
    result=analyze(rows,entries,['Final text 7']*256,records,plan,draws=20)
    assert result['quality']['exact']['status']=='pass'
    assert result['quality']['fixed:1']['status']=='unresolved'
    assert result['quality']['fixed:11']['status']=='pass'
    assert result['early_exact_inputs']==256
    assert not result['controller_entry_released']
