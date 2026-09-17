"""Source-only manual edits, versioned with the director plan. No AI calls."""
import json
import uuid
from typing import Literal
from fastapi import APIRouter,Depends,HTTPException,Request
from pydantic import Field
from .schemas import Strict,Span,Caption
from .auth import current_user
from .db import connect,enqueue
from .visuals import VisualCard
from .sound_effects import SoundEffect,DURATIONS
from .music import Music

router=APIRouter(prefix='/api/studio')
class Cutaway(Span):
    source_start: float=Field(ge=0)

class ExternalBroll(Cutaway):
    asset_id:str=Field(pattern=r'^[a-f0-9]{32}$')

class Clip(Span):
    sound_effects:list[SoundEffect]=Field(default_factory=list,max_length=4)
    external_broll: ExternalBroll | None=None
    cutaway: Cutaway | None=None
    card: VisualCard | None=None
    id: str=Field(default_factory=lambda:uuid.uuid4().hex,pattern=r'^[a-zA-Z0-9_-]{1,64}$')
    approved: bool=True
    locked: bool=False
    shot_type: Literal['presenter','close_up','medium','broll','document','archive','news']='presenter'
    zoom_end: float | None=Field(default=None,ge=1,le=3)
    x_end: float | None=Field(default=None,ge=0,le=1)
    y_end: float | None=Field(default=None,ge=0,le=1)
    audio_fade_ms: int=Field(default=0,ge=0,le=100)
    transition: Literal['cut','fade','crossfade','zoom','wipe','circle']='cut'

    zoom: float=Field(default=1,ge=1,le=3)
    x: float=Field(default=.5,ge=0,le=1)
    y: float=Field(default=.5,ge=0,le=1)
    text: str=Field(default='',max_length=160)
class Edit(Strict):
    music: Music | None=None
    clips: list[Clip]=Field(min_length=1,max_length=40)
    captions: list[Caption]=Field(default_factory=list,max_length=160)
    subtitles: bool=False
    normalize: bool=False
    font_size: Literal['small','medium','large']='medium'
    position: Literal['bottom','top']='bottom'
    color: Literal['white','yellow']='white'
class Save(Strict):
    revision: int=Field(ge=1)
    edit: Edit
class Render(Strict):
    revision: int=Field(ge=1)
    quality_review:bool=False

def init(db):
    from .music_plans import init as init_music_plans
    init_music_plans(db)
    from .creative_plans import init as init_creative
    init_creative(db)
    from .assets import init as init_assets
    init_assets(db)
    from .timeline_proposals import init as init_proposals
    init_proposals(db)
    db.execute('CREATE TABLE IF NOT EXISTS studio_manual(project_id TEXT PRIMARY KEY REFERENCES projects(id) ON DELETE CASCADE,config TEXT NOT NULL)')
def read(pid,db):
    row=db.execute('SELECT config FROM studio_manual WHERE project_id=?',(pid,)).fetchone()
    if not row:return None
    config=json.loads(row[0])
    for i,c in enumerate(config['clips']):c.setdefault('id',f'legacy_{i}')
    return Edit.model_validate(config).model_dump()

def check(edit,duration):
    for c in edit.clips:
        if any(e.at+DURATIONS[e.kind]>c.end-c.start for e in c.sound_effects):raise HTTPException(422,'invalid_sound_range')
        if c.external_broll and (c.cutaway or c.external_broll.end>c.end-c.start or c.external_broll.end-c.external_broll.start<.08):raise HTTPException(422,'invalid_cutaway_range')
        if c.cutaway and (c.cutaway.end>c.end-c.start or c.cutaway.end-c.cutaway.start<.08 or c.cutaway.source_start+c.cutaway.end-c.cutaway.start>duration):raise HTTPException(422,'invalid_cutaway_range')
        if c.card and (c.card.end>c.end-c.start or c.card.end-c.card.start<.5):raise HTTPException(422,'invalid_card_range')
        if c.card and c.card.kind=='comparison' and not c.card.secondary:raise HTTPException(422,'comparison_requires_two_values')
    ids=[c.id for c in edit.clips]
    if len(ids)!=len(set(ids)):raise HTTPException(422,'duplicate_decision')
    if any(c.locked and not c.approved for c in edit.clips):raise HTTPException(422,'lock_requires_approval')
    if any(c.end>duration or c.end-c.start<.08 for c in edit.clips):raise HTTPException(422,'invalid_clip_range')
    if sum(c.end-c.start for c in edit.clips)>duration*2:raise HTTPException(422,'manual_cut_too_long')
    if any(c.end>duration for c in edit.captions):raise HTTPException(422,'invalid_caption_range')
    if edit.subtitles and (not edit.captions or any(not (c.en.strip() or c.zh.strip() or c.original.strip()) for c in edit.captions)):raise HTTPException(422,'captions_required')

def locked_state(pid,revision,db):
    from .studio import state
    s=state(pid,db)
    if not s or not s['plan'] or revision!=s['revision']:raise HTTPException(409,'plan_changed')
    if db.execute("SELECT 1 FROM jobs WHERE project_id=? AND status IN ('queued','running')",(pid,)).fetchone():raise HTTPException(409,'job_already_running')
    return s

