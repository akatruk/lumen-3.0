import fcntl
import json
import logging
import sys
import time
import uuid
from .config import settings
from .database import worker_guard
from .db import init_db,connect,project,update,event,enqueue
from .schemas import Analysis
from . import media,ai

log=logging.getLogger('lumen.worker')

# Create-video / Remotion steps shown in the live activity card (not analysis).
RENDER_ACTIVITY = (
    'preparing_voice', 'creating', 'preparing_picture', 'matching_music',
    'drawing_graphics', 'rendering', 'rendering_shots', 'assembling',
    'mixing_music', 'burning_captions', 'writing_file', 'checking', 'render_queued',
)


def progress(pid, stage, value, *, note=None, plan=None):
    """Update stage/progress and refresh the live activity card (clock + step list)."""
    current = project(pid) or {}
    meta = dict(current.get('metadata') or {})
    previous = meta.get('activity') if isinstance(meta.get('activity'), dict) else {}
    log = [row for row in (previous.get('log') or []) if isinstance(row, dict) and row.get('step')]
    if previous.get('step') and previous.get('step') != stage:
        log.append({'step': previous['step']})
        log = log[-12:]
    if isinstance(plan, list) and plan:
        chosen = plan
    elif stage in RENDER_ACTIVITY:
        # Drop stale analysis steps (director / reference_*) so the page shows the render path.
        base = [
            'preparing_voice', 'drawing_graphics', 'rendering', 'assembling', 'checking',
        ]
        if stage == 'render_queued':
            chosen = ['render_queued'] + [s for s in base if s != 'preparing_voice']
        elif stage in base:
            # Keep voice step only when this job actually entered it (or stays on it).
            if stage == 'preparing_voice' or previous.get('step') == 'preparing_voice' or any(
                row.get('step') == 'preparing_voice' for row in log
            ):
                chosen = list(base)
            else:
                chosen = [s for s in base if s != 'preparing_voice']
            if stage not in chosen:
                chosen = [stage] + chosen
        else:
            chosen = [stage]
    else:
        chosen = previous.get('plan') if isinstance(previous.get('plan'), list) and previous.get('plan') else [stage]
    same = previous.get('step') == stage and previous.get('at')
    meta['activity'] = {
        'step': stage,
        'part': None,
        'done': None,
        'total': None,
        'at': previous.get('at') if same else time.time(),
        'log': log,
        'plan': chosen,
        'note': note if note is not None else (previous.get('note') if same else None),
    }
    status = current.get('status')
    # Keep analyzing for analysis notes; render jobs stay queued/rendering.
    if status not in ('analyzing', 'importing') and stage in RENDER_ACTIVITY:
        if status not in ('rendering', 'complete', 'failed', 'needs_review'):
            status = 'rendering' if stage != 'render_queued' else 'queued'
        update(pid, status=status, stage=stage, progress=value, metadata=meta)
    else:
        update(pid, stage=stage, progress=value, metadata=meta)
    event(pid, 'stage', stage)

def fit_caption_ends(rows, audio):
    """Keep caption times inside the speech file. Alignment can run a little past it."""
    from pathlib import Path
    if not audio or not Path(audio).is_file():
        return rows
    from .music import probe_audio
    spoken = float((probe_audio(audio) or {}).get('duration') or 0)
    if spoken <= 0:
        return rows
    fitted = []
    for row in rows:
        start = float(row['start'])
        end = min(float(row['end']), spoken)
        if start >= spoken or end - start < 0.08:
            continue
        fitted.append({**row, 'end': end})
    return fitted


def dub_captions(segments, code):
    """Captions follow the dubbed lines. The schema still requires every language field."""
    rows = []
    language = code if code in ('en', 'zh', 'ru') else 'en'
    for segment in segments or []:
        text = segment['text']
        row = {
            'start': segment['start'],
            'end': segment['end'],
            'original': text,
            'en': '',
            'zh': '',
            'ru': '',
        }
        row[language] = text
        rows.append(row)
    return rows


