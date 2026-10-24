"""One frozen E1 timing run; two independent model processes, no other phases."""
from datetime import datetime, timezone
import argparse
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time
import zipfile

for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[name] = '4'
os.environ['TOKENIZERS_PARALLELISM'] = 'false'
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from anytime_ncm.evidence_preflight import sha, write_new
from anytime_ncm.evidence_timing import analyze, make_schedule, validate_schedule, value_hash
from anytime_ncm.wmt_data import StringRows, identity

OUT = ROOT / 'results/evidence_gaps/e1'
LOCK = ROOT / 'docs/studies/evidence-gaps/e1-lock.json'
SOURCES = ['scripts/run_evidence_e1.py', 'src/anytime_ncm/evidence_timing.py', 'src/anytime_ncm/forced_wmt.py',
           'tests/test_evidence_timing.py', 'src/anytime_ncm/wmt_model.py', 'src/anytime_ncm/online.py',
           'src/anytime_ncm/upstream_adapter.py', 'src/anytime_ncm/target_encoding.py',
           'src/anytime_ncm/evidence_preflight.py', 'src/anytime_ncm/stronger_s1.py',
           'src/anytime_ncm/wmt_data.py', 'docs/studies/evidence-gaps/e1-protocol.md',
           'docs/studies/evidence-gaps/e1-lock.json', 'docs/studies/evidence-gaps/e1-schedule.json',
           'configs/phase4_wmt_sources.json', 'third_party/ncm/models/next_concept.py',
           'third_party/ncm/models/quant.py', 'third_party/ncm/models/vqvae.py', 'third_party/ncm/scripts/eval_shard.py']


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def prepare():
    manifest = ROOT/'results/evidence_gaps/e0/input-manifest.json'
    schedule_path = ROOT/'docs/studies/evidence-gaps/e1-schedule.json'
    protocol = 'docs/studies/evidence-gaps/e1-protocol.md'
    if LOCK.exists() or schedule_path.exists():
        raise ValueError('E1 prospective lock/schedule already exist')
    schedule = make_schedule(read(manifest)['E1_existing_exploration'])
    write_new(schedule_path, schedule)
    write_new(LOCK, {'stage':'E1','base_commit':'e5e1cc128940d1d7fce99437c680581eb569de7b',
                    'protocol':protocol,'protocol_sha256':sha(ROOT/protocol),
                    'schedule':schedule_path.relative_to(ROOT).as_posix(),'schedule_sha256':sha(schedule_path),
                    'E0_manifest_sha256':sha(manifest),'config_sha256':sha(ROOT/'configs/phase4_wmt_sources.json'),
                    'parent_manifest_sha256':sha(ROOT/'docs/partitions/wmt14-phase4.json'),
                    'per_process_limits':dict(inputs=500,generator_levels=3300,decoder=1900,encoder=0),
                    'total_limits':dict(inputs=1000,generator_levels=6600,decoder=3800,encoder=0),
                    'identity_bootstrap_draws':10000,'identity_bootstrap_seed':20261025,
                    'orchestration_wall_seconds':1800,'setup_wall_seconds':2700,'reporting_wall_seconds':2700,
                    'artifact_bytes':268435456,'paid_compute_dollars':0,'new_input_outcome_release':False,
                    'forbidden_work':dict(target_encodings=0,fits=0,new_references=0,new_input_identities=0)})
    print('Prepared frozen prospective E1 schedule/lock; zero released-checkpoint requests.', flush=True)


def load_plan():
    lock = read(LOCK)
    if sha(ROOT / lock['protocol']) != lock['protocol_sha256'] or sha(ROOT / lock['schedule']) != lock['schedule_sha256']:
        raise ValueError('Frozen E1 protocol/schedule hash differs')
    manifest_path = ROOT / 'results/evidence_gaps/e0/input-manifest.json'
    if sha(manifest_path) != lock['E0_manifest_sha256']:
        raise ValueError('Sealed E0 manifest differs')
    if sha(ROOT/'configs/phase4_wmt_sources.json') != lock['config_sha256'] or sha(ROOT/'docs/partitions/wmt14-phase4.json') != lock['parent_manifest_sha256']:
        raise ValueError('Pinned config/parent identity manifest differs')
    entries = read(manifest_path)['E1_existing_exploration']
    schedule = read(ROOT / lock['schedule'])
    validate_schedule(schedule, entries)
    return lock, entries, schedule


