"""Existing-evidence campaign closeout. No model, fit, reference scoring or resampling."""
import argparse,hashlib,json,resource,signal,subprocess,sys,time,xml.etree.ElementTree as ET,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from anytime_ncm.evidence_preflight import sha,write_new
from anytime_ncm.quality_campaign import campaign_root,verify_campaign,record_phase,usage_zero
C=campaign_root(ROOT);B=ROOT/'docs/studies/quality-tolerant';OUT=C/'closeout';REPORT=B/'campaign-20261029-final-report.md';RUNBOOK=B/'campaign-20261029-verification.md'
PHASES=['01-signal-pilot','02-light-signal-pilot','03-signal-discrimination','04-joint-controller-selection','05-joint-cost-diagnostic','06-development-eligibility','07-development-collection','07r-development-reporting','08-development-controller','09-development-evaluation','09r-evaluation-reporting','09t-first-timing-diagnostic']
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def git(*a):return subprocess.check_output(['git.exe',*a],cwd=ROOT,text=True,timeout=60).strip()
def cpu():
    a=resource.getrusage(resource.RUSAGE_SELF);b=resource.getrusage(resource.RUSAGE_CHILDREN);return a.ru_utime+a.ru_stime+b.ru_utime+b.ru_stime

def hashes(values):
    for p,h in values.items():
        if sha(ROOT/p)!=h:raise ValueError('Frozen evidence changed: '+p)
def load():
    lock=read(B/'campaign-closeout-lock.json');s=read(B/'campaign-closeout-source-lock.json')
    for k in ('source_sha256','protected_sha256','private_sha256'):hashes(s[k])
    if git('-C','third_party/ncm','rev-parse','HEAD')!=s['upstream_commit'] or git('-C','third_party/ncm','status','--porcelain'):raise ValueError('Upstream changed')
    return lock,s

