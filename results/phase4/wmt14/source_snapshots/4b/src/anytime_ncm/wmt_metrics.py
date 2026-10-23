"""Exact corpus BLEU/chrF, guarded development selection and paired quality intervals."""
import math
import numpy as np
from sacrebleu.metrics import BLEU,CHRF
from anytime_ncm.wmt_policy import diagnostics,simulate

def scores(hyps,refs):
    b=BLEU();c=CHRF();bl=BLEU(lowercase=True)
    result={"bleu":b.corpus_score(hyps,[refs]).score,"chrf":c.corpus_score(hyps,[refs]).score,
            "bleu_lowercase":bl.corpus_score(hyps,[refs]).score}
    ds=[diagnostics(h,r) for h,r in zip(hyps,refs,strict=True)]
    nums=[d["numeric_reference_f1"] for d in ds if d["reference_has_digit_numbers"]]
    result.update(numeric_reference_f1=float(np.mean(nums)) if nums else None,numeric_reference_coverage=len(nums),
        negation_cue_mismatch_rate=float(np.mean([d["negation_cue_mismatch"] for d in ds])),
        bleu_signature=str(b.get_signature()),chrf_signature=str(c.get_signature()))
    return result

def feasible(candidate,full):
    numeric=candidate["numeric_reference_f1"] is None or candidate["numeric_reference_f1"]>=full["numeric_reference_f1"]-.02
    return candidate["bleu"]>=full["bleu"]-.5 and candidate["chrf"]>=full["chrf"]-1.0 and numeric and candidate["negation_cue_mismatch_rate"]<=full["negation_cue_mismatch_rate"]+.02

def select_policies(rows,refs):
    full=scores([r["levels"][-1]["text"] for r in rows],refs);fixed=[]
    for depth in range(1,12):
        s=scores([r["levels"][depth-1]["text"] for r in rows],refs)
        fixed.append({"depth":depth,"metrics":s,"feasible":feasible(s,full)})
    chosen_fixed=min(x["depth"] for x in fixed if x["feasible"])
    selected={};candidates={}
    for kind in ("stability","guarded"):
        options=[]
        for minimum in (5,8,10):
            for patience in (1,2):
                for epsilon in (0.,.02,.05):
                    spec=dict(kind=kind,minimum=minimum,patience=patience,epsilon=epsilon)
                    exits=[simulate(spec,r["levels"]) for r in rows]
                    s=scores([r["levels"][d-1]["text"] for r,d in zip(rows,exits)],refs)
                    options.append({"spec":spec,"metrics":s,"feasible":feasible(s,full),
                        "mean_inspections":float(np.mean([d-minimum+1 for d in exits])),
                        "mean_levels":float(np.mean(exits)),"early_inputs":sum(d<11 for d in exits)})
        good=[o for o in options if o["feasible"]]
        best=min(good,key=lambda o:(o["mean_inspections"],o["mean_levels"],-o["spec"]["minimum"],o["spec"]["patience"],o["spec"]["epsilon"])) if good else next(o for o in options if o["spec"]==dict(kind=kind,minimum=10,patience=2,epsilon=0.))
        selected[kind]=best["spec"];candidates[kind]=options
    return {"full":full,"fixed_candidates":fixed,"adaptive_candidates":candidates,
       "methods":{"full":{"kind":"full"},"fixed":{"kind":"fixed","depth":chosen_fixed},
                  "stability":selected["stability"],"adaptive":selected["guarded"]}}

def paired_quality(hyps,base,refs):
    result={}
    rng=np.random.default_rng(20261023);indices=rng.integers(0,len(refs),size=(10000,len(refs)))
    for name,metric in (("bleu",BLEU()),("chrf",CHRF())):
        a=np.asarray(metric._extract_corpus_statistics(hyps,[refs]),dtype=np.int64)
        b=np.asarray(metric._extract_corpus_statistics(base,[refs]),dtype=np.int64)
        point=metric._compute_score_from_stats(a.sum(axis=0).tolist()).score-metric._compute_score_from_stats(b.sum(axis=0).tolist()).score
        direct=metric.corpus_score(hyps,[refs]).score-metric.corpus_score(base,[refs]).score
        if abs(point-direct)>1e-10:raise ValueError("Sufficient-statistics corpus parity differs.")
        aa=a[indices].sum(axis=1);bb=b[indices].sum(axis=1)
        diffs=[metric._compute_score_from_stats(x.tolist()).score-metric._compute_score_from_stats(y.tolist()).score for x,y in zip(aa,bb)]
        result[name]={"difference":point,"ci95":np.percentile(diffs,[2.5,97.5]).tolist()}
    return result

def claim_gate(timing,quality,heuristic_feasible):
    interval=timing["relative_mean_reduction_ci95"]
    qpass=all(quality[n]["ci95"][0]>=-loss for n,loss in (("bleu",.5),("chrf",1.)))
    qfail=any(quality[n]["ci95"][1]<-loss for n,loss in (("bleu",.5),("chrf",1.)))
    if not heuristic_feasible or qfail or interval[1]<.05:return "no-go"
    if qpass and timing["relative_mean_reduction"]>=.05 and interval[0]>0:return "go"
    return "inconclusive"