def git(*args, directory=ROOT):
    return subprocess.check_output(['git', '-c', 'safe.directory=' + str(ROOT), '-c', 'safe.directory=' + str(ROOT / 'third_party/ncm'),
                                    '-c', 'core.autocrlf=true', '-C', str(directory), *args], text=True).strip()


def cached_inputs(entries):
    from anytime_ncm.stronger_s1 import selective_rows, validate_rows
    inventory = read(ROOT / 'docs/studies/stronger-research-inventory.json')
    path = ROOT / 'results/phase4/wmt14/trajectories.jsonl'
    if sha(path) != inventory['files']['results/phase4/wmt14/trajectories.jsonl']['sha256']:
        raise ValueError('Cached trajectory bytes changed')
    rows, skipped = selective_rows(path, entries, 'exploration', inventory['s1_population'])
    validate_rows(rows)
    sources = StringRows((ROOT / 'data/wmt14/sources.pickle').read_bytes()).select({e['index'] for e in entries})
    return {row['index']: row for row in rows}, sources, skipped


def parity(result, cached, expected):
    codes = result['codes'][0].cpu().tolist()
    end = sum([1, 4, 8, 14, 20, 26, 32, 40, 48, 56, 64][:expected['depth']])
    if result['prefix_ids'] != cached['prefix_ids'] or identity(result['prefix_ids']) != expected['identity'] or codes != cached['codes'][:end]:
        raise ValueError('Source/generated prefix parity failed')
    observed = result['observations']
    levels = [expected['depth']] if expected['schedule'] == 'terminal' else list(range(1, expected['depth']+1))
    if [x['level'] for x in observed] != levels:
        raise ValueError('Observation schedule differs')
    for observation in observed:
        old = cached['levels'][observation['level']-1]
        if observation['ids'] != old['ids'] or observation['text'] != old['text']:
            raise ValueError('Decoded cumulative-prefix parity failed')
    return {'codes_sha256': value_hash(codes), 'ids_sha256': value_hash(result['ids']),
            'text_sha256': value_hash(result['text']),
            'observations': [{'level': x['level'], 'ids_sha256': value_hash(x['ids']), 'text_sha256': value_hash(x['text'])} for x in observed]}


