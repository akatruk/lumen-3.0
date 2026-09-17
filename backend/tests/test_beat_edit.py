from backend.beat_edit import propose
from backend.manual import Edit,Clip
from backend.music import Music
from backend.schemas import Caption
from backend.tests.test_studio import client,create,seed_plan

def edit():return Edit(music=Music(asset_id='a'*32),clips=[Clip(start=0,end=2),Clip(start=2,end=4),Clip(start=4,end=6)])

def test_multiple_cut_alignment_preserves_coverage_and_music():
    original=edit();result,changes=propose(original,[2.2,4.1],10,[])
    assert len(changes)==2
    assert result.clips[0].end==result.clips[1].start==2.2
    assert result.clips[1].end==result.clips[2].start==4.1
    assert sum(c.end-c.start for c in result.clips)==6
    assert not any(c.approved for c in result.clips)
    assert result.music==original.music
    assert original.clips[0].end==2

def test_speech_locks_and_layers_are_not_shifted():
    original=edit();original.clips[2].locked=True
    speech=[Caption(start=2.05,end=2.1,original='word',en='word',zh='词')]
    result,changes=propose(original,[2.2,4.1],10,speech)
    assert not changes and result==original
    original=edit();original.clips[1].text='Keep exact timing'
    assert propose(original,[2.2,4.1],10,[])[1]==[]

def test_loop_offset_maps_music_time_to_output():
    original=edit();original.music.source_start=1
    _,changes=propose(original,[1.2],3,[])
    assert [c['to_output'] for c in changes]==[2.2,4.2]

def test_preview_is_private_revision_checked_and_does_not_save(client):
    import json,time
    from backend.db import connect
    pid=create(client).json()['id'];seed_plan(pid)
    original=edit();url=f'/api/studio/projects/{pid}/manual'
    with connect() as db:
        db.execute('INSERT INTO studio_assets VALUES(?,?,?,?,?,?,?)',('a'*32,pid,'b'*32,'Music','Owned',json.dumps({'kind':'music','duration':10,'rhythm':{'accents':[2.2,4.1]}}),time.time()))
    response=client.put(url,json={'revision':1,'edit':original.model_dump()});assert response.status_code==200,response.text
    response=client.post(url+'/beat-preview',json={'revision':2});assert response.status_code==200,response.text
    assert client.get(url).json()['edit']==original.model_dump()
    assert client.post(url+'/beat-preview',json={'revision':1}).status_code==409
    from backend.app import app
    from backend.auth import current_user
    app.dependency_overrides[current_user]=lambda:{'id':'v','email':'other@example.com'}
    assert client.post(url+'/beat-preview',json={'revision':2}).status_code==404

def test_beat_edit_renders_with_unchanged_total_duration(tmp_path):
    from backend import media
    from backend.tests.test_studio import plan
    source=tmp_path/'source.mp4';track=tmp_path/'music.wav'
    media.ffmpeg('-f','lavfi','-i','testsrc2=s=160x240:d=6:r=30','-f','lavfi','-i','sine=frequency=440:duration=6','-c:v','libx264','-c:a','aac',source)
    media.ffmpeg('-f','lavfi','-i','sine=frequency=220:duration=3',track)
    original=edit();original.clips[1].zoom=1.2
    proposal,changes=propose(original,[2.2],3,[])
    assert changes
    for c in proposal.clips:c.approved=True
    result=media.render(source,tmp_path,media.probe(source),plan(),[],'en','original',manual=proposal.model_dump(),asset_paths={'a'*32:track})
    assert abs(result['metadata']['duration']-6)<.2
    assert result['metadata']['has_audio']
