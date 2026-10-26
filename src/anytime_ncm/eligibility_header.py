"""Pinned-member SGML header normalization; segment bytes are unchanged."""
import re
from anytime_ncm.eligibility_audit import parse_sgm,need

def canonical_header(data,kind,member):
    suffix='-deen-src.de.sgm' if kind=='source' else '-deen-ref.en.sgm'
    need(kind in ('source','reference') and member.endswith(suffix),'Unattested language-pair member')
    pattern=rb'<srcset\b[^>]*>' if kind=='source' else rb'<refset\b[^>]*>'
    matches=list(re.finditer(pattern,data,re.I));need(len(matches)==1,'Ambiguous/missing dataset header')
    m=matches[0];header=m[0].decode('utf-8')
    attrs={k.lower():v for k,v in re.findall(r'([A-Za-z_]+)\s*=\s*["\x27]([^"\x27]*)["\x27]',header)}
    need(attrs.get('srclang','').lower() in ('de','deu','ger','german','any'),'Wrong source language')
    if kind=='reference':need(attrs.get('trglang','').lower() in ('en','eng','english'),'Wrong reference language')
    corrected=re.sub(r'(\bsrclang\s*=\s*)["\x27][^"\x27]*["\x27]',lambda x:x[1]+'"de"',header,flags=re.I)
    if kind=='reference':corrected=re.sub(r'(\btrglang\s*=\s*)["\x27][^"\x27]*["\x27]',lambda x:x[1]+'"en"',corrected,flags=re.I)
    return data[:m.start()]+corrected.encode('utf-8')+data[m.end():],attrs

def parse_official_sgm(data,kind,charge,member):
    canonical,_=canonical_header(data,kind,member)
    return parse_sgm(canonical,kind,charge)
