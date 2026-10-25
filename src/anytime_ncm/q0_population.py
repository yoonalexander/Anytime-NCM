"""Q0 aggregate-only reference coverage and source document metadata helpers."""
from __future__ import annotations
from collections import Counter
import hashlib
import html
import re
import numpy as np
from scipy.stats import binom
from anytime_ncm.wmt_data import StringRows
from anytime_ncm.wmt_policy import NUMBER
from anytime_ncm.q0_statistics import cp_upper, power_rows


def populations(parent,reservations,expected=3003):
    partitions=parent['partitions']; entries=[x for rows in partitions.values() for x in rows]
    if len(entries)!=expected or {x['index'] for x in entries}!=set(range(expected)):
        raise ValueError('Parent group/index inventory differs')
    if len({x['identity'] for x in entries})!=expected or any(x['indices']!=[x['index']] for x in entries):
        raise ValueError('Require unique singleton canonical groups')
    roles={'S1_exploration':partitions['exploration'][:128],'S1_development':partitions['development'][:64]}
    role_counts={'E2_audit':256,'E3_development':128,'E4_confirmation':1024,'closed_unallocated':571}
    if set(reservations['roles'])!=set(role_counts):raise ValueError('Reserved role family differs')
    canonical={x['identity']:x['index'] for x in partitions['reserved']}; all_reserved=[]
    for name,count in role_counts.items():
        rows=reservations['roles'][name]
        if len(rows)!=count:raise ValueError('Frozen role count differs')
        for x in rows:
            if canonical.get(x['identity'])!=x['index'] or x['indices']!=[x['index']]:raise ValueError('Reservation/parent mismatch')
        all_reserved.extend(x['index'] for x in rows);roles[name]=rows
    if len(all_reserved)!=len(set(all_reserved)) or set(all_reserved)!=set(canonical.values()):
        raise ValueError('Reserved roles overlap or fail to cover original reservation')
    selected={n:[x['index'] for x in rows] for n,rows in roles.items()}
    if len(set().union(*(set(v) for v in selected.values())))!=2171:
        raise ValueError('Audit allowlist differs from2171')
    consumed=set(selected['S1_exploration']+selected['S1_development']+selected['E2_audit'])
    final=[x['index'] for x in partitions['phase4_final']]
    if len(final)!=256 or len(consumed)!=448 or consumed.intersection(final):raise ValueError('Consumed inventory differs')
    return selected,sorted(consumed),final


def normalize_source(text):
    return re.sub(r'\s+',' ',html.unescape(text).strip())


def parse_source_sgml(data,expected=3003):
    """Only caller's selected source member; no XML entities, DTDs or network expansion."""
    text=data.decode('utf-8');result=[];doc=None;seen_segments=set()
    for line in text.splitlines():
        stripped=line.strip()
        if re.match(r'<doc\b',stripped,re.I):
            match=re.search(r'\bdocid\s*=\s*["\x27]([^"\x27]+)["\x27]',stripped,re.I)
            if match is None:raise ValueError('Source doc label missing')
            doc=hashlib.sha256(html.unescape(match[1]).encode('utf-8')).hexdigest()
        elif re.match(r'</doc\s*>',stripped,re.I):doc=None
        elif re.match(r'<seg\b',stripped,re.I):
            if len(result)>=expected:raise ValueError('Source segment cap exceeded')
            match=re.fullmatch(r'<seg\b([^>]*)>(.*)</seg>\s*',stripped,re.I)
            if match is None or doc is None:raise ValueError('Source segment structure/document missing')
            seg=re.search(r'\bid\s*=\s*["\x27]([^"\x27]+)["\x27]',match[1],re.I)
            if seg is None or (doc,seg[1]) in seen_segments:raise ValueError('Segment ID missing/duplicate')
            seen_segments.add((doc,seg[1]));result.append((doc,seg[1],match[2]))
    if len(result)!=expected:raise ValueError('Source segment count differs')
    return result


