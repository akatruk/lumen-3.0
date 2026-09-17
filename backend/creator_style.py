"""Reusable editorial preferences and measurements of the actual proposed edit."""
from typing import Literal
from pydantic import Field
from .schemas import Strict

class Style(Strict):
    structure: Literal['preserve','hook_proof_takeaway','problem_solution','comparison']='preserve'
    pacing: Literal['calm','balanced','dynamic']='balanced'
    presenter_percent: int=Field(default=60,ge=0,le=100)
    visuals: Literal['minimal','balanced','illustrated']='balanced'

STRUCTURES={
    'preserve':'Preserve the existing narrative order; improve local clarity without changing chronology.',
    'hook_proof_takeaway':'Open on a source-supported promise or strongest moment, develop evidence, end on an existing takeaway.',
    'problem_solution':'Establish the actual problem, show the available explanation or solution, finish with a supported next step.',
    'comparison':'Introduce the compared choices, group existing evidence consistently, end on a qualified conclusion. Do not fabricate missing sides.',
}

def brief(style):
    s=Style.model_validate(style or {})
    return {'structure':STRUCTURES[s.structure],
            'shot_duration_target_seconds':{'calm':[6,12],'balanced':[3,7],'dynamic':[1.5,4]}[s.pacing],
            'presenter_percent_target':s.presenter_percent,'visual_mix':s.visuals,
            'constraint':'Preferences, not quotas: preserve complete speech, facts and context. Do not split unchanged footage to fake pace. Use only available visuals. Explain unmet preferences.'}

def measure(edit,style):
    s=Style.model_validate(style or {});total=sum(c.end-c.start for c in edit.clips)
    presenter=0;visual=0
    for c in edit.clips:
        length=c.end-c.start
        inserts=[(x.start,x.end) for x in (c.cutaway,c.external_broll) if x]
        covered=0;end=0
        for a,b in sorted(inserts):
            covered+=max(0,min(length,b)-max(end,a));end=max(end,b)
        if c.shot_type=='presenter':presenter+=max(0,length-covered)
        visual+=length if c.shot_type in ('broll','document','archive','news') else covered
    return {'preferences':s.model_dump(),'average_shot_seconds':round(total/max(1,len(edit.clips)),2),
            'presenter_percent':round(100*presenter/total,1),'broll_percent':round(100*visual/total,1),
            'classification_based':True}