def _ready_speech(folder, expected, voice):
    """Reuse speech already recorded for these lines. Do not call a translator again."""
    from pathlib import Path
    path = Path(folder) / 'rendition.json'
    if not path.is_file():
        return None
    saved = json.loads(path.read_text(encoding='utf-8'))
    audio = (saved.get('audio') or {}).get('file')
    if not audio or not Path(audio).is_file():
        return None
    if saved.get('status') not in {'audio_ready', 'aligned', 'ready', 'rendered'}:
        return None
    if voice and saved.get('voiceId') not in (None, voice):
        return None
    spoken = [(line.get('text') or '').strip() for line in saved.get('localizedScript') or []]
    if spoken != [text.strip() for text in expected]:
        return None
    return saved


def _dub_for_job(pid, payload, folder):
    """Target-language speech for this rendition. The source recording stays untouched."""
    from .dubbing_audio import localize_for_speech, synthesize
    from .language import rendition_dir
    from .rendition import localize_script, materialize_speech, semantic_segments, source_record, store_rendition, translations_from_rows
    locale = payload.get('target_language')
    transcript = (payload.get('plan') or {}).get('transcript') or []
    translations = translations_from_rows(transcript, locale)
    if not translations:
        segments = semantic_segments(transcript)
        if not segments:
            raise ValueError('localized_script_missing')
        translations = localize_for_speech(pid, segments, locale)
    source = source_record(transcript)
    spoken = localize_script(source['segments'], locale, source['sourceLanguage'], translations)
    saved = _ready_speech(rendition_dir(settings.data_dir, pid, locale), [line['text'] for line in spoken], payload.get('voice'))
    if saved:
        del folder
        return saved

    record = materialize_speech(
        rendition_dir(settings.data_dir, pid, locale),
        transcript,
        locale,
        synthesize,
        translations=translations,
        voice=payload.get('voice'),
    )
    store_rendition(rendition_dir(settings.data_dir, pid, locale), record)
    if not (record.get('audio') or {}).get('file') and record.get('audioMode') != 'original':
        raise ValueError('VOICE_SETUP_REQUIRED')
    del folder
    return record