def align_sources(pinned,official,role_indices=None):
    if set(pinned)!=set(range(len(official))):raise ValueError('Incomplete alignment indices')
    mapping=[];raw=0;normalized=[]
    for i,(doc,seg,text) in enumerate(official):
        raw+=pinned[i]==text
        a=normalize_source(pinned[i]);b=normalize_source(text)
        if a!=b:raise ValueError('Ordered normalized source alignment failed at row '+str(i))
        normalized.append(hashlib.sha256(a.encode('utf-8')).hexdigest())
        mapping.append({'index':i,'document_sha256':doc,'segment_id':seg})
    duplicate_groups=sum(v>1 for v in Counter(normalized).values())
    alias_roles={}
    for name,indices in (role_indices or {}).items():
        for i in indices:alias_roles.setdefault(normalized[i],set()).add(name)
    cross_role_aliases=sum(len(v)>1 for v in alias_roles.values())
    return mapping,{'rows':len(mapping),'raw_equal_rows':raw,'normalized_equal_rows':len(mapping),
                    'normalized_source_alias_groups':duplicate_groups,'normalized_cross_role_alias_groups':cross_role_aliases,'normalization':'HTML unescape; strip/collapse whitespace; exact ordered equality'}


def planning(covered):
    if covered==0:return {'covered':0,'zero_adverse_upper':None,'NI_floor_met':False,'zero_event_half_margin_floor_met':False,'hypothetical_power':[]}
    k=np.arange(covered+1);u=cp_upper(k,covered,.025);passing=u<=.02
    result={'covered':covered,'zero_adverse_upper':float(u[0]),'NI_floor_met':covered>=183,
            'zero_event_half_margin_floor_met':covered>=368,'independence_assumed_not_established':True,'hypothetical_power':[]}
    for p in [.005,.01]:
        weights=binom.pmf(k,covered,p);power=float(weights[passing].sum())
        _,cross=power_rows([covered],alpha=.025,alternative=p)
        if abs(power-float(cross[0]))>1e-10:raise AssertionError('Exact power arithmetic mismatch')
        result['hypothetical_power'].append({'adverse_probability':p,'NI_power':power,
          'NI_power80_met':power>=.8,'NI_and_half_margin_precision_probability':float(weights[passing&(u-k/covered<=.01)].sum())})
    return result


def aggregate_references(raw,roles,consumed,original_final,document_map=None,expected=3003):
    """Return aggregates only; decoded references/positive-index flags never leave."""
    selected=set().union(*(set(v) for v in roles.values()))
    if selected.intersection(original_final):raise ValueError('Consumed-final references forbidden')
    references=StringRows(raw).select(selected,expected=expected)
    covered={i for i,value in references.items() if NUMBER.search(value) is not None}
    del references
    all_roles=dict(roles,consumed_union=list(consumed))
    result={'reference_materializations':len(selected),'output_reference_texts':0,'per_input_coverage_fields_written':0,'roles':{}}
    docs=None if document_map is None else {x['index']:x['document_sha256'] for x in document_map}
    known_consumed=set(consumed)|set(original_final)
    consumed_docs=set() if docs is None else {docs[i] for i in known_consumed}
    for name,indices in all_roles.items():
        row={'groups':len(indices),'numeric_covered_groups':len(set(indices)&covered),
             'coverage_fraction':len(set(indices)&covered)/len(indices),
             'numeric_planning_iid_only':planning(len(set(indices)&covered)),
             'negation_denominator_planning_iid_only':planning(len(indices))}
        if docs is None:row['document_metadata']='unavailable'
        else:
            sizes=Counter(docs[i] for i in indices);cues=Counter(docs[i] for i in indices if i in covered)
            shared=[i for i in indices if docs[i] in consumed_docs]
            disjoint=[i for i in indices if docs[i] not in consumed_docs]
            row['documents']={'count':len(sizes),'with_numeric_covered_groups':len(cues),
                'cluster_size_min':min(sizes.values()),'cluster_size_max':max(sizes.values()),
                'cluster_size_median':float(np.median(list(sizes.values()))),
                'shared_with_known_consumed_documents':len(set(sizes)&consumed_docs),
                'groups_in_known_consumed_documents':len(shared),
                'numeric_groups_in_known_consumed_documents':len(set(shared)&covered),
                'groups_in_documents_disjoint_from_known_consumed':len(disjoint),
                'numeric_groups_in_documents_disjoint_from_known_consumed':len(set(disjoint)&covered),
                'disjoint_counts_are_diagnostic_not_reallocated':True}
        result['roles'][name]=row
    if docs is not None:
        docroles={name:{docs[i] for i in ids} for name,ids in roles.items()}
        docroles['original_consumed_final']={docs[i] for i in original_final}
        result['document_overlap_counts']={a:{b:len(da&db) for b,db in docroles.items()} for a,da in docroles.items()}
        result['known_consumed_groups_for_document_exposure']=len(known_consumed)
        result['known_consumed_documents']=len(consumed_docs)
        result['full_corpus_documents']=len(set(docs.values()))
    del covered
    return result
