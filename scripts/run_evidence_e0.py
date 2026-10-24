"""Run one frozen input-only/synthetic E0. Never import model libraries."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time

for variable in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[variable] = '4'
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from anytime_ncm.evidence_preflight import (Budget, input_audit, mc_precision, minimum_coverage,
    cp_upper, representative_bootstraps, sha, trial_grid, write_new)
import numpy as np
import scipy
import sacrebleu

SOURCES = ['scripts/run_evidence_e0.py', 'src/anytime_ncm/evidence_preflight.py',
           'src/anytime_ncm/wmt_data.py', 'tests/test_evidence_preflight.py',
           'docs/studies/evidence-gaps/e0-protocol.md', 'docs/studies/evidence-gaps/e0-lock.json',
           'docs/studies/evidence-gaps/e0-recovery-amendment.md']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--remote-head', required=True, help='HEAD verified against GitHub main immediately before this run')
    args = parser.parse_args()
    start = time.monotonic()
    # Match native Windows Git's CRLF normalization without changing any files/config.
    git = lambda *x: subprocess.check_output(['git', '-c', 'safe.directory=' + str(ROOT),
        '-c', 'safe.directory=' + str(ROOT / 'third_party/ncm'), '-c', 'core.autocrlf=true', *x], cwd=ROOT, text=True).strip()
    head = git('rev-parse', 'HEAD')
    if head != args.remote_head or git('branch', '--show-current') != 'main' or git('status', '--porcelain'):
        raise ValueError('Need clean main and verified source/protocol push before E0')
    lock_path = ROOT / 'docs/studies/evidence-gaps/e0-lock.json'
    lock = json.loads(lock_path.read_text(encoding='utf-8'))
    if sha(ROOT / lock['protocol']) != lock['protocol_sha256']:
        raise ValueError('Frozen E0 protocol digest differs')
    if len(lock['scenarios']) * len(lock['sample_sizes']) != 24 or len(lock['representative_families']) * len(lock['sample_sizes']) != 12:
        raise ValueError('Frozen simulation dimensions differ')
    if sacrebleu.__version__ != '2.6.0':
        raise ValueError('Metric environment differs')
    limit = lock['limits']
    resource.setrlimit(resource.RLIMIT_AS, (limit['rss_bytes'], limit['rss_bytes']))
    out = ROOT / 'results/evidence_gaps/e0'
    out.mkdir(parents=True, exist_ok=False)
    counts = {'trials': 0, 'bootstrap_draws': 0, 'representative_datasets': 0}
    receipt = {'stage': 'E0', 'started_utc': datetime.now(timezone.utc).isoformat(),
               'head': head, 'verified_remote_head_argument': args.remote_head,
               'source_sha256': {p: sha(ROOT / p) for p in SOURCES},
               'python': sys.version, 'numpy': np.__version__, 'scipy': scipy.__version__,
               'sacrebleu': sacrebleu.__version__, 'model_libraries_imported': False,
               'forbidden_work': lock['forbidden_work'], 'counts': counts}
    receipt['upstream_commit'] = subprocess.check_output(['git', '-c', 'safe.directory=' + str(ROOT / 'third_party/ncm'), '-C', str(ROOT / 'third_party/ncm'), 'rev-parse', 'HEAD'], text=True).strip()
    if receipt['upstream_commit'] != 'c70274273f489abc73832b2b98584a8483b6b203':
        raise ValueError('Pinned upstream revision differs')
    write_new(out / 'started.json', receipt)
    ledger = (out / 'ledger.jsonl').open('x', encoding='utf-8', newline='\n')

    def check():
        if time.monotonic() - start > limit['execution_wall_seconds']:
            raise RuntimeError('E0 wall-time cap')
        if 'torch' in sys.modules or 'transformers' in sys.modules:
            raise RuntimeError('Forbidden model library imported')
        if sum(p.stat().st_size for p in out.rglob('*') if p.is_file()) > limit['artifact_bytes']:
            raise RuntimeError('E0 storage cap')

    budget = Budget(limit, ledger)
    counts = budget.counts
    receipt['counts'] = counts

    def consume(kind, amount, label):
        check()
        budget.consume(kind, amount, label)

    try:
        audit = input_audit(ROOT, lock)
        write_new(out / 'input-manifest.json', {'roles': audit.pop('roles'), 'E1_existing_exploration': audit.pop('E1_existing_exploration'), 'outcome_access_released': False})
        write_new(out / 'exposure-audit.json', audit)
        trials = trial_grid(lock, consume)
        write_new(out / 'synthetic-trials.json', {'interpretation': 'normal difference proxies and cue bounds, not real corpus power', 'scenarios': trials})
        examples = representative_bootstraps(lock, consume)
        write_new(out / 'synthetic-bootstrap.json', {'interpretation': '12 fixed synthetic corpora, not interval-coverage validation', 'datasets': examples})
        coverage = {stage: {'tail_alpha': lock[stage]['tail_alpha'],
                             'minimum_zero_event_numeric_coverage': minimum_coverage(lock[stage]['tail_alpha']),
                             'zero_event_bounds': {str(n): cp_upper(0, n, lock[stage]['tail_alpha']) for n in [16, 51, 205, 256, 512, 1024]},
                             'bootstrap_precision': mc_precision(lock[stage]['future_bootstrap_draws'], lock[stage]['tail_alpha'], 89 if stage == 'E2' else 10)}
                    for stage in ('E2', 'E4')}
        write_new(out / 'statistical-feasibility.json', coverage)
        check()
        receipt.update(finished_utc=datetime.now(timezone.utc).isoformat(), wall_seconds=time.monotonic() - start,
                       conservative_setup_and_reporting_wall_charge_seconds=limit['setup_wall_seconds'] + limit['reporting_wall_seconds'],
                       max_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
                       status='complete_with_statistical_limitations',
                       decisions={'E1': 'eligible for separate timing protocol/execution request; not run',
                                  'E2_nonidentical': 'precision gate unresolved: conservative cue coverage floor exceeds 256',
                                  'E2_exact': 'by-construction quality route retained; actual costs/headroom unmeasured',
                                  'E3_E4': 'remain blocked; no outcomes released'})
        receipt['artifact_sha256'] = {p.name: sha(p) for p in out.iterdir() if p.is_file() and p.name not in ('started.json', 'execution.json', 'failure.json')}
        write_new(out / 'execution.json', receipt)
        print(json.dumps({'status': receipt['status'], 'counts': counts, 'coverage': coverage, 'wall_seconds': receipt['wall_seconds']}), flush=True)
    except Exception as error:
        write_new(out / 'failure.json', {'error': str(error), 'counts': counts, 'wall_seconds': time.monotonic() - start})
        raise
    finally:
        ledger.close()


if __name__ == '__main__':
    main()