@router.get('/projects/{pid}/manual')
def get(pid:str,user=Depends(current_user)):
    from .studio import owned,state
    p=owned(pid,user)
    with connect() as db:
        s=state(pid,db);edit=read(pid,db);saved=edit is not None
    if edit is None:
        edit=Edit(clips=[Clip(start=0,end=p['metadata']['duration'])],captions=(s['plan'] or {}).get('transcript',[])).model_dump()
    from .timeline import compile_timeline
    return {'revision':s['revision'],'edit':edit,'saved':saved,'timeline':compile_timeline(Edit.model_validate(edit))}

@router.put('/projects/{pid}/manual')
def save(pid:str,body:Save,user=Depends(current_user)):
    from .studio import owned
    p=owned(pid,user);check(body.edit,p['metadata']['duration'])
    with connect() as db:
        db.lock();locked_state(pid,body.revision,db)
        from .assets import validate as validate_assets
        validate_assets(body.edit,pid,db)
        old=read(pid,db)
        if old:
            previous_music=old.get('music')
            if previous_music and previous_music.get('locked'):
                incoming_music=body.edit.music.model_dump() if body.edit.music else None
                if incoming_music not in (previous_music,previous_music|{'locked':False}):raise HTTPException(409,'locked_decision')
            incoming={c.id:(i,c.model_dump()) for i,c in enumerate(body.edit.clips)}
            for i,c in enumerate(old['clips']):
                if not c['locked']:continue
                match=incoming.get(c['id'])
                if not match or match[0]!=i or any(match[1][k]!=v for k,v in c.items() if k!='locked'):
                    raise HTTPException(409,'locked_decision')
        db.execute('INSERT INTO studio_manual(project_id,config) VALUES(?,?) ON CONFLICT(project_id) DO UPDATE SET config=excluded.config',(pid,body.edit.model_dump_json()))
        db.execute('UPDATE studio_projects SET revision=revision+1 WHERE project_id=?',(pid,))
    return {'revision':body.revision+1,'edit':body.edit.model_dump()}

class BeatPreview(Strict):
    revision:int=Field(ge=1)

@router.post('/projects/{pid}/manual/beat-preview')
def beat_preview(pid:str,body:BeatPreview,user=Depends(current_user)):
    from .studio import owned
    from .beat_edit import propose
    p=owned(pid,user)
    with connect() as db:
        db.lock();s=locked_state(pid,body.revision,db)
        saved=read(pid,db)
        if not saved:raise HTTPException(422,'save_manual_first')
        edit=Edit.model_validate(saved)
        if not edit.music:raise HTTPException(422,'music_required')
        if any(not c.approved for c in edit.clips):raise HTTPException(422,'approve_shots_first')
        row=db.execute('SELECT metadata FROM studio_assets WHERE id=? AND project_id=?',(edit.music.asset_id,pid)).fetchone()
        if not row:raise HTTPException(422,'asset_not_found')
        metadata=json.loads(row['metadata']);rhythm=metadata.get('rhythm')
        if not rhythm:raise HTTPException(422,'analyze_rhythm_first')
        speech=[Caption.model_validate(c) for c in s['plan'].get('transcript',[])]+edit.captions
        skipped=[]
        proposal,changes=propose(edit,rhythm['accents'],metadata['duration'],speech,skipped)
        check(proposal,p['metadata']['duration'])
    return {'revision':body.revision,'edit':proposal.model_dump(),'changes':changes,'skipped':skipped}

@router.post('/projects/{pid}/manual/render')
def render(pid:str,body:Render,request:Request,user=Depends(current_user)):
    from .studio import owned
    from .app import rate_limit
    rate_limit(request,'render',12,3600)
    p=owned(pid,user)
    with connect() as db:
        db.lock();s=locked_state(pid,body.revision,db);edit=read(pid,db)
        if edit is None:raise HTTPException(422,'save_manual_first')
        check(Edit.model_validate(edit),p['metadata']['duration'])
        from .assets import validate as validate_assets
        validate_assets(Edit.model_validate(edit),pid,db)
        if not any(c['approved'] for c in edit['clips']):raise HTTPException(422,'no_approved_changes')
        enqueue(db,pid,'studio_render',{'revision':s['revision'],'plan':s['plan'],'decisions':[],'manual':edit,'quality_review':body.quality_review})
        db.execute("UPDATE projects SET status='queued',stage='render_queued',progress=0,error=NULL WHERE id=?",(pid,))
    return {'ok':True}

@router.post('/projects/{pid}/manual/from-plan')
def from_plan(pid:str,body:Render,user=Depends(current_user)):
    from .studio import owned
    from .schemas import Recommendation
    from .media import build_timeline
    p=owned(pid,user)
    with connect() as db:
        db.lock();s=locked_state(pid,body.revision,db)
        approved={d['id']:d for d in s['decisions'] if d['approved']}
        recs=[Recommendation.model_validate(r|{'start':approved[r['id']]['start'],'end':approved[r['id']]['end']}) for r in s['plan']['recommendations'] if r['id'] in approved]
        timeline=build_timeline(p['metadata']['duration'],recs)
    edit=Edit(clips=[Clip(start=a,end=b) for a,b in timeline],captions=s['plan']['transcript'],subtitles=any(r.action=='captions' for r in recs),normalize=any(r.action=='normalize_audio' for r in recs))
    return {'revision':s['revision'],'edit':edit.model_dump()}
