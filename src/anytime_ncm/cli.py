"""Dependency-free snapshot inspection and checkout-dependent research commands."""
import argparse
from collections.abc import Sequence
import json
from pathlib import Path
from anytime_ncm import __version__
from anytime_ncm.snapshot import load_snapshot

def research_repository(explicit: Path | None) -> Path:
    candidates=[explicit.resolve()] if explicit else [Path.cwd(),*Path.cwd().parents,Path(__file__).resolve().parents[2]]
    for root in candidates:
        if (root/'.gitmodules').is_file() and (root/'configs').is_dir() and (root/'third_party/ncm').is_dir():return root
    raise ValueError('This command requires an existing Anytime-NCM research checkout. Pass --repository PATH before the command; see docs/delivery/INSTALL.md. Snapshot status needs no checkout or models.')

def main(argv: Sequence[str] | None = None) -> int:
    parser=argparse.ArgumentParser(prog='anytime-ncm',description='Inspect a closed NCM research snapshot. No useful quality-preserving adaptive speedup is established.')
    parser.add_argument('--version',action='version',version=__version__)
    parser.add_argument('--repository',type=Path,help='Existing research checkout for legacy collection/trajectory verification; not needed for status.')
    commands=parser.add_subparsers(dest='command')
    status=commands.add_parser('status',help='Read the packaged aggregate research outcome without models or datasets.')
    status.add_argument('--json',action='store_true',help='Print the complete versioned aggregate snapshot with source links and limitations.')
    collector=commands.add_parser('collect',help='Historical offline collector; requires a research checkout, pinned assets and a separately authorized protocol.')
    collector.add_argument('--config',type=Path,required=True);collector.add_argument('--output-path');collector.add_argument('--run-id')
    verifier=commands.add_parser('validate-trajectories',help='Audit existing selected trajectory files in a research checkout; no model inference.')
    verifier.add_argument('--metadata',type=Path,required=True)
    args=parser.parse_args(argv)
    if args.command=='status':
        value=load_snapshot();e=value['latest_evaluation']
        if args.json:print(json.dumps(value,indent=2,sort_keys=True,allow_nan=False))
        else:
            print(f'Anytime NCM {__version__} — research snapshot; studies closed')
            print(value['outcome'])
            print(f"Latest development evaluation: {e['inputs']:,} inputs; {e['early_exits']} early exits.")
            print(f"Actual mean saving: {100*e['mean_saving']:.3f}%; BLEU loss: {e['quality_losses']['bleu']:.6f} (allowed 0.5; fails).")
            print('Q0 remains failed; independent confirmation is not ready. See status --json for limits and evidence.')
        return 0
    if args.command in {'collect','validate-trajectories'}:
        try:
            repository=research_repository(args.repository)
            from anytime_ncm.collect import run_collection,verify_run
            if args.command=='collect':
                overrides={k:v for k,v in [('output_path',args.output_path),('run_id',args.run_id)] if v is not None};report=run_collection(repository,args.config,overrides=overrides)
            else:report=verify_run(repository,args.metadata)
        except ImportError:
            parser.exit(2,'Research dependencies are not installed. Use the pinned research environment in docs/delivery/INSTALL.md; base snapshot inspection has no runtime dependencies.\n')
        except (ValueError,RuntimeError,OSError) as error:parser.exit(1,f'{error}\n')
        print(json.dumps({k:v for k,v in report.items() if k!='source_sha256'},indent=2,sort_keys=True));return 0
    parser.print_help();return 0
