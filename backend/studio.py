"""Reference-to-owned-footage projects. Legacy projects remain unchanged."""
import json
import re
import shutil
import time
import uuid
from pathlib import Path
from typing import Literal
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import Field, ValidationError
from starlette.concurrency import run_in_threadpool
from .auth import current_user
from .config import settings
from .db import connect, enqueue, project, update
from .schemas import Strict, Text, Span, Analysis, Recommendation
from . import media, ai, douyin

router=APIRouter(prefix='/api/studio')
PLATFORMS=['douyin','instagram_reels','youtube_shorts','tiktok','xiaohongshu']

from .creator_style import Style

class Creator(Strict):
    style: Style=Field(default_factory=Style)
    topic: Literal['real_estate','citizenship','travel']
    audience: str=Field(min_length=1,max_length=1000)
    tone: str=Field(min_length=1,max_length=1000)
    rules: str=Field(default='',max_length=2000)

class EffectSwitches(Strict):
    blur: bool=True
    glow: bool=True
    shadow: bool=True
    color: bool=True
    speed: bool=True
    stabilize: bool=True
    kinetic: bool=True
    progress: bool=True
    split: bool=True
    screen: bool=True

class EffectBoard(Strict):
    name: Literal['clean','punch','soft','kinetic','split']='clean'
    amount: float=Field(default=1,ge=0.4,le=1.6)
    effects: EffectSwitches=Field(default_factory=EffectSwitches)

class Create(Strict):
    request_id: str=Field(pattern=r'^[a-f0-9]{32}$')
    references: list[str]=Field(default_factory=list,max_length=5)
    reference_upload_id: str=Field(default='',max_length=32)
    title: str=Field(min_length=1,max_length=120)
    script: str=Field(min_length=1,max_length=6000)
    creator: Creator
    language: Literal['en','zh']='en'
    budget: float=Field(default=5,ge=1,le=10)
    concept_id: str=Field(default='',max_length=32)
    style_match: bool=False
    effect_board: EffectBoard | None=None
    owned_rights_confirmed: Literal[True]

class Shot(Span):
    observation: Text
    visual_type: Text
    narrative_role: Text
    motion: Text
    transition: Text
    subtitle_emphasis: Text
    music: Text
    emotion: Text
    information_density: Text
    reusable_method: Text

class DNA(Strict):
    summary: Text
    shots: list[Shot]=Field(min_length=1,max_length=50)
    uncertainties: list[Text]=Field(max_length=8)

class Transfer(Strict):
    recommendation_id: str
    reference_id: str
    reference_start: float=Field(ge=0)
    reference_end: float=Field(gt=0)
    method: Text
    fit: Text

class Director(Analysis):
    transfers: list[Transfer]=Field(max_length=12)

class Decision(Strict):
    id: str
    approved: bool
    locked: bool
    start: float=Field(ge=0)
    end: float=Field(gt=0)

class PlanEdit(Strict):
    revision: int=Field(ge=1)
    decisions: list[Decision]=Field(max_length=12)

class RenderPlan(Strict):
    revision: int=Field(ge=1)

def init(db):
    from .uploads import init as init_uploads
    init_uploads(db)
    from .manual import init as init_manual
    init_manual(db)
    db.execute('''CREATE TABLE IF NOT EXISTS studio_projects(
      project_id TEXT PRIMARY KEY REFERENCES projects(id) ON DELETE CASCADE,
      context TEXT NOT NULL, dna TEXT NOT NULL DEFAULT '[]', plan TEXT,
      decisions TEXT NOT NULL DEFAULT '[]', revision INTEGER NOT NULL DEFAULT 0)''')
    db.execute('''CREATE TABLE IF NOT EXISTS studio_requests(user_id TEXT NOT NULL REFERENCES users(id), token TEXT NOT NULL, project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE, PRIMARY KEY(user_id,token))''')

def state(pid,db=None):
    if db is None:
        with connect() as conn:return state(pid,conn)
    row=db.execute('SELECT * FROM studio_projects WHERE project_id=?',(pid,)).fetchone()
    if not row:return None
    return {k:(json.loads(row[k]) if row[k] is not None else None) for k in ('context','dna','plan','decisions')}|{'revision':row['revision']}

def owned(pid,user):
    p=project(pid,user['id'])
    if not p or not state(pid):raise HTTPException(404,'not_found')
    return p

