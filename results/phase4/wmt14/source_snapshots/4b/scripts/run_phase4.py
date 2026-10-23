"""Execute bounded WMT14 Phase 4 or verify saved evidence without model imports."""
import argparse,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("stage",choices=("4a","4b","4c","report","verify","verify-a","verify-b"));a=p.parse_args()
    if a.stage in ("4a","4b","4c"):
        from anytime_ncm.phase4_run import audit,development,final
        {"4a":audit,"4b":development,"4c":final}[a.stage](ROOT)
    else:
        from anytime_ncm.phase4 import report,verify,analyze
        r={"report":lambda:report(ROOT),"verify":lambda:verify(ROOT),"verify-a":lambda:verify(ROOT,False),
           "verify-b":lambda:analyze(ROOT,"4b")}[a.stage]()
        print("Phase 4 WMT14:",r.get("decision",r.get("status","verified")))
        if a.stage!="report":
            assert "torch" not in sys.modules and "matplotlib" not in sys.modules
            print("PASS: saved-data verification imports neither torch nor matplotlib.")
if __name__=="__main__":main()
