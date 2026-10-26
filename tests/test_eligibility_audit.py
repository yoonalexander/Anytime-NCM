"""Deterministic invented fixtures only; no corpus or model files."""
import itertools,math
import numpy as np
import pytest
from scipy.optimize import brentq
from scipy.stats import binom
from anytime_ncm.eligibility_audit import *

@pytest.mark.parametrize('j',[1,2,128,512,1024])
def test_zero_formula(j):
    counts=[2]*j
    assert float(cue_upper(0,counts))==pytest.approx(zero_upper(counts),abs=2e-11)
    assert float(cue_upper(0,counts))>0

@pytest.mark.parametrize('s',[0,.001,.01,.02,.2,.8,1])
def test_root_independently(s):
    j=512;counts=[2]*j;u=float(cue_upper(s,counts))
    if s==1:assert u==1;return
    root=brentq(lambda q:j*float(kl(s,q))-math.log(40),max(s,1e-14),1-1e-14) if s>0 else -math.expm1(math.log(.025)/j)
    assert u>=root-1e-12 and u-root<2e-11

def test_fixed_weight_not_unweighted_doc_mean():
    counts=[1,9]
    assert zero_upper(counts)>zero_upper([5,5])
    assert float(cue_upper(.1,counts))>=.1
    assert cue_upper(0,[0,0]) is None
    assert zero_upper([0,0]) is None
    assert float(cue_upper(.1,[0,1,9]))==float(cue_upper(.1,[1,9]))

@pytest.mark.parametrize('counts,s',[([-1,2],0),([1.5,2],0),([1,2],-1),([1,2],1.1),([1,2],float('nan'))])
def test_bound_invalid(counts,s):
    with pytest.raises(ValueError):cue_upper(s,counts)

def test_monotone_and_alpha():
    s=np.linspace(0,1,51);u=cue_upper(s,[1,2,7]*100)
    assert np.all(np.diff(u)>=0) and np.all(u>=s)
    assert np.all(cue_upper(s,[1]*500,.001)>=cue_upper(s,[1]*500,.025))

@pytest.mark.parametrize('counts',[[1,1,1],[1,2,5],[0,1,5]])
def test_exact_heterogeneous_cluster_coverage(counts):
    probs=[.001,.02,.25];weights=np.array(counts)/sum(counts);truth=float(weights@probs);failure=0.
    for bits in itertools.product([0,1],repeat=3):
        prob=math.prod(p if b else 1-p for b,p in zip(bits,probs));s=float(weights@bits)
        if float(cue_upper(s,counts))<truth-1e-12:failure+=prob
    assert failure<=.025+1e-12

def test_fractional_losses_and_precision():
    counts=[2]*512;positive=float(np.mean([.25]+[0]*511));u=float(cue_upper(positive,counts))
    assert u>=positive and u>0
    assert float(cue_upper(0,[2]*128))>.02
    assert float(cue_upper(0,[2]*1024))<.01

def test_reference_eb_zero_not_magic():
    assert eb_ratio(np.zeros((1,512)),[2]*512) is None or float(eb_ratio(np.zeros((1,512)),[2]*512)[0])>.02

def sgm(kind='source',text='A 123 sentence',language='de',doc='article',seg='1'):
    tag='srcset' if kind=='source' else 'refset';target='' if kind=='source' else ' trglang="en"'
    return f'<{tag} srclang="{language}"{target}>\n<doc docid="{doc}" origlang="de">\n<seg id="{seg}">{text}</seg>\n</doc>\n</{tag}>'.encode()

def test_parser_source_reference_access():
    charges=[];c=lambda *a:charges.append(a)
    src=parse_sgm(sgm(),'source',c);ref=parse_sgm(sgm('reference'),'reference',c)
    assert src[0]['text']=='A 123 sentence' and ref[0]['covered']
    assert 'text' not in ref[0] and charges==[('source_materializations',1),('reference_materializations',1)]

@pytest.mark.parametrize('fault',['wrong_language','missing_doc','duplicate','unclosed','multiline','cap'])
def test_parser_failure(fault):
    data=sgm()
    if fault=='wrong_language':data=sgm(language='fr')
    elif fault=='missing_doc':data=data.replace(b'docid=',b'bad=')
    elif fault=='duplicate':data=data.replace(b'</doc>',b'<seg id="1">duplicate</seg>\n</doc>')
    elif fault=='unclosed':data=data.replace(b'</doc>',b'')
    elif fault=='multiline':data=data.replace(b'A 123 sentence',b'A\n123 sentence')
    with pytest.raises(ValueError):parse_sgm(data,'source',lambda *a:None,cap=0 if fault=='cap' else 20000)

def row(i,doc=None,prefix=None,year=2015,covered=True):
    return dict(index=i,year=year,doc_hash=doc or str(i),raw_hash='r'+str(i),normalized_hash='n'+str(i),prefix_hash=prefix or 'p'+str(i),covered=covered,story_hash=None)

def empty_history():return {k:set() for k in ['raw_hash','normalized_hash','prefix_hash','doc_hash']}

def test_aliases_components_and_private_flags():
    rows=[row(0,'doc0','same'),row(1,'doc1','same'),row(2,'doc2'),row(3,'doc3'),row(4,'doc4')]
    a,m,private=inventory(rows,empty_history())
    assert a['aliases_removed']==1 and a['eligible_components']==4 and len(m)==4
    assert all('covered' not in x and 'text' not in x for x in m)
    assert sum(x['input_count'] for x in private['components'])==4
    assert inventory(rows,empty_history())[1]==m
    assert len({x['component'] for x in m if x['role']=='development'}&{x['component'] for x in m if x['role']=='confirmation'})==0

def test_entire_historical_overlap_component_excluded():
    rows=[row(0,'same_doc'),row(1,'same_doc'),row(2)]
    h=empty_history();h['prefix_hash'].add('p0');a,m,_=inventory(rows,h)
    assert a['excluded_canonical_inputs']=={'historical_overlap':2} and len(m)==1

def test_oversize_not_split_and_coverage_none():
    rows=[row(i,'large',covered=False) for i in range(129)]
    a,m,_=inventory(rows,empty_history());assert a['excluded_canonical_inputs']=={'component_over128':129} and not m
    a,m,_=inventory([row(i,covered=False) for i in range(10)],empty_history())
    assert a['roles']['confirmation']['numeric_zero_adverse_KL_upper'] is None and not a['operational_screen_passed']

def test_shared_story_merges_cross_year():
    a=row(0,year=2015);b=row(1,year=2016);a['story_hash']=b['story_hash']='same_url'
    result,manifest,_=inventory([a,b],empty_history())
    assert result['eligible_components']==1 and len({x['component'] for x in manifest})==1

def test_cross_component_dependence_negative_control():
    # With one shared flag, a zero sample occurs with probability.98 at true risk.02.
    assert zero_upper([2]*512)<.02
    assert .98>.025
