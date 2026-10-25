"""Static review figures from saved aggregate receipts only; no outcome loaders."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'paper/stronger-research-v4/figures'
OUT.mkdir(parents=True,exist_ok=True)
read=lambda p:json.loads((ROOT/p).read_text())
e2=read('results/evidence_gaps/e2/analysis.json')
terminal=read('results/evidence_gaps/e2_terminal_screen/analysis.json')
for name in ('quality-latency.pdf','quality-latency.png','exact-depths.pdf','exact-depths.png','reviewed-data.json'):
    if (OUT/name).exists():raise FileExistsError('Preserve original figure export: '+name)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42})
fig,axes=plt.subplots(1,2,figsize=(10,3.7),layout='constrained')
x=[e2['methods'][f'fixed:{d}']['mean_ms'] for d in range(1,12)]
for ax,metric,label in zip(axes,('bleu','chrf'),('Corpus BLEU','Corpus chrF'),strict=True):
    y=[e2['quality'][f'fixed:{d}']['metrics'][metric] for d in range(1,12)]
    ax.plot(x,y,'o-',color='#436784',markersize=4,label='Fixed terminal depths')
    ax.scatter([e2['methods']['exact']['mean_ms']],[y[-1]],marker='D',color='#bb622f',s=42,zorder=4,label='Exact, every-level (E2)')
    ax.scatter([terminal['methods']['terminal_exact']['mean_ms']],[y[-1]],marker='s',facecolor='white',edgecolor='#247567',linewidth=1.5,s=44,zorder=5,label='Assembled terminal (post hoc)')
    for i in (0,5,9,10):ax.annotate(str(i+1),(x[i],y[i]),xytext=(3,-13 if i==9 else 6),textcoords='offset points',fontsize=8)
    ax.set(xlabel='Mean ready-output latency (ms)',ylabel=label,xlim=(8,155))
    ax.grid(axis='y',alpha=.18)
axes[0].legend(loc='upper left',fontsize=8,frameon=False)
fig.savefig(OUT/'quality-latency.pdf');fig.savefig(OUT/'quality-latency.png',dpi=180);plt.close(fig)
fig,ax=plt.subplots(figsize=(8,2.8),layout='constrained')
depths=list(range(1,12));counts=[e2['exact_depth_counts'][str(d)] for d in depths]
bars=ax.bar(depths,counts,color=['#436784']*10+['#90979b'],width=.72)
for bar,n in zip(bars,counts,strict=True):
    if n:ax.text(bar.get_x()+bar.get_width()/2,n+3,str(n),ha='center',fontsize=9)
ax.set(xlabel='Earliest exact-final-text level',ylabel='Audit inputs',xticks=depths,ylim=(0,240))
ax.text(.02,.91,'43/256 exit before level 11; mean depth 10.684',transform=ax.transAxes,fontsize=10)
ax.grid(axis='y',alpha=.15);ax.set_axisbelow(True)
fig.savefig(OUT/'exact-depths.pdf');fig.savefig(OUT/'exact-depths.png',dpi=180);plt.close(fig)
with (OUT/'reviewed-data.json').open('x') as f:
    json.dump(dict(population='256 consumed E2 audit groups',fixed_mean_ms=x,fixed_quality={m:[e2['quality'][f'fixed:{d}']['metrics'][m] for d in depths] for m in ('bleu','chrf')},exact_mean_ms=e2['methods']['exact']['mean_ms'],assembled_terminal_mean_ms=terminal['methods']['terminal_exact']['mean_ms'],exact_depth_counts=e2['exact_depth_counts'],post_hoc_terminal=True,new_model_calls=0),f,indent=2);f.write('\n')
print('Exported two PDF/PNG figures from saved E2/screen aggregate receipts only.')
