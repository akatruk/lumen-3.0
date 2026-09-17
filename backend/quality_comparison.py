"""Compare compatible rubric scores; never turn a delta into approval."""
import math
CATEGORIES=('hook','clarity','pacing','visuals','audio')
RUBRIC='editorial-five-v1'

def scores(result):
    qa=result.get('qa')
    if not isinstance(qa,dict):return None
    rows=qa.get('scores',[])
    if not isinstance(rows,list) or any(not isinstance(r,dict) for r in rows):return None
    values={r.get('category'):r.get('value') for r in rows}
    if len(rows)!=5 or set(values)!=set(CATEGORIES):return None
    if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or not 0<=v<=100 for v in values.values()):return None
    return values

def compare(previous,current):
    if not previous or not previous.get('render_id'):return None
    result={'previous_render_id':previous['render_id'],'comparable':False,'reason':'missing_scores'}
    a,b=scores(previous),scores(current)
    if a is None or b is None:return result
    if not previous.get('quality_model') or previous.get('quality_model')!=current.get('quality_model') or previous.get('quality_rubric')!=RUBRIC or current.get('quality_rubric')!=RUBRIC:
        return result|{'reason':'different_or_unknown_evaluator'}
    before=round(sum(a.values())/5,1);after=round(sum(b.values())/5,1)
    return result|{'comparable':True,'reason':None,'previous_score':before,'current_score':after,'delta':round(after-before,1),
        'categories':[{'category':c,'previous':a[c],'current':b[c],'delta':round(b[c]-a[c],1)} for c in CATEGORIES],
        'regressions':[c for c in CATEGORIES if b[c]<a[c]]}
