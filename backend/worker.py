import fcntl
import json
import logging
import time
import uuid
from .config import settings
from .database import worker_guard
from .db import init_db,connect,project,update,event,enqueue
from .schemas import Analysis
from . import media,ai

log=logging.getLogger('lumen.worker')

def progress(pid,stage,value):
    update(pid,stage=stage,progress=value)
    event(pid,'stage',stage)

def analyze_job(p):
    pid=p['id']; folder=settings.data_dir/pid; source=folder/'source'
    update(pid,status='analyzing',error=None)
    progress(pid,'preparing',8)
    if not source.exists():
        from .douyin import import_source
        import_source(p)
    metadata=media.probe(source)
    if metadata['duration']>settings.max_duration_seconds: raise ValueError('video_too_long')
    media.prepare(source,folder)
    metadata['preview_ready']=True
    update(pid,metadata=metadata)
    silences=media.silence_ranges(source,metadata['duration']) if metadata['has_audio'] else []
    progress(pid,'understanding',30)
    analysis=ai.analyze(pid,folder,metadata,p['brief'],p['language'],silences)
    progress(pid,'planning',65)
    selected=[]
    for r in analysis.recommendations:
        safe = r.auto_apply and r.confidence>=0.85 and (p['generative'] or r.action!='generate_broll')
        if r.action=='remove':
            safe = safe and any(s['start']<=r.start and s['end']>=r.end for s in silences)
            safe = safe and not any(c.start<r.end and c.end>r.start for c in analysis.transcript)
        # Persist the verified decision so UI defaults match automatic rendering.
        r.auto_apply = bool(safe)
        if safe: selected.append(r.id)
    update(pid,analysis=analysis.model_dump(),status='ready',stage='ready',progress=100)
    if p['auto_render'] and selected:
        with connect() as db:
            db.execute("UPDATE projects SET status='queued',stage='render_queued',progress=0 WHERE id=?",(pid,))
            enqueue(db,pid,'render',{'recommendations':selected})

def render_job(p,payload):
    pid=p['id']; folder=settings.data_dir/pid
    analysis=Analysis.model_validate(p['analysis'])
    selected=[r for r in analysis.recommendations if r.id in payload['recommendations']]
    if len(selected)!=len(set(payload['recommendations'])): raise ValueError('invalid_recommendation')
    if any(r.action=='generate_broll' for r in selected) and not p['generative']: raise ValueError('generation_not_enabled')
    manual=payload.get('manual')
    if manual: selected=[]
    else: media.build_timeline(p['metadata']['duration'],selected)
    update(pid,status='rendering',error=None)
    progress(pid,'creating',10)
    brolls=[]
    generative=[r for r in selected if r.action=='generate_broll']
    if len(generative)>2: raise ValueError('too_many_generated_clips')
    for r in generative:
        brolls.append(ai.generate_broll(pid,folder,folder/'source',r,p['aspect'] if p['aspect'] in ('16:9','9:16') else ('16:9' if p['metadata']['width']>=p['metadata']['height'] else '9:16')))
    progress(pid,'rendering',40)
    render_id=uuid.uuid4().hex
    render_folder=folder/'renders'/render_id
    render_folder.mkdir(parents=True)
    asset_paths={}
    if manual:
        from .assets import validate as validate_assets
        from .manual import Edit
        with connect() as db:asset_paths=validate_assets(Edit.model_validate(manual),pid,db)
    result=media.render(folder/'source',render_folder,p['metadata'],analysis,selected,p['language'],p['aspect'],brolls,**({'manual':manual,'asset_paths':asset_paths} if manual else {}))
    result['render_id']=render_id
    if asset_paths:
        used_assets={c['external_broll']['asset_id'] for c in manual['clips'] if c['approved'] and c.get('external_broll')}
        if manual.get('music'):used_assets.add(manual['music']['asset_id'])
        with connect() as db:
            result['asset_credits']=[{'asset_id':ident,'title':row['title'],'attribution':row['attribution']} for ident in sorted(used_assets) if (row:=db.execute('SELECT title,attribution FROM studio_assets WHERE id=? AND project_id=?',(ident,pid)).fetchone())]
    progress(pid,'checking',85)
    try:
        if manual and not payload.get('quality_review'): raise ValueError('manual_review_required')
        qa=ai.review(pid,render_folder,p['brief'],manual if manual else [r.model_dump() for r in selected])
        result['qa']=qa.model_dump()
        score=round(sum(s.value for s in qa.scores)/len(qa.scores),1) if getattr(qa,'scores',None) else None
        result['quality_score']=score
        result['qa_status']='passed' if qa.passed and (score is None or score>=75) else 'needs_review'
    except Exception as exc:
        result['qa']=None; result['qa_status']='unavailable'
        if manual and not payload.get('quality_review'):
            result['qa_status']='manual_review_required'
        else: event(pid,'quality_review_unavailable',safe_error(exc))
    if manual:result['manual_transcript']=manual['captions'] if manual['subtitles'] else []
    # A failed quality review is never published as approved.
    status='complete' if result['qa_status']=='passed' else 'needs_review'
    update(pid,result=result,status=status,stage=status,progress=100)
    event(pid,'render_complete',json.dumps({'applied':result['applied'],'quality':result['qa_status']}))

