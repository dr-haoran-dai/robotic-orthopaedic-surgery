from pathlib import Path
import json,re,shutil,subprocess,sys
import pandas as pd,numpy as np,openpyxl
import statsmodels.formula.api as smf
from openpyxl.styles import Alignment,Font
ROOT=Path(__file__).resolve().parent;DEST=ROOT/'phase2_replication'
r=pd.read_csv(DEST/'data/ratings.csv');grid=pd.read_csv(DEST/'data/analysis/analysis_rows.csv')
r['int14']=r[[f'kp{k}' for k in range(1,8)]].sum(axis=1)
g=r.groupby(['sample_id','model','lang','question','session']).int14.sum().reset_index(name='int28');g['kp']=g.int28/28
g['model_f']=(g.model=='DeepSeek').astype(int);g['lang_f']=(g.lang=='EN').astype(int)
model=smf.mixedlm('kp ~ model_f * lang_f',g,groups=g.question).fit(reml=False)
mixed={key:{'estimate':float(model.params[key]),'ci':model.conf_int().loc[key].tolist(),'p':float(model.pvalues[key])} for key in model.fe_params.index}
(ROOT/'MIXED_MODEL_CORRECTED.json').write_text(json.dumps(mixed,indent=2),encoding='utf-8')
content=[]
for (modelname,lang,q),sub in r.groupby(['model','lang','question']):
    samples=sub.groupby('session')[[f'kp{k}' for k in range(1,8)]].sum()
    rates=samples.sum(axis=1)/28
    content.append({'model':modelname,'lang':lang,'q':int(q),'kp_mean':float(rates.mean()),'range':float(rates.max()-rates.min()),'same_rate':float((samples.max(axis=0)==samples.min(axis=0)).mean())})
content=pd.DataFrame(content);text=pd.read_csv(ROOT/'text_only_results/stability_corrected_text_only.csv')
content=content.merge(text[['model','lang','q','mean_j']],on=['model','lang','q'],validate='one_to_one')
content.to_csv(ROOT/'CONTENT_AND_TEXT_STABILITY_CORRECTED.csv',index=False)
stats={'coverage_range_mean':float(content['range'].mean()),'identical_keypoint_rate':float(content.same_rate.mean()),'mean_Jaccard_using_archived_3decimal_method':float(content.mean_j.mean()),'minimum_Jaccard_cell':content.loc[content.mean_j.idxmin(),['model','lang','q','mean_j']].to_dict(),'near_identical_triplets':int((content.mean_j>=.6).sum())}
(ROOT/'STABILITY_SUMMARY_CORRECTED.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2),encoding='utf-8')
# Existing exploratory correlations: only length and stability inputs for R207 change.
oldread=pd.read_csv(DEST/'data/analysis/readability_rows_v1.1.csv')
oldst=pd.read_csv(DEST/'data/analysis/stability_text_rows.csv')
newst=oldst.copy()
for row in text.itertuples():
    sel=(newst.q==row.q)&(newst.model==row.model)&(newst.lang==row.lang)
    newst.loc[sel,'mean_j']=row.mean_j
newst.to_csv(DEST/'data/analysis/stability_text_rows.csv',index=False)
body=(ROOT/'inputs/R207_corrected_response.txt').read_text(encoding='utf-8')
oldread.loc[oldread.r_id=='R207','words']=len(re.sub(r'\s','',body))
# Invalidate old ARC fields for the changed record in the current derived grid.
arcfile=ROOT/'ARC_外机运行交接包/VALIDATED_R207.json'
arcdata=json.loads(arcfile.read_text(encoding='utf-8'))['metrics'] if arcfile.exists() else {}
for c in oldread.columns:
    if c.startswith('arc_'):oldread.loc[oldread.r_id=='R207',c]=round(arcdata[c[4:]],4) if c[4:] in arcdata else np.nan
oldread.to_csv(DEST/'data/analysis/readability_rows_v1.1.csv',index=False)
run=subprocess.run([sys.executable,'-B','analysis/recompute_exploratory_correlations.py'],cwd=DEST,capture_output=True,text=True)
assert run.returncode==0,run.stderr
# Preserve every original ESM3 sheet in a private historical workbook; current
# analyses are explicit new sheets, so old and new endpoints cannot silently mix.
BASE=Path('D:/桌面/论文/LLM+机器人手术/v2.0_升级工作区_2026-11-04/12_投稿_JRS')
w=openpyxl.load_workbook(BASE/'ESM_files/ESM_3.xlsx')
for sh in w:sh.sheet_state='hidden'
core=json.loads((ROOT/'CORE_RESULTS_CORRECTED.json').read_text())
primary=pd.DataFrame([{'stratum':s,**{k:v for k,v in z.items() if k!='ci'},'ci_low':z['ci'][0],'ci_high':z['ci'][1]} for s,z in core['primary'].items()])
q=g.groupby(['question','model','lang']).kp.mean().reset_index()
for name,frame in [('CURRENT Primary',primary),('CURRENT Question cells',q),('CURRENT Sessions',g),('CURRENT Stability',content)]:
    sh=w.create_sheet(name);sh.append(frame.columns.tolist())
    for row in frame.itertuples(index=False,name=None):sh.append(row)
    sh.freeze_panes='A2';sh.auto_filter.ref=sh.dimensions
    for row in sh:
        for c in row:c.alignment=Alignment(wrap_text=True,vertical='top')
    for c in sh[1]:c.font=Font(bold=True)
    for col in sh.columns:sh.column_dimensions[col[0].column_letter].width=22
notes=w.create_sheet('READ FIRST')
notes.append(['Layer','Scope'])
notes.append(['CURRENT','Corrected original-session text and original-rater R207 returns. Clinical key-point and Likert scores updated; raw flags total26. ARC re-run and two-control checks completed; new R207 candidates not yet third-adjudicated.' if arcdata else 'Corrected scores; Chinese ARC pending; new error candidates not adjudicated.'])
notes.append(['Hidden historical sheets','Inherited ESM3 original data preserved; not current corrected results. Old 18-event adjudication remains historical review; new flags are separate.'])
notes.column_dimensions['A'].width=30;notes.column_dimensions['B'].width=110
for row in notes:
    for c in row:c.alignment=Alignment(wrap_text=True,vertical='top')
notes.row_dimensions[2].height=90;notes.row_dimensions[3].height=75
w.active=w.index(notes)
w.save(ROOT/'ESM_3_CORRECTED_author_review.xlsx')
# New scoring figure uses corrected values; no old baseline plot is overwritten.
source=(ROOT/'render_figure2_v2.py').read_text(encoding='utf-8')
source=source.replace("'figure2_style_preview'","'figure2_corrected_scores'")
source=source.replace('question_coverage_exact.csv','question_coverage_CORRECTED.csv').replace('primary_recheck.json','primary_CORRECTED.json')
source=source.replace('Style preview · original ratings; R207 re-scoring pending','Corrected ratings · author-review draft')
source=source.replace('Figure_2_STYLE_PREVIEW_BASELINE','Figure_2_CORRECTED_author_review')
path=ROOT/'render_figure2_corrected.py';path.write_text(source,encoding='utf-8')
run=subprocess.run([sys.executable,'-B',str(path)],capture_output=True,text=True,encoding='utf-8')
assert run.returncode==0,run.stderr
print(json.dumps({'mixed_model':mixed,'stability':stats,'ESM3':'created; historical sheets hidden, CURRENT sheets labelled'},ensure_ascii=False,indent=2))
