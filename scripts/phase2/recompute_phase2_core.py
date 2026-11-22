from pathlib import Path
import shutil,json,hashlib,re,types
import pandas as pd,numpy as np
from fractions import Fraction
from scipy import stats

ROOT=Path(__file__).resolve().parent
OLD=Path('D:/Codex/outputs/robotic_LLM_adjudication_2026-11-08/github_candidate_v0.8/robotic-orthopaedic-surgery')
DEST=ROOT/'phase2_replication'
def main():
    if not DEST.exists():shutil.copytree(OLD,DEST)
    shutil.copy2(ROOT/'staged_R207_corrected/ratings.csv',DEST/'data/ratings.csv')
    r=pd.read_csv(DEST/'data/ratings.csv');a=r[(r.model=='DeepSeek')&(r.lang=='ZH')&(r.question==19)&(r.session==3)].set_index('rater')
    grid=pd.read_csv(OLD/'data/analysis/analysis_rows.csv');before=grid.copy(deep=True);idx=grid.index[grid.r_id=='R207'].item()
    for name,csvfield in [('kp','kp'),('err','error_count'),('准确性','accuracy'),('完整性','completeness'),('清晰度','clarity'),('一致性','consistency')]:
        vals={k:(int(a.loc[k,[f'kp{i}' for i in range(1,8)]].sum())/14 if name=='kp' else int(a.loc[k,csvfield])) for k in ['A','B']}
        for k in ['A','B']:grid.at[idx,name+'_'+k.lower()]=vals[k]
        grid.at[idx,name]=(vals['A']+vals['B'])/2
    grid.at[idx,'unsafe']='有' if a.unsafe.any() else '无'
    pd.testing.assert_frame_equal(grid.drop(idx),before.drop(idx))
    grid.to_csv(DEST/'data/analysis/analysis_rows.csv',index=False)
    # Keep the source correction explicit. No old ARC value is treated as current.
    manifest=json.loads((DEST/'input_manifest.json').read_text())
    for rel in manifest['packaged_inputs']:
        manifest['packaged_inputs'][rel]=hashlib.sha256((DEST/rel).read_bytes()).hexdigest()
    manifest['postreview_correction']='R207 corrected original-session text and actual original-rater returns, 2026-11-19. Original reference targets remain historical.'
    (DEST/'input_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    source=(OLD/'analysis/run_analysis.py').read_text()
    arc_ready=(ROOT/'ARC_MERGE_VERIFICATION.json').exists()
    if not arc_ready:
        source=re.sub(r'^    for field,lang in \[.*?\]:$',"    for field,lang in [('fkgl','EN'),('fres','EN')]:",source,flags=re.M)
    module=types.ModuleType('phase2_core');module.__file__=str(DEST/'analysis/run_analysis.py')
    exec(compile(source,module.__file__,'exec'),module.__dict__)
    # Original 'compare' asserts all results equal old outputs. Replace this
    # only for correction mode with independent exhaustive primary validation.
    def compare(result):
        rows=[]
        for language in ['Overall','EN','ZH']:
            deltas=[];cg=[];ds=[]
            for q in range(1,21):
                vals={}
                for model in ['ChatGPT','DeepSeek']:
                    s=r[(r.question==q)&(r.model==model)]
                    if language!='Overall':s=s[s.lang==language]
                    vals[model]=Fraction(int(s[[f'kp{k}' for k in range(1,8)]].to_numpy().sum()),14*len(s))
                cg.append(vals['ChatGPT']);ds.append(vals['DeepSeek']);deltas.append(cg[-1]-ds[-1])
            nonzero=[z for z in deltas if z]
            weights=np.rint(2*stats.rankdata(np.array([abs(z) for z in nonzero],dtype=object))).astype(int)
            all_sums=np.array([0],dtype=np.int16)
            for weight in weights:all_sums=np.concatenate([all_sums,all_sums+weight])
            positive=sum(w for w,z in zip(weights,nonzero) if z>0)
            p=min(1.,2*np.mean(all_sums<=min(positive,int(weights.sum())-positive)))
            actual=result['primary'][language]
            assert actual['p']==p
            assert abs(actual['cg']-float(sum(cg)/20))<1e-12
            assert abs(actual['ds']-float(sum(ds)/20))<1e-12
            independent_ci=stats.t.interval(.95,19,loc=np.mean([float(z) for z in deltas]),scale=stats.sem([float(z) for z in deltas]))
            assert np.allclose(independent_ci,actual['ci'],atol=1e-12,rtol=0)
            rows.append({'language':language,'exhaustive_p_matches':True,'means_and_CI_match':True})
        (DEST/'results/verification_CORRECTED.json').write_text(json.dumps({'status':'passed_for_core','primary_checks':rows,'ARC_updated':arc_ready,'scope':'Core scoring and available validated readability outputs. New R207 flags not independently third-adjudicated. Historical 75 checks are not asserted against corrected outputs.'},indent=2),encoding='utf-8')
    module.compare=compare;module.main()
    current=json.loads((DEST/'results/analysis_results.json').read_text());old=json.loads((OLD/'results/analysis_results.json').read_text())
    core={'state':'CORE_RECOMPUTED_ZH_ARC_PENDING','primary':current['primary'],'likert':current['likert'],'errors':current['errors'],'reliability':current['reliability'],'readability_EN':current['readability'],'pending':['Chinese ARC re-run: blocked by Windows application control','New R207 rater-flag candidates require separate adjudication; original 18 adjudications preserved','Mixed model, manuscript, ESM and final figures integration'],'input_records':480,'changed_records':2}
    if arc_ready:
        core['state']='CORE_AND_READABILITY_RECOMPUTED'
        core['readability']=core.pop('readability_EN')
        core['pending']=[x for x in core['pending'] if not x.startswith('Chinese ARC')]
    (ROOT/'CORE_RESULTS_CORRECTED.json').write_text(json.dumps(core,ensure_ascii=False,indent=2),encoding='utf-8')
    data=grid.copy();data['int28']=data.r_id.map(r.merge(grid[['r_id','model','lang','question','session']],on=['model','lang','question','session'],validate='many_to_one').assign(int14=lambda x:x[[f'kp{i}' for i in range(1,8)]].sum(axis=1)).groupby('r_id').int14.sum())
    q=data.groupby(['question','lang','model']).int28.sum().unstack(['lang','model'])/84
    q.to_csv(ROOT/'inputs/question_coverage_CORRECTED.csv')
    result=[{'stratum':s,'difference':z['mean_difference'],'ci_lo':z['ci'][0],'ci_hi':z['ci'][1]} for s,z in current['primary'].items()]
    (ROOT/'inputs/primary_CORRECTED.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    overall=data.groupby(['question','model']).int28.sum().unstack()
    leading=int((overall.DeepSeek>overall.ChatGPT).sum())
    olderr=r.groupby('model').error_count.sum().to_dict()
    print(json.dumps({'primary':current['primary'],'DeepSeek_leading_questions':leading,'raw_rater_flag_instances':olderr,'Q19_ZH':q.loc[19,'ZH'].to_dict(),'scope':'ARC updated; new third-rater adjudication pending' if arc_ready else 'Chinese ARC and new third-rater adjudication pending'},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
