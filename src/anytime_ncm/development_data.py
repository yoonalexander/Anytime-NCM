"""Selective byte-header SGML reader: decode only prospectively allocated payloads."""
import re
from anytime_ncm.eligibility_header import canonical_header
ATTR=re.compile(rb'([A-Za-z_]+)\s*=\s*["\x27]([^"\x27]*)["\x27]')

def selected_segments(data,kind,member,active,expected_rows,meter,expected_headers=None):
    if kind not in ('source','reference') or not isinstance(data,bytes) or any(type(i)is not int or not 0<=i<expected_rows for i in active):raise ValueError('Invalid selective SGML allocation')
    canonical_header(data,kind,member) # validates only the one dataset header and pinned language-pair suffix
    doc=None;seen=set();headers=[];selected={}
    for raw in data.splitlines():
        line=raw.strip()
        if re.match(rb'<doc\b',line,re.I):
            if doc is not None:raise ValueError('Nested document')
            attrs={k.lower():v for k,v in ATTR.findall(line)};doc=attrs.get(b'docid')
            if not doc:raise ValueError('Missing document identity')
        elif re.match(rb'</doc\s*>',line,re.I):
            if doc is None:raise ValueError('Unexpected document close')
            doc=None
        elif re.match(rb'<seg\b',line,re.I):
            m=re.fullmatch(rb'<seg\b([^>]*)>(.*)</seg>\s*',line,re.I)
            if m is None or doc is None:raise ValueError('Malformed/outside document segment')
            attrs={k.lower():v for k,v in ATTR.findall(m[1])};segment=attrs.get(b'id')
            if not segment or (doc,segment) in seen or len(headers)>=expected_rows:raise ValueError('Missing/duplicate/extra segment header')
            key=(doc,segment);seen.add(key);index=len(headers)
            if expected_headers is not None and (index>=len(expected_headers) or key!=expected_headers[index]):raise ValueError('Source/reference header alignment failed before body decode')
            meter.take(kind+'_segment_headers');headers.append(key)
            if index in active:
                meter.take(kind+'_body_decodes');selected[index]=m[2].decode('utf-8')
    if doc is not None or len(headers)!=expected_rows or set(selected)!=set(active):raise ValueError('Incomplete selective SGML member')
    return selected,headers
