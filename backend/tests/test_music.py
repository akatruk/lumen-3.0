import uuid
import pytest
from backend.music import Music,mix,probe_audio
from backend.manual import Edit,Clip
from backend import media
from backend.tests.test_studio import client,create,seed_plan

def test_music_upload_and_project_isolation(client,tmp_path):
    track=tmp_path/'track.wav'
    media.ffmpeg('-f','lavfi','-i','sine=frequency=220:duration=2',track)
    data=track.read_bytes()
    pid=create(client).json()['id'];seed_plan(pid)
    ident=client.post('/api/studio/uploads',json={'size':len(data),'token':uuid.uuid4().hex}).json()['id']
    assert client.put(f'/api/studio/uploads/{ident}?offset=0',content=data).status_code==200
    body={'asset_project_id':pid,'request_id':uuid.uuid4().hex,'title':'Owned music','attribution':'Synthetic test','owned_rights_confirmed':True,'kind':'music'}
    response=client.post(f'/api/studio/uploads/{ident}/asset',json=body)
    assert response.status_code==201,response.text
    aid=response.json()['id'];url=f'/api/studio/projects/{pid}/manual'
    edit=client.get(url).json()['edit'];edit['music']=Music(asset_id=aid).model_dump()
    assert client.put(url,json={'revision':1,'edit':edit}).status_code==200
    saved=client.get(url).json()
    assert saved['timeline']['tracks']['music'][0]['asset_id']==aid
    edit['music']['source_start']=3
    assert client.put(url,json={'revision':2,'edit':edit}).status_code==422
    other=create(client).json()['id'];seed_plan(other)
    edit['music']['source_start']=0
    assert client.put(f'/api/studio/projects/{other}/manual',json={'revision':1,'edit':edit}).status_code==422
    edit['music']=None;edit['clips'][0]['external_broll']={'asset_id':aid,'start':0,'end':1,'source_start':0}
    assert client.put(url,json={'revision':2,'edit':edit}).status_code==422

@pytest.mark.parametrize('has_audio',[True,False])
def test_music_loop_preserves_video_duration_and_creates_audio(tmp_path,has_audio):
    source=tmp_path/'source.mp4';track=tmp_path/'track.wav'
    args=['-f','lavfi','-i','color=red:s=160x240:d=4:r=12']
    if has_audio:args+=['-f','lavfi','-i','sine=frequency=440:duration=4']
    media.ffmpeg(*args,'-c:v','libx264',source)
    media.ffmpeg('-f','lavfi','-i','sine=frequency=220:duration=1',track)
    assert probe_audio(track)['kind']=='music'
    out=mix(source,track,tmp_path,Music(asset_id='a'*32,source_start=.2).model_dump(),4,has_audio)
    meta=media.probe(out)
    assert meta['has_audio'] and abs(meta['duration']-4)<.2
    _,stats=media.ffmpeg('-ss',2,'-i',out,'-t',.5,'-af','volumedetect','-vn','-f','null','-')
    assert 'mean_volume: -inf' not in stats

def test_music_is_in_compiled_timeline():
    from backend.timeline import compile_timeline
    edit=Edit(clips=[Clip(start=0,end=2)],music=Music(asset_id='a'*32))
    assert compile_timeline(edit)['tracks']['music'][0]['end']==2

def test_gain_curve_changes_the_real_rendered_audio(tmp_path):
    import re
    from backend.music import MusicLevel
    source=tmp_path/'source.mp4';track=tmp_path/'track.wav'
    media.ffmpeg('-f','lavfi','-i','color=black:s=160x240:d=4:r=12','-c:v','libx264',source)
    media.ffmpeg('-f','lavfi','-i','sine=frequency=220:duration=4',track)
    config=Music(asset_id='a'*32,fade_in=0,fade_out=0,levels=[MusicLevel(at=0,gain_db=-36),MusicLevel(at=3,gain_db=-6)])
    output=mix(source,track,tmp_path,config.model_dump(),4,False)
    levels=[]
    for at in (.2,2.8):
        _,stats=media.ffmpeg('-ss',at,'-i',output,'-t',.2,'-af','volumedetect','-vn','-f','null','-')
        levels.append(float(re.search(r'mean_volume: ([\-\d.]+)',stats).group(1)))
    assert levels[1]-levels[0]>10