def worker(block, seconds):
    import torch
    import transformers
    from anytime_ncm.wmt_model import WmtModel
    from anytime_ncm.forced_wmt import forced_request, ForwardCounter
    from anytime_ncm.target_encoding import model_fingerprint
    start = time.monotonic()
    lock, entries, schedule = load_plan()
    started = read(OUT / 'started.json')
    if any(sha(ROOT / p) != digest for p, digest in started['source_sha256'].items()):
        raise ValueError('Execution source changed')
    plan = [r for r in schedule if r['block'] == block]
    receipt = {'block': block, 'pid': os.getpid(), 'started_utc': datetime.now(timezone.utc).isoformat(),
               'counts': dict(inputs=0, generator_levels=0, decoder=0, encoder=0), 'completed_requests': 0}
    write_new(OUT / f'block-{block}-started.json', receipt)
    counter = None
    result = None
    try:
        if (sys.version_info[:3] != (3, 12, 3) or torch.__version__ != '2.10.0+cu128'
                or torch.version.cuda != '12.8' or transformers.__version__ != '4.57.6'
                or not torch.cuda.is_available() or torch.cuda.get_device_name() != 'NVIDIA GeForce RTX 5060'):
            raise RuntimeError('Material inference environment drift')
        torch.set_num_threads(4)
        cached, sources, skipped = cached_inputs(entries)
        receipt['cached_rows'] = len(cached)
        receipt['output_bodies_skipped'] = skipped
        load_start = time.monotonic()
        model = WmtModel(ROOT)
        receipt['model_load_seconds'] = time.monotonic() - load_start
        receipt['environment'] = {'python': sys.version, 'torch': torch.__version__, 'cuda': torch.version.cuda,
                                  'transformers': transformers.__version__, 'gpu': torch.cuda.get_device_name(),
                                  'cpu_threads': torch.get_num_threads(), 'precision': 'float32/eval',
                                  'tf32_matmul': torch.backends.cuda.matmul.allow_tf32,
                                  'tf32_cudnn': torch.backends.cudnn.allow_tf32,
                                  'device_total_memory': torch.cuda.get_device_properties(0).total_memory,
                                  'free_total_device_bytes_before': list(torch.cuda.mem_get_info())}
        try:
            receipt['nvidia_smi_metadata'] = subprocess.check_output(['nvidia-smi', '--query-gpu=driver_version,name,memory.total', '--format=csv,noheader'], text=True).strip()
        except (OSError, subprocess.SubprocessError):
            receipt['nvidia_smi_metadata'] = 'unavailable'
        fingerprint = lambda: {'generator': model_fingerprint(model.net), 'tokenizer': model_fingerprint(model.tokenizer.vqvae)}
        receipt['state_before'] = fingerprint()
        counter = ForwardCounter(model, lock['per_process_limits'])
        begin_event, end_event = torch.cuda.Event(enable_timing=True), torch.cuda.Event(enable_timing=True)
        with (OUT / f'block-{block}-starts.jsonl').open('x', encoding='utf-8', newline='\n') as ledger, (OUT / f'block-{block}-requests.jsonl').open('x', encoding='utf-8', newline='\n') as stream:
            for number, request in enumerate(plan):
                if time.monotonic() - start > seconds:
                    raise RuntimeError('E1 worker wall cap')
                before = dict(counter.counts)
                counter.take('inputs')
                ledger.write(json.dumps(dict(request, request_count=counter.counts['inputs'], work_before=before)) + '\n')
                ledger.flush()
                torch.cuda.synchronize()
                torch.cuda.reset_peak_memory_stats()
                torch.manual_seed(20261023)
                result = None
                wall_start = time.perf_counter_ns()
                begin_event.record()
                result = forced_request(model, sources[request['index']], request['depth'], request['schedule'])
                end_event.record()
                torch.cuda.synchronize()
                wall_ms = (time.perf_counter_ns() - wall_start) / 1e6
                gpu_ms = begin_event.elapsed_time(end_event)
                work = {k: counter.counts[k] - before[k] for k in before}
                expected_work = dict(inputs=1, generator_levels=request['depth'], decoder=1 if request['schedule'] == 'terminal' else request['depth'], encoder=0)
                if work != expected_work:
                    raise RuntimeError('Real generator/decoder work differs from forced schedule')
                hashes = parity(result, cached[request['index']], request)
                record = dict(request, wall_ms=wall_ms, cuda_stream_span_ms=gpu_ms,
                              peak_allocated_bytes=torch.cuda.max_memory_allocated(), peak_reserved_bytes=torch.cuda.max_memory_reserved(),
                              work=work, parity=True, **hashes)
                stream.write(json.dumps(record, allow_nan=False) + '\n')
                stream.flush()
                receipt['completed_requests'] += 1
                if number in (19, 179, 339, 499):
                    if sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file()) > lock['artifact_bytes']:
                        raise RuntimeError('E1 artifact cap exceeded')
                    print(f'E1 block {block}: {number+1}/500 allocated requests complete; parity/work checks passed', flush=True)
        receipt['state_after'] = fingerprint()
        if receipt['state_before'] != receipt['state_after'] or counter.counts != lock['per_process_limits']:
            raise RuntimeError('Model state changed or process allocation incomplete')
        receipt.update(status='complete', counts=dict(counter.counts), actual_forward_calls=dict(counter.calls),
                       wall_seconds=time.monotonic()-start, max_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
                       free_total_device_bytes_after=list(torch.cuda.mem_get_info()), finished_utc=datetime.now(timezone.utc).isoformat())
        write_new(OUT / f'block-{block}-execution.json', receipt)
    except Exception as error:
        receipt.update(status='failed', error=type(error).__name__ + ': ' + str(error), counts=dict(counter.counts) if counter else receipt['counts'], wall_seconds=time.monotonic()-start)
        if result is not None:
            write_new(OUT / f'block-{block}-failure-output.json', {'request':request,'codes': result['codes'][0].cpu().tolist(), 'observations': result['observations'], 'prefix_ids': result['prefix_ids']})
        write_new(OUT / f'block-{block}-failure.json', receipt)
        raise
    finally:
        if counter: counter.close()


