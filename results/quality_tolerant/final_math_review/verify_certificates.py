"""Verify fixed rational certificates only; no profile decode/optimizer/grid replay."""
from fractions import Fraction as F
from pathlib import Path
import hashlib,json,math,re,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'results/quality_tolerant/final_math_review'
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def frac(v):return F(v['numerator'])/F(v['denominator'])
def verify():
    checked=0
    def need(v,label):
        nonlocal checked
        if not v:raise AssertionError(label)
        checked+=1
    execution=read(OUT/'execution.json');lock=read(ROOT/'docs/studies/quality-tolerant/final-math-review-lock.json')
    for key,base in [('source_sha256',ROOT),('protected_sha256',ROOT),('artifact_sha256',OUT)]:
        for p,h in execution[key].items():need(sha(base/p)==h,'Frozen hash '+p)
    counts={k:0 for k in execution['counts']}
    for line in (OUT/'ledger.jsonl').read_text(encoding='utf-8').splitlines():
        e=json.loads(line);counts[e['kind']]+=e['amount'];need(counts[e['kind']]==e['total'],'Ledger counter')
    need(counts==execution['counts'],'Ledger/receipt parity')
    for k,n in counts.items():need(n<=lock['limits'][k],'Frozen allocation')
    need(counts['profile_decodes']==1 and counts['profile_vectors']==4 and counts['weight_values']==1488,'One metadata release')
    results=read(OUT/'exact-results.json');weights=read(OUT/'weight-distributions.json')['profiles']
    for name,result in results.items():
        c=sorted([int(k) for k,n in weights[name].items() for _ in range(n)],reverse=True);C=sum(c)
        need(len(c)==result['J'] and C==result['total_count'] and max(c)==result['max_count'],'Anonymous profile totals')
        for case in result['cases']:
            d=frac(case['delta']);active=case['active_counts'];ps=[frac(x) for x in case['active_event_probabilities']];tau=frac(case['tau_count_units'])
            need(active==c[:len(active)] and len(ps)==len(active),'Active prefix certificate')
            need(all(x>tau for x in active) and all(x<=tau for x in c[len(active):]),'Complementary active/inactive inequalities')
            need(all(p==1-tau/x and 0<p<1 for x,p in zip(active,ps)),'Stationarity and feasibility')
            need(sum((F(x,C)*p for x,p in zip(active,ps)),F(0))==d,'Exact outside/precision mean constraint')
            q=math.prod((1-p for p in ps),start=F(1));need(q==frac(case['sharp_all_zero_probability']),'Exact product certificate')
            need(case['exceeds_primary_alpha']==(q>F(1,40)),'Exact alpha comparison')
            need(frac(case['randomized_zero_rejection_upper'])==min(F(1),F(1,40)/q),'Randomized zero-rejection limit')
            # An independent feasible witness suffices even without global optimality.
            witness=case['simple_top_k_witness'];k=witness['k'];T=sum(c[:k]);p=frac(witness['event_probability']);simpleq=(1-p)**k
            need(witness['active_counts']==c[:k] and T==witness['count_total'],'Simple top-count certificate')
            need(F(T,C)*p==d and simpleq==frac(witness['all_zero_probability']),'Independent exact null witness')
            need(simpleq<=q,'Witness does not exceed certified optimum')
            if name.startswith('confirmation_') and d==F(201,10000):
                need(simpleq>F(1,40) and simpleq>F(1,20),'Strict outside-margin counterexample at both alphas')
                need(F(1,40)/q<F(4,5),'Zero-alternative rejection cap below80 percent')
        for root in result['sharp_zero_brackets'].values():
            lo=frac(root['lower']);hi=frac(root['upper']);need(hi-lo==frac(root['width'])==F(1,2**64),'Recorded exact root width')
            need(0<lo<hi<1 and root['steps']==64,'Root range/allocation')
        need(frac(result['sharp_zero_brackets']['1/40']['upper'])<F(str(result['largest_cap_zero_upper'])),'Full weights tighten reference')
    validation=read(OUT/'deterministic-validation.json');need(sum(x['points'] for x in validation['grids'])==16093 and all(x['passed'] for x in validation['grids']),'Recorded coarse validation allocation')
    for example in validation['target_counterexamples']:
        probs=list(map(frac,example['probabilities']));ds=list(map(frac,example['per_input_losses']));cs=example['counts']
        direct=sum((p*d for p,d in zip(probs,ds)),F(0));ratio=sum((p*c*d for p,c,d in zip(probs,cs,ds)),F(0))/sum((p*c for p,c in zip(probs,cs)),F(0))
        need(direct==frac(example['expected_realized_ratio']) and ratio==frac(example['ratio_of_expected_totals']) and direct!=ratio,'Target distinction exact algebra')
    tests=ET.parse(OUT/'focused-tests.xml');need(len(tests.findall('.//testcase'))==27 and not tests.findall('.//failure') and not tests.findall('.//error'),'27 deterministic tests')
    d=read(OUT/'decision.json');need(d['status']=='close_current_zero_loss_confirmatory_route' and not d['Q0_passed'] and not d['Q2_authorized'] and not d['reserved_outputs_released'],'No-go scope preserved')
    for p in [ROOT/'docs/studies/quality-tolerant/final-math-review-results.md',ROOT/'docs/studies/quality-tolerant-translation-roadmap.md',OUT/'README.md']:
        for target in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf-8')):
            if '://' not in target:need((p.parent/target.split('#')[0]).exists(),'Local evidence link')
    completion=OUT/'completion.json'
    if completion.exists():
        for p,h in read(completion)['artifact_sha256'].items():need(sha(ROOT/p)==h,'Completion hash')
    return dict(verified=True,checks=checked,private_profile_decodes=0,optimizations_replayed=0,grids_replayed=0,exact_threshold_certificates=12,tests=27,model_requests=0)
if __name__=='__main__':print(json.dumps(verify()))
