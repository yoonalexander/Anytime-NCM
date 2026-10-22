"""Exploration-only standardized logistic fitting and frozen development selection."""
import json
from anytime_ncm.learned_features import FeatureTracker,feature_names,probability,offline_trace
from anytime_ncm.phase3 import OUTPUT,begin,finish,failed,examples,calibration,verify_stage,save,load_rows,require
from anytime_ncm.sudoku import validate_solution

def training_data(root):
    rows=load_rows(root/"results/followup/sudoku_easy_r3/trajectories.jsonl")
    selected={e.identity:e for stage in ("train","development") for e in examples(root,stage)}
    require(len(rows)==1400 and {r["sample_id"] for r in rows}==set(selected),"Training scope differs.")
    for row in rows:
        e=selected[row["sample_id"]]
        require(row["partition"]==e.partition and row["dataset_index"]==e.index,"Training identity differs.")
        for s in row["levels"]:
            require(s["correctness"]["is_valid_solution"]==validate_solution(e.puzzle,s["decoded_ids"]).is_valid_solution,
                    "Training target validity differs.")
    return rows,selected

def matrix(rows,selected,family,partition):
    x=[];y=[]
    for row in rows:
        if row["partition"]!=partition:continue
        tracker=FeatureTracker(selected[row["sample_id"]].puzzle,family)
        for i,state in enumerate(row["levels"],1):
            x.append(tracker.observe(i,state["decoded_ids"],state["code_ids"]))
            y.append(int(state["correctness"]["is_valid_solution"]))
    return x,y

def select_policy(model,rows,selected):
    candidates=[]
    for minimum in (1,6,10):
        for threshold in (.5,.9,.99,.999,1.0):
            early=invalid=loss=inspections=0
            for row in rows:
                if row["partition"]!="development":continue
                depth,trace=offline_trace(model,row["levels"],selected[row["sample_id"]].puzzle,minimum,threshold)
                valid=row["levels"][depth-1]["correctness"]["is_valid_solution"]
                final=row["levels"][-1]["correctness"]["is_valid_solution"]
                early+=depth<12;invalid+=depth<12 and not valid;loss+=final and not valid;inspections+=len(trace)
            candidates.append({"minimum":minimum,"threshold":threshold,"early_inputs":early,
                "invalid_early":invalid,"solve_loss":loss,"mean_inspections":inspections/400,
                "feasible":invalid==0 and loss==0})
    eligible=[c for c in candidates if c["feasible"]]
    require(eligible,"Mandatory threshold-1 fallback should be feasible.")
    best=min(eligible,key=lambda c:(c["mean_inspections"],c["minimum"],c["threshold"]))
    return {**best,"model":model},candidates

def fit(root):
    out,path,receipt=begin(root,"3a")
    try:
        import numpy as np,sklearn,scipy,warnings
        from sklearn.linear_model import LogisticRegression
        from sklearn.exceptions import ConvergenceWarning
        from threadpoolctl import threadpool_limits
        rows,selected=training_data(root);all_models={};chosen={};candidates={}
        for family in ("base","internal"):
            x,y=matrix(rows,selected,family,"exploration");dx,dy=matrix(rows,selected,family,"development")
            x=np.asarray(x,dtype=np.float64);dx=np.asarray(dx,dtype=np.float64)
            mean=x.mean(axis=0);scale=x.std(axis=0);scale[scale==0]=1
            trained=[]
            for c in (.1,1.,10.):
                with warnings.catch_warnings(),threadpool_limits(limits=4):
                    warnings.simplefilter("error",ConvergenceWarning)
                    lr=LogisticRegression(C=c,solver="lbfgs",max_iter=2000,tol=1e-8,random_state=20261022)
                    lr.fit((x-mean)/scale,y)
                model={"family":family,"C":c,"feature_names":list(feature_names(family)),
                       "weights":lr.coef_[0].tolist(),"intercept":float(lr.intercept_[0]),
                       "mean":mean.tolist(),"scale":scale.tolist(),"iterations":int(lr.n_iter_[0])}
                ps=[probability(model,f) for f in dx]
                expected=lr.predict_proba((dx-mean)/scale)[:,1]
                require(np.allclose(ps,expected,rtol=0,atol=1e-12),"Portable probability parity differs.")
                trained.append({"model":model,"development":calibration(ps,dy),
                                "training":calibration([probability(model,f) for f in x],y)})
            winner=min(trained,key=lambda t:(t["development"]["log_loss"],t["model"]["C"]))
            chosen[family],candidates[family]=select_policy(winner["model"],rows,selected)
            all_models[family]=trained
        result={"study":"Phase 3A","status":"complete","target":"current valid solution; no future/reference inference features",
             "training_identities":1000,"training_states":12000,"development_identities":400,"development_states":4800,
             "training_positive_states":sum(r["levels"][-1]["correctness"]["is_valid_solution"] for r in rows if r["partition"]=="exploration"),
             "development_positive_states":sum(r["levels"][-1]["correctness"]["is_valid_solution"] for r in rows if r["partition"]=="development"),
             "positive_pre_final_states":sum(s["correctness"]["is_valid_solution"] for r in rows for s in r["levels"][:-1]),
             "fits":6,"selected":chosen,"models":all_models,"policy_candidates":candidates,
             "versions":{"numpy":np.__version__,"sklearn":sklearn.__version__,"scipy":scipy.__version__},
             "phase2_final_rows_used":0,"phase3_final_rows_used":0}
        save(out/"training.json",result)
        receipt.update(fits=6,phase2_final_rows_materialized=0,phase3_final_rows_materialized=0)
        finish(out,path,receipt,["training.json"])
        print("Phase 3A: six fits; no NCM inference; selected",[(f,s["model"]["C"],s["minimum"],s["threshold"]) for f,s in chosen.items()],flush=True)
        return result
    except Exception as error:failed(path,receipt,error);raise

def verify_training(root):
    out=root/OUTPUT;verify_stage(root,"3a")
    result=json.loads((out/"training.json").read_text(encoding="utf-8"))
    rows,selected=training_data(root)
    require(result["fits"]==6 and result["positive_pre_final_states"]==0,"Training scope/labels differ.")
    for family in ("base","internal"):
        x,y=matrix(rows,selected,family,"exploration");dx,dy=matrix(rows,selected,family,"development")
        import numpy as np
        mean=np.mean(x,axis=0);scale=np.std(x,axis=0);scale[scale==0]=1
        models=result["models"][family];require(len(models)==3,"Fit count differs.")
        for t in models:
            m=t["model"];require(m["mean"]==mean.tolist() and m["scale"]==scale.tolist(),"Exploration-only normalization differs.")
            require(t["development"]==calibration([probability(m,f) for f in np.asarray(dx,dtype=np.float64)],dy)
                    and t["training"]==calibration([probability(m,f) for f in np.asarray(x,dtype=np.float64)],y),"Saved model diagnostics differ.")
            require(m["iterations"]<2000 and m["feature_names"]==list(feature_names(family)),"Fit convergence/features differ.")
        winner=min(models,key=lambda t:(t["development"]["log_loss"],t["model"]["C"]))
        best,candidates=select_policy(winner["model"],rows,selected)
        require(result["selected"][family]==best and result["policy_candidates"][family]==candidates,"Frozen selection differs.")
    return result
