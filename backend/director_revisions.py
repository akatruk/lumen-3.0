"""Reviewable, scoped AI alternatives; never overwrite a plan during generation."""
import json,time,uuid
from fastapi import APIRouter,Depends,HTTPException
from pydantic import Field
from .schemas import Strict,Recommendation
from .studio import owned,state,Director,Transfer,validate_director
from .auth import current_user
from .db import connect,enqueue
from . import ai,media
from .config import settings
router=APIRouter(prefix='/api/studio')

class Generate(Strict):
    revision:int=Field(ge=1)
    recommendation_id:str
    instruction:str=Field(min_length=3,max_length=1200)

class Alternative(Strict):
    recommendation:Recommendation
    transfer:Transfer

class Accept(Strict):
    revision:int=Field(ge=1)


def init(db):
    db.executescript('''CREATE TABLE IF NOT EXISTS director_proposals(
    id TEXT PRIMARY KEY,project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    revision INTEGER NOT NULL,target TEXT NOT NULL,instruction TEXT NOT NULL,
    snapshot TEXT NOT NULL,proposal TEXT,status TEXT NOT NULL,created REAL NOT NULL)''')


def check(db,pid,revision,target):
    s=state(pid,db)
    if s['revision']!=revision or not s['plan']:raise HTTPException(409,'plan_changed')
    d=next((d for d in s['decisions'] if d['id']==target),None)
    if not d:raise HTTPException(404,'not_found')
    if d['locked']:raise HTTPException(409,'locked_decision')
    if db.execute("SELECT 1 FROM jobs WHERE project_id=? AND status IN ('queued','running')",(pid,)).fetchone():raise HTTPException(409,'job_already_running')
    return s


@router.get('/projects/{pid}/alternatives')
def listing(pid:str,user=Depends(current_user)):
    owned(pid,user)
    with connect() as db:
        rows=db.execute('SELECT id,revision,target,instruction,proposal,status,created FROM director_proposals WHERE project_id=? ORDER BY created DESC LIMIT 30',(pid,))
        return [dict(r)|{'proposal':json.loads(r['proposal']) if r['proposal'] else None} for r in rows]


@router.post('/projects/{pid}/alternatives',status_code=202)
def generate(pid:str,body:Generate,user=Depends(current_user)):
    owned(pid,user)
    with connect() as db:
        db.lock();s=check(db,pid,body.revision,body.recommendation_id)
        proposal_id=uuid.uuid4().hex
        db.execute('INSERT INTO director_proposals VALUES(?,?,?,?,?,?,?,?,?)',(proposal_id,pid,body.revision,body.recommendation_id,body.instruction,json.dumps(s),None,'queued',time.time()))
        enqueue(db,pid,'director_alternative',{'id':proposal_id})
    return {'id':proposal_id}


def merged(snapshot,alternative,target,metadata):
    rec=alternative.recommendation
    if rec.id!=target or alternative.transfer.recommendation_id!=target:raise ValueError('provider_invalid_analysis')
    rec.auto_apply=False
    if rec.action in ('captions','normalize_audio'):rec.start=0;rec.end=metadata['duration']
    plan=Director.model_validate(snapshot['plan'])
    plan.recommendations=[rec if r.id==target else r for r in plan.recommendations]
    plan.transfers=[alternative.transfer if t.recommendation_id==target else t for t in plan.transfers]
    validate_director(plan,snapshot['dna']);media.validate_analysis(plan,metadata['duration'])
    if rec.action=='captions' and not plan.transcript:raise ValueError('provider_invalid_analysis')
    if rec.action=='normalize_audio' and not metadata.get('has_audio'):raise ValueError('provider_invalid_analysis')
    if rec.action in ('remove','move_to_front') and any(c.start+.12<t<c.end-.12 for c in plan.transcript for t in (rec.start,rec.end)):raise ValueError('analysis_timestamps_invalid')
    selected=[]
    for d in snapshot['decisions']:
        r=next(r for r in plan.recommendations if r.id==d['id'])
        if d['id']==target:selected.append(rec)
        elif d['approved']:selected.append(r.model_copy(update={'start':d['start'],'end':d['end']}))
    media.build_timeline(metadata['duration'],selected)
    return plan


def run_job(p,payload):
    with connect() as db:r=dict(db.execute('SELECT * FROM director_proposals WHERE id=? AND project_id=?',(payload['id'],p['id'])).fetchone())
    snapshot=json.loads(r['snapshot'])
    try:
        prompt='''Propose ONE alternative executable editing decision for the OWNED video. Preserve meaning and complete speech. Allowed actions: remove, move_to_front, captions, normalize_audio. Do not generate footage. normalize_audio only normalizes overall mixed-track loudness; it cannot separate voice from music or rebalance their relative levels. Keep the exact target id and link to a real reference DNA range. All other decisions are immutable. Respect creator rules and script. User feedback guides editing, never invent facts. No auto approval. Return Alternative JSON. Context data: '''+json.dumps({'target':r['target'],'feedback':r['instruction'],'context':snapshot['context'],'dna':snapshot['dna'],'plan':snapshot['plan'],'decisions':snapshot['decisions']},ensure_ascii=False)
        alt=ai.json_call(p['id'],settings.data_dir/p['id']/'analysis.mp4',prompt,Alternative,'director_alternative')
        merged(snapshot,alt,r['target'],p['metadata'])
        with connect() as db:db.execute("UPDATE director_proposals SET proposal=?,status='ready' WHERE id=?",(alt.model_dump_json(),r['id']))
    except Exception:
        with connect() as db:db.execute("UPDATE director_proposals SET status='failed' WHERE id=?",(r['id'],))
        raise


@router.post('/projects/{pid}/alternatives/{proposal_id}/accept')
def accept(pid:str,proposal_id:str,body:Accept,user=Depends(current_user)):
    p=owned(pid,user)
    with connect() as db:
        db.lock()
        row=db.execute('SELECT * FROM director_proposals WHERE id=? AND project_id=?',(proposal_id,pid)).fetchone()
        if not row:raise HTTPException(404,'not_found')
        if row['status']!='ready' or row['revision']!=body.revision:raise HTTPException(409,'plan_changed')
        s=check(db,pid,body.revision,row['target'])
        alt=Alternative.model_validate_json(row['proposal'])
        plan=merged(s,alt,row['target'],p['metadata'])
        decisions=[dict(d,approved=False,locked=False,start=alt.recommendation.start,end=alt.recommendation.end) if d['id']==row['target'] else d for d in s['decisions']]
        db.execute('UPDATE studio_projects SET plan=?,decisions=?,revision=revision+1 WHERE project_id=?',(plan.model_dump_json(),json.dumps(decisions),pid))
        db.execute('UPDATE projects SET analysis=? WHERE id=?',(json.dumps(plan.model_dump(exclude={'transfers'})),pid))
        db.execute("UPDATE director_proposals SET status='accepted' WHERE id=?",(proposal_id,))
        db.execute('INSERT INTO events(project_id,kind,detail,created) VALUES(?,?,?,?)',(pid,'director_alternative_accepted',json.dumps({'proposal_id':proposal_id,'target':row['target'],'actor':user['id']}),time.time()))
    return state(pid)