def safe_error(exc):
    allowed={'douyin_not_configured','douyin_daily_limit','douyin_auth_failed','douyin_credits_required','douyin_rate_limited','douyin_search_failed','douyin_media_unavailable','upload_too_large','budget_limit','not_a_video','invalid_duration','resolution_too_large','video_too_long','provider_not_configured',
    'provider_credits_required','provider_auth_failed','provider_request_failed','provider_invalid_analysis','provider_analysis_truncated','analysis_timestamps_invalid',
    'analysis_duplicate_ids','analysis_multiple_hooks','hook_overlaps_cut','too_much_removed','generation_submission_uncertain',
    'generation_request_failed','generation_poll_failed','generation_failed','generation_timed_out','generation_not_enabled',
    'media_processing_failed','output_audio_missing','output_duration_mismatch','too_many_generated_clips'}
    return str(exc) if str(exc) in allowed else 'processing_failed'

def run_once():
    with connect() as db:
        db.lock()
        row=db.execute("SELECT * FROM jobs WHERE status='queued' ORDER BY created LIMIT 1").fetchone()
        if not row: return False
        job=dict(row)
        db.execute("UPDATE jobs SET status='running',updated=? WHERE id=?",(time.time(),job['id']))
    p=project(job['project_id'])
    try:
        if job['kind']=='analyze': analyze_job(p)
        elif job['kind']=='render': render_job(p,json.loads(job['payload']))
        elif job['kind']=='studio_analyze':
            from .studio import analyze
            analyze(p)
        elif job['kind']=='studio_render':
            from .studio import render_job as studio_render
            studio_render(p,json.loads(job['payload']))
        elif job['kind']=='creative_plan':
            from .creative_plans import run_job as creative_job
            creative_job(p,json.loads(job['payload']))
        elif job['kind']=='music_plan':
            from .music_plans import run_job as music_job
            music_job(p,json.loads(job['payload']))
        elif job['kind']=='stock_discover':
            from .stock_discovery import run_job as discovery_job
            discovery_job(p,json.loads(job['payload']))
        elif job['kind']=='stock_import':
            from .stock import run_job as stock_job
            stock_job(p,json.loads(job['payload']))
        elif job['kind']=='timeline_proposal':
            from .timeline_proposals import run_job as timeline_proposal_job
            timeline_proposal_job(p,json.loads(job['payload']))
        elif job['kind']=='director_alternative':
            from .director_revisions import run_job as alternative_job
            alternative_job(p,json.loads(job['payload']))
        elif job['kind']=='platform_variants':
            from .variants import run_job
            run_job(p,json.loads(job['payload']))
        else: raise ValueError('unknown_job')
        state='complete'
    except Exception as exc:
        code=safe_error(exc)
        log.error('Job %s failed: %s (%s)',job['id'],code,type(exc).__name__)
        if job['kind'] not in ('platform_variants','director_alternative','timeline_proposal','creative_plan','music_plan','stock_import','stock_discover'): update(p['id'],status='failed',stage='failed',error=code)
        event(p['id'],'failed',code)
        state='failed'
    with connect() as db:
        db.execute('UPDATE jobs SET status=?,updated=? WHERE id=?',(state,time.time(),job['id']))
    return True

def serve(guard):
    init_db()
    lock=(settings.data_dir/'worker.lock').open('w')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    # Do not auto-replay ambiguous paid calls after process death.
    with connect() as db:
        for row in db.execute("SELECT project_id,kind,payload FROM jobs WHERE status='running'"):
            if row["kind"]=="stock_discover":
                db.execute("UPDATE stock_discoveries SET status='failed',error='worker_interrupted' WHERE id=?",(json.loads(row['payload'])['id'],))
            elif row["kind"]=="stock_import":
                db.execute("UPDATE stock_imports SET status='failed',error='worker_interrupted' WHERE id=?",(json.loads(row['payload'])['id'],))
            elif row["kind"]=="music_plan":
                db.execute("UPDATE music_plans SET status='failed' WHERE project_id=? AND status='queued'",(row[0],))
            elif row["kind"]=="creative_plan":
                db.execute("UPDATE creative_plans SET status='failed',error='worker_interrupted' WHERE project_id=? AND status='queued'",(row[0],))
            elif row["kind"]=="timeline_proposal":
                db.execute("UPDATE timeline_proposals SET status='failed' WHERE project_id=? AND status='queued'",(row[0],))
            elif row["kind"]=="director_alternative":
                db.execute("UPDATE director_proposals SET status='failed' WHERE project_id=? AND status='queued'",(row[0],))
            elif row["kind"]=="platform_variants":
                db.execute("UPDATE platform_packages SET status='failed' WHERE project_id=?",(row[0],))
            else:
                db.execute("UPDATE projects SET status='failed',stage='failed',error='worker_interrupted' WHERE id=?",(row[0],))
        db.execute("UPDATE jobs SET status='failed' WHERE status='running'")
    while True:
        if guard is not None: guard.execute('SELECT 1')
        (settings.data_dir/'worker.heartbeat').write_text(str(time.time()))
        if not run_once(): time.sleep(2)

def main():
    with worker_guard() as guard:
        serve(guard)

if __name__=='__main__':
    logging.basicConfig(level=logging.INFO)
    main()
