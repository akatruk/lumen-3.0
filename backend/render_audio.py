"""Carry selected voice by source time; publish picture and audio together."""
import json
import re
import shutil
import time
import uuid
from html import unescape
from .config import settings
from . import media, final_output


def snapshot(db,p):
    selection=db.execute('SELECT master_id,version_id FROM project_final_outputs WHERE project_id=?',(p['id'],)).fetchone()
    if not selection or selection['version_id']=='master':return None
    selected=final_output.current(db,p['id'],selection['master_id'])
    if not selected:raise ValueError('selected_audio_unavailable')
    from .final_music import voice_of,config_of
    voice=voice_of(selected)
    result={'selection':dict(selection),'music':config_of(selected,p.get('result') or {}),'voice':None}
    if voice:
        row=db.execute("SELECT * FROM dubbing_versions WHERE id=? AND project_id=? AND kind='video' AND status='ready'",(voice,p['id'])).fetchone()
        if not row:raise ValueError('selected_audio_unavailable')
        old=json.loads(row['snapshot']).get('master')
        if not old and (p.get('result') or {}).get('render_id')==row['master_id']:old=p['result']
        if not old or not old.get('timeline'):raise ValueError('voiceover_timeline_unavailable')
        origin=json.loads(row['snapshot']).get('carried_voice')
        if origin:
            ancestor=db.execute("SELECT id FROM dubbing_versions WHERE id=? AND project_id=? AND kind='video' AND status='ready'",(origin['id'],p['id'])).fetchone()
            if not ancestor:raise ValueError('selected_audio_unavailable')
        result['voice']=origin or {'id':voice,'language':row['language'],'voice':row['voice'],'timeline':old['timeline']}
        source=settings.data_dir/p['id']/'dubbing'/result['voice']['id']
        if not (source/'voice.wav').is_file() and not (source/'video.mp4').is_file():raise ValueError('selected_audio_unavailable')
    return result


def map_ranges(previous, current):
    spans=[];offset=0
    for a,b in previous:
        spans.append((a,b,offset));offset+=b-a
    mapped=[]
    for start,end in current:
        cursor=start
        while cursor<end-1e-6:
            matches=[(a,b,o) for a,b,o in spans if a<=cursor+1e-6 and b>cursor+1e-6]
            if not matches:raise ValueError('voiceover_range_unavailable')
            a,b,offset=matches[0];stop=min(end,b)
            mapped.append((offset+cursor-a,offset+stop-a));cursor=stop
    return mapped


def prepare(pid, voice, folder, timeline):
    ranges=map_ranges(voice['timeline'],timeline)
    original=settings.data_dir/pid/'dubbing'/voice['id']
    source=original/'voice.wav'
    if not source.is_file():source=original/'video.mp4'
    if not source.is_file():raise ValueError('selected_audio_unavailable')
    graph=[]
    for i,(a,b) in enumerate(ranges):graph.append(f'[0:a]atrim=start={a}:end={b},asetpts=PTS-STARTPTS[a{i}]')
    graph.append(''.join(f'[a{i}]' for i in range(len(ranges)))+f'concat=n={len(ranges)}:v=0:a=1[out]')
    clean=folder/'voice-clean.wav'
    media.ffmpeg('-i',source,'-filter_complex_threads','1','-filter_complex',';'.join(graph),'-map','[out]','-c:a','pcm_s16le','-ar','48000',clean,timeout=600)
    # Never pad over missing speech coverage.
    from .music import probe_audio
    if abs(probe_audio(clean)['duration']-sum(b-a for a,b in timeline))>.2:raise ValueError('output_duration_mismatch')
    old_vtt=original/'subtitles.vtt'
    phrases=[]
    if old_vtt.is_file():
        def seconds(s):
            h,m,t=s.split(':');return int(h)*3600+int(m)*60+float(t)
        cues=[]
        for chunk in re.split(r'\n\s*\n',old_vtt.read_text()):
            m=re.search(r'(\d+:\d+:\d+\.\d+) --> (\d+:\d+:\d+\.\d+)\n([\s\S]+)',chunk)
            if m:cues.append((seconds(m[1]),seconds(m[2]),unescape(m[3])))
        offset=0
        for a,b in ranges:
            for x,y,text in cues:
                left=max(a,x);right=min(b,y)
                if right>left:phrases.append({'start':offset+left-a,'end':offset+right-a,'text':text})
            offset+=b-a
    from .dubbing_audio import write_vtt
    write_vtt(folder/'voice-subtitles.vtt',phrases)
    return clean


