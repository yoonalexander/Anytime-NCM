"""Synthetic checks of S2A denominators and retrospective match labels."""
import importlib.util
from pathlib import Path
import pytest
spec=importlib.util.spec_from_file_location('s2a',Path(__file__).resolve().parents[1]/'scripts/run_stronger_s2a.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

def test_final_agreement_visible_and_ids_separate_and_transitions_counted():
    levels=[dict(level=k,ids=[k]*64,text=('no 12 apples' if k>=10 else 'apples')) for k in range(1,12)]
    r=module.diagnose([dict(identity='a',index=0,levels=levels)],['no 12 apples'],[10])
    assert r['states']==11 and r['transitions']==10
    assert r['ever_early_final_text_match']==1 and r['ever_early_final_ids_match']==0
    assert r['identities'][0]['first_early_text_match']==10
    assert r['numeric_reference_coverage']==1 and r['persistent_numeric_cue_miss_inputs']==0
    assert r['o1_mean_sentence_chrf_change']==0

def test_persistent_cues_and_empty_reference_word_coverage():
    levels=[dict(level=k,ids=[0]*64,text='a different answer') for k in range(1,12)]
    r=module.diagnose([dict(identity='a',index=0,levels=levels)],['not 37'],[11])
    assert r['persistent_numeric_cue_miss_inputs']==r['persistent_negation_cue_miss_inputs']==1
    empty=module.diagnose([dict(identity='a',index=0,levels=levels)],[''],[11])
    assert empty['levels'][0]['reference_word_recall_macro'] is None and empty['levels'][0]['word_coverage']==0
