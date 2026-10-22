"""Run finite Phase 2 subphases or verify saved evidence without model imports."""
import argparse
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage",choices=("2a","2b","2c","report","verify","verify-a","verify-b"))
    args=parser.parse_args()
    if args.stage in ("2a","2b","2c"):
        from anytime_ncm.phase2_run import emit_a,development,final
        {"2a":emit_a,"2b":development,"2c":final}[args.stage](ROOT)
    else:
        from anytime_ncm.phase2 import report,verify_report,verify_a,verify_development
        result={"report":report,"verify":verify_report,"verify-a":verify_a,"verify-b":verify_development}[args.stage](ROOT)
        print("Phase 2:",result.get("decision",result.get("status",result.get("selected_verifier","verified"))))
        if args.stage!="report":
            assert "torch" not in sys.modules and "matplotlib" not in sys.modules
            print("PASS: saved-data verification imports neither torch nor matplotlib.")
if __name__=="__main__":main()
