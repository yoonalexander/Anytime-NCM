"""Local artifact/arithmetic verification; no dataset parse or simulation replay."""
import hashlib,json,math,re,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'results/quality_tolerant/eligibility_audit'
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def verify():
    checks=0
    def need(v,label):
        nonlocal checks
        if not v:raise AssertionError(label)
        checks+=1
    first=load(OUT/'execution.json');last=load(OUT/'metadata_correction/execution.json')
    for record,directory in [(first,OUT),(last,OUT/'metadata_correction')]:
        for name,base in [('source_sha256',ROOT),('protected_sha256',ROOT),('artifact_sha256',directory)]:
            for p,h in record[name].items():need(sha(base/p)==h,'Frozen artifact: '+p)
    counts={k:0 for k in first['counts']}
    for directory,record in [(OUT,first),(OUT/'metadata_correction',last)]:
        for line in (directory/'ledger.jsonl').read_text().splitlines():
            event=json.loads(line);counts[event['kind']]+=event['amount'];need(counts[event['kind']]==event['total'],'Ledger total')
        need(counts==record['counts'],'Cumulative receipt counters')
    need(last['counts']['synthetic_datasets']==48000 and last['new_synthetic_datasets']==0,'No simulation replay')
    methods=load(OUT/'method-results.json');need(len(methods['scenarios'])==24 and methods['datasets']==48000 and methods['null_sanity_checks_passed'],'Frozen synthetic grid')
    need(sha(OUT/'method-results.json')==sha(OUT/'metadata_correction/method-results.json'),'Copied method result byte parity')
    for s in methods['scenarios']:
        need(s['joint_two_cue_NI']['trials']==2000,'Case allocation')
        if s['risk']>=.02:
            for ep in s['endpoints'].values():need(ep['NI']['rate']<=.025,'Observed null sanity')
    inventory=load(OUT/'metadata_correction/population-summary.json');manifest=load(OUT/'metadata_correction/split-manifest.json');acq=load(OUT/'metadata_correction/acquisition.json');d=load(OUT/'completion-decision.json')
    need(len(acq['archives'])==6 and sum(x['rows'] for x in acq['archives'])==inventory['candidate_rows']==13955,'Six-frame count')
    need(sum(x['archive_bytes'] for x in acq['archives'])==last['counts']['download_bytes'],'Unique archive transport bytes')
    need(inventory['candidate_rows']-inventory['aliases_removed']-sum(inventory['excluded_canonical_inputs'].values())==len(manifest),'Alias/exclusion accounting')
    need(len({(x['year'],x['index']) for x in manifest})==len(manifest),'Unique canonical source records')
    need(len({x['identity'] for x in manifest})==len(manifest),'Unique effective prefixes')
    components={}
    for x in manifest:
        need(set(x)=={'year','index','identity','component','role'},'Source-only public manifest')
        components.setdefault(x['component'],set()).add(x['role'])
    need(all(len(v)==1 for v in components.values()),'Whole-component split isolation')
    for role,data in inventory['roles'].items():
        need(sum(x['role']==role for x in manifest)==data['inputs'],'Role input count')
        need(sum(role in v for v in components.values())==data['components'],'Role component count')
        for name,J,b in [('numeric_zero_adverse_KL_upper',data['covered_components'],data['max_numeric_component_fraction']),('negation_zero_adverse_KL_upper',data['components'],data['max_input_component_fraction'])]:
            exact=min(1,J*b*(-math.expm1(math.log(.025)/J)))
            need(abs(exact-data[name])<1e-12,'Independent zero-loss arithmetic')
            need(exact>.02,'No-go retained')
    need(inventory['roles']['confirmation']['max_input_component_fraction']>.01 and not inventory['operational_screen_passed'],'Frozen concentration-screen failure')
    need(not d['Q0_passed'] and not d['Q2_ready'] and not d['Q2_started'] and not d['reserved_outputs_released'],'No phase release')
    cases=0
    for path in [OUT/'focused-tests.xml',OUT/'metadata_correction/focused-tests.xml']:
        xml=ET.parse(path);need(not xml.findall('.//failure') and not xml.findall('.//error'),'Passing tests');cases+=len(xml.findall('.//testcase'))
    need(cases==48,'36+12 focused tests')
    for p in [ROOT/'docs/studies/quality-tolerant/eligibility-audit-results.md',ROOT/'docs/studies/quality-tolerant-translation-roadmap.md',OUT/'README.md']:
        for target in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf-8')):
            if '://' not in target:need((p.parent/target.split('#')[0]).exists(),'Local evidence link')
    completion=OUT/'completion.json'
    if completion.exists():
        for p,h in load(completion)['artifact_sha256'].items():need(sha(ROOT/p)==h,'Completion hash')
    return dict(verified=True,checks=checks,tests=cases,synthetic_datasets=48000,new_synthetic_datasets=0,new_dataset_or_model_body_decodes=0,source_only_manifest_records_checked=len(manifest),Q2_ready=False)
if __name__=='__main__':print(json.dumps(verify()))
