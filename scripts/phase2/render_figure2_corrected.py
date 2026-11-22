from pathlib import Path
import json, os
os.environ['MPLCONFIGDIR']=str(Path(__file__).resolve().parent/'mpl_cache')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib.lines import Line2D
from matplotlib.ticker import MultipleLocator
import numpy as np
import pandas as pd
from scipy import stats
from PIL import Image

OUT=Path(__file__).resolve().parent/'figure2_corrected_scores';OUT.mkdir(exist_ok=True)
WORK=Path(__file__).resolve().parent/'inputs'
plt.rcParams.update({'font.family':'Arial','font.size':8,'svg.fonttype':'none','pdf.fonttype':42,'ps.fonttype':42,'axes.linewidth':.65,'xtick.major.width':.6,'ytick.major.width':.6,'text.color':'#333333','axes.labelcolor':'#333333','axes.edgecolor':'#c3c2b7','xtick.color':'#465568','ytick.color':'#333333'})
NAVY='#333333';BLUE='#1c5cab';TEAL='#168277';ORANGE='#c96a2e';GREY='#D9E0E6';LIGHT='#F4F7F9'

def export(fig,stem):
    fig.savefig(OUT/(stem+'.pdf'),facecolor='white')
    fig.savefig(OUT/(stem+'.svg'),facecolor='white')
    fig.savefig(OUT/(stem+'.png'),dpi=300,facecolor='white')
    fig.savefig(OUT/(stem+'_preview.png'),dpi=180,facecolor='white')
    with Image.open(OUT/(stem+'.png')) as im:
        im.convert('RGB').save(OUT/(stem+'.tif'),compression='tiff_lzw',dpi=(300,300))
    # Layout evidence: no rendered text extends beyond the canvas.
    fig.canvas.draw();renderer=fig.canvas.get_renderer();fw,fh=fig.canvas.get_width_height();bad=[]
    for text in fig.findobj(matplotlib.text.Text):
        if text.get_visible() and text.get_text():
            box=text.get_window_extent(renderer)
            if box.x0 < -1 or box.y0 < -1 or box.x1 > fw+1 or box.y1 > fh+1:bad.append(text.get_text())
    print(stem,'size_mm',np.array(fig.get_size_inches())*25.4,'outside_text',bad)
    if bad:raise ValueError('Text outside canvas')