def analyze_job(p):
    pid=p['id']; folder=settings.data_dir/pid; source=folder/'source'
    update(pid,status='analyzing',error=None)
    from .analysis_activity import note
    note(pid,'prepare',plan=['prepare','owned_sound','owned_model','director'])
    if not source.exists():
        from .douyin import import_source
        import_source(p)
    metadata=media.probe(source)
    if metadata['duration']>settings.max_duration_seconds: raise ValueError('video_too_long')
    media.prepare(source,folder)
    try:
        saved=(project(pid) or {}).get('metadata') or {}
    except Exception:
        saved={}
    update(pid,metadata={**saved,**metadata,'preview_ready':True})
    note(pid,'owned_sound')
    silences=media.silence_ranges(source,metadata['duration']) if metadata['has_audio'] else []
    note(pid,'owned_model')
    analysis=ai.analyze(pid,folder,metadata,p['brief'],p['language'],silences)
    note(pid,'director')
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
    from .director_v3 import PROJECT_ID
    if p['id'] == PROJECT_ID:
        raise ValueError('director_v3_required')
    pid=p['id']; folder=settings.data_dir/pid
    analysis=Analysis.model_validate(p['analysis'])
    selected=[r for r in analysis.recommendations if r.id in payload['recommendations']]
    if len(selected)!=len(set(payload['recommendations'])): raise ValueError('invalid_recommendation')
    if any(r.action=='generate_broll' for r in selected) and not p['generative']: raise ValueError('generation_not_enabled')
    manual=payload.get('manual')
    if manual: selected=[]
    else: media.build_timeline(p['metadata']['duration'],selected)
    from . import render_audio
    with connect() as db:delivery=render_audio.snapshot(db,p)
    if payload.get('illustration'):
        delivery = None
    if not manual and delivery:
        from .manual import Edit,Clip
        from .studio import state as studio_state
        from .voice_cleanup import default_enabled
        style=bool(((studio_state(pid) or {}).get('context') or {}).get('style_match'))
        manual=Edit(clips=[Clip(start=a,end=b) for a,b in media.build_timeline(p['metadata']['duration'],selected)],
            captions=analysis.transcript,subtitles=any(r.action=='captions' for r in selected),
            normalize=any(r.action=='normalize_audio' for r in selected),music=delivery['music'],
            voice_cleanup=default_enabled(style, bool(delivery.get('voice')))).model_dump()
        payload=payload|{'quality_review':True} # Automatic renders already run QA.
    if not manual:
        from .manual import Edit, Clip
        spans=media.build_timeline(p['metadata']['duration'],selected)
        manual=Edit(clips=[Clip(start=a,end=b) for a,b in spans],
            captions=analysis.transcript,subtitles=any(r.action=='captions' for r in selected),
            normalize=any(r.action=='normalize_audio' for r in selected)).model_dump()
    timeline=[(c['start'],c['end']) for c in manual['clips'] if c.get('approved',True)] if manual else media.build_timeline(p['metadata']['duration'],selected)
    if delivery and delivery['voice']:render_audio.map_ranges(delivery['voice']['timeline'],timeline)
    update(pid,status='rendering',error=None)
    progress(pid,'preparing_picture',8)
    brolls=[]
    generative=[r for r in selected if r.action=='generate_broll']
    if len(generative)>2: raise ValueError('too_many_generated_clips')
    # A hosted clip is not a Hypit prompt. The picture is the author source.
    progress(pid,'preparing_picture',12)
    render_id=uuid.uuid4().hex
    render_folder=folder/'renders'/render_id
    render_folder.mkdir(parents=True)
    asset_paths={}
    if manual:
        from .studio import state as studio_state
        current=studio_state(pid)
        context=(current or {}).get('context') if current else None
        if (context or {}).get('style_match') and not manual.get('music') and not payload.get('illustration'):
            from .style_match import attach_recommended_bed
            progress(pid,'matching_music',16)
            manual=attach_recommended_bed(pid, manual, current)
        from .assets import validate as validate_assets
        from .manual import Edit
        from .media import _without_dub
        # Prompt-assembly bindings (duration/width/…) may ride on the job manual.
        if isinstance(manual, dict):
            for key in ('duration', 'width', 'height', 'aspect', 'visual_energy', 'promptBindings'):
                manual.pop(key, None)
        with connect() as db:asset_paths=validate_assets(Edit.model_validate(_without_dub(manual)),pid,db)
    voice_audio=render_audio.prepare(pid,delivery['voice'],render_folder,timeline) if delivery and delivery['voice'] and not payload.get('illustration') else None
    picture_engine='hypit'
    effect_board=None
    if manual:
        from .studio import state as studio_state
        from .style_match import board_for_render
        from .hypit_picture import engine_for
        current=studio_state(pid)
        effect_board=((current or {}).get('context') or {}).get('effect_board') if current else None
        manual=board_for_render(manual,(current or {}).get('context') if current else None)
        if ((current or {}).get('context') or {}).get('style_match'):
            from .style_match import animate_for_render, present_for_render
            progress(pid,'drawing_graphics',22)
            manual=animate_for_render(manual)
            manual=present_for_render(manual)
        if payload.get('dubbed'):
            progress(pid,'preparing_voice',18)
            record=_dub_for_job(pid, payload, render_folder)
            manual=dict(manual)
            if (record.get('audio') or {}).get('file'):
                manual['dub_audio']=record['audio']['file']
            code=payload.get('language') or 'en'
            manual['captions']=fit_caption_ends(
                dub_captions((record.get('alignment') or {}).get('segments') or [], code),
                (record.get('audio') or {}).get('file'),
            )
            manual['subtitles']=bool(manual['captions'])
        if payload.get('illustration'):
            from .hypit_prompt import illustration_request
            from .media import _without_dub
            manual=dict(manual)
            # Prompt assembly must not see the speech file path as an Edit field.
            manual['presentation_prompt']=illustration_request(_without_dub(manual))
        picture_engine=engine_for((current or {}).get('context') if current else None)
    spoken=(delivery or {}).get('voice') or {}
    result=media.render(folder/'source',render_folder,p['metadata'],analysis,selected,p['language'],p['aspect'],brolls,preserve_caption_master=True,on_progress=lambda stage,value:progress(pid,stage,value),picture_engine=picture_engine,presentation_language=spoken.get('language'),effect_board=effect_board if manual else None,**({'voice_audio':voice_audio} if voice_audio else {}),**({'manual':manual,'asset_paths':asset_paths} if manual else {}))
    result['render_id']=render_id
    if delivery and delivery['voice']:result['voiceover']={k:delivery['voice'][k] for k in ('language','voice')}
    if asset_paths:
        used_assets={c['external_broll']['asset_id'] for c in manual['clips'] if c['approved'] and c.get('external_broll')}
        used_assets.update(c['stock_still'] for c in manual['clips'] if c['approved'] and c.get('stock_still'))
        if manual.get('music'):used_assets.add(manual['music']['asset_id'])
        with connect() as db:
            result['asset_credits']=[{'asset_id':ident,'title':row['title'],'attribution':row['attribution']} for ident in sorted(used_assets) if (row:=db.execute('SELECT title,attribution FROM studio_assets WHERE id=? AND project_id=?',(ident,pid)).fetchone())]
    progress(pid,'checking',94)
    try:
        if manual and not payload.get('quality_review'): raise ValueError('manual_review_required')
        qa=ai.review(pid,render_folder,p['brief'],manual if manual else [r.model_dump() for r in selected])
        result['qa']=qa.model_dump()
        from .quality_comparison import RUBRIC
        result['quality_model']=settings.analysis_model
        result['quality_rubric']=RUBRIC
        score=round(sum(s.value for s in qa.scores)/len(qa.scores),1) if getattr(qa,'scores',None) else None
        result['quality_score']=score
        result['qa_status']='passed' if qa.passed and (score is None or score>=75) else 'needs_review'
    except Exception as exc:
        result['qa']=None; result['qa_status']='unavailable'
        if manual and not payload.get('quality_review'):
            result['qa_status']='manual_review_required'
        else: event(pid,'quality_review_unavailable',safe_error(exc))
    from .quality_comparison import compare
    result['quality_comparison']=compare(p.get('result'),result)
    if manual:result['manual_transcript']=manual['captions'] if manual['subtitles'] else []
    # A failed quality review is never published as approved.
    status='complete' if result['qa_status']=='passed' else 'needs_review'
    with connect() as db:
        db.lock();render_audio.publish(db,p,result,render_folder,delivery,status)
    try:
        from .render_retention import prune_pictures
        prune_pictures(pid, result['render_id'])
    except Exception:
        log.exception('render retention failed for %s', pid)
    event(pid,'render_complete',json.dumps({'applied':result['applied'],'quality':result['qa_status']}))