def audit():
    phases=[];tests=0
    for name in PHASES:
        a=read(C/'accounting'/('phase-'+name+'.json'));p=C/a['evidence_path'];e=read(p)
        if sha(p)!=a['evidence_sha256'] or e['campaign_usage']!=a['usage']:raise ValueError('Accounting not bound to evidence')
        if name not in ('07-development-collection','09-development-evaluation') and e.get('status')!='complete':raise ValueError('Unfinished phase not preserved as failure')
        source=e.get('source_commit') or read(p.parent/'started.json').get('source_commit')
        if not isinstance(source,str) or len(source)!=40:raise ValueError('Missing prospective execution commit')
        if source:
            subprocess.run(['git.exe','merge-base','--is-ancestor',source,'HEAD'],cwd=ROOT,check=True,timeout=60)
        xml=p.parent/'synthetic-tests.xml'
        tree=ET.parse(xml).getroot();suites=[tree] if tree.tag=='testsuite' else list(tree.findall('testsuite'))
        n=sum(int(v.get('tests',0)) for v in suites);fail=sum(int(v.get('errors',0))+int(v.get('failures',0))+int(v.get('skipped',0)) for v in suites)
        if n<1 or fail:raise ValueError('Missing/nonpassing recorded focused tests')
        tests+=n
        if not (p.parent/'execution-sources.zip').is_file():raise ValueError('Missing execution source archive')
        for rel,h in e.get('artifact_sha256',{}).items():
            if sha(p.parent/rel)!=h:raise ValueError('Executed artifact changed')
        phases.append(dict(phase=name,evidence=p.relative_to(ROOT).as_posix(),source_commit=source,recorded_focused_tests=n,scientific_decision=read(p.parent/'decision.json') if (p.parent/'decision.json').exists() else dict(status='preserved_reporting_failure'),charge=a['usage'],terminal_kind='preserved_failure' if name in ('07-development-collection','09-development-evaluation') else 'complete'))
    if tests!=73:raise ValueError('Unexpected campaign focused-test ledger')
    p7=read(C/'development_collection_reporting/completion.json');p9=read(C/'development_evaluation_reporting/execution.json');q=read(C/'development_evaluation_reporting/quality-points.json');t=read(C/'first_timing_diagnostic/analysis.json');te=read(C/'first_timing_diagnostic/execution.json');policy=read(C/'development_controller/policy.json');q0=read(ROOT/'results/quality_tolerant/final_math_review/decision.json');exact=read(ROOT/'results/quality_tolerant/final_math_review/exact-results.json');eligibility=read(ROOT/'results/quality_tolerant/eligibility_audit/completion-decision.json')
    if p7['original_parent_final_resource_gate_reached'] or p9['original_cache_terminal_receipt_available'] or p9['original_cache_final_state_hashes_available']:raise ValueError('Missing original receipt falsely repaired')
    if q['controller']['point_pass'] or q['controller']['losses']['bleu']<=.5 or q['controller']['metrics']['numeric_reference_coverage']!=289 or t['quality_point_pass'] or t['original_success_contract_established'] or t['original_phase09_matrix_complete']:raise ValueError('Negative quality/incomplete-matrix boundary changed')
    if q0['Q0_passed'] or eligibility['operational_metadata_screen_passed'] or q0['reserved_outputs_released']:raise ValueError('Confirmation prerequisites changed; cannot use this negative-closeout path')
    if te['counts']['inputs']!=4772 or te['new_fits'] or te['new_corpus_scores'] or not te['model_states_unchanged']:raise ValueError('Incomplete timing diagnostic')
    if policy['policy']['name']!='ridge:cheap:8:guard0:0.6' or policy['locked_fixed_comparator']!='fixed:11' or policy['evaluation_outcomes_seen_for_selection']!=0:raise ValueError('Policy/comparator changed')
    policy_commit='993180fe8f12d5a84b87a8f57aba10ced1dd1d9a';blob=subprocess.check_output(['git.exe','show',policy_commit+':results/quality_tolerant/campaign_20261029/development_controller/policy.json'],cwd=ROOT,timeout=60)
    if hashlib.sha256(blob).hexdigest()!=sha(C/'development_controller/policy.json'):raise ValueError('Policy not byte-identical to prior push')
    subprocess.run(['git.exe','merge-base','--is-ancestor',policy_commit,'de2bc20dffc4c51634accb6727758a5f41b34046'],cwd=ROOT,check=True,timeout=60)
    campaign=verify_campaign(ROOT);u=campaign['charged_usage']
    private_root=ROOT/'data/quality_tolerant_campaign_20261029';combined_storage=sum(p.stat().st_size for d in (C,private_root) for p in d.rglob('*') if p.is_file())
    if combined_storage>read(B/'campaign-20261029-lock.json')['ceilings']['artifact_bytes']:raise ValueError('Combined campaign artifact limit')
    if u['real_fits']!=16 or u['controller_families']!=2 or u['confirmation_evaluations'] or u['download_bytes'] or u['paid_dollars']:raise ValueError('Unexpected campaign work')
    numeric_upper=exact['confirmation_numeric']['sharp_zero_brackets']['1/40']['upper']['decimal'];negation_upper=exact['confirmation_inputs']['sharp_zero_brackets']['1/40']['upper']['decimal']
    if numeric_upper<=.02 or negation_upper<=.02:raise ValueError('Existing mathematical obstruction changed')
    readiness=dict(status='not_ready_no_confirmation_release',quality_point_gate_passed=False,Q0_passed=False,original_population_method_route_closed=True,confirmation_population_inputs=eligibility['confirmation']['inputs'],confirmation_components=eligibility['confirmation']['components'],numeric_covered_inputs=eligibility['confirmation']['numeric_covered'],numeric_covered_components=eligibility['confirmation']['covered_components'],sharp_all_zero_numeric_endpoint=numeric_upper,sharp_all_zero_negation_endpoint=negation_upper,unchanged_cue_margin=.02,largest_component_fraction=eligibility['confirmation']['max_input_component_fraction'],operational_component_screen_passed=False,scope='Existing independent heterogeneous bounded-component all-zero marginal route; not all possible signed-data methods or populations',proposed_confirmation7700_and_historical_E3_E4_unallocated_still_sealed=True,new_method_simulations_or_metadata_collection=0)
    requirements=[
      dict(requirement='Objective: useful controller OR bounded negative/inconclusive closeout',result='negative_closeout_supported',evidence=['development_evaluation_reporting/quality-points.json','first_timing_diagnostic/analysis.json'],meaning='Selected rule fails original BLEU point screen; timing cannot rescue it.'),
      dict(requirement='16-input confidence instrumentation, parity, variation and cost',result='completed_failed_original_gate_preserved_bounded_alternative_qualified',evidence=['signal_pilot/execution.json','signal_pilot/decision.json','light_signal_pilot/execution.json','light_signal_pilot/decision.json']),
      dict(requirement='Prospective signal discrimination, cheap baselines and sparse-label disclosure',result='completed_development_evidence_only',evidence=['signal_discrimination/execution.json','signal_discrimination/decision.json','development_controller/prediction-diagnostics.json','development_controller/endpoint-component-support.json']),
      dict(requirement='At most2families/32fits, frozen selection before evaluation and causal actual timing',result='completed_bounded_revision_negative',evidence=['development_controller/execution.json','development_controller/policy.json','development_evaluation/access-release.json','first_timing_diagnostic/execution.json'],limits='16fits/2families. Original12method/tworepeat matrix incomplete; first diagnostic2methods/one repeat.'),
      dict(requirement='Eligible bounded development extension with whole-component roles and variable cues',result='completed_with_preserved_original_reporting_failure',evidence=['development_eligibility/source-only-allocation.json','development_collection/failure-preservation.json','development_collection_reporting/completion.json','development_collection_reporting/label-support.json']),
      dict(requirement='Confirmation only if original statistical/population prerequisites met',result='correctly_withheld_not_ready',evidence=['confirmation-readiness.json'],limits='No new sharper method, margins, population assumptions or confirmation release.'),
      dict(requirement='Original quality and actual-latency success contract',result='not_established',evidence=['development_evaluation_reporting/quality-points.json','first_timing_diagnostic/analysis.json'],limits='BLEU point fail; independent quality guarantees and feasible-fixed frontier unavailable.'),
      dict(requirement='Preserve historical sources, failures, budgets, actual-work distinctions and upstream',result='verified_with_explicit_missing_receipts',evidence=['phase-audit.json','decision.json'],limits='Originalphase07parent resource receipt and phase09cache final state/resource receipt missing; never invented.'),
      dict(requirement='Code/tests/source archives/access receipts and runnable saved verification',result='delivered',evidence=['phase-audit.json'],limits='73recorded focused passes; no fresh whole-suite claim. Private corpora/checkpoints remain local/ignored.'),
      dict(requirement='Updated roadmap, plain-language report, final decision and Git delivery',result='artifacts_generated_delivery_verified_separately',evidence=['decision.json','completion-review.json'],limits='Final saved verifier, link checks and live local/remote equality required after artifact generation.')]
    return dict(phases=phases,recorded_focused_tests=tests,quality=q,timing=t,readiness=readiness,requirements=requirements,campaign=campaign,combined_campaign_public_private_bytes=combined_storage,known_actual_model_attempts=11799+te['counts']['inputs'])

