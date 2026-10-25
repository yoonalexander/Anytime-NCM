"""Invented reference/source fixtures only; no real asset or network access."""
import pickle
import numpy as np
import pytest
from anytime_ncm.q0_population import normalize_source,parse_source_sgml,align_sources,aggregate_references,planning

@pytest.mark.parametrize('a,b',[(' a  b ','a b'),('a &amp; b','a & b'),('a\nb','a b')])
def test_normalization(a,b):assert normalize_source(a)==b


def test_document_alignment_and_no_plaintext_output():
    raw=b'<srcset>\n<doc docid="newsA">\n<seg id="1"> A &amp; B </seg>\n<seg id="2">C</seg>\n</doc>\n</srcset>'
    rows=parse_source_sgml(raw,expected=2)
    mapping,checks=align_sources({0:'A & B',1:'C'},rows)
    assert len(mapping)==2 and checks['normalized_equal_rows']==2
    assert set(mapping[0])=={'index','document_sha256','segment_id'}
    assert len(mapping[0]['document_sha256'])==64 and mapping[0]['document_sha256']==mapping[1]['document_sha256']
    with pytest.raises(ValueError):align_sources({0:'C',1:'A & B'},rows)

@pytest.mark.parametrize('raw',[b'<seg id="1">x</seg>',b'<doc>\n<seg id="1">x</seg>',b'<doc docid="a">\n<seg>x</seg>',b'<doc docid="a">\n<seg id="1">x</seg>\n<seg id="1">y</seg>'])
def test_bad_document_metadata(raw):
    with pytest.raises(ValueError):parse_source_sgml(raw,expected=1)


def test_selective_reference_coverage_and_document_overlap():
    raw=pickle.dumps(['has 12','not a number','value 2.5%','sealed word'],protocol=4)
    roles={'first':[0,1],'second':[2]}
    docs=[{'index':i,'document_sha256':'a' if i<2 else 'b','segment_id':str(i)} for i in range(4)]
    result=aggregate_references(raw,roles,[0,1],[3],docs,expected=4)
    assert result['reference_materializations']==3
    assert result['roles']['first']['numeric_covered_groups']==1
    assert result['roles']['second']['numeric_covered_groups']==1
    assert result['document_overlap_counts']['first']['second']==0
    assert result['roles']['second']['documents']['groups_in_known_consumed_documents']==1
    assert result['per_input_coverage_fields_written']==0
    assert 'has 12' not in str(result)
    with pytest.raises(ValueError):aggregate_references(raw,{'forbidden':[3]},[],[3],expected=4)


def test_unselected_invalid_utf8_never_decoded():
    raw=pickle.dumps(['12','zzzz'],protocol=4).replace(b'zzzz',b'\xff\xff\xff\xff')
    result=aggregate_references(raw,{'permitted':[0]},[0],[],expected=2)
    assert result['roles']['permitted']['numeric_covered_groups']==1


def test_pickle_code_execution_opcodes_rejected():
    with pytest.raises(ValueError):aggregate_references(b'\x80\x04cos\nsystem\n.',{'one':[0]},[],[],expected=1)

@pytest.mark.parametrize('n',[0,48,183,192,240,368,436,1024])
def test_planning_without_outcomes(n):
    result=planning(n)
    assert result['NI_floor_met']==(n>=183)
    assert result['zero_event_half_margin_floor_met']==(n>=368)
    if n:assert 0<result['zero_adverse_upper']<1


def test_model_libraries_absent():
    import sys
    assert not any(m=='torch' or m.startswith('torch.') or m=='transformers' or m.startswith('transformers.') for m in sys.modules)



def invented_manifests():
    rows=[{'index':i,'indices':[i],'identity':f'{i:064x}'} for i in range(3003)]
    parent={'partitions':{'exploration':rows[:512],'development':rows[512:768],'phase4_final':rows[768:1024],'reserved':rows[1024:]}}
    reserved={'roles':{'E2_audit':rows[1024:1280],'E3_development':rows[1280:1408],'E4_confirmation':rows[1408:2432],'closed_unallocated':rows[2432:]}}
    return parent,reserved


def test_exact_population_scope_and_consumed_final_exclusion():
    from anytime_ncm.q0_population import populations
    parent,reserved=invented_manifests();roles,consumed,final=populations(parent,reserved)
    allowed=set().union(*(set(x) for x in roles.values()))
    assert len(allowed)==2171 and len(consumed)==448 and len(final)==256
    assert not allowed.intersection(final)


def test_overlapping_or_mismatched_reservations_rejected():
    from anytime_ncm.q0_population import populations
    parent,reserved=invented_manifests()
    reserved['roles']['E4_confirmation'][0]=reserved['roles']['E3_development'][0]
    with pytest.raises(ValueError):populations(parent,reserved)


def test_aliases_require_a_new_design():
    from anytime_ncm.q0_population import populations
    parent,reserved=invented_manifests();parent['partitions']['exploration'][0]['indices']=[0,1]
    with pytest.raises(ValueError):populations(parent,reserved)
