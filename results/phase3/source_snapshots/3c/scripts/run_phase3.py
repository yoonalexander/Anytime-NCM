"""Run bounded learned-policy stages or verify saved evidence without model imports."""
import argparse,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("stage",choices=("3a","3b","3c","report","verify","verify-a","verify-b"))
    a=p.parse_args()
    if a.stage=="3a":
        from anytime_ncm.train_policy import fit
        fit(ROOT)
    elif a.stage in ("3b","3c"):
        from anytime_ncm.phase3_run import development,final
        {"3b":development,"3c":final}[a.stage](ROOT)
    else:
        from anytime_ncm.phase3 import report,verify,analyze
        from anytime_ncm.train_policy import verify_training
        r={"report":lambda:report(ROOT),"verify":lambda:verify(ROOT),
           "verify-a":lambda:verify_training(ROOT),"verify-b":lambda:analyze(ROOT,"3b")}[a.stage]()
        print("Phase 3:",r.get("decision",r.get("status","verified")))
        if a.stage!="report":
            assert "torch" not in sys.modules and "matplotlib" not in sys.modules
            print("PASS: saved-data verification imports neither torch nor matplotlib.")
if __name__=="__main__":main()
