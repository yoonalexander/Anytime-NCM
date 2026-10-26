"""Verify planning artifacts only; never decode source/reference/outcome bodies."""
from pathlib import Path
import hashlib,json,math,re
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'results/quality_tolerant/population_design'
def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()
def verify():
    checks=0
    def need(v,message):
        nonlocal checks
        if not v:raise AssertionError(message)
        checks+=1
    source=json.loads((OUT/'source-lock.json').read_text())
    for rel,h in source['protected_sha256'].items():need(sha(ROOT/rel)==h,'Historical hash: '+rel)
    for rel,h in source['read_aggregate_and_document_sha256'].items():need(sha(ROOT/rel)==h,'Evidence hash: '+rel)
    base=ROOT/'docs/studies/quality-tolerant';config=json.loads((base/'population-design.json').read_text());decision=json.loads((OUT/'decision.json').read_text());a=json.loads((OUT/'analytic-feasibility.json').read_text())
    need(config['margins']==dict(bleu=.5,chrf=1.,numeric_reference_f1=.02,negation_mismatch=.02),'Margins unchanged')
    need(config['alpha']==dict(claim=.025,exclusions_total=.025,exclusion_each=.000625,numerical_additional=.001),'Multiplicity unchanged')
    need([x['year'] for x in config['candidate_frame']]==list(range(2015,2021)),'Bounded candidate frame')
    need(all(x['status']=='candidate_not_audited' for x in config['candidate_frame']),'No eligibility claim')
    need(all(v==0 for v in config['current_execution'].values()),'No empirical/synthetic work')
    need(all(v is False for v in config['gates'].values()),'No automatic release')
    need(decision['design_complete'] and not decision['statistical_feasibility_passed'] and not decision['Q2_started'] and not decision['reserved_outputs_released'],'Decision scope')
    caps=config['future_caps_proposed_only']
    need(caps['q2_timed_requests']==256*12*2*2,'Timed request cap')
    need(caps['q2_total_requests']==caps['q2_timed_requests']+caps['q2_warmups']+caps['q2_trajectory_requests'],'Total request cap')
    need(caps['q2_generator_levels']==caps['q2_decoder_invocations']==11*caps['q2_total_requests'],'Worst-case work cap')
    coefficient=7*math.log(4/a['claim_alpha'])/(3*.02)
    need(abs(coefficient-a['coverage_coefficient_per_M'])<1e-10,'Independent analytical coefficient')
    need(abs(coefficient*config['component_max_unique_inputs']-a['necessary_coverage_strict_lower_bound'])<1e-8,'Reference obstruction arithmetic')
    need(a['necessary_coverage_strict_lower_bound']>caps['metadata_pairs'],'Reference method infeasible under cap')
    docs=[base/'population-and-cluster-design.md',OUT/'README.md',ROOT/'docs/studies/quality-tolerant-translation-roadmap.md']
    for path in docs:
        for target in re.findall(r'\]\(([^)]+)\)',path.read_text(encoding='utf-8')):
            if '://' not in target:need((path.parent/target.split('#')[0]).exists(),'Missing link: '+target)
    completion=OUT/'completion.json'
    if completion.exists():
        r=json.loads(completion.read_text())
        for rel,h in r['artifact_sha256'].items():need(sha(ROOT/rel)==h,'Design artifact hash: '+rel)
    return dict(verified=True,checks=checks,historical_files_preserved=len(source['protected_sha256']),new_source_reference_outcome_body_decodes=0,new_model_requests=0,new_simulations=0,scope='planning artifacts, deterministic arithmetic and streaming preservation hashes only')
if __name__=='__main__':print(json.dumps(verify()))
