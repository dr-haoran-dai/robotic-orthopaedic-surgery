"""Recompute text-only changes using the original ordered-body parser/method.
Does not invent clinical ratings or ARC results. All outputs stay beside script.
"""
from pathlib import Path
import re,json,hashlib,shutil
import pandas as pd
from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph
from docx.oxml.ns import qn

ROOT=Path(__file__).resolve().parent
BASE=Path('D:/桌面/论文/LLM+机器人手术/v2.0_升级工作区_2026-11-04')
def parse(path):
    doc=Document(path);answers={};q=session=None;buffer=[]
    def flush():
        if q and session:
            answers[q,session]=' '.join(x for x in buffer if x.strip()).strip()
        buffer.clear()
    for child in doc.element.body.iterchildren():
        if child.tag==qn('w:p'):
            para=Paragraph(child,doc);text=para.text.strip()
            match=re.match(r'^Q(\d+)\s*[｜|]',text)
            if para.style.name.startswith('Heading 2') and match:
                flush();q=int(match[1]);session=None;continue
            match=re.match(r'^第([123])次',text) or re.match(r'^Round ([123])\b',text)
            if match:flush();session=int(match[1]);continue
            if session and text and not text.startswith(('本回答由 AI 生成','（回答由 AI 生成')):buffer.append(text)
        elif child.tag==qn('w:tbl') and session:
            for row in Table(child,doc).rows:buffer.append(' '.join(c.text.strip() for c in row.cells if c.text.strip()))
    flush();assert len(answers)==60,(path,len(answers))
    return answers
def tokens(text,language):
    if language=='ZH':
        clean=re.sub(r'[\s\d\W]+','',text,flags=re.UNICODE)
        return set(clean[i:i+2] for i in range(len(clean)-1)),len(re.sub(r'\s','',text))
    words=re.findall(r'[a-z0-9]+',text.lower());return set(words),len(words)
def compute(answers):
    rows=[]
    for model,language in [('ChatGPT','ZH'),('ChatGPT','EN'),('DeepSeek','ZH'),('DeepSeek','EN')]:
        for q in range(1,21):
            sets,lengths=zip(*(tokens(answers[model,language,q,s],language) for s in [1,2,3]))
            jac=[len(sets[a]&sets[b])/len(sets[a]|sets[b]) for a,b in [(0,1),(0,2),(1,2)]]
            rows.append(dict(q=q,model=model,lang=language,len1=lengths[0],len2=lengths[1],len3=lengths[2],j12=round(jac[0],3),j13=round(jac[1],3),j23=round(jac[2],3),mean_j=round(sum(jac)/3,3)))
    return pd.DataFrame(rows)
def main():
    sources=[('ChatGPT','ZH','一'),('ChatGPT','EN','二'),('DeepSeek','ZH','三'),('DeepSeek','EN','四')]
    answers={};hashes={}
    for model,lang,part in sources:
        p=BASE/f'04_生成记录/采集_第{part}部分_{model}{"中文" if lang=="ZH" else "英文"}_2026-11-04.docx'
        hashes[p.name]=hashlib.sha256(p.read_bytes()).hexdigest()
        answers.update({(model,lang,q,s):t for (q,s),t in parse(p).items()})
    original=compute(answers)
    archived=pd.read_csv(BASE/'06_分析/_stability_text_rows.csv')
    merged=original.merge(archived,on=['q','model','lang'],validate='one_to_one',suffixes=('_new','_ref'))
    for field in ['len1','len2','len3','j12','j13','j23','mean_j']:
        assert (abs(merged[field+'_new']-merged[field+'_ref'])<1e-12).all(),field
    corrected=parse(ROOT/'source_snapshot/采集_第三部分_DeepSeek中文_2026-11-04_更正版v1_2026-11-11.docx')
    changes=[(q,s) for q,s in corrected if corrected[q,s]!=answers['DeepSeek','ZH',q,s]]
    assert changes==[(19,3)],changes
    answers['DeepSeek','ZH',19,3]=corrected[19,3]
    current=compute(answers)
    diff=original.merge(current,on=['q','model','lang'],suffixes=('_old','_corrected'))
    diff=diff[(diff.mean_j_old!=diff.mean_j_corrected)|(diff.len3_old!=diff.len3_corrected)]
    assert len(diff)==1
    dest=ROOT/'text_only_results';dest.mkdir(exist_ok=True)
    original.to_csv(dest/'stability_baseline_reproduced.csv',index=False)
    current.to_csv(dest/'stability_corrected_text_only.csv',index=False)
    diff.to_csv(dest/'R207_text_change.csv',index=False)
    # Use the original ARC export cleanup: no generated score, only new input text.
    text=(ROOT/'inputs/R207_corrected_response.txt').read_text(encoding='utf-8')
    arc=[]
    for line in text.splitlines():
        line=re.sub(r'^#+\s*','',line.strip()).replace('**','').replace('__','')
        line=re.sub(r'^>\s?','',line);line=re.sub(r'^[-*•]\s+','• ',line)
        if line:arc.append(line)
    (dest/'ARC_input_R207_CORRECTED.txt').write_text('\n'.join(arc)+'\n',encoding='utf-8')
    record={'status':'TEXT_METRICS_ONLY','baseline_80_cells_reproduced':True,'only_changed_answer':['DeepSeek','ZH',19,3],'old_mean_Jaccard_rounded':float(diff.mean_j_old.iloc[0]),'corrected_mean_Jaccard_rounded':float(diff.mean_j_corrected.iloc[0]),'ARC_new_score':'not available; run corrected input in same ARC version/settings before final readability comparisons','clinical_results':'not updated; waiting A/B','source_hashes':hashes}
    (dest/'verification.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(record,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
