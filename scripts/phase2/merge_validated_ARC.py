from pathlib import Path
import json,hashlib
import pandas as pd
ROOT=Path(__file__).resolve().parent;DEST=ROOT/'phase2_replication'
record=json.loads((ROOT/'ARC_外机运行交接包/VALIDATED_R207.json').read_text(encoding='utf-8'))
assert record['status']=='CONTROL_CHECKS_PASSED' and record['r_id']=='R207' and record['file_id']=='DeepSeek_Q19_s3'
output=ROOT/'ARC_外机运行交接包/output/0ARC_Chinese_Results.csv'
assert hashlib.sha256(output.read_bytes()).hexdigest()==record['output_sha256']
grid=pd.read_csv(ROOT/'inputs/analysis_rows.csv');meta=grid.loc[grid.r_id=='R207'].iloc[0]
assert (meta.model,meta.lang,int(meta.question),int(meta.session))==('DeepSeek','ZH',19,3)
ratings=pd.read_csv(DEST/'data/ratings.csv')
sel=(ratings.model==meta.model)&(ratings.lang==meta.lang)&(ratings.question==meta.question)&(ratings.session==meta.session)
ids=ratings.loc[sel,'sample_id'].unique();assert len(ids)==1
p=DEST/'data/readability_derived.csv';frame=pd.read_csv(p);old=frame.copy(deep=True);mask=frame.sample_id==ids[0];assert mask.sum()==1
changes=[]
for key in ['lexical_richness','syntactic_richness','semantic_accuracy_n_v']:
    col='arc_'+key;value=round(record['metrics'][key],4);changes.append({'field':col,'old':float(frame.loc[mask,col].iloc[0]),'new':value,'raw':record['metrics'][key]});frame.loc[mask,col]=value
pd.testing.assert_frame_equal(frame.loc[~mask],old.loc[~mask]);frame.to_csv(p,index=False)
p=DEST/'data/analysis/readability_rows_v1.1.csv';frame=pd.read_csv(p);mask=frame.r_id=='R207';assert mask.sum()==1
for key,value in record['metrics'].items():frame.loc[mask,'arc_'+key]=round(value,4)
frame.to_csv(p,index=False)
(ROOT/'ARC_MERGE_VERIFICATION.json').write_text(json.dumps({'status':'passed','r_id':'R207','sample_id':ids[0],'metadata':['DeepSeek','ZH',19,3],'unchanged_other_readability_rows':239,'unchanged_other_Chinese_rows':119,'changes_primary_readability':changes,'source_output_sha256':record['output_sha256']},ensure_ascii=False,indent=2),encoding='utf-8')
print('ARC merged into unique R207; other239 derived rows unchanged.')
