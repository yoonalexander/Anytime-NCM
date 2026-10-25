"""Deterministic Q0 result/coverage audit; no new trials or bootstrap draws."""
from __future__ import annotations
import os
for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[name]='1'
import hashlib
import json
from pathlib import Path
import resource
import signal
import sys
import time
from xml.etree import ElementTree as ET

root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'src'))
from anytime_ncm.q0_statistics import TAIL, cp_upper, eb_upper
from scipy.stats import binom
import numpy as np


def main():
    start=time.monotonic()
    resource.setrlimit(resource.RLIMIT_AS,(2<<30,2<<30))
    resource.setrlimit(resource.RLIMIT_CPU,(1200,1200))
    signal.alarm(60)
    out=root/'results/quality_tolerant/q0'
    target=out/'independent-checks.json'
    if target.exists():raise RuntimeError('Refuse overwrite independent audit')
    execution=json.loads((out/'execution.json').read_text())
    lock=json.loads((root/'docs/studies/quality-tolerant/q0-lock.json').read_text())
    analytic=json.loads((out/'statistical-feasibility.json').read_text())
    checks=[]
    def require(name,condition):
        if not condition:raise AssertionError(name)
        checks.append(name)
    rows=[]
    for n in [*lock['grid_n'],385]:
        k=np.arange(n+1); upper=cp_upper(k,n)
        # Direct binomial-tail inversion, independent of beta inverse-survival calculation.
        require(f'CP inversion n={n}',np.max(np.abs(binom.cdf(k[:-1],n,upper[:-1])-TAIL))<1e-10)
        for p in [0.,.005,.01,.02,.03]:
            weights=binom.pmf(k,n,p)
            cpcoverage=float(weights[upper>=p].sum())
            eb=eb_upper(k,k,n)
            ebcoverage=float(weights[eb>=p].sum())
            power=float(weights[upper<=.02].sum())
            require(f'Bernoulli CP coverage n={n},p={p}',cpcoverage>=1-TAIL-1e-12)
            require(f'Bernoulli EB coverage n={n},p={p}',ebcoverage>=1-TAIL-1e-12)
            if p>=.02:require(f'Boundary/outside false acceptance n={n},p={p}',power<=TAIL+1e-12)
            rows.append({'n':n,'adverse_probability':p,'primary_upper_coverage':cpcoverage,
                         'eb_diagnostic_upper_coverage':ebcoverage,'primary_pass_probability':power})
    # Audit saved results only; no random number generator or bootstrap is called.
    corpus=json.loads((out/'synthetic-corpus.json').read_text())
    require('four fixed text datasets',len(corpus)==4)
    require('eight direct-corpus parity comparisons',all(abs(v['point_loss']-v['direct_loss'])<1e-10 for d in corpus for v in d['metrics']))
    require('identical synthetic text gives zero losses',all(v['point_loss']==0 for v in corpus[0]['metrics']))
    require('modified synthetic text gives positive losses',all(v['point_loss']>0 for d in corpus[1:] for v in d['metrics']))
    require('small corpus bootstrap tails correctly unresolved',all(v['interval']['lower'] is None and v['interval']['guard']['rank']==0 for d in corpus for v in d['metrics']))
    timing=json.loads((out/'synthetic-timing.json').read_text())
    require('four frozen timing effects',len(timing)==4)
    require('paired timing point parity',all(abs(v['point_savings']-v['effect'])<1e-12 for v in timing))
    require('paired timing interval shift parity',all(abs((v['interval']['lower']-timing[0]['interval']['lower'])-v['effect'])<1e-12 for v in timing))
    require('null timing interval contains zero',timing[0]['interval']['lower']<0<timing[0]['interval']['upper'])
    require('all timing ranks resolved at 18',all(v['interval']['guard']['rank']==18 for v in timing))
    trial=json.loads((out/'synthetic-trials.json').read_text())
    require('48 frozen trial cases',len(trial)==48)
    require('every trial case has 2000 trials',all(v['primary_pass']['trials']==2000 for v in trial))
    require('zero chance to pass below cue floor',all(v['primary_pass']['events']==0 for v in trial if v['n']<385))
    require('positive and fractional zero-variance cases not rescued by EB',all(v['eb_diagnostic_pass']['events']==0 for v in trial if v['case'] in ['zero','rare','boundary','outside','fractional']))
    for n in [512,1024]:
        r=next(v for v in trial if v['n']==n and v['case']=='cluster8')
        require(f'naive cluster false-accept probability exceeds nominal n={n}',r['naive_exact_false_pass_at_boundary']>TAIL)
        require(f'cluster-unit inadequate coverage not certified n={n}',r['cluster_unit_pass']['events']==0)
    tests=ET.parse(out/'focused-tests.xml')
    suites=tests.findall('.//testsuite')
    require('26 tests and zero failures/errors',sum(int(x.get('tests','0')) for x in suites)==26 and all(int(x.get('failures','0'))==0 and int(x.get('errors','0'))==0 for x in suites))
    require('power minimum exceeds all-coverage E4',analytic['power']['0.005']['first_n_power80']==1038>1024)
    require('no eligible consumed union reaches floor',analytic['consumed_union_max_numeric_coverage']==240<analytic['zero_event_floors']['primary59'])
    for rel,sha in execution['source_sha256'].items():
        require('source SHA '+rel,hashlib.sha256((root/rel).read_bytes()).hexdigest()==sha)
    for rel,sha in execution['protected_sha256'].items():
        require('preserved SHA '+rel,hashlib.sha256((root/rel).read_bytes()).hexdigest()==sha)
    elapsed=time.monotonic()-start
    require('cumulative measured execution+check below 1800s',execution['wall_seconds']+elapsed<1800)
    receipt={'stage':'Q0 deterministic result audit','passed':True,'checks':checks,'check_count':len(checks),
        'exact_bernoulli_cases':rows,'extra_trials':0,'extra_bootstrap_draws':0,'real_body_reads':0,
        'verification_wall_seconds':elapsed,'max_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
        'checker_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'checker_path':str(Path(__file__).relative_to(root)),
        'scope':'Different binomial-CDF arithmetic plus saved-result checks by the same assistant; not independent human review.'}
    with target.open('x',encoding='utf-8') as f:json.dump(receipt,f,indent=2);f.write('\n')
    print(json.dumps({'passed':True,'checks':len(checks),'new_trials':0,'new_draws':0,'wall_seconds':elapsed}))
    signal.alarm(0)


if __name__=='__main__':main()
