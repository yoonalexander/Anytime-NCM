"""Bounded selective extraction of the already allocated development-evaluation role."""
import gzip,hashlib,io,tarfile
from pathlib import Path
from anytime_ncm.development_data import selected_segments

def key(e):return str(e['year'])+':'+str(e['index'])
def digest(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for block in iter(lambda:f.read(1<<20),b''):h.update(block)
    return h.hexdigest()

def extract_corpus(root,entries,archives,meter,decompressed_cap):
    root=Path(root);wanted={key(e) for e in entries}
    if len(wanted)!=len(entries) or any(e['role']!='development_evaluation' for e in entries):raise ValueError('Only allocated development evaluation may be extracted')
    sources={};references={};receipts=[]
    for item in archives:
        path=root/item['path']
        if not path.is_file() or path.stat().st_size!=item['bytes'] or digest(path)!=item['sha256']:raise ValueError('Pinned cached archive changed; no network fallback')
        remaining=decompressed_cap-meter.counts['decompressed_bytes']
        with gzip.open(path,'rb') as f:payload=f.read(remaining)
        if len(payload)>=remaining:raise RuntimeError('Decompression cap boundary')
        meter.take('decompressed_bytes',len(payload));members={}
        with tarfile.open(fileobj=io.BytesIO(payload),mode='r:') as tar:
            for kind in ('source','reference'):
                matches=[m for m in tar.getmembers() if m.name==item[kind+'_member']]
                if len(matches)!=1 or not matches[0].isfile() or matches[0].size>16<<20:raise ValueError('Invalid pinned member')
                with tar.extractfile(matches[0]) as f:members[kind]=f.read()
                if hashlib.sha256(members[kind]).hexdigest()!=item[kind+'_sha256']:raise ValueError('Pinned member bytes changed')
        active={e['index'] for e in entries if e['year']==item['year']};s,h=selected_segments(members['source'],'source',item['source_member'],active,item['rows'],meter);refs,_=selected_segments(members['reference'],'reference',item['reference_member'],active,item['rows'],meter,h)
        for i in active:sources[str(item['year'])+':'+str(i)]=s[i];references[str(item['year'])+':'+str(i)]=refs[i]
        receipts.append(dict(year=item['year'],headers_each=item['rows'],selected_payloads_each=len(active),unselected_payloads_skipped_before_utf8=True))
    if set(sources)!=wanted or set(references)!=wanted:raise ValueError('Incomplete allocated evaluation extraction')
    return sources,references,receipts