def run(remote):
    start = time.monotonic()
    if git('rev-parse', 'HEAD') != remote or git('branch', '--show-current') != 'main' or git('status', '--porcelain'):
        raise ValueError('Need clean main with verified source/protocol remote equality')
    if git('rev-parse', 'HEAD', directory=ROOT/'third_party/ncm') != 'c70274273f489abc73832b2b98584a8483b6b203':
        raise ValueError('Pinned upstream differs')
    lock, entries, schedule = load_plan()
    OUT.mkdir(parents=True, exist_ok=False)
    started = {'stage': 'E1', 'started_utc': datetime.now(timezone.utc).isoformat(), 'source_commit': remote,
               'source_sha256': {p: sha(ROOT/p) for p in SOURCES}, 'new_input_outcome_release': False, 'new_reference_access': False}
    write_new(OUT/'started.json', started)
    try:
        config = read(ROOT/'configs/phase4_wmt_sources.json')
        hashes = {}
        for path, info in config['files'].items():
            if path.endswith('reference_translations.pickle'): continue
            actual = sha(ROOT/path)
            if actual != info['sha256'] or (ROOT/path).stat().st_size != info['size']:
                raise ValueError('Pinned local asset differs: ' + path)
            hashes[path] = actual
        write_new(OUT/'preflight.json', {'assets_sha256': hashes, 'config_sha256': sha(ROOT/'configs/phase4_wmt_sources.json'),
                                       'E0_manifest_sha256': lock['E0_manifest_sha256'], 'upstream_commit': git('rev-parse','HEAD',directory=ROOT/'third_party/ncm')})
        with zipfile.ZipFile(OUT/'execution-sources.zip','x',compression=zipfile.ZIP_DEFLATED) as z:
            for path in SOURCES: z.writestr(path, (ROOT/path).read_bytes())
            z.writestr('manifest.json', json.dumps(started, indent=2))
        for block in range(2):
            remaining = lock['orchestration_wall_seconds'] - (time.monotonic()-start)
            if remaining <= 0: raise RuntimeError('E1 orchestration wall cap')
            subprocess.run([sys.executable, str(Path(__file__).resolve()), '--worker', str(block), '--worker-seconds', str(remaining)],
                           cwd=ROOT, check=True, timeout=remaining)
        rows = [json.loads(line) for block in range(2) for line in (OUT/f'block-{block}-requests.jsonl').read_text(encoding='utf-8').splitlines()]
        processes = [read(OUT/f'block-{block}-execution.json') for block in range(2)]
        if processes[0]['pid'] == processes[1]['pid']:
            raise RuntimeError('Process IDs unexpectedly identical')
        counts = {k:sum(p['counts'][k] for p in processes) for k in lock['total_limits']}
        if counts != lock['total_limits']: raise RuntimeError('E1 total allocation incomplete')
        report = analyze(rows, schedule, entries)
        write_new(OUT/'analysis.json', report)
        elapsed = time.monotonic()-start
        size = sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file())
        if elapsed > lock['orchestration_wall_seconds'] or size > lock['artifact_bytes']:
            raise RuntimeError('E1 time/storage cap exceeded')
        write_new(OUT/'execution.json', {'status':'complete', 'source_commit':remote, 'counts':counts,
                  'requests':len(rows),'timed_requests':960,'warmups':40,'process_ids':[p['pid'] for p in processes],
                  'orchestration_wall_seconds':elapsed,'conservative_setup_reporting_charge_seconds':5400,'artifact_bytes':size,
                  'all_parity_passed':True,'state_fingerprints_unchanged':True,'new_input_identities':0,'new_references':0,
                  'fits':0,'target_encodings':0,'paid_compute_dollars':0,'decision':report['decision'],
                  'artifact_sha256':{p.name:sha(p) for p in OUT.iterdir() if p.is_file()}})
        print('E1 complete:',report['decision'],counts,flush=True)
    except Exception as error:
        write_new(OUT/'failure.json', {'error':type(error).__name__+': '+str(error),'orchestration_wall_seconds':time.monotonic()-start,'automatic_retry':False})
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--remote-head')
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--worker', type=int, choices=(0,1))
    parser.add_argument('--worker-seconds', type=float)
    args = parser.parse_args()
    if args.prepare:
        prepare()
    elif args.worker is not None:
        if not args.worker_seconds or args.worker_seconds <= 0: raise ValueError('Worker needs a positive remaining wall allocation')
        worker(args.worker,args.worker_seconds)
    elif args.remote_head:
        run(args.remote_head)
    else:
        parser.error('Supply --remote-head after source lock push/verification')
