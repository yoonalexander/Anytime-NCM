"""Pure causal feature extraction and portable logistic scoring; no labels/references."""
from collections import Counter
import math

LENGTHS=(1,2,4,6,9,13,18,26,37,50,67,89)
BASE_NAMES=("level_fraction","code_fraction","clue_density",*(f"decoded_hist_{i}" for i in range(12)),
            "decoded_change","has_previous")
INTERNAL_NAMES=(*(f"code_hist_{i}" for i in range(16)),"code_entropy","code_max_frequency",
                "code_distinct_fraction","code_adjacent_change")

def feature_names(family):
    if family not in ("base","internal"): raise ValueError("Unknown feature family.")
    return BASE_NAMES+(INTERNAL_NAMES if family=="internal" else ())

class FeatureTracker:
    def __init__(self,puzzle,family):
        self.family=family;feature_names(family)
        if len(puzzle)!=91 or any(type(t)is not int or not 0<=t<=11 for t in puzzle):
            raise ValueError("Expected a 91-token puzzle.")
        self.clues=sum(1<=t<=9 for t in puzzle)/81
        self.previous=None;self.level=0
    def observe(self,level,ids,current_codes):
        if type(level)is not int or not self.level<level<=12: raise ValueError("Levels must increase.")
        if len(ids)!=89 or any(type(t)is not int or not 0<=t<=11 for t in ids):
            raise ValueError("Expected current decoded IDs only.")
        if len(current_codes)!=LENGTHS[level-1] or any(type(c)is not int or not 0<=c<16 for c in current_codes):
            raise ValueError("Only current codebook codes are allowed.")
        histogram=Counter(ids);n=len(ids)
        change=sum(a!=b for a,b in zip(ids,self.previous))/n if self.previous is not None else 1.0
        result=[level/12,sum(LENGTHS[:level])/322,self.clues,
                *(histogram[i]/n for i in range(12)),change,float(self.previous is not None)]
        if self.family=="internal":
            h=Counter(current_codes);m=len(current_codes)
            probs=[h[i]/m for i in range(16)]
            result.extend([*probs,-sum(p*math.log(p) for p in probs if p)/math.log(16),
                           max(probs),len(h)/16,
                           sum(a!=b for a,b in zip(current_codes,current_codes[1:]))/max(1,m-1)])
        self.previous=tuple(ids);self.level=level
        return tuple(result)

def probability(model,features):
    if len(features)!=len(model["weights"]) or len(features)!=len(feature_names(model["family"])):
        raise ValueError("Feature/model shape mismatch.")
    z=model["intercept"]+sum(w*(v-m)/s for w,v,m,s in zip(
        model["weights"],features,model["mean"],model["scale"],strict=True))
    if not math.isfinite(z):raise ValueError("Non-finite score.")
    return 1/(1+math.exp(-z)) if z>=0 else math.exp(z)/(1+math.exp(z))

def offline_trace(model,states,puzzle,minimum,threshold):
    if len(states)!=12:raise ValueError("Need all saved levels for offline simulation.")
    tracker=FeatureTracker(puzzle,model["family"]);trace=[]
    for level,state in enumerate(states,1):
        if level<minimum:continue
        f=tracker.observe(level,state["decoded_ids"],state["code_ids"])
        p=probability(model,f);trace.append({"level":level,"features":list(f),"probability":p,
                                          "decoded_ids":state["decoded_ids"]})
        if level<12 and p>=threshold:return level,trace
    return 12,trace
