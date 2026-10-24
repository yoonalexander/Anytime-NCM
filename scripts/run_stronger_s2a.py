"""One prospectively frozen pass over already-exposed WMT data for S2A."""
import os,sys,time,re,resource
from pathlib import Path
for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[name]='4'
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
import numpy as np
from sacrebleu.metrics import CHRF
from anytime_ncm.stronger_s1 import read,save,sha,selective_rows,validate_rows,validate_population,INVENTORY
from anytime_ncm.wmt_data import StringRows
from anytime_ncm.wmt_policy import cues

def diagnose(rows,refs,exits):
    metric=CHRF();states=[];identities=[];covered=0;persistent_num=0;required_neg=0;persistent_neg=0
    for row,ref,exit_level in zip(rows,refs,exits,strict=True):
        words=set(re.findall(r'\b\w+\b',ref.casefold()));numbers,neg=cues(ref);covered+=bool(numbers);required_neg+=neg
        quality=[];recall=[];all_nums=set();any_neg=False;matches=[];idmatches=[]
        for state in row['levels']:
            quality.append(metric.sentence_score(state['text'],[ref]).score)
            hyp_words=set(re.findall(r'\b\w+\b',state['text'].casefold()));recall.append(len(words&hyp_words)/len(words) if words else None)
            nums,n=cues(state['text']);all_nums.update(nums);any_neg|=n
            matches.append(state['text']==row['levels'][-1]['text']);idmatches.append(state['ids']==row['levels'][-1]['ids'])
        persistent_num+=bool(set(numbers)-all_nums);persistent_neg+=neg and not any_neg
        identities.append({'identity':row['identity'],'index':row['index'],'sentence_chrf_by_level':quality,'reference_word_recall_by_level':recall,
           'text_equals_final_by_level':matches,'ids_equal_final_by_level':idmatches,'first_early_text_match':next((k for k,v in enumerate(matches[:10],1) if v),None),
           'numeric_reference':bool(numbers),'persistent_missing_numeric_cue':bool(set(numbers)-all_nums),'negation_reference':neg,'persistent_missing_negation_cue':neg and not any_neg,
           'final_negation_cue_mismatch':cues(row['levels'][-1]['text'])[1]!=neg,'o1_exit':exit_level,'o1_minus_full_sentence_chrf':quality[exit_level-1]-quality[-1]})
    levels=[];transitions=[]
    for k in range(11):
        vals=[r['reference_word_recall_by_level'][k] for r in identities if r['reference_word_recall_by_level'][k] is not None]
        levels.append({'level':k+1,'inputs':len(rows),'reference_word_recall_macro':float(np.mean(vals)) if vals else None,'word_coverage':len(vals),
           'exact_final_text_matches':sum(r['text_equals_final_by_level'][k] for r in identities),'exact_final_ids_matches':sum(r['ids_equal_final_by_level'][k] for r in identities)})
        if k:
            delta=np.array([r['sentence_chrf_by_level'][k]-r['sentence_chrf_by_level'][k-1] for r in identities])
            transitions.append({'from':k,'to':k+1,'transitions':len(rows),'improved':int((delta>1e-12).sum()),'damaged':int((delta< -1e-12).sum()),'unchanged':int((np.abs(delta)<=1e-12).sum()),'mean_sentence_chrf_change':float(delta.mean())})
    return {'inputs':len(rows),'states':len(rows)*11,'transitions':len(rows)*10,'levels':levels,'adjacent':transitions,'ever_early_final_text_match':sum(r['first_early_text_match'] is not None for r in identities),
        'ever_early_final_ids_match':sum(any(r['ids_equal_final_by_level'][:10]) for r in identities),'numeric_reference_coverage':covered,'persistent_numeric_cue_miss_inputs':persistent_num,
        'negation_reference_coverage':required_neg,'persistent_negation_cue_miss_inputs':persistent_neg,'final_negation_mismatches':sum(r['final_negation_cue_mismatch'] for r in identities),
        'o1_mean_sentence_chrf_change':float(np.mean([r['o1_minus_full_sentence_chrf'] for r in identities])),'identities':identities}

def main():
    start=time.monotonic();out=ROOT/'results/stronger_research/s2a';assert not out.exists(),'No silent diagnosis replay';out.mkdir(parents=True)
    receipt={'status':'started','new_model_calls':0,'new_fits':0,'new_final_outcomes':0,'protocol_sha256':sha(ROOT/'docs/studies/stronger-research-s2a-protocol.md'),'source_sha256':sha(Path(__file__))};save(out/'execution.json',receipt)
    try:
        pop=validate_population(read(ROOT/'docs/partitions/wmt14-phase4.json'),read(ROOT/INVENTORY));result={}
        for split,selected in pop.items():
            s1=read(ROOT/f'results/stronger_research/s1/{split}/result.json')
            rows,skipped=selective_rows(ROOT/'results/phase4/wmt14/trajectories.jsonl',selected,split,pop);validate_rows(rows)
            refs=StringRows((ROOT/'data/wmt14/reference_translations.pickle').read_bytes()).select({r['index'] for r in selected})
            result[split]=diagnose(rows,[refs[r['index']] for r in rows],s1['assignments']['O1']['exits'])
            save(out/(split+'.json'),result[split])
        assert sum(r['states'] for r in result.values())==2112 and sum(r['transitions'] for r in result.values())==1920
        receipt.update(status='complete',seconds=time.monotonic()-start,max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            input_hashes={n:sha(ROOT/n) for n in ['results/phase4/wmt14/trajectories.jsonl','data/wmt14/reference_translations.pickle','results/stronger_research/s1/exploration/result.json','results/stronger_research/s1/development/result.json']})
        assert receipt['seconds']<7200 and receipt['max_rss_kib']<2*1024*1024
        assert sum(p.stat().st_size for p in out.rglob('*') if p.is_file())<256*1024*1024
        assert 'torch' not in sys.modules
    except Exception as error:receipt.update(status='failed',error=repr(error));raise
    finally:save(out/'execution.json',receipt)
    print({s:{k:v for k,v in r.items() if k not in ('identities','levels','adjacent')} for s,r in result.items()})
if __name__=='__main__':main()
