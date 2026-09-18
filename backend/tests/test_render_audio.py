import json,math,array,subprocess
import pytest
from backend.tests.test_final_music import client,prepared,REAL_PROBE
from backend.db import connect,project
from backend.config import settings
from backend.worker import run_once
from backend import media,render_audio
from backend.final_output import current,path


def test_voice_ranges_follow_trim_reorder_and_fail_for_unvoiced_source():
    assert render_audio.map_ranges([[4,8],[0,2]],[[0,2],[5,7]])==[(4,6),(1,3)]
    assert render_audio.map_ranges([[0,3],[3,8]],[[2,5]])==[(2,3),(3,5)]
    with pytest.raises(ValueError,match='voiceover_range_unavailable'):render_audio.map_ranges([[0,2],[4,8]],[[1,5]])


def source_fixture(client,monkeypatch):
    pid,voice,aid,revision=prepared(client,monkeypatch)
    monkeypatch.setattr(media,'probe',REAL_PROBE)
    root=settings.data_dir/pid
    media.ffmpeg('-f','lavfi','-i','color=red:s=160x240:d=8:r=30','-f','lavfi','-i','sine=frequency=110:duration=8','-c:v','libx264','-c:a','aac','-f','mp4',root/'source')
    old=root/'dubbing'/voice
    media.ffmpeg('-f','lavfi','-i','color=blue:s=160x240:d=8:r=30','-f','lavfi','-i','sine=frequency=440:duration=4','-f','lavfi','-i','sine=frequency=880:duration=4','-filter_complex','[1:a][2:a]concat=n=2:v=0:a=1[a]','-map','0:v','-map','[a]','-c:v','libx264','-c:a','aac',old/'video.mp4')
    from backend.dubbing_audio import write_vtt
    write_vtt(old/'subtitles.vtt',[{'start':.2,'end':1.2,'text':'First'},{'start':4.2,'end':5.2,'text':'Second'}])
    media.ffmpeg('-f','lavfi','-i','sine=frequency=220:duration=8','-f','wav',root/'assets'/aid)
    p=project(pid);p['result']['timeline']=[[0,8]];p['result']['metadata']['duration']=8
    with connect() as db:
        db.execute('UPDATE projects SET metadata=?,result=? WHERE id=?',(json.dumps(REAL_PROBE(root/'source')),json.dumps(p['result']),pid))
        db.execute('UPDATE dubbing_versions SET snapshot=? WHERE id=?',(json.dumps({'master':p['result']}),voice))
    return pid,voice,revision


def energy(video,t,frequency):
    raw=subprocess.check_output(['ffmpeg','-v','error','-ss',str(t),'-i',str(video),'-t','0.4','-vn','-ac','1','-ar','8000','-f','s16le','-'])
    samples=array.array('h',raw)
    return sum(v*math.sin(2*math.pi*frequency*i/8000) for i,v in enumerate(samples))**2+sum(v*math.cos(2*math.pi*frequency*i/8000) for i,v in enumerate(samples))**2


def test_consecutive_picture_renders_keep_voice_music_and_final_download(client,monkeypatch):
    pid,voice,revision=source_fixture(client,monkeypatch)
    url=f'/api/studio/projects/{pid}/manual'
    edit=client.get(url).json()['edit'];edit['clips']=[{'start':4,'end':8,'zoom':1.2},{'start':0,'end':2}]
    edit['music'].update(gain_db=-12,fade_in=0,fade_out=0,duck=False)
    revision=client.put(url,json={'revision':revision,'edit':edit}).json()['revision']
    summary=client.get(url+'/summary').json();assert summary['voiceover']=={'language':'ru','voice':'ru-male'}
    assert client.post(url+'/render',json={'revision':revision}).status_code==200
    from backend import worker
    monkeypatch.setattr(worker.ai,'review',lambda *a,**kw:pytest.fail('No AI regeneration'))
    assert run_once()
    p=project(pid)
    with connect() as db:selected=current(db,pid,p['result']['render_id'])
    assert selected['delivery']=='mix' and selected['source_voice']!=voice
    video=path(pid,selected)
    assert energy(video,.5,880)>energy(video,.5,440)*50
    assert energy(video,4.5,440)>energy(video,4.5,880)*50
    assert energy(video,.5,220)>energy(video,.5,110)*10 # added music, not original speech
    pixel=subprocess.check_output(['ffmpeg','-v','error','-ss','0.5','-i',str(video),'-vf','scale=1:1','-frames:v','1','-f','rawvideo','-pix_fmt','rgb24','-'])
    assert pixel[0]>180 and pixel[2]<50 # new RED picture, not old BLUE dub
    assert client.get(f'/api/projects/{pid}/media/result').content==video.read_bytes()
    carried=settings.data_dir/pid/'dubbing'/selected['source_voice']
    assert (carried/'voice.wav').is_file()
    assert '00:00:00.200 --> 00:00:01.200\nSecond' in (carried/'subtitles.vtt').read_text()
    saved=client.get(url).json();saved['edit']['clips']=[{'start':0,'end':2}]
    revision=client.put(url,json={'revision':saved['revision'],'edit':saved['edit']}).json()['revision']
    assert client.post(url+'/render',json={'revision':revision}).status_code==200
    assert run_once();p=project(pid)
    with connect() as db:new=current(db,pid,p['result']['render_id'])
    assert energy(path(pid,new),.5,440)>energy(path(pid,new),.5,880)*50
    # Restoring an earlier cut uses the retained original voice, not a truncated descendant.
    saved=client.get(url).json();saved['edit']['clips']=[{'start':2,'end':4}]
    revision=client.put(url,json={'revision':saved['revision'],'edit':saved['edit']}).json()['revision']
    response=client.post(url+'/render',json={'revision':revision})
    assert response.status_code==200
    assert run_once()
    p=project(pid)
    with connect() as db:restored=current(db,pid,p['result']['render_id'])
    assert energy(path(pid,restored),.5,440)>energy(path(pid,restored),.5,880)*50
    response=client.put(f'/api/studio/projects/{pid}/dubbing/final',json={'master_id':p['result']['render_id'],'version_id':'master'})
    assert response.status_code==200
    assert run_once()
    with connect() as db:original=current(db,pid,p['result']['render_id'])
    assert original['source_voice']==''
    assert energy(path(pid,original),.5,110)>energy(path(pid,original),.5,440)*50