def documents(a):
    q=a['quality']['controller']['losses'];t=a['timing'];lo=t['conditional_nominal_interval']['lower'];hi=t['conditional_nominal_interval']['upper'];usage=a['campaign']['charged_usage'];c=t['methods']['controller']['mean_ms'];full=t['methods']['fixed:11']['mean_ms'];session=', '.join(f'{100*v:.3f}%' for v in t['session_savings'])
    report=f"""# Anytime NCM: bounded campaign complete, selected controller fails quality screen

October 29, 2026. **This campaign did not establish the intended quality-and-latency advantage.** The final frozen controller stops early on 315 of 1,188 development-evaluation inputs, but its corpus BLEU loss is {q['bleu']:.6f}, above 0.5 allowed. Actual mean ready-output time is {c:.3f} ms versus {full:.3f} ms native full ({100*t['mean_saving']:.3f}% saving). This is a bounded negative development result for this selected rule; it does not prove every adaptive translation approach fails.

[Final decision](../../../results/quality_tolerant/campaign_20261029/closeout/decision.json), [objective-by-objective audit](../../../results/quality_tolerant/campaign_20261029/closeout/requirements.json), [phase/test/provenance audit](../../../results/quality_tolerant/campaign_20261029/closeout/phase-audit.json), [confirmation readiness](../../../results/quality_tolerant/campaign_20261029/closeout/confirmation-readiness.json), [verification runbook](campaign-20261029-verification.md), [live roadmap](../quality-tolerant-translation-roadmap.md), [original campaign objective](campaign-20261029-objective.md).

## What the final rule actually did

The 19-feature ridge rule was pushed at 993180f before evaluation outcomes. It observes level 8, exits at score <=0.6, otherwise goes directly to level 11. It uses no level-10 inspection, extra raw-logit summary or literal guard. Thresholds/coefficients/comparator were unchanged after evaluation. Evaluation uses 1,188 inputs in 60 whole document-alias components, including 289 references with numeric cues. Unknown checkpoint-training overlap and broad prior development exposure remain.

| Full-relative endpoint | Evaluation point | Requirement | Result |
| --- | ---: | ---: | --- |
| Corpus BLEU loss |{q['bleu']:.6f}|<=0.5|Fail|
| Corpus chrF loss |{q['chrf']:.6f}|<=1.0|Pass point only|
| Reference-defined mean numeric F1 loss |{q['numeric_reference_f1']:.6f}|<=0.02|Pass point only|
| Negation mismatch increase |{q['negation_cue_mismatch_rate']:.6f}|<=0.02|Pass point only|
| Actual mean ready-output saving vs full |{100*t['mean_saving']:.3f}%|>=5%|{'Timing screen passed' if t['timing_screen_passed'] else 'Timing screen not passed'}|

Actual per-session savings: {session}; retained conditional nominal paired interval [{100*lo:.3f}%,{100*hi:.3f}%]. Two processes, one timed repeat per input/method/session, 20 warmups and 4,772 requests, all causal exit/current-prefix/feature/output/work checks and unchanged model states verified. The timer includes tokenization, generation, observations, reconstruction, decoding/transfers, features, scalar decisions and final synchronization. CUDA stream spans are separate records.

Intervals resample 60 whole components 20,000 times, condition on the two observed sessions, and retain original nominal tail .05/22 and Monte Carlo family 11 despite only one observed contrast. Their approximate interpretation requires suitable independent/exchangeable components; no hardware/session-population or finite-sample guarantee follows. No quality confidence bounds were established. Corpus metrics/literal cues do not certify semantics.

All 11 fixed depths have corpus point scores; depths 1-10 fail them, but no adjusted quality exclusion was established. Their actual timings were omitted from the final smaller diagnostic. Consequently improvement over all potentially feasible fixed alternatives remains unproved. Historical all-fixed timings for a different policy/population cannot fill that gap. This report does not claim the original success contract was met.

## What the campaign learned

The original 16-input rich confidence pilot failed its whole-request cost gate. A separately frozen lighter pilot qualified selected-token raw-logit extraction; these scores are not calibrated probabilities. Initial richer probes modestly improved level8ranking on consumed calibration data, without demonstrating useful controller performance.

The first rich controller's actual calibration saving was 4.161%, below 5%. A metadata-first whole-component development extension added 3,408 fit, 891 calibration and 1,188 evaluation inputs while leaving 7,700 proposed confirmation inputs reserved. Numeric supervision grew to 714 fit and 226 calibration covered references, and fit negation-change labels became variable (34 adverse examples at level 8; 11 at level 10) rather than all zero. These are development support counts, not protection or power guarantees.

Final matched ridge ablations and shallow trees used 16 total real fits across 2 families. Richer features improved ranking modestly, but the frozen cost/quality selection chose cheap features. Selected calibration BLEU loss of .446092 and projected 5.325% saving did not transfer to the evaluation BLEU tolerance. Changed sample/population/model/target choices prevent attributing improvement or failure to a single cause. No true continuation-value estimator, generator/tokenizer training or target encoding was performed.

## Preserved failures and scope limits

The original phase07 collection completed 4,304 native requests but failed NumPy-boolean support-report serialization. A reporting-only repair recovered saved labels; original partial JSON/full reservation and missing original parent final CPUgate remain preserved.

The original phase09 evaluation completed 1,193 native-cache requests but failed terminal JSON serialization of TorchVersion. Its final state hashes/environment/resource values were not durably saved. Reporting-only repair verified every saved trace/public binding and computed the above corpus points without new inference. Missing process-state/resource observations remain unavailable. The version field was explicitly normalized and a durable initial receipt added before the final timing diagnostic.

**The original 12-method/two-repeat evaluation matrix remains incomplete.** Full conservative failure charges left insufficient CPU for it. A prospectively frozen first controller/native-full timing diagnostic retained all 1,188 inputs but used 2 methods and one repeat; its quality failure was already known and could not be rescued. This is a separate bounded diagnostic, not retrospective completion of the failed matrix. No policy was retuned or sample replaced.

## Confirmation and stopping decision

Confirmation is not ready and was not released. The selected controller fails its development BLEU point gate. Independently, the prior final-math review's declared heterogeneous independent-component all-zero marginal route remains closed: sharp endpoints .034389 for numeric loss and .025542 for negation increase exceed .02, and the largest confirmation component (85/7,700) exceeds the frozen 1% operational screen. These are limitations of that model/population/observation route, not universal impossibility for every signed-data method or population. No new method was chosen to rescue this result.

Q0 remains failed; 7,700 proposed confirmation inputs and historical E3/E4/unallocated outcomes stay sealed. No further model families, fits, development extension, retuning or confirmation follows this campaign. A materially different scientific hypothesis would be a new study with new justification; it is not remaining work in this completed negative campaign. Human rights/authorship/independent scientific review and external submission remain separate and unperformed.

## Evidence, resources and delivery

There are 73 recorded passing focused test cases across prospectively locked stages; no fresh whole-suite run is claimed. [Phase09quality/repair detail](development-evaluation-results.md), [original phase09protocol](development-evaluation-protocol.md), [first timing protocol](first-timing-diagnostic-protocol.md), [phase08comparison](development-controller-results.md), [final mathematical review](final-math-review-results.md) preserve the primary evidence and methodological sources. Separate same-assistant arithmetic reviews are not independent human scientific review.

Charged before this reporting phase: {usage['model_requests']} attempts, {usage['model_orchestration_seconds']:.3f} model seconds, {usage['cpu_seconds']:.3f} CPU seconds, 16 fits / 2 families, $0; known actual attempts {a['known_actual_model_attempts']}. Conservative failed reservations are charges, not claims all reserved calls ran. Closeout accounting adds its measured CPU/reporting allowance without refunds. Public/private artifacts, models/data kept outside Git, missing historical resource receipts and unknown checkpoint overlap remain explicit. All source locks, archived execution bytes, failures and pinned upstream are preserved.

The final saved verifier and Git live-equality check complete delivery. This negative closeout answers the bounded campaign objective without asserting that the project has achieved its intended useful adaptive stopping advantage.
"""
    runbook=r"""# Campaign verification and artifact availability

The campaign is closed with a negative quality point result. These are saved-evidence commands; they do not repeat inference, fitting, reference scoring or bootstrap. Use the verified repository root C:\Users\Admin\Documents\Projects\Anytime-NCM. WSL2 Ubuntu-24.04, user ncm, Python /home/ncm/.venvs/anytime-ncm are the recorded environment; requirements.lock and pinned assets remain unchanged. Private source/reference/trajectory caches stay ignored and require the original local machine or separately lawful provision. Public Git artifacts alone cannot reproduce private corpus computations; no redistribution license is asserted.

~~~powershell
.\scripts\wsl_python.ps1 -PythonArguments @('scripts/repair_evaluation_reporting.py','verify')
.\scripts\wsl_python.ps1 -PythonArguments @('scripts/run_first_timing_diagnostic.py','verify')
.\scripts\wsl_python.ps1 -PythonArguments @('scripts/close_quality_campaign.py','verify')
git status --short
git rev-parse HEAD
git ls-remote origin refs/heads/main
~~~

All three verifiers must pass; the final two hashes must match for completed Git delivery. No real checkpoint load or GPU is needed for these saved checks. They need the pinned Python analysis dependencies and existing hash-bound private caches; they stop on missing files/digest drift. Do not fix a failure by overwriting historical receipts, malformed original label-support.json or source locks.

Fresh experiment replay is not authorized by this runbook. Original run modes are one-shot and their directories already exist. The failed phase09 full matrix cannot be silently resumed/retried, and this campaign's final timing is a separately frozen 2-method/one-repeat diagnostic. New corpus collection, thresholds, fits, target encoding, generator/tokenizer training, confirmation, contacts or submission require a new justified scope. Existing E3/E4/unallocated and 7,700 proposed-confirmation outcomes remain sealed.

Inspect the final report, closeout/requirements.json, phase-audit.json, confirmation-readiness.json, decision.json and original per-phase execution/failure/source archives together. Source hashes demonstrate byte preservation; they cannot reconstruct missing original process-state/resource observations or establish semantic quality guarantees.
"""
    return report,runbook