def replace_picture_audio(picture,voice,folder,duration):
    out=folder/'voiced-picture.mp4'
    media.ffmpeg('-i',picture,'-i',voice,'-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','192k','-af','apad','-t',duration,'-movflags','+faststart',out,timeout=600)
    return out


def publish(db,p,result,folder,delivery,status):
    """File generation must be complete before entering this short transaction."""
    latest=db.execute('SELECT result FROM projects WHERE id=?',(p['id'],)).fetchone()
    if json.loads(latest['result'] or '{}').get('render_id')!=(p.get('result') or {}).get('render_id'):raise ValueError('master_changed')
    ident=None
    if delivery:
        selected=db.execute('SELECT master_id,version_id FROM project_final_outputs WHERE project_id=?',(p['id'],)).fetchone()
        if not selected or dict(selected)!=delivery['selection']:raise ValueError('final_changed')
    if delivery and delivery.get('voice'):
        voice=delivery['voice'];ident=uuid.uuid4().hex
        dest=settings.data_dir/p['id']/'dubbing'/ident;dest.mkdir(parents=True)
        shutil.copyfile(folder/'voice-clean.wav',dest/'voice.wav')
        shutil.copyfile(folder/'voice-subtitles.vtt',dest/'subtitles.vtt')
        shutil.copyfile(folder/('music-free.mp4' if result.get('music') else 'result.mp4'),dest/'video.mp4')
        db.execute("INSERT INTO dubbing_versions(id,project_id,request_id,master_id,language,voice,kind,status,progress,snapshot,result,created) VALUES(?,?,?,?,?,?,'video','ready',100,?,?,?)",
            (ident,p['id'],uuid.uuid4().hex,result['render_id'],voice['language'],voice['voice'],json.dumps({'master':result,'carried_from':voice['id'],'carried_voice':voice}),json.dumps(result['metadata']),time.time()))
        if result.get('music'):
            mix_id=uuid.uuid4().hex;dest=settings.data_dir/p['id']/'audio-mixes'/mix_id;dest.mkdir(parents=True)
            shutil.copyfile(folder/'result.mp4',dest/'video.mp4')
            row=db.execute('SELECT title FROM studio_assets WHERE id=? AND project_id=?',(result['music']['asset_id'],p['id'])).fetchone()
            db.execute("INSERT INTO final_music_versions(id,project_id,request_id,master_id,source_voice,expected_final,music,title,status,result,created) VALUES(?,?,?,?,?,?,?,?,'ready',?,?)",
                (mix_id,p['id'],uuid.uuid4().hex,result['render_id'],ident,'master',json.dumps(result['music']),row['title'] if row else '',json.dumps(result['metadata']),time.time()))
            ident=mix_id
    # Delivery copies above hold the selected voice. The immutable Master retains
    # original edit audio so an explicit restore never returns the carried voice.
    if (folder/'original-audio.mp4').is_file():
        (folder/'original-audio.mp4').replace(folder/'result.mp4')
        if (folder/'original-music-free.mp4').is_file():(folder/'original-music-free.mp4').replace(folder/'music-free.mp4')
        if (folder/'original-caption-free.mp4').is_file():(folder/'original-caption-free.mp4').replace(folder/'caption-free.mp4')
    db.execute('UPDATE projects SET result=?,status=?,stage=?,progress=100,error=NULL,updated=? WHERE id=?',(json.dumps(result),status,status,time.time(),p['id']))
    if delivery:final_output.select(db,p['id'],result['render_id'],ident or 'master')


def summary(db,p,timeline):
    try:
        delivery=snapshot(db,p)
        if not delivery or not delivery['voice']:return None
        voice=delivery['voice']
        map_ranges(voice['timeline'],timeline)
        return {k:voice[k] for k in ('language','voice')}
    except ValueError as exc:
        return {'error':str(exc)}