def flow_figure():
    fig=plt.figure(figsize=(170/25.4,184/25.4));ax=fig.add_axes([0,0,1,1]);ax.set(xlim=(0,170),ylim=(0,184));ax.axis('off')
    def box(x,y,w,h,fc='white',ec=GREY,lw=.8):
        ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.0,rounding_size=1.2',facecolor=fc,edgecolor=ec,linewidth=lw))
    def tx(x,y,s,size=8,weight='normal',color=NAVY,ha='center',va='center',**kwargs):
        return ax.text(x,y,s,fontsize=size,fontweight=weight,color=color,ha=ha,va=va,linespacing=1.38,**kwargs)
    def arrow(x1,y1,x2,y2):
        ax.add_patch(FancyArrowPatch((x1,y1),(x2,y2),arrowstyle='-|>',mutation_scale=8,linewidth=.9,color='#667888',shrinkA=0,shrinkB=0))
    def stage(y,h,num,label,color):
        box(2,y,13,h,fc=color,ec=color)
        tx(8.5,y+h-4.3,num,9,'bold')
        tx(8.5,y+(h-5)/2,label,7.2,'bold',rotation=90)
    stage(150,31,'1','QUESTION BANK','#E8F2F0')
    stage(99,46,'2','RESPONSE GENERATION','#EAF0F8')
    stage(39,55,'3','EVALUATION','#F9EEE1')
    stage(2,32,'4','ANALYSIS','#EBEDF2')
    box(21,162,147,19)
    tx(94.5,174.5,'20 bilingual surgeon-level questions',10,'bold')
    tx(94.5,167.5,'Four themes × 5 questions  |  Arthroplasty 7 · Trauma 7 · Spine 6',7.5)
    box(21,150,147,10,fc=LIGHT)
    tx(94.5,155,'Reference checklist: 7 key points per question · 140 total',8.2,'bold')
    arrow(94.5,150,94.5,146.3)
    # Symmetric branches describe response counts without implying identical product tiers.
    ax.plot([57,132],[146,146],color='#667888',lw=.9)
    arrow(57,146,57,143);arrow(132,146,132,143)
    box(21,118,72,25,fc='#F2F6FB',ec=BLUE)
    box(97,118,71,25,fc='#EFF7F5',ec=TEAL)
    tx(57,136.5,'ChatGPT',10,'bold',BLUE)
    tx(132.5,136.5,'DeepSeek',10,'bold',TEAL)
    tx(57,126,'English 60  |  Chinese 60\n120 responses',8)
    tx(132.5,126,'English 60  |  Chinese 60\n120 responses',8)
    arrow(57,118,57,115.5);arrow(132.5,118,132.5,115.5)
    box(21,99,147,16,fc=LIGHT)
    tx(94.5,109,'3 independent sessions per question–model–language cell',8.1,'bold')
    tx(94.5,103,'20 questions × 2 models × 2 languages × 3 sessions = 240 responses',7.4)
    arrow(94.5,99,94.5,94.5)
    box(21,80,147,14)
    tx(94.5,89,'Randomised order and concealed model identifiers',8.8,'bold')
    tx(94.5,83.5,'Two orthopaedic surgeons independently audit all 240 responses',7.7)
    arrow(94.5,80,94.5,77)
    ax.plot([57,132],[77,77],color='#667888',lw=.9)
    arrow(57,77,57,74.3);arrow(132,77,132,74.3)
    box(21,43,72,31,fc='#F4F7FB',ec=BLUE)
    box(97,43,71,31,fc='#FDF7F0',ec=ORANGE)
    tx(57,68.5,'Expert audit',9,'bold',BLUE)
    tx(57,55.5,'Key-point coverage (primary)\nErroneous statements and unsafe advice\nAccuracy · completeness · clarity\nConsistency with evidence (4-point scales)',7.1)
    tx(132.5,68.5,'Additional response measures',8.5,'bold',ORANGE)
    tx(132.5,55.5,'Citation existence and study-type labels\nText and content stability across sessions\nEnglish: FKGL / FRES\nChinese: ARC indices',7.1)
    arrow(57,43,57,38);arrow(132.5,43,132.5,38)
    ax.plot([57,132.5],[38,38],color='#667888',lw=.9)
    arrow(94.5,38,94.5,34.5)
    box(21,2,147,32,fc=LIGHT,ec='#AAB7C4')
    tx(94.5,27.5,'Question-level paired comparison · n = 20 questions',9,'bold')
    tx(94.5,20.3,'Primary: Wilcoxon + Holm adjustment (overall / English / Chinese)',7.8)
    tx(94.5,13.8,'Mean paired differences with 95% confidence intervals',7.8)
    tx(94.5,7.2,'Sensitivity analyses · inter-rater reliability · exploratory secondary outcomes',7.4)
    export(fig,'Figure_1_study_workflow');plt.close(fig)

