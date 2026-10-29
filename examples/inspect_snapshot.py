"""Print saved aggregate research results; no models, datasets or GPU required."""
from anytime_ncm.snapshot import load_snapshot
snapshot=load_snapshot()
e=snapshot['latest_evaluation']
print(snapshot['outcome'])
print(f"{e['inputs']} inputs; {100*e['mean_saving']:.2f}% mean time saved; BLEU loss {e['quality_losses']['bleu']:.3f} / 0.5 allowed.")
print('Quality-and-latency success established:',e['original_success_contract_established'])
