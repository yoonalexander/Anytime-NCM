"""Separate saved-record E1 arithmetic/parity checker. No model inference/imports."""
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import re
import statistics
import sys
import zipfile
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'results/evidence_gaps/e1'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for part in iter(lambda:stream.read(1 << 20), b''): h.update(part)
    return h.hexdigest()


def value_hash(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=True,separators=(',',':')).encode()).hexdigest()


def percentile(values, p):
    values = sorted(float(v) for v in values)
    position = (len(values)-1)*p
    i = int(position)
    j = min(i+1,len(values)-1)
    return values[i]+(values[j]-values[i])*(position-i)


def main():
    target = OUT/'independent-checks.json'
    if target.exists(): raise FileExistsError('Preserve original E1 verification receipt')
    execution, started = read(OUT/'execution.json'), read(OUT/'started.json')
    for path, expected in execution['artifact_sha256'].items():
        if digest(OUT/path) != expected: raise ValueError('Run artifact hash differs: '+path)
    for path, expected in started['source_sha256'].items():
        if digest(ROOT/path) != expected: raise ValueError('Executed source hash differs: '+path)
    with zipfile.ZipFile(OUT/'execution-sources.zip') as z:
        for path, expected in started['source_sha256'].items():
            if hashlib.sha256(z.read(path)).hexdigest() != expected: raise ValueError('Execution archive differs')
    lock = read(ROOT/'docs/studies/evidence-gaps/e1-lock.json')
    schedule = read(ROOT/lock['schedule'])
    entries = read(ROOT/'results/evidence_gaps/e0/input-manifest.json')['E1_existing_exploration']
    selected = {e['index']:e['identity'] for e in entries}
    cache = {}
    header = re.compile(rb'^\{"identity":"([a-f0-9]{64})","index":(\d+),"partition":"([a-z_]+)"')
    # Other existing output bodies remain opaque, just as in execution.
    with (ROOT/'results/phase4/wmt14/trajectories.jsonl').open('rb') as stream:
        for raw in stream:
            m = header.match(raw)
            if not m: raise ValueError('Bad cached metadata header')
            index = int(m[2])
            if index in selected:
                if m[1].decode() != selected[index] or m[3] != b'exploration': raise ValueError('Wrong cache identity')
                cache[index] = json.loads(raw)
    if set(cache) != set(selected): raise ValueError('Missing permitted cached rows')
    processes = [read(OUT/f'block-{i}-execution.json') for i in range(2)]
    if processes[0]['pid'] == processes[1]['pid']: raise ValueError('Expected separate process IDs')
    rows = []
    for block in range(2):
        actual = [json.loads(s) for s in (OUT/f'block-{block}-requests.jsonl').read_text().splitlines()]
        starts = [json.loads(s) for s in (OUT/f'block-{block}-starts.jsonl').read_text().splitlines()]
        if len(actual) != 500 or len(starts) != 500: raise ValueError('Missing process rows')
        running = dict(inputs=0,generator_levels=0,decoder=0,encoder=0)
        for request,begin in zip(actual,starts,strict=True):
            planned = schedule[request['request_id']]
            if any(request[k]!=v or begin[k]!=v for k,v in planned.items()): raise ValueError('Order/identity schedule mismatch')
            if begin['work_before'] != running or begin['request_count'] != running['inputs']+1: raise ValueError('Pre-call ledger differs')
            delta = dict(inputs=1,generator_levels=request['depth'],decoder=1 if request['schedule']=='terminal' else request['depth'],encoder=0)
            if request['work'] != delta or not request['parity']: raise ValueError('Work/parity mismatch')
            running = {k:running[k]+delta[k] for k in running}
            old = cache[request['index']]
            end = sum([1,4,8,14,20,26,32,40,48,56,64][:request['depth']])
            last = old['levels'][request['depth']-1]
            if request['codes_sha256'] != value_hash(old['codes'][:end]) or request['ids_sha256'] != value_hash(last['ids']) or request['text_sha256'] != value_hash(last['text']): raise ValueError('Saved actual/cached output hashes differ')
            expected_levels = [request['depth']] if request['schedule']=='terminal' else list(range(1,request['depth']+1))
            if [o['level'] for o in request['observations']] != expected_levels: raise ValueError('Inspections differ')
            for o in request['observations']:
                cached = old['levels'][o['level']-1]
                if o['ids_sha256'] != value_hash(cached['ids']) or o['text_sha256'] != value_hash(cached['text']): raise ValueError('Observation hash differs')
            if not math.isfinite(request['wall_ms']) or request['wall_ms']<=0: raise ValueError('Invalid timing')
        if running != lock['per_process_limits'] or running != processes[block]['counts']: raise ValueError('Process counts differ')
        if processes[block]['state_before'] != processes[block]['state_after']: raise ValueError('Weight/buffer fingerprint changed')
        rows.extend(actual)
    analysis = read(OUT/'analysis.json')
    group = defaultdict(list)
    rawcells = defaultdict(list)
    identities = [e['identity'] for e in entries]
    for r in rows:
        if r['phase']=='timed':
            key=f"{r['schedule']}:{r['depth']}"
            group[r['block'],r['identity'],key].append(r['wall_ms'])
            rawcells[key].append(r['wall_ms'])
    cells = list(analysis['cells'])
    means = {key:np.array([[statistics.fmean(group[b,identity,key]) for identity in identities] for b in range(2)]) for key in cells}
    for key in cells:
        saved = analysis['cells'][key]
        for name,value in [('mean_ms',statistics.fmean(rawcells[key])),('median_ms',statistics.median(rawcells[key])),('p95_ms',percentile(rawcells[key],.95))]:
            if not math.isclose(value,saved[name],rel_tol=0,abs_tol=1e-10): raise ValueError('Cell summary differs')
    # Replay the same frozen 10,000 resamples, not a new sensitivity/draw set.
    ix = np.random.Generator(np.random.PCG64(20261025)).integers(0,16,size=(10000,16))
    checked = 0
    for candidate,baseline,saved in [(k,'terminal:11',v) for k,v in analysis['versus_terminal_11'].items()]+[(f'every_level:{d}',f'terminal:{d}',v) for d,v in analysis['every_level_versus_terminal'].items()]:
        for label, a, b in [('pooled',means[candidate].mean(axis=0),means[baseline].mean(axis=0)),*[(f'block_{i}',means[candidate][i],means[baseline][i]) for i in range(2)]]:
            point=1-statistics.fmean(a)/statistics.fmean(b)
            resampled=1-a[ix].mean(axis=1)/b[ix].mean(axis=1)
            ci=[percentile(resampled,.025),percentile(resampled,.975)]
            recorded=saved[label]
            if not math.isclose(point,recorded['relative_mean_reduction'],abs_tol=1e-12): raise ValueError('Relative mean point differs')
            if not np.allclose(ci,recorded['relative_mean_reduction_ci95_nominal'],rtol=0,atol=1e-12): raise ValueError('Paired descriptive interval differs')
            checked+=1
    if any(name in sys.modules for name in ('torch','transformers')): raise RuntimeError('Verification imported model library')
    receipt={'status':'passed','same_assistant_separate_implementation':True,'independent_human_review':False,
             'request_rows_checked':len(rows),'timed_rows':sum(r['phase']=='timed' for r in rows),'paired_contrasts_and_process_summaries_checked':checked,
             'output_hashes_and_every_observation_match_cache':True,'source_and_artifact_hashes_match':True,'model_fingerprints_unchanged':True,
             'distinct_model_processes':2,'bootstrap_indices_sha256':hashlib.sha256(ix.tobytes()).hexdigest(),
             'resample_interpretation':'same frozen 10000 identity vectors replayed, no new draw set','new_model_requests':0,'new_input_identities':0,'new_references':0,
             'verifier_sha256':digest(Path(__file__)),'execution_receipt_sha256':digest(OUT/'execution.json'),
             'limitations':['nominal intervals conditional on sixteen exposed identities/two fixed process blocks','no quality noninferiority or adaptive policy confirmation']}
    with target.open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(receipt,stream,indent=2);stream.write('\n')
    print(json.dumps(receipt),flush=True)


if __name__=='__main__': main()
