"""Execute the prospectively frozen saved-WMT audit; never loads models."""
import argparse,os,sys
from pathlib import Path
for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[name]='4'
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('split',choices=('exploration','development'));args=p.parse_args()
    from anytime_ncm.stronger_s1 import run
    run(ROOT,args.split)