def safe_error(exc):
    allowed={'selected_audio_unavailable','voiceover_timeline_unavailable','voiceover_range_unavailable','douyin_not_configured','douyin_daily_limit','douyin_auth_failed','douyin_credits_required','douyin_rate_limited','douyin_search_failed','douyin_media_unavailable','upload_too_large','budget_limit','not_a_video','invalid_duration','resolution_too_large','video_too_long','provider_not_configured',
    'provider_credits_required','provider_auth_failed','provider_request_failed','provider_invalid_analysis','provider_analysis_truncated','analysis_timestamps_invalid','analysis_proxy_missing','stock_unavailable',
    'analysis_duplicate_ids','analysis_multiple_hooks','hook_overlaps_cut','too_much_removed','generation_submission_uncertain',
    'generation_request_failed','generation_poll_failed','generation_failed','generation_timed_out','generation_not_enabled',
    'media_processing_failed','ffmpeg_ass_unavailable','output_audio_missing','output_duration_mismatch','too_many_generated_clips','hypit_unavailable','target_voice_not_ready','VOICE_SETUP_REQUIRED','MISSING_TARGET_LANGUAGE_VOICE','VOICE_PROVIDER_NOT_CONFIGURED','TRANSCRIPTION_PROVIDER_UNAVAILABLE','SOURCE_TRANSCRIPT_UNAVAILABLE','SOURCE_LANGUAGE_UNVERIFIED','TRANSCRIPTION_FAILED','TRANSCRIPTION_TIMEOUT','localized_script_missing','director_v3_required','director_v3_renderer_missing','director_v3_render_failed','duration_step','visual_energy','visual_variation',
    'unverified_claim','property_not_approved','property_plan_changed','property_workflow','property_too_short','property_delivery_missing','reference_media_blocked','invalid_media_path','asset_not_found','PLANNER_UNAVAILABLE','PLANNER_INVALID','TRANSCRIPTION_MEMORY','TRANSCRIPTION_BUSY','coder_scene_disabled','coder_scene_failed'}
    return str(exc) if str(exc) in allowed else 'processing_failed'

