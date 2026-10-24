"""Export static scientific figures from the frozen S1/S2 records only."""
from pathlib import Path
import json,hashlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'paper/stronger-research-v3/figures';OUT.mkdir(parents=True,exist_ok=True)
load=lambda p:json.loads(p.read_text(encoding='utf-8'))
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.edgecolor':'#666666','axes.labelcolor':'#222222','xtick.color':'#333333','ytick.color':'#333333','pdf.fonttype':42})
colors={'exploration':'#235B8D','development':'#A87420'};markers={'exploration':'o','development':'s'}
fig,ax=plt.subplots(figsize=(6.6,3.7));reviewed=[];i=0
for split in ['exploration','development']:
    r=load(ROOT/f'results/stronger_research/s1/{split}/result.json')
    for point in ['O0','O1','O2']:
        c=r['analysis']['comparisons'][point+'_vs_full'];v=100*c['estimated_reduction'];lo,hi=[100*x for x in c['conditional_reduction']['ci95']]
        ax.errorbar(v,i,xerr=[[v-lo],[hi-v]],fmt=markers[split],color=colors[split],capsize=3,markersize=6,linewidth=1.3)
        reviewed.append(dict(split=split,point=point,n=r['inputs'],estimate_percent=v,ci95_percent=[lo,hi]));i+=1
ax.set_yticks(range(6),[f"{r['split'].capitalize()} {r['point']} (n={r['n']})" for r in reviewed]);ax.invert_yaxis()
ax.axvline(0,color='#333333',linewidth=1);ax.axvline(5,color='#555555',linestyle='--',linewidth=1)
ax.set_xlabel('Assumed cost reduction vs full depth (%)');ax.grid(axis='x',color='#dddddd',linewidth=.6);ax.set_axisbelow(True)
ax.set_title('Conditional oracle-cost estimates',loc='left',fontweight='bold',fontsize=12,pad=10)
fig.tight_layout();fig.savefig(OUT/'conditional-cost.pdf',bbox_inches='tight');fig.savefig(OUT/'conditional-cost.png',dpi=220,bbox_inches='tight');plt.close(fig)
fig,axes=plt.subplots(1,2,figsize=(6.6,3.3));diagnosis=[]
for split in ['exploration','development']:
    r=load(ROOT/f'results/stronger_research/s2a/{split}.json');n=r['inputs'];x=list(range(1,11));y=[100*q['exact_final_text_matches']/n for q in r['levels'][:10]]
    axes[0].plot(x,y,color=colors[split],marker=markers[split],markersize=3.5,linewidth=1.3,label=f'{split.capitalize()} (n={n})',linestyle='-' if split=='exploration' else '--')
    xx=[q['to'] for q in r['adjacent']];yy=[100*q['damaged']/q['transitions'] for q in r['adjacent']]
    axes[1].plot(xx,yy,color=colors[split],marker=markers[split],markersize=3.5,linewidth=1.3,linestyle='-' if split=='exploration' else '--')
    diagnosis.append(dict(split=split,n=n,early_levels=x,final_visible_match_percent=y,transition_to_levels=xx,chrf_decrease_percent=yy))
axes[0].set(title='Early visible text equals final',xlabel='Prefix level (before final)',ylabel='Inputs (%)',ylim=(0,25),xticks=[1,3,5,7,9,10])
axes[1].set(title='Adjacent chrF decreases',xlabel='Transition destination level',ylabel='Transitions (%)',ylim=(0,35),xticks=[2,4,6,8,10,11])
for ax in axes:ax.grid(axis='y',color='#dddddd',linewidth=.6);ax.set_axisbelow(True)
handles,labels=axes[0].get_legend_handles_labels();fig.legend(handles,labels,loc='lower center',ncol=2,frameon=False,fontsize=9,bbox_to_anchor=(.5,-.02))
fig.tight_layout(rect=(0,.07,1,1));fig.savefig(OUT/'saved-diagnostics.pdf',bbox_inches='tight');fig.savefig(OUT/'saved-diagnostics.png',dpi=220,bbox_inches='tight');plt.close(fig)
(OUT/'reviewed-data.json').write_text(json.dumps({'conditional_cost':reviewed,'diagnostics':diagnosis,'sources':['results/stronger_research/s1/{split}/result.json','results/stronger_research/s2a/{split}.json'],'uncertainty':'Cost intervals are conditional fixed-assignment bootstrap; diagnosis curves descriptive without bands','actual_latency_for_oracle':'unavailable'},indent=2)+'\n')
print('Exported 2 vector PDF figures and PNG previews from reviewed saved results.')

fig,axes=plt.subplots(1,2,figsize=(6.6,3.1));frontier=[]
for split in ['exploration','development']:
    r=load(ROOT/f'results/stronger_research/s1/{split}/result.json');codes=[sum([1,4,8,14,20,26,32,40,48,56,64][:q['depth']]) for q in r['fixed_depths']]
    found=r['assignments']['O1']
    for ax,metric,title in zip(axes,['bleu','chrf'],['Corpus BLEU','Corpus chrF']):
        yy=[q['metrics'][metric] for q in r['fixed_depths']]
        ax.plot(codes,yy,color=colors[split],marker=markers[split],markersize=3,linewidth=1.2,linestyle='-' if split=='exploration' else '--')
        ax.scatter([found['mean_codes']],[found['metrics'][metric]],marker='*',s=100,color=colors[split],edgecolors='#222222',linewidths=.5,zorder=4)
        ax.set(title=title,xlabel='Mean generated code positions',ylabel='Score (0-100)',xlim=(0,325),ylim=(0,25 if metric=='bleu' else 55),xticks=[0,100,200,300]);ax.grid(color='#dddddd',linewidth=.6);ax.set_axisbelow(True)
    frontier.append({'split':split,'fixed_codes':codes,'fixed_bleu':[q['metrics']['bleu'] for q in r['fixed_depths']],'fixed_chrf':[q['metrics']['chrf'] for q in r['fixed_depths']],'found_o1_mean_codes':found['mean_codes'],'found_o1_bleu':found['metrics']['bleu'],'found_o1_chrf':found['metrics']['chrf']})
fig.text(.5,-.02,'Blue circles: exploration; gold squares: development; stars: found O1 assignments',ha='center',fontsize=8)
fig.tight_layout();fig.savefig(OUT/'quality-work.pdf',bbox_inches='tight');fig.savefig(OUT/'quality-work.png',dpi=220,bbox_inches='tight');plt.close(fig)
d=load(OUT/'reviewed-data.json');d['quality_work']=frontier;(OUT/'reviewed-data.json').write_text(json.dumps(d,indent=2)+'\n')
