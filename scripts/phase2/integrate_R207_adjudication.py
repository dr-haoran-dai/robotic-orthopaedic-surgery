from pathlib import Path
import json,hashlib,shutil
from math import comb
import pandas as pd
import openpyxl

ROOT=Path(__file__).resolve().parent
SOURCE=Path('D:/桌面/论文/LLM+机器人手术/v2.0_升级工作区_2026-11-04/05_评分/发老师/R207_新增错误候选_第三裁决人待裁决.xlsx')
DEST=ROOT/'R207_adjudication_received';DEST.mkdir(exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
digest=sha(SOURCE);archived=DEST/f'R207_裁决回表_{digest[:12]}.xlsx'
shutil.copy2(SOURCE,archived);assert sha(archived)==digest
w=openpyxl.load_workbook(SOURCE);s=w.worksheets[0];rows=list(s.values)[1:]
assert {r[0] for r in rows}=={'R207-E1','R207-E2'}
assert [(r[0],r[6]) for r in rows]==[('R207-E1','否'),('R207-E2','是')]
anchors=[(im.anchor._from.col,im.anchor._from.row) for im in s._images]
assert (9,1) in anchors and (9,2) in anchors
original=pd.read_csv(ROOT/'phase2_replication/data/adjudication/adjudicated_events_18.csv')
grid=pd.read_csv(ROOT/'inputs/analysis_rows.csv');m=grid.loc[grid.r_id=='R207'].iloc[0]
new=[]
for r in rows:
    new.append({'event_id':r[0],'r_id':'R207','model':m.model,'lang':m.lang,'question':int(m.question),'session':int(m.session),'decision':r[5],'counted_factual_error':int(r[6]=='是'),'unresolved':0,'rationale':r[7],'source_ids':'R207 returned workbook / original corrected response','recorded_date':str(r[8]),'author_confirmation_date':'','source_workbook_sha256':digest,'signature_record':'Embedded signature image at J2/J3; signer identity not independently authenticated by Codex'})
events=pd.concat([original,pd.DataFrame(new)],ignore_index=True)
assert len(events)==20 and events.counted_factual_error.sum()==7 and events.event_id.is_unique
events.to_csv(DEST/'adjudicated_events_20.csv',index=False)
counts=events.groupby('r_id')[['counted_factual_error','unresolved']].sum()
responses=grid[['r_id','model','lang','question','session']].merge(counts,left_on='r_id',right_index=True,how='left',validate='one_to_one').fillna({'counted_factual_error':0,'unresolved':0})
comparisons=[]
for mode in ['confirmed_only','unresolved_positive_sensitivity']:
    positive=responses.counted_factual_error.gt(0)
    if mode!='confirmed_only':positive=positive|responses.unresolved.gt(0)
    d=responses.assign(positive=positive)
    for language in ['Overall','EN','ZH']:
        f=d if language=='Overall' else d[d.lang==language]
        t=f.groupby(['question','model']).positive.max().unstack()
        b=int((t.ChatGPT&~t.DeepSeek).sum());c=int((t.DeepSeek&~t.ChatGPT).sum());n=b+c
        p=min(1.,2*sum(comb(n,k) for k in range(min(b,c)+1))/2**n) if n else 1.
        comparisons.append({'scenario':mode,'language':language,'question_pairs':20,'CG_positive_responses':int(f.loc[f.model=='ChatGPT','positive'].sum()),'DS_positive_responses':int(f.loc[f.model=='DeepSeek','positive'].sum()),'CG_positive_questions':int(t.ChatGPT.sum()),'DS_positive_questions':int(t.DeepSeek.sum()),'CG_only_discordant':b,'DS_only_discordant':c,'exact_p_unadjusted':p})
pd.DataFrame(comparisons).to_csv(DEST/'question_comparisons_after_R207.csv',index=False)
responses.to_csv(DEST/'responses_after_R207.csv',index=False)
# Keep the actual independent returns from earlier snapshots. Current external
# A=1 form is explicitly a later post-adjudication layer, not rewritten history.
base=SOURCE.parent
formdiff=[]
for rater in ['A','B']:
    p=base/f'评分表_评者{rater}_v1.1_已填.xlsx'
    if not p.exists():continue
    old={r[0]:r for r in list(openpyxl.load_workbook(ROOT/f'returned_forms/returned_{rater}.xlsx')['评分'].values)[1:] if r[0]}
    current={r[0]:r for r in list(openpyxl.load_workbook(p)['评分'].values)[1:] if r[0]}
    assert set(old)==set(current)
    assert all(old[k]==current[k] for k in old if k!='R207')
    formdiff.append({'rater':rater,'original_return_error_count':old['R207'][9],'post_adjudication_form_error_count':current['R207'][9],'sha256':sha(p)})
    shutil.copy2(p,DEST/f'post_adjudication_form_{rater}.xlsx')
record={'status':'received_decisions_integrated_as_separate_layer','source_sha256':digest,'events':20,'counted_events':7,'noncounted_wording_events':9,'rejected_flags':3,'unresolved':1,'counted_responses':int(responses.counted_factual_error.gt(0).sum()),'counted_distinct_questions':int(events.loc[events.counted_factual_error.gt(0),'question'].nunique()),'original_rater_flag_instances':26,'post_adjudication_adjusted_form_instances':25,'original_rater_returns_preserved':True,'forms_diff':formdiff,'signature_images':anchors,'signature_scope':'Source workbook records review/signing and contains embedded images. Codex checks their presence/anchors, not cryptographic authenticity or identity.','comparisons':comparisons}
(DEST/'RECEIPT_AND_COUNTS.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(record,ensure_ascii=False,indent=2))
