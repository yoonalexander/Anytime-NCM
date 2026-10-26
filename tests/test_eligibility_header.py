"""Invented header fixtures only; no archive reads."""
import pytest
from anytime_ncm.eligibility_header import canonical_header,parse_official_sgm

def sample(lang='any',target='en',kind='source'):
    tag='srcset' if kind=='source' else 'refset';extra='' if kind=='source' else f' trglang="{target}"'
    return f'<{tag} srclang="{lang}"{extra}>\n<doc docid="invented">\n<seg id="1">A 123 sentence.</seg>\n</doc>\n</{tag}>'.encode()

@pytest.mark.parametrize('lang',['any','de','German','deu','ger'])
def test_standard_source_labels(lang):
    data=sample(lang);fixed,attrs=canonical_header(data,'source','test/newstest2015-deen-src.de.sgm')
    assert attrs['srclang']==lang and fixed.split(b'\n')[1:]==data.split(b'\n')[1:]
    charges=[];rows=parse_official_sgm(data,'source',lambda *a:charges.append(a),'test/newstest2015-deen-src.de.sgm')
    assert rows[0]['text']=='A 123 sentence.' and charges==[('source_materializations',1)]

@pytest.mark.parametrize('target',['en','eng','English'])
def test_reference_labels(target):
    rows=parse_official_sgm(sample(target=target,kind='reference'),'reference',lambda *a:None,'test/newstest2015-deen-ref.en.sgm')
    assert rows[0]['covered'] and 'text' not in rows[0]

@pytest.mark.parametrize('fault',['wrong_source','wrong_target','unattested_member','duplicate_header'])
def test_rejects(fault):
    data=sample(kind='reference');member='test/newstest2015-deen-ref.en.sgm'
    if fault=='wrong_source':data=sample('fr',kind='reference')
    elif fault=='wrong_target':data=sample(target='de',kind='reference')
    elif fault=='unattested_member':member='test/not-de-en.sgm'
    else:data+=b'<refset srclang="de" trglang="en">'
    with pytest.raises(ValueError):parse_official_sgm(data,'reference',lambda *a:None,member)