def run(commit):
    started=time.monotonic();lock,s=load();verify_campaign(ROOT,lock['campaign_reservation'])
    if git('rev-parse','HEAD')!=commit or git('branch','--show-current')!='main' or git('status','--porcelain') or git('ls-remote','origin','refs/heads/main').split()[0]!=commit:raise ValueError('Need clean pushed closeout lock')
    OUT.mkdir(parents=True,exist_ok=False);write_new(OUT/'started.json',dict(source_commit=commit,new_model_work=False));signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('Closeout wall cap')));signal.setitimer(signal.ITIMER_REAL,lock['wall_seconds'])
    try:
        with zipfile.ZipFile(OUT/'execution-sources.zip','x',compression=zipfile.ZIP_DEFLATED) as z:
            for p in s['source_sha256']:z.writestr(p,(ROOT/p).read_bytes())
            z.writestr('source-lock.json',json.dumps(s,indent=2))
        a=audit();write_new(OUT/'phase-audit.json',dict(phases=a['phases'],recorded_focused_passes=a['recorded_focused_tests'],fresh_whole_suite=False));write_new(OUT/'confirmation-readiness.json',a['readiness']);write_new(OUT/'requirements.json',a['requirements']);report,runbook=documents(a)
        for p,text in [(REPORT,report),(RUNBOOK,runbook)]:
            with p.open('x',encoding='utf-8',newline='\n') as f:f.write(text)
        if any(k=='torch' or k.startswith('torch.') or k=='transformers' or k.startswith('transformers.') for k in sys.modules):raise ValueError('Unexpected model framework')
        for k in ('source_sha256','protected_sha256','private_sha256'):hashes(s[k])
        if cpu()>lock['execution_cpu_cap_seconds'] or resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>lock['rss_bytes'] or sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file())>lock['artifact_bytes']:raise RuntimeError('Closeout resources')
        usage=usage_zero();usage.update(cpu_seconds=cpu()+lock['reporting_cpu_charge_seconds'],artifact_bytes=lock['artifact_bytes']);verify_campaign(ROOT,usage)
        write_new(OUT/'decision.json',dict(status='bounded_campaign_complete_negative_for_selected_controller',objective_branch='justified_negative_closeout',original_success_contract_established=False,quality_point_failure='BLEU',quality_point_loss=a['quality']['controller']['losses']['bleu'],margin=.5,Q0_passed=False,confirmation_ready=False,confirmation_released=False,original_phase09_matrix_complete=False,first_timing_diagnostic_complete=True,post_evaluation_refits=0,known_actual_model_attempts=a['known_actual_model_attempts'],failed_reservations_not_refunded=True,original_missing_receipts_preserved=True,no_more_campaign_models_or_data_branches=True))
        write_new(OUT/'execution.json',dict(status='complete',source_commit=commit,new_model_requests=0,new_checkpoint_loads=0,new_fits=0,new_reference_scores=0,new_reference_or_trajectory_body_reads=0,new_bootstrap_draws=0,new_simulations=0,recorded_focused_tests=a['recorded_focused_tests'],phases_audited=12,protected_files=len(s['protected_sha256']),private_digest_checks=len(s['private_sha256']),combined_campaign_public_private_bytes=a['combined_campaign_public_private_bytes'],report_sha256=sha(REPORT),runbook_sha256=sha(RUNBOOK),cpu_seconds_before_reporting_charge=cpu(),total_wall_seconds=time.monotonic()-started,max_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,campaign_usage=usage,paid_dollars=0,artifact_sha256={p.relative_to(OUT).as_posix():sha(p) for p in OUT.rglob('*') if p.is_file()}));print(json.dumps(record_phase(ROOT,'10-campaign-closeout','closeout/execution.json')),flush=True)
    except BaseException as error:
        write_new(OUT/'failure.json',dict(error=repr(error),campaign_usage=lock['campaign_reservation'],conservative_reservation_charge=True,automatic_retry=False));record_phase(ROOT,'10-campaign-closeout','closeout/failure.json');raise
    finally:signal.setitimer(signal.ITIMER_REAL,0)

def verify():
    lock,s=load();e=read(OUT/'execution.json');hashes({('results/quality_tolerant/campaign_20261029/closeout/'+p):h for p,h in e['artifact_sha256'].items()})
    if e['status']!='complete' or any(e[k] for k in ('new_model_requests','new_fits','new_reference_scores','new_reference_or_trajectory_body_reads','new_bootstrap_draws')) or sha(REPORT)!=e['report_sha256'] or sha(RUNBOOK)!=e['runbook_sha256']:raise ValueError('Incomplete closeout')
    a=audit();d=read(OUT/'decision.json')
    if d['status']!='bounded_campaign_complete_negative_for_selected_controller' or d['original_success_contract_established'] or a['campaign']['charged_usage']['confirmation_evaluations']:raise ValueError('Wrong closeout claim')
    print(json.dumps(dict(verified=True,objective_branch='negative_closeout',no_new_model_scoring_resampling=True,campaign=a['campaign'])))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=('run','verify'));p.add_argument('--commit');a=p.parse_args();run(a.commit) if a.mode=='run' else verify()