def test_audio_failure_preserves_previous_final(client,monkeypatch):
    pid,voice,aid,revision=prepared(client,monkeypatch)
    before=project(pid)['result']
    assert client.post(f'/api/studio/projects/{pid}/manual/render',json={'revision':revision}).status_code==200
    monkeypatch.setattr(render_audio,'prepare',lambda *a,**kw:(_ for _ in ()).throw(ValueError('selected_audio_unavailable')))
    assert run_once()
    assert project(pid)['result']==before
    assert client.get(f'/api/projects/{pid}/media/result').content==b'chosen voiceover'


def test_repair_uses_current_picture_without_reverting_to_old_dub(client,monkeypatch):
    import shutil
    pid,voice,revision=source_fixture(client,monkeypatch)
    p=project(pid);p['result']['render_id']='c'*32
    folder=settings.data_dir/pid/'renders'/p['result']['render_id'];folder.mkdir()
    shutil.copyfile(settings.data_dir/pid/'source',folder/'result.mp4')
    with connect() as db:db.execute('UPDATE projects SET result=? WHERE id=?',(json.dumps(p['result']),pid))
    selected=render_audio.repair(project(pid))
    assert selected['master_id']=='c'*32
    assert energy(path(pid,selected),.5,440)>energy(path(pid,selected),.5,110)*50
    def packets(file):return subprocess.check_output(['ffmpeg','-v','error','-i',str(file),'-map','0:v:0','-c','copy','-f','hash','-hash','sha256','-'])
    assert packets(path(pid,selected))==packets(folder/'result.mp4')
    assert client.get(f'/api/projects/{pid}/media/result').content==path(pid,selected).read_bytes()


def test_auto_cleanup_keeps_selected_audio_and_changes_picture_timeline(client,monkeypatch):
    from types import SimpleNamespace
    from backend import worker
    pid,voice,revision=source_fixture(client,monkeypatch)
    # Selected delivery music is authoritative for cleanup mode (not an unsaved manual track).
    import uuid
    current_master=project(pid)['result']['render_id']
    assert client.post(f'/api/studio/projects/{pid}/final-music',json={'request_id':uuid.uuid4().hex,'revision':revision,'master_id':current_master,'final_id':voice}).status_code==202
    assert run_once()
    with connect() as db:
        db.execute('UPDATE studio_projects SET decisions=? WHERE project_id=?',(json.dumps([{'id':'cut','start':2,'end':4,'approved':True,'locked':False}]),pid))
    monkeypatch.setattr(worker.ai,'review',lambda *a,**k:SimpleNamespace(passed=True,scores=[],model_dump=lambda:{'passed':True,'observations':[],'issues':[],'scores':[],'revisions':[]}))
    assert client.post(f'/api/studio/projects/{pid}/render',json={'revision':revision}).status_code==200
    assert run_once();p=project(pid)
    assert p['result']['timeline']==[[0,2],[4,8]]
    with connect() as db:selected=current(db,pid,p['result']['render_id'])
    assert selected['language']=='ru'
    assert selected['delivery']=='mix'
    assert energy(path(pid,selected),.5,220)>energy(path(pid,selected),.5,110)*10
    assert energy(path(pid,selected),.5,440)>energy(path(pid,selected),.5,110)*50
    assert energy(path(pid,selected),2.5,880)>energy(path(pid,selected),2.5,110)*50