def failure_detail(exc):
    """Worker-log text. The browser still receives only safe_error()."""
    from .hypit_picture import capture_note
    return capture_note(exc)

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
        elif job['kind']=='transcribe':
            from .transcription import run_job as transcribe_job
            transcribe_job(p,json.loads(job['payload'] or '{}'))
        elif job['kind']=='director_v3':
            from .director_v3 import run_job as director_v3_job
            director_v3_job(p,json.loads(job['payload']))
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
        elif job['kind']=='final_music':
            from .final_music import run_job as final_music_job
            final_music_job(p,json.loads(job['payload']))
        elif job['kind']=='dubbing':
            from .dubbing import run_job as dubbing_job
            dubbing_job(p,json.loads(job['payload']))
        elif job['kind']=='director_alternative':
            from .director_revisions import run_job as alternative_job
            alternative_job(p,json.loads(job['payload']))
        elif job['kind']=='platform_variants':
            from .variants import run_job
            run_job(p,json.loads(job['payload']))
        elif job['kind']=='property_render':
            from .property_video import render_job as property_render_job
            property_render_job(p,json.loads(job['payload']))
        elif job['kind']=='coder_scene':
            from .coder_scene import run_job as coder_scene_job
            coder_scene_job(p,json.loads(job['payload'] or '{}'))
        else: raise ValueError('unknown_job')
        state='complete'
    except Exception as exc:
        code=safe_error(exc)
        # A closed worker terminal must not skip the status update or hide the cause.
        detail=''
        try:
            detail=failure_detail(exc)
            log.error('Job %s failed: %s (%s)%s',job['id'],code,type(exc).__name__,f'; {detail}' if detail else '')
            for handler in logging.getLogger().handlers:
                handler.flush()
        except Exception:
            pass
        if job['kind']=='transcribe':
            from .transcription import mark_transcription
            mark_transcription(p['id'], 'transcription_failed', transcription_error=code)
        elif job['kind'] not in ('final_music','dubbing','platform_variants','director_alternative','timeline_proposal','creative_plan','music_plan','stock_import','stock_discover'):
            # Keep a human note on the activity card — safe_error alone hides ModuleNotFound etc.
            try:
                current = project(p['id']) or {}
                meta = dict(current.get('metadata') or {})
                prev = meta.get('activity') if isinstance(meta.get('activity'), dict) else {}
                note = detail or f'{type(exc).__name__}: {exc}'
                if len(note) > 280:
                    note = note[:277] + '…'
                meta['activity'] = {
                    **prev,
                    'step': prev.get('step') or current.get('stage') or 'failed',
                    'note': note,
                    'at': prev.get('at') or time.time(),
                    'plan': prev.get('plan') or [],
                    'log': prev.get('log') or [],
                }
                update(p['id'], status='failed', stage='failed', error=code, metadata=meta)
            except Exception:
                update(p['id'], status='failed', stage='failed', error=code)
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
        for row in db.execute("SELECT project_id,kind,payload,id FROM jobs WHERE status='running'"):
            if row["kind"]=="final_music":
                db.execute("UPDATE final_music_versions SET status='failed',error='worker_interrupted' WHERE id=?",(json.loads(row['payload'])['id'],))
            elif row["kind"]=="dubbing":
                db.execute("UPDATE dubbing_versions SET status='failed',error='worker_interrupted' WHERE id=?",(json.loads(row['payload'])['id'],))
            elif row["kind"]=="stock_discover":
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
            elif row["kind"]=="transcribe":
                from .transcription import recover_transcribe_job
                recover_transcribe_job(db, row)
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
    for stream in (sys.stdout, sys.stderr):
        reconfigure=getattr(stream, 'reconfigure', None)
        if reconfigure:
            try: reconfigure(line_buffering=True)
            except (OSError, ValueError): pass
    logging.basicConfig(level=logging.INFO)
    main()