def results_figure():
    q=pd.read_csv(WORK/'question_coverage_CORRECTED.csv',header=[0,1],index_col=0)
    # pandas adds the original index-name row; retain only integer question numbers.
    q=q.loc[pd.to_numeric(q.index,errors='coerce').notna()]
    q.index=q.index.astype(int)
    results=json.loads((WORK/'primary_CORRECTED.json').read_text(encoding='utf-8'))
    fig=plt.figure(figsize=(170/25.4,188/25.4))
    fig.text(.035,.969,'A',fontsize=12,fontweight='bold')
    ax=fig.add_axes([.19,.758,.47,.176])
    cols=[NAVY,BLUE,ORANGE]
    for i,(r,color) in enumerate(zip(results,cols)):
        y=2-i;v=100*r['difference'];lo=100*r['ci_lo'];hi=100*r['ci_hi']
        ax.errorbar(v,y,xerr=[[v-lo],[hi-v]],fmt='D' if i==0 else 'o',markersize=5.1,elinewidth=.85,capsize=3,color=color,ecolor='#52514e',capthick=.7,zorder=3)
        ax.text(1.06,y,f'{v:+.1f} [{lo:+.1f}, {hi:+.1f}]',transform=ax.get_yaxis_transform(),va='center',fontsize=7.8,color=color)
    ax.axvline(0,color='#8995A3',linestyle='solid',lw=.8)
    ax.set(xlim=(-17,5.5),ylim=(-.5,2.5),yticks=[2,1,0],yticklabels=['Overall','English','Chinese'],xticks=[-15,-10,-5,0,5])
    ax.tick_params(axis='y',length=0,pad=7,labelsize=8);ax.tick_params(axis='x',labelsize=7.5)
    ax.spines[['top','right','left']].set_visible(False)
    ax.set_xlabel('ChatGPT − DeepSeek (percentage points)',fontsize=8,labelpad=6)
    fig.text(.688,.939,'Mean difference [95% CI]',fontsize=7.3,color='#586675')
    fig.text(.035,.690,'B',fontsize=12,fontweight='bold')
    fig.legend(handles=[Line2D([0],[0],color=BLUE,marker='o',linestyle='None',label='English',markersize=4.5),Line2D([0],[0],color=ORANGE,marker='s',linestyle='None',label='Chinese',markersize=4.5)],loc='upper right',bbox_to_anchor=(.968,.678),frameon=False,ncol=2,columnspacing=1.2,handletextpad=.3,fontsize=7.5)
    ax=fig.add_axes([.40,.108,.55,.525])
    labels={1:'Precision / visualisation',9:'Reach and angulation',10:'Intelligent assistance',11:'Pedicle screw accuracy',12:'Pelvic screw fixation',2:'Indication boundaries',13:'Arthroplasty selection',14:'Spine indications',15:'Fracture selection',16:'Osteoporotic fixation',3:'Haptic feedback',4:'Setup and workflow',5:'Emergency conversion',6:'Credentials and training',17:'Arthroplasty learning curve',7:'Long-term outcomes',8:'Resource allocation',18:'Registry outcomes',19:'Radiation exposure',20:'Spine cost-effectiveness'}
    groups=[('Platform accuracy and safety',[1,9,10,11,12]),('Indications and contraindications',[2,13,14,15,16]),('Workflow and learning curve',[3,4,5,6,17]),('Long-term outcomes and costs',[7,8,18,19,20])]
    row=0
    plot_data=[]
    for g,(name,questions) in enumerate(groups):
        # Reserve one full line above each block for its theme label.
        ax.text(-.66,row,name,transform=ax.get_yaxis_transform(),ha='left',va='center',fontsize=7.15,fontweight='bold',clip_on=False)
        row+=1
        for question in questions:
            en=100*(q.loc[question,('EN','ChatGPT')]-q.loc[question,('EN','DeepSeek')])
            zh=100*(q.loc[question,('ZH','ChatGPT')]-q.loc[question,('ZH','DeepSeek')])
            ax.plot([en,zh],[row,row],color='#C3CBD4',lw=1,zorder=1)
            ax.scatter(en,row,s=17,c=BLUE,zorder=3)
            ax.scatter(zh,row,s=16,c=ORANGE,marker='s',zorder=3)
            weight='bold' if question in [14,19] else 'normal'
            ax.text(-.66,row,f'Q{question:<2}  {labels[question]}',transform=ax.get_yaxis_transform(),ha='left',va='center',fontsize=6.85,fontweight=weight,clip_on=False)
            plot_data.append({'question':question,'en_difference_pp':en,'zh_difference_pp':zh})
            row+=1
    ax.axvline(0,color='#8995A3',linestyle='solid',lw=.8,zorder=0)
    ax.set(xlim=(-40,30),ylim=(row-.35,-.55),xticks=[-40,-20,0,20],yticks=[])
    ax.grid(axis='x',color='#e1e0d9',lw=.5,linestyle='solid',zorder=0)
    ax.spines[['top','right','left']].set_visible(False)
    ax.tick_params(axis='x',labelsize=7.5)
    ax.set_xlabel('ChatGPT − DeepSeek (percentage points)',fontsize=8,labelpad=5)
    pd.DataFrame(plot_data).to_csv(OUT/'Figure_2_plot_data.csv',index=False)
    fig.text(.035,.020,'Corrected ratings · author-review draft',fontsize=7,color='#666666');export(fig,'Figure_2_CORRECTED_author_review');plt.close(fig)

results_figure()
