"""Non-executing selective UTF-8 pickle-list access and effective-prefix partitions."""
import hashlib,json,random,struct

class StringRows:
    def __init__(self,data):self.data=data
    def select(self,indices,expected=3003):
        d=self.data;p=2;memo=[];rows=[];last=None;stopped=False
        if d[:2]!=b"\x80\x04":raise ValueError("Require pinned protocol-4 string list.")
        while p<len(d):
            op=d[p];p+=1
            if op==0x95:p+=8
            elif op==ord("]"):
                if memo or rows:raise ValueError("Nested lists unsupported.")
                last=None
            elif op==0x94:memo.append(last)
            elif op in (ord("("),ord("e"),ord("a")):pass
            elif op in (0x8c,ord("X"),0x8d):
                width={0x8c:1,ord("X"):4,0x8d:8}[op]
                n=int.from_bytes(d[p:p+width],"little");p+=width
                if p+n>len(d):raise ValueError("Truncated string.")
                last=(p,p+n);rows.append(last);p+=n
            elif op in (ord("h"),ord("j")):
                width=1 if op==ord("h") else 4;ix=int.from_bytes(d[p:p+width],"little");p+=width
                if ix>=len(memo) or memo[ix] is None:raise ValueError("Invalid string memo.")
                last=memo[ix];rows.append(last)
            elif op==ord("."):
                if p!=len(d):raise ValueError("Trailing pickle bytes.")
                stopped=True;break
            else:raise ValueError("Unsupported string pickle opcode: "+str(op))
        if not stopped or len(rows)!=expected or not indices<=set(range(expected)):raise ValueError("String-row count/selection differs.")
        return {i:d[a:b].decode("utf-8") for i,(a,b) in enumerate(rows) if i in indices}

def identity(prefix):
    return hashlib.sha256(json.dumps(list(prefix),separators=(",",":")).encode()).hexdigest()

def make_manifest(sources,tokenizer,pad=151643):
    groups={}
    for i,text in enumerate(sources):
        ids=(tokenizer(text)["input_ids"][:96]+[pad]*96)[:96]
        groups.setdefault(identity(ids),[]).append(i)
    forced={h for h,ix in groups.items() if min(ix)<32}
    keys=sorted(set(groups)-forced);random.Random(20261023).shuffle(keys)
    partition={"exploration":sorted(forced),"development":[],"phase4_final":[],"reserved":[]}
    pos=0
    for name,n in (("exploration",512-len(forced)),("development",256),("phase4_final",256)):
        partition[name].extend(keys[pos:pos+n]);pos+=n
    partition["reserved"]=keys[pos:]
    return {"task":"wmt14","seed":20261023,"source_rows":len(sources),"unique_effective_prefix_groups":len(groups),
      "identity":"SHA256 compact JSON of official first96-token padded prefix; aliases grouped",
      "partitions":{name:sorted([{"index":min(groups[h]),"indices":groups[h],"identity":h} for h in hs],key=lambda r:r["index"])
                    for name,hs in partition.items()}}

def select_entries(manifest,stage,released=False):
    allowed={"audit_exploration":("exploration",128),"audit_development":("development",64),
             "development":("development",64),"warmup":("exploration",8),"final":("phase4_final",256)}
    if stage not in allowed or stage=="final" and not released:raise ValueError("Restricted WMT stage.")
    name,count=allowed[stage];rows=manifest["partitions"][name]
    if len(rows)<count:raise ValueError("Insufficient preassigned groups.")
    return [dict(r,partition=name) for r in rows[:count]]
