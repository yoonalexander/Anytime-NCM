"""Render presentation-only figures from frozen public aggregates (no research)."""
import json,hashlib
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch,FancyArrowPatch
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'docs/assets';OUT.mkdir(exist_ok=True)
s=json.loads((ROOT/'src/anytime_ncm/snapshot.json').read_text());e=s['latest_evaluation']
for item in s['sources']:
    if hashlib.sha256((ROOT/item['path']).read_bytes()).hexdigest()!=item['sha256']:raise ValueError('Figure source drift')
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none','savefig.facecolor':'white'})
blue='#315b8a';orange='#b56d21';ink='#233344';quiet='#687787'
fig,axes=plt.subplots(1,2,figsize=(13.5,5.8),gridspec_kw={'width_ratios':[1,1.35]});fig.subplots_adjust(left=.09,right=.93,top=.77,bottom=.26,wspace=.55)
fig.suptitle('Earlier output saved time, but missed the quality tolerance',x=.06,y=.97,ha='left',fontsize=19,fontweight='bold',color=ink)
fig.text(.06,.88,'Frozen controller \u00b7 1,188 development-evaluation inputs \u00b7 315 early exits',color=quiet,fontsize=11)
a=axes[0];values=[e['full_mean_ms'],e['controller_mean_ms']];a.bar([0,1],values,color=['#e2e8ef',blue],edgecolor=[ink,blue],width=.55);a.set_xticks([0,1],['Native full','Early-stop rule']);a.set_ylim(0,165);a.set_ylabel('Mean ready-output time (ms)');a.set_title('Actual complete request latency',loc='left',fontsize=12,pad=18)
for i,v in enumerate(values):a.text(i,v+4,f'{v:.3f} ms',ha='center',color=ink,fontweight='bold')
lo,hi=e['conditional_nominal_saving_interval'];a.text(.5,.95,f"{100*e['mean_saving']:.2f}% mean time saved",transform=a.transAxes,ha='center',fontsize=11,color=blue)
a.text(.5,-.24,f'Conditional paired interval: {100*lo:.2f}%\u2013{100*hi:.2f}%',transform=a.transAxes,ha='center',fontsize=9,color=quiet)
b=axes[1];keys=['bleu','chrf','numeric_reference_f1','negation_cue_mismatch_rate'];labels=['Corpus BLEU','Corpus chrF','Numeric F1','Negation mismatch'];ratios=[e['quality_losses'][k]/e['quality_margins'][k] for k in keys];b.barh(range(4),ratios,color=[orange,blue,blue,blue],height=.5);b.set_yticks(range(4),labels);b.invert_yaxis();b.set_xlim(0,1.65);b.axvline(1,color=ink,linestyle='--',linewidth=1.2);b.set_title('Quality loss relative to its allowed margin',loc='left',fontsize=12,pad=18);b.set_xlabel('Loss \u00f7 allowed loss (point-feasible at \u22641)')
for i,k in enumerate(keys):
    v=e['quality_losses'][k];m=e['quality_margins'][k];text=(f'{v:.3f}' if i<2 else f'{v:.5f}')+f' / {m:g}'+('  FAIL' if i==0 else '')
    b.text(ratios[i]+.025,i,text,va='center',fontsize=9,color=orange if i==0 else ink)
fig.text(.06,.1,'Quality values are corpus points, not noninferiority bounds. Two processes; one timed repeat per input/method/session.',fontsize=9,color=quiet)
fig.text(.06,.055,'Controller/full diagnostic only. Original full comparison matrix incomplete; feasible fixed-depth frontier unestablished.',fontsize=9,color=quiet)
fig.savefig(OUT/'results.svg');fig.savefig(OUT/'results.png',dpi=160);plt.close(fig)
fig,ax=plt.subplots(figsize=(13.5,4.8));ax.set_xlim(0,13.5);ax.set_ylim(0,4.8);ax.axis('off');fig.subplots_adjust(0,0,1,1)
ax.text(.5,4.34,'Observe the current prefix. Stop only on current information.',fontsize=18,fontweight='bold',color=ink)
ax.text(.5,3.87,'ARCHITECTURE ILLUSTRATION \u00b7 frozen checkpoint \u00b7 no reference/future outcome enters the online decision',fontsize=9,color=quiet)
boxes=[(.5,'Input','Source text / puzzle'),(3.65,'Frozen NCM','Generate next code level'),(6.8,'Current prefix','Reconstruct + decode'),(9.95,'Causal rule','Stop now or continue')]
for x,title,body in boxes:
    patch=FancyBboxPatch((x,2.15),2.7,1.14,boxstyle='round,pad=0.03,rounding_size=0.12',facecolor='#eff3f7',edgecolor=blue,linewidth=1.2);ax.add_patch(patch);ax.text(x+.16,2.93,title,fontsize=13,fontweight='bold',color=ink);ax.text(x+.16,2.49,body,fontsize=10,color=quiet)
for x in [3.2,6.35,9.5]:ax.add_patch(FancyArrowPatch((x,2.72),(x+.4,2.72),arrowstyle='-|>',mutation_scale=13,color=blue,linewidth=1.3))
ax.annotate('',xy=(5.,3.4),xytext=(11.3,3.4),arrowprops=dict(arrowstyle='->',connectionstyle='arc3,rad=.08',color=orange,linewidth=1.2));ax.text(7.1,3.44,'continue generation',fontsize=9,color=orange)
ax.text(10.15,1.77,'or return the current output',fontsize=10,color=orange)
ax.plot([.5,13],[1.4,1.4],color='#c7d1dc',linestyle='--',linewidth=1)
ax.text(.5,1.02,'OFFLINE EVIDENCE',fontsize=10,fontweight='bold',color=ink);ax.text(3.2,1.02,'Recorded outputs + references \u2192 corpus quality and paired timing audit',fontsize=11,color=quiet)
ax.text(.5,.5,'Actual skipped work, intermediate/final parity, immutable source locks and preserved failed gates.',fontsize=10,color=quiet)
fig.savefig(OUT/'architecture.svg');fig.savefig(OUT/'architecture.png',dpi=160);plt.close(fig)
(OUT/'sources.json').write_text(json.dumps(dict(results_graphic='Saved aggregate execution evidence, presentation only; no new inference or statistics.',architecture='Original illustration; not an execution trace or proof of effectiveness.',sources=s['sources'],population=e['inputs'],timing_interval_meaning='Conditional nominal paired component bootstrap on two observed sessions',quality_uncertainty='No noninferiority confidence bounds established'),indent=2)+'\n',encoding='utf-8')
print('Rendered docs/assets/results and architecture SVG/PNG from pinned aggregates')

for svg in OUT.glob("*.svg"):
    svg.write_text("\n".join(line.rstrip() for line in svg.read_text(encoding="utf-8").splitlines())+"\n",encoding="utf-8",newline="\n")
