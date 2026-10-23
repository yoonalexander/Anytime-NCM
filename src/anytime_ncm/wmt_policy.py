"""Reference-free stability policies and explicitly heuristic semantic cues."""
import re
NUMBER=re.compile(r"(?<!\w)\d+(?:[.,]\d+)*(?:%)?")
NEGATION=re.compile(r"\b(?:no|not|never|neither|without)\b|n['\u2019]t\b",re.I)
def cues(text):
    nums=tuple(sorted(set(NUMBER.findall(text))))
    return nums,bool(NEGATION.search(text))
def diagnostics(hyp,ref):
    h,n=cues(hyp);r,rn=cues(ref)
    f1=2*len(set(h)&set(r))/(len(h)+len(r)) if r else None
    return {"numeric_reference_f1":f1,"reference_has_digit_numbers":bool(r),
            "negation_cue_mismatch":n!=rn,"number_cues":list(h),"negation_cue":n}
class Stability:
    def __init__(self,spec):self.spec=spec;self.previous=None;self.text=None;self.count=0;self.level=0
    def observe(self,level,ids,text):
        if type(level)is not int or not self.level<level<=11:raise ValueError("Increasing current levels only.")
        if len(ids)!=64:raise ValueError("Full-resolution current tokens required.")
        change=sum(a!=b for a,b in zip(ids,self.previous))/64 if self.previous is not None else None
        guarded=self.spec["kind"]=="guarded"
        small=change is not None and change<=self.spec["epsilon"] and (not guarded or cues(text)==cues(self.text))
        self.count=self.count+1 if small else 0
        self.previous=tuple(ids);self.text=text;self.level=level
        return bool(level<11 and self.count>=self.spec["patience"]),change
def simulate(spec,states):
    if len(states)!=11:raise ValueError("Need full offline trajectory.")
    if spec["kind"]=="full":return 11
    if spec["kind"]=="fixed":return spec["depth"]
    tracker=Stability(spec)
    for s in states:
        if s["level"]<spec["minimum"]:continue
        stop,_=tracker.observe(s["level"],s["ids"],s["text"])
        if stop:return s["level"]
    return 11