@router.post('/projects',status_code=201)
async def create(request:Request,config:str=Form(...),file:UploadFile=File(...),user=Depends(current_user),reference:UploadFile|None=File(None)):
    from .app import rate_limit
    rate_limit(request,'studio_create',8,3600)
    try:body=Create.model_validate_json(config)
    except ValidationError:raise HTTPException(422,'invalid_settings') from None
    with connect() as db:
        existing=db.execute('SELECT project_id FROM studio_requests WHERE user_id=? AND token=?',(user['id'],body.request_id)).fetchone()
    if existing:
        await file.close()
        return project(existing['project_id'],user['id'])
    if body.concept_id and not re.fullmatch(r'[a-f0-9]{32}',body.concept_id):raise HTTPException(422,'invalid_settings')
    if body.reference_upload_id and not re.fullmatch(r'[a-f0-9]{32}',body.reference_upload_id):raise HTTPException(422,'invalid_settings')
    has_reference_file=reference is not None and bool(getattr(reference,'filename',None))
    if not body.references and not body.reference_upload_id and not has_reference_file:raise HTTPException(422,'invalid_settings')
    if len(set(body.references))!=len(body.references):raise HTTPException(422,'invalid_settings')
    try:refs=[douyin.owned_result(r,user['id']) for r in body.references] if body.references else []
    except douyin.DouyinError as exc:raise HTTPException(422,str(exc)) from None
    if len({r['aweme_id'] for r in refs})!=len(refs):raise HTTPException(422,'duplicate_reference')
    if shutil.disk_usage(settings.data_dir).free<1.5*1024**3:raise HTTPException(507,'storage_full')
    used=await run_in_threadpool(lambda:sum(p.stat().st_size for p in settings.data_dir.rglob('*') if p.is_file()))
    if used>settings.max_storage_gb*1024**3:raise HTTPException(507,'storage_full')
    pid=uuid.uuid4().hex;folder=settings.data_dir/pid;folder.mkdir()
    try:
        size=0
        with (folder/'source').open('wb') as out:
            while chunk:=await file.read(1024*1024):
                size+=len(chunk)
                if size>settings.max_upload_mb*1024*1024:raise HTTPException(413,'upload_too_large')
                out.write(chunk)
        try:meta=await run_in_threadpool(media.probe,folder/'source')
        except Exception:raise HTTPException(422,'not_a_video') from None
        if not 30<=meta['duration']<=settings.max_duration_seconds:raise HTTPException(422,'owned_duration')
        if meta['height']<=meta['width']:raise HTTPException(422,'owned_vertical')
        context=body.model_dump(exclude={'references','concept_id','reference_upload_id'})
        context['platforms']=PLATFORMS
        context['references']=[{k:r[k] for k in ('aweme_id','title','author','share_url','duration')}|{'role':'reference_only'} for r in refs]
        if has_reference_file or body.reference_upload_id:
            dest=folder/'reference_source'
            if has_reference_file:
                ref_size=0
                with dest.open('wb') as out:
                    while chunk:=await reference.read(1024*1024):
                        ref_size+=len(chunk)
                        if ref_size>settings.max_upload_mb*1024*1024:raise HTTPException(413,'upload_too_large')
                        out.write(chunk)
            else:
                from .uploads import owned as upload_owned, path as upload_path
                with connect() as db: upload_owned(db, body.reference_upload_id, user)
                shutil.copy(upload_path(body.reference_upload_id), dest)
                with connect() as db: db.execute('DELETE FROM studio_uploads WHERE id=? AND user_id=?',(body.reference_upload_id,user['id']))
                upload_path(body.reference_upload_id).unlink(missing_ok=True)
            try: await run_in_threadpool(media.probe, dest)
            except Exception: raise HTTPException(422,'not_a_video') from None
            context['reference_file']=True
            context['style_match']=True
        now=time.time()
        with connect() as db:
            db.lock()
            existing=db.execute('SELECT project_id FROM studio_requests WHERE user_id=? AND token=?',(user['id'],body.request_id)).fetchone()
            if existing:
                shutil.rmtree(folder,ignore_errors=True)
                return project(existing['project_id'],user['id'])
            count=db.execute("SELECT COUNT(*) FROM projects WHERE user_id=? AND status IN ('queued','analyzing','rendering')",(user['id'],)).fetchone()[0]
            if count>=3:raise HTTPException(429,'too_many_jobs')
            db.execute('INSERT INTO projects(id,user_id,title,brief,language,aspect,auto_render,generative,budget,status,stage,metadata,created,updated) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(pid,user['id'],body.title,body.script,body.language,'original',0,0,body.budget,'queued','queued',json.dumps(meta),now,now))
            db.execute('INSERT INTO studio_projects(project_id,context) VALUES(?,?)',(pid,json.dumps(context,ensure_ascii=False)))
            db.execute('INSERT INTO studio_requests VALUES(?,?,?)',(user['id'],body.request_id,pid))
            if body.concept_id:
                from .trends import attach_concept
                attach_concept(db,user['id'],pid,body.concept_id)
            enqueue(db,pid,'studio_analyze')
    except Exception:
        shutil.rmtree(folder,ignore_errors=True);raise
    finally:
        await file.close()
        if hasattr(reference, 'close'): await reference.close()
    return project(pid,user['id'])

@router.get('/projects/{pid}')
def detail(pid:str,user=Depends(current_user)):
    owned(pid,user);return state(pid)

@router.put('/projects/{pid}/effect-board')
def save_effect_board(pid:str,body:EffectBoard,user=Depends(current_user)):
    """Store the visual-effect recipe on the project. A finished file does not lock it."""
    owned(pid,user)
    with connect() as db:
        db.lock()
        current=state(pid,db)
        context=current['context']
        if 'effect_board_in_edit' not in context:
            context['effect_board_in_edit']=json.loads(json.dumps(context.get('effect_board')))
        context['effect_board']=body.model_dump()
        db.execute('UPDATE studio_projects SET context=? WHERE project_id=?',(json.dumps(context,ensure_ascii=False),pid))
    return {'effect_board':context['effect_board']}

@router.get('/projects/{pid}/references/{reference_id}')
def reference_media(pid:str,reference_id:str,user=Depends(current_user)):
    owned(pid,user);s=state(pid)
    if reference_id not in [r['aweme_id'] for r in s['context']['references']]:raise HTTPException(404,'not_found')
    path=settings.data_dir/pid/'references'/reference_id/'analysis.mp4'
    if not path.is_file():raise HTTPException(404,'not_ready')
    return FileResponse(path,media_type='video/mp4')

@router.put('/projects/{pid}/plan')
def edit(pid:str,body:PlanEdit,user=Depends(current_user)):
    p=owned(pid,user)
    with connect() as db:
        db.lock();s=state(pid,db)
        if db.execute("SELECT 1 FROM jobs WHERE project_id=? AND status IN ('queued','running')",(pid,)).fetchone():raise HTTPException(409,'job_already_running')
        if s['revision']!=body.revision or not s['plan']:raise HTTPException(409,'plan_changed')
        recs={r['id']:r for r in s['plan']['recommendations']};old={r['id']:r for r in s['decisions']}
        decisions=[d.model_dump() for d in body.decisions]
        if len(decisions)!=len(recs) or {d['id'] for d in decisions}!=set(recs):raise HTTPException(422,'invalid_recommendation')
        selected=[]
        for d in decisions:
            before=old[d['id']]
            if before['locked'] and any(before[k]!=d[k] for k in ('start','end','approved')):raise HTTPException(409,'locked_decision')
            if d['locked'] and not d['approved']:raise HTTPException(422,'lock_requires_approval')
            if d['end']<=d['start'] or d['end']>p['metadata']['duration']:raise HTTPException(422,'analysis_timestamps_invalid')
            if recs[d['id']]['action'] in ('captions','normalize_audio') and (d['start']!=before['start'] or d['end']!=before['end']):raise HTTPException(422,'whole_clip_action')
            if d['approved']:selected.append(Recommendation.model_validate(recs[d['id']]|{'start':d['start'],'end':d['end']}))
        try:media.build_timeline(p['metadata']['duration'],selected)
        except ValueError as exc:raise HTTPException(422,str(exc)) from None
        db.execute('UPDATE studio_projects SET decisions=?,revision=revision+1 WHERE project_id=?',(json.dumps(decisions),pid))
    return state(pid)

@router.post('/projects/{pid}/render')
def render(pid:str,body:RenderPlan,request:Request,user=Depends(current_user)):
    from .app import rate_limit
    rate_limit(request,'render',12,3600);p=owned(pid,user)
    with connect() as db:
        db.lock();s=state(pid,db)
        if not s['plan'] or s['revision']!=body.revision:raise HTTPException(409,'plan_changed')
        if db.execute("SELECT 1 FROM jobs WHERE project_id=? AND status IN ('queued','running')",(pid,)).fetchone():raise HTTPException(409,'job_already_running')
        selected=[d for d in s['decisions'] if d['approved']]
        if not selected:raise HTTPException(422,'no_approved_changes')
        from .render_audio import summary as audio_summary
        approved={d['id']:d for d in selected}
        recs=[Recommendation.model_validate(r|{'start':approved[r['id']]['start'],'end':approved[r['id']]['end']}) for r in s['plan']['recommendations'] if r['id'] in approved]
        audio=audio_summary(db,p,media.build_timeline(p['metadata']['duration'],recs))
        if audio and audio.get('error'):raise HTTPException(422,audio['error'])
        enqueue(db,pid,'studio_render',{'revision':s['revision'],'plan':s['plan'],'decisions':selected})
        db.execute("UPDATE projects SET status='queued',stage='render_queued',progress=0,error=NULL WHERE id=?",(pid,))
    return {'ok':True}

def analyze(p):
    pid=p['id'];folder=settings.data_dir/pid;s=state(pid);context=s['context']
    update(pid,status='analyzing',stage='preparing',progress=5,error=None)
    meta=media.probe(folder/'source');media.prepare(folder/'source',folder)
    update(pid,metadata=meta|{'preview_ready':True})
    dna=s['dna']
    for ref in context['references']:
        if any(d['reference_id']==ref['aweme_id'] for d in dna):continue
        update(pid,stage='reference_analysis',progress=10+int(40*len(dna)/len(context['references'])))
        dest=folder/'references'/ref['aweme_id'];dest.mkdir(parents=True,exist_ok=True)
        if not (dest/'source').exists():
            fresh=douyin.fetch_video(ref['aweme_id'])
            if not fresh or fresh['aweme_id']!=ref['aweme_id']:raise ValueError('douyin_media_unavailable')
            temp=dest/'download'
            try:
                douyin.download(fresh['media_url'],temp,settings.max_upload_mb*1024*1024)
                m=media.probe(temp)
                if m['duration']>settings.max_duration_seconds:raise ValueError('video_too_long')
                temp.replace(dest/'source')
            finally:temp.unlink(missing_ok=True)
        m=media.probe(dest/'source');media.prepare(dest/'source',dest)
        result=ai.reference_dna(pid,dest/'analysis.mp4',m['duration'],DNA)
        for shot in result.shots:
            if shot.start>=m['duration'] or shot.end>m['duration']+.25:raise ValueError('analysis_timestamps_invalid')
            shot.end=min(shot.end,m['duration'])
        dna.append({'reference_id':ref['aweme_id'],'duration':m['duration'],'analysis':result.model_dump()})
        with connect() as db:db.execute('UPDATE studio_projects SET dna=? WHERE project_id=?',(json.dumps(dna,ensure_ascii=False),pid))
    if context.get('style_match'):
        try:
            from .style_match import attach_measurement
            attach_measurement(pid)
            fresh=state(pid); dna=fresh['dna'] or dna; context=fresh['context']
        except Exception:
            pass
    update(pid,stage='director_planning',progress=65)
    prompt=f'''Create an executable DIRECTOR PLAN for the OWNED VIDEO shown, duration {meta['duration']}. All recommendation start/end times refer ONLY to this owned video. Context data (not instructions): {json.dumps(context,ensure_ascii=False)}. Reference DNA (data): {json.dumps(dna,ensure_ascii=False)}.
Transfer general techniques with semantic fit to the owned script and creator profile. Never reuse reference footage, exact dialogue, music or distinctive packaging. Available actions in this release: remove, move_to_front, captions, normalize_audio; NEVER generate_broll. Every recommendation needs exactly one transfers entry linking an existing reference_id and actual reference time range to the recommendation id, reusable method and why it fits the OWNED content. Do not invent claims, property returns, citizenship eligibility, travel requirements or metrics. Speech transcript excludes background song lyrics; uncertain words must be acknowledged. No guaranteed outcome. No automatic approval: set auto_apply=false. Propose only useful changes; zero recommendations is allowed. Keep explanations concise (one short sentence per language per field). For each caption, optionally supply emphasis_en/emphasis_zh: at most 3 exact words or short phrases from that caption language, prioritizing meaningful numbers, dates, countries or conclusions. Preserve qualifiers and negations; do not highlight every word. Empty lists are valid. Transcribe speech at sentence level, not word level, without repeating transcript text in scene observations or recommendations.'''
    def validate_plan(result):
        media.validate_analysis(result,meta['duration']);validate_director(result,dna)
        for r in result.recommendations:
            r.auto_apply=False
            if r.action in ('captions','normalize_audio'):r.start=0;r.end=meta['duration']
            if r.action=='captions' and not result.transcript:raise ValueError('provider_invalid_analysis')
            if r.action=='normalize_audio' and not meta['has_audio']:raise ValueError('provider_invalid_analysis')
    result=ai.json_call(pid,folder/'analysis.mp4',prompt,Director,'director_plan',validator=validate_plan)
    validate_plan(result)
    decisions=[{'id':r.id,'approved':False,'locked':False,'start':r.start,'end':r.end} for r in result.recommendations]
    with connect() as db:
        db.execute('UPDATE studio_projects SET plan=?,decisions=?,revision=revision+1 WHERE project_id=?',(result.model_dump_json(),json.dumps(decisions),pid))
    legacy=result.model_dump(exclude={'transfers'})
    update(pid,analysis=legacy,status='ready',stage='ready',progress=100)
    if context.get('style_match'):
        try:
            from .style_match import match_project
            match_project(pid)
        except Exception:
            from .style_match import record_failure
            record_failure(pid)
    # DNA and source analysis feed the executable decision pass automatically.
    from .creative_plans import queue_plan
    with connect() as db:
        db.lock();current=state(pid,db)
        if not db.execute('SELECT 1 FROM creative_plans WHERE project_id=? AND revision=?',(pid,current['revision'])).fetchone():
            queue_plan(db,pid,current)

def validate_director(result,dna):
    refs={d['reference_id']:d['duration'] for d in dna}
    ids={r.id for r in result.recommendations}
    if len(result.transfers)!=len(ids) or {t.recommendation_id for t in result.transfers}!=ids:raise ValueError('provider_invalid_analysis')
    if any(r.action=='generate_broll' for r in result.recommendations):raise ValueError('provider_invalid_analysis')
    for t in result.transfers:
        if t.reference_id not in refs or not 0<=t.reference_start<t.reference_end<=refs[t.reference_id]:raise ValueError('analysis_timestamps_invalid')

def render_job(p,payload):
    if payload.get('manual'):
        try:
            current = state(p['id'])
            if current.get('context', {}).get('style_match'):
                from .style_pictures import attach_art
                payload['manual'] = attach_art(p['id'], payload['manual'])
        except Exception:
            pass
    from .worker import render_job as legacy_render
    plan=payload['plan'];decisions={d['id']:d for d in payload['decisions']}
    analysis=Analysis.model_validate({k:v for k,v in plan.items() if k!='transfers'})
    for r in analysis.recommendations:
        if r.id in decisions:r.start=decisions[r.id]['start'];r.end=decisions[r.id]['end']
    # The renderer can only read owned source; reference files never enter inputs.
    legacy_render(p|{'analysis':analysis.model_dump()}, {'recommendations':list(decisions),**({'quality_review':True} if payload.get('quality_review') else {}),**({'manual':payload['manual']} if payload.get('manual') else {})})
    if state(p['id']).get('context',{}).get('style_match'):
        try:
            from .style_match import score_output
            score_output(p['id'])
        except Exception:
            pass
    result=project(p['id'])['result'];result['plan_revision']=payload['revision']
    update(p['id'],result=result)
    if payload.get('quality_review') and result.get('qa_status')=='needs_review' and result.get('qa',{}).get('revisions'):
        from .creative_plans import queue_plan
        with connect() as db:
            db.lock();current=state(p['id'],db)
            if current['revision']==payload['revision'] and not any(d['locked'] for d in current['decisions']):
                from .ai import quality_edit_context
                feedback={'revisions':result['qa']['revisions'],'render_id':result['render_id'],
                          'render_timeline':result['timeline'],'quality_comparison':result.get('quality_comparison'),
                          'output_timeline':quality_edit_context(payload['manual'])['final_output_timeline'] if payload.get('manual') else None}
                ident=queue_plan(db,p['id'],current,'Improve the prior rendered edit using quality_feedback. Review timestamps refer to OUTPUT. Preserve correct content.',quality_feedback=feedback)
                result['quality_revision_id']=ident
            else:result['quality_revision_blocked']='locked_or_changed'
        update(p['id'],result=result)
