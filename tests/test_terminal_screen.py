"""Synthetic screen checks; no empirical artifact/model access."""
import copy
import numpy as np
import pytest
from anytime_ncm.terminal_screen import assemble,calculate
from anytime_ncm.evidence_timing import value_hash


def fixture():
    entries=[dict(index=i,identity=f'{i:064x}') for i in range(256)]
    rows=[dict(**e,levels=[dict(text='final' if d in (7,11) else str(d),ids=[d]) for d in range(1,12)]) for e in entries]
    records=[]
    for e in entries:
        for b in range(2):
            for repeat in range(2):
                for method in ['exact']+[f'fixed:{d}' for d in range(1,12)]:
                    depth=7 if method=='exact' else int(method.split(':')[1]);old=rows[e['index']]['levels'][depth-1]
                    records.append(dict(**e,block=b,repeat=repeat,phase='timed',method=method,depth=depth,schedule='every_level' if method=='exact' else 'terminal',
                        wall_ms=float(depth+4 if method=='exact' else depth),parity=True,work=dict(inputs=1,generator_levels=depth,decoder=depth if method=='exact' else 1,encoder=0),
                        ids_sha256=value_hash(old['ids']),text_sha256=value_hash(old['text'])))
    return entries,rows,records


def test_assembled_cost_selects_quality_depth_not_fastest_request():
    entries,rows,records=fixture();data,depths=assemble(entries,rows,records)
    assert set(depths.values())=={7}
    assert np.all(data['terminal_exact']==7) and np.all(data['full']==11) and np.all(data['dense_exact']==11)
    report=calculate(data,draws=100)
    assert report['contrasts']['terminal_exact_versus_full']['relative_mean_reduction']==pytest.approx(4/11)
    assert report['post_hoc'] and not report['E3_release'] and not report['certified_global_oracle_optimum']


@pytest.mark.parametrize('problem',['missing','duplicate','identity','work','output','schedule'])
def test_incomplete_or_mismatched_inputs_fail(problem):
    entries,rows,records=fixture()
    if problem=='missing':records.pop()
    if problem=='duplicate':records.append(copy.deepcopy(records[0]))
    if problem=='identity':records[0]['identity']='unknown'
    if problem=='work':records[0]['work']['decoder']=1
    if problem=='output':records[0]['text_sha256']='bad'
    if problem=='schedule':records[0]['schedule']='terminal'
    with pytest.raises(ValueError):assemble(entries,rows,records)