def repair(p):
    """Recover a stale audio selection on the current immutable picture, without AI."""
    from .db import connect,event
    from . import music,assets
    with connect() as db:
        if db.execute("SELECT 1 FROM jobs WHERE project_id=? AND status IN ('queued','running')",(p['id'],)).fetchone():raise ValueError('job_already_running')
        delivery=snapshot(db,p)
    if not delivery or not delivery['voice']:raise ValueError('selected_audio_unavailable')
    result=p['result'];folder=settings.data_dir/p['id']/'renders'/('audio-repair-'+uuid.uuid4().hex);folder.mkdir(parents=True)
    clean=prepare(p['id'],delivery['voice'],folder,result['timeline'])
    original=settings.data_dir/p['id']/'renders'/result['render_id']/'result.mp4'
    duration=result['metadata']['duration']
    voiced=replace_picture_audio(original,clean,folder,duration)
    tracks=(result.get('director_timeline') or {}).get('tracks',{})
    effects=tracks.get('sound_effects',[])
    if effects:
        from .sound_effects import mix
        voiced=mix(voiced,folder,effects,duration,True)
    config=result.get('music')
    if config:
        shutil.copyfile(voiced,folder/'music-free.mp4')
        voiced=music.mix(voiced,assets.path(p['id'],config['asset_id']),folder,config,duration,True)
    args=['-i',voiced,'-map','0:v:0','-map','0:a:0','-c:v','copy','-c:a','aac','-b:a','192k']
    if any(a.get('normalize') for a in tracks.get('audio',[])):args+=['-af','loudnorm=I=-16:TP=-1.5:LRA=11']
    media.ffmpeg(*args,'-movflags','+faststart',folder/'result.mp4',timeout=600)
    meta=media.probe(folder/'result.mp4')
    if not meta['has_audio'] or abs(meta['duration']-duration)>.2:raise ValueError('output_duration_mismatch')
    with connect() as db:
        db.lock()
        if db.execute("SELECT 1 FROM jobs WHERE project_id=? AND status IN ('queued','running')",(p['id'],)).fetchone():raise ValueError('job_already_running')
        publish(db,p,result,folder,delivery,p['status'])
        selected=final_output.current(db,p['id'],result['render_id'])
    event(p['id'],'render_audio_restored',selected['id'])
    return selected


def preserve_original_audio(picture,source,folder,duration,manual,asset_paths,normalize):
    """Keep the explicit 'original edit audio' choice working after carrying a voice."""
    from . import music
    work=folder/'original-audio-work';work.mkdir()
    audio=source
    if manual:
        effects=[];cursor=0
        for c in manual['clips']:
            effects.extend(e|{'at':cursor+e['at']} for e in c['sound_effects']);cursor+=c['end']-c['start']
        if effects:
            from .sound_effects import mix
            audio=mix(audio,work,effects,duration,media.probe(audio)['has_audio'])
    config=(manual or {}).get('music')
    if config:
        media.ffmpeg('-i',picture,'-i',audio,'-map','0:v:0','-map','1:a:0?','-c','copy','-movflags','+faststart',folder/'original-music-free.mp4',timeout=600)
        audio=music.mix(audio,asset_paths[config['asset_id']],work,config,duration,media.probe(audio)['has_audio'])
    args=['-i',picture,'-i',audio,'-map','0:v:0','-map','1:a:0?','-c:v','copy','-c:a','aac','-b:a','192k']
    if normalize and media.probe(audio)['has_audio']:args+=['-af','loudnorm=I=-16:TP=-1.5:LRA=11']
    media.ffmpeg(*args,'-movflags','+faststart',folder/'original-audio.mp4',timeout=600)
    if (folder/'caption-free.mp4').is_file():
        media.ffmpeg('-i',folder/'caption-free.mp4','-i',folder/'original-audio.mp4','-map','0:v:0','-map','1:a:0?','-c','copy','-movflags','+faststart',folder/'original-caption-free.mp4',timeout=600)
    shutil.rmtree(work)
