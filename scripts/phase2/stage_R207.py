"""Validate original-rater returns and stage an audited, separate ratings copy.

Default: check only. --apply writes a NEW directory; never changes source files.
Clinical scores are never inferred or filled by this script.
"""
from pathlib import Path
import argparse,json,hashlib,sys,datetime
import pandas as pd
import openpyxl

ROOT=Path(__file__).resolve().parent
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def integer(value,lo,hi,label):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or int(value)!=value or not lo<=value<=hi:
        raise ValueError(f'{label}: expected integer {lo}..{hi}, got {value!r}')
    return int(value)
def read_scores(path,rater):
    book=openpyxl.load_workbook(path,data_only=False)
    sheet=book['评分'];rows=[tuple(c.value for c in row) for row in sheet.iter_rows(min_row=2) if row[0].value]
    if len(rows)==240:
        frozen=ROOT/f'returned_forms/frozen_{rater}.xlsx'
        reference=list(openpyxl.load_workbook(frozen)['评分'].values)
        incoming=list(sheet.values)
        if incoming[0]!=reference[0]:raise ValueError(f'{rater}: full-form headers differ')
        old={r[0]:r for r in reference[1:] if r[0]};new={r[0]:r for r in rows}
        if len(new)!=240 or set(new)!=set(old):raise ValueError(f'{rater}: response keys differ')
        if any(new[k]!=old[k] for k in old if k!='R207'):raise ValueError(f'{rater}: non-R207 cells changed')
        selected=[new['R207']]
    else:selected=rows
    if len(selected)!=1 or selected[0][:2]!=('R207','Q19'):raise ValueError(f'{rater}: exactly R207/Q19 required')
    row=selected[0];required=list(range(2,10))+[11]+list(range(13,17))
    missing=[sheet.cell(1,i+1).value for i in required if row[i] is None]
    if missing:raise ValueError(f'{rater}: unfilled fields: '+', '.join(missing))
    if any(isinstance(v,str) and v.startswith('=') for v in row):raise ValueError('Clinical scores must be entries, not formulas')
    categories={'覆盖':2,'部分覆盖':1,'未覆盖':0}
    if any(v not in categories for v in row[2:9]):raise ValueError(f'{rater}: invalid KP category')
    errors=integer(row[9],0,100000,'error count')
    if row[11] not in {'无','有'}:raise ValueError(f'{rater}: unsafe must be 无/有')
    if errors and not row[10]:raise ValueError(f'{rater}: error rationale required')
    if row[11]=='有' and not row[12]:raise ValueError(f'{rater}: unsafe rationale required')
    result={f'kp{k}':categories[row[k+1]] for k in range(1,8)}
    result.update(error_count=errors,unsafe=int(row[11]=='有'))
    for i,key in enumerate(['accuracy','completeness','clarity','consistency'],13):result[key]=integer(row[i],1,4,key)
    return result,{'error_reason':row[10],'unsafe_reason':row[12],'notes':row[17]}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--a',type=Path,default=ROOT/'returned_forms/returned_A.xlsx')
    parser.add_argument('--b',type=Path,default=ROOT/'returned_forms/returned_B.xlsx')
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args();scores={};notes={};problems=[]
    for rater,path in [('A',args.a),('B',args.b)]:
        try:scores[rater],notes[rater]=read_scores(path,rater)
        except (ValueError,KeyError,FileNotFoundError) as error:problems.append(str(error))
    if problems:
        print(json.dumps({'state':'WAITING_FOR_VALID_ORIGINAL_RATER_RETURNS','problems':problems,'ratings_written':False},ensure_ascii=False,indent=2));return 2
    baseline=ROOT/'inputs/ratings.csv'
    provenance=json.loads((ROOT/'SOURCE_AND_STATUS.json').read_text(encoding='utf-8-sig'))
    for filename,expected in provenance['baseline_input_sha256'].items():
        if digest(ROOT/'inputs'/filename)!=expected:raise ValueError(f'Baseline changed: {filename}')
    # Guard the actual supplied baseline, not a guessed row number.
    ratings=pd.read_csv(baseline);before=ratings.copy(deep=True)
    metadata=pd.read_csv(ROOT/'inputs/analysis_rows.csv')
    m=metadata[metadata.r_id=='R207'];assert len(m)==1
    m=m.iloc[0];mask=(ratings.model==m.model)&(ratings.lang==m.lang)&(ratings.question==m.question)&(ratings.session==m.session)
    assert len(ratings)==480 and mask.sum()==2 and set(ratings.loc[mask,'rater'])=={'A','B'}
    changes=[]
    for rater in ['A','B']:
        index=ratings.index[mask&(ratings.rater==rater)];assert len(index)==1
        i=index[0]
        for field,new in scores[rater].items():
            changes.append({'r_id':'R207','rater':rater,'field':field,'old':int(ratings.at[i,field]),'new':new})
            ratings.at[i,field]=new
    pd.testing.assert_frame_equal(ratings.loc[~mask],before.loc[~mask])
    assert ratings[['sample_id','model','lang','question','session','rater']].equals(before[['sample_id','model','lang','question','session','rater']])
    record={'state':'VALIDATED_READY_TO_STAGE','applied':args.apply,'baseline_sha256':digest(baseline),'returned_form_sha256':{'A':digest(args.a),'B':digest(args.b)},'changes':changes,'rationale':notes,'unchanged_other_rows':478,'scope':'Staging clinical scores only; full revised analyses, ARC derivation, manuscript and final figures must run against this new layer. Original adjudication is not automatically rewritten.'}
    if args.apply:
        dest=ROOT/'staged_R207_corrected'
        dest.mkdir(exist_ok=False)
        ratings.to_csv(dest/'ratings.csv',index=False)
        (dest/'change_record.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
        (dest/'R207_corrected_response.txt').write_bytes((ROOT/'inputs/R207_corrected_response.txt').read_bytes())
    print(json.dumps(record,ensure_ascii=False,indent=2));return 0
if __name__=='__main__':sys.exit(main())
