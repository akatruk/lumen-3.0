import json,uuid
from backend.tests.test_dubbing import client,setup,ready_delivery,MASTER
from backend.db import connect,project
from backend.config import settings
from backend.worker import run_once
from backend import media
REAL_PROBE=media.probe
from backend.music import Music
from backend.auth import current_user
from backend.app import app


def prepared(client,monkeypatch):
    pid=setup(client,monkeypatch);voice=ready_delivery(pid)
    client.put(f'/api/studio/projects/{pid}/dubbing/final',json={'master_id':MASTER,'version_id':voice})
    aid=uuid.uuid4().hex
    folder=settings.data_dir/pid/'assets';folder.mkdir(parents=True)
    (folder/aid).write_bytes(b'music')
    with connect() as db:db.execute('INSERT INTO studio_assets VALUES(?,?,?,?,?,?,?)',(aid,pid,uuid.uuid4().hex,'Test track','Synthetic',json.dumps({'kind':'music','duration':60}),0))
    url=f'/api/studio/projects/{pid}/manual';edit=client.get(url).json()['edit'];edit['music']=Music(asset_id=aid).model_dump()
    r=client.put(url,json={'revision':1,'edit':edit});assert r.status_code==200
    return pid,voice,aid,r.json()['revision']


def test_music_reaches_final_keeps_voice_and_replaces_instead_of_stacking(client,monkeypatch):
    pid,voice,aid,revision=prepared(client,monkeypatch)
    url=f'/api/studio/projects/{pid}/final-music'
    request={'request_id':uuid.uuid4().hex,'revision':revision,'master_id':MASTER,'final_id':voice}
    response=client.post(url,json=request)
    assert response.status_code==202,response.text
    assert client.post(url,json=request).json()==response.json()
    from backend import music
    calls=[]
    def mix(source,track,folder,config,duration,has_audio):
        calls.append(source.read_bytes());out=folder/'music-mix.mp4';out.write_bytes(b'voice and music');return out
    monkeypatch.setattr(music,'mix',mix)
    monkeypatch.setattr(media,'probe',lambda path:{'duration':40,'has_audio':True})
    assert run_once()
    assert calls==[b'chosen voiceover']
    assert client.get(f'/api/projects/{pid}/media/result').content==b'voice and music'
    state=client.get(url).json();assert state['voice_id']==voice and state['music']['asset_id']==aid
    request.update(request_id=uuid.uuid4().hex,final_id=state['final_id'])
    assert client.post(url,json=request).status_code==202
    assert run_once();assert calls==[b'chosen voiceover',b'chosen voiceover']
    # Removing added music restores the same voice, not the pre-dub Master.
    manual=f'/api/studio/projects/{pid}/manual';saved=client.get(manual).json();saved['edit']['music']=None
    r=client.put(manual,json={'revision':saved['revision'],'edit':saved['edit']});assert r.status_code==200
    request.update(request_id=uuid.uuid4().hex,revision=r.json()['revision'],final_id=client.get(url).json()['final_id'])
    assert client.post(url,json=request).status_code==202
    assert run_once();assert client.get(f'/api/projects/{pid}/media/result').content==b'chosen voiceover'
    assert client.get(url).json()['music'] is None
    assert client.get(f'/api/projects/{pid}/media/master').content==b'original master'


def test_final_music_rejects_stale_and_failure_keeps_previous_final(client,monkeypatch):
    pid,voice,aid,revision=prepared(client,monkeypatch)
    url=f'/api/studio/projects/{pid}/final-music';request={'request_id':uuid.uuid4().hex,'revision':revision,'master_id':MASTER,'final_id':voice}
    assert client.post(url,json=request|{'final_id':'master'}).status_code==409
    assert client.post(url,json=request|{'master_id':'e'*32}).status_code==409
    assert client.post(url,json=request|{'revision':revision+1}).status_code==409
    response=client.post(url,json=request);assert response.status_code==202
    monkeypatch.setattr(media,'probe',lambda path:(_ for _ in ()).throw(ValueError('bad media')))
    assert run_once()
    assert client.get(url).json()['jobs'][0]['status']=='failed'
    assert client.get(f'/api/projects/{pid}/media/result').content==b'chosen voiceover'
    app.dependency_overrides[current_user]=lambda:{'id':'v'}
    assert client.get(url).status_code==404
    assert client.post(url,json=request).status_code==404
    assert client.get(url+'/'+response.json()['id']+'/video.mp4').status_code==404


def test_real_final_mix_contains_voice_and_music_with_unchanged_picture(client,monkeypatch):
    import array,math,subprocess
    pid,voice,aid,revision=prepared(client,monkeypatch)
    monkeypatch.setattr(media,"probe",REAL_PROBE)
    source=settings.data_dir/pid/'dubbing'/voice/'video.mp4'
    media.ffmpeg('-f','lavfi','-i','color=blue:s=160x240:d=4:r=12','-f','lavfi','-i','sine=frequency=440:duration=4','-c:v','libx264','-c:a','aac',source)
    track=settings.data_dir/pid/'assets'/aid
    media.ffmpeg('-f','lavfi','-i','sine=frequency=220:duration=4','-f','wav',track)
    before=project(pid)['result'];before['metadata']['duration']=4
    with connect() as db:db.execute('UPDATE projects SET result=? WHERE id=?',(json.dumps(before),pid))
    manual=f'/api/studio/projects/{pid}/manual';saved=client.get(manual).json();saved['edit']['music'].update(gain_db=-6,duck=False,fade_in=0,fade_out=0)
    revision=client.put(manual,json={'revision':saved['revision'],'edit':saved['edit']}).json()['revision']
    url=f'/api/studio/projects/{pid}/final-music'
    r=client.post(url,json={'request_id':uuid.uuid4().hex,'revision':revision,'master_id':MASTER,'final_id':voice});assert r.status_code==202
    assert run_once();output=settings.data_dir/pid/'audio-mixes'/r.json()['id']/'video.mp4'
    assert output.is_file()
    assert client.get(f'/api/projects/{pid}/media/result').content==output.read_bytes()
    assert abs(media.probe(output)['duration']-4)<.15
    def picture(path):return subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-map','0:v','-c:v','copy','-f','hash','-'])
    assert picture(output)==picture(source)
    samples=array.array('f',subprocess.check_output(['ffmpeg','-v','error','-ss','1','-i',str(output),'-t','1','-map','0:a','-ac','1','-ar','16000','-f','f32le','-']))
    def energy(frequency):return abs(sum(v*complex(math.cos(2*math.pi*frequency*i/16000),math.sin(2*math.pi*frequency*i/16000)) for i,v in enumerate(samples)))/len(samples)
    assert energy(440)>.03,'Selected voice must remain audible'
    assert energy(220)>.01,'Added music must actually exist in downloaded audio'
    assert energy(330)<.002


def test_switching_voice_keeps_the_final_music(client,monkeypatch):
    pid,voice,aid,revision=prepared(client,monkeypatch)
    from backend import music
    def mix(source,track,folder,config,duration,has_audio):
        output=folder/'music-mix.mp4';output.write_bytes(source.read_bytes()+b' plus music');return output
    monkeypatch.setattr(music,'mix',mix);monkeypatch.setattr(media,'probe',lambda path:{'duration':40,'has_audio':True})
    url=f'/api/studio/projects/{pid}/final-music'
    assert client.post(url,json={'request_id':uuid.uuid4().hex,'revision':revision,'master_id':MASTER,'final_id':voice}).status_code==202
    assert run_once()
    new_voice=ready_delivery(pid);(settings.data_dir/pid/'dubbing'/new_voice/'video.mp4').write_bytes(b'new voice')
    response=client.put(f'/api/studio/projects/{pid}/dubbing/final',json={'master_id':MASTER,'version_id':new_voice});assert response.status_code==200
    assert run_once()
    assert client.get(f'/api/projects/{pid}/media/result').content==b'new voice plus music'
    assert client.get(url).json()['voice_id']==new_voice
    assert client.get(url).json()['music']['asset_id']==aid


def test_new_dubbing_job_retains_music_and_waits_for_mix(client,monkeypatch):
    from backend.tests.test_dubbing import body
    from backend import music,dubbing_audio as audio
    pid,voice,aid,revision=prepared(client,monkeypatch)
    def mix(source,track,folder,config,duration,has_audio):
        out=folder/'music-mix.mp4';out.write_bytes(source.read_bytes()+b' plus music');return out
    monkeypatch.setattr(music,'mix',mix);monkeypatch.setattr(media,'probe',lambda path:{'duration':40,'has_audio':True})
    url=f'/api/studio/projects/{pid}/final-music'
    client.post(url,json={'request_id':uuid.uuid4().hex,'revision':revision,'master_id':MASTER,'final_id':voice});assert run_once()
    old=client.get(url).json()['final_id']
    monkeypatch.setattr(audio,'translate',lambda pid,phrases,language:[dict(p,text='New voice') for p in phrases])
    monkeypatch.setattr(audio,'synthesize',lambda text,voice,path,model:path.write_bytes(b'mp3'))
    monkeypatch.setattr(audio,'fit_phrase',lambda source,output,seconds:output.write_bytes(b'wav'))
    def assemble(master,folder,phrases,duration):
        (folder/'video.mp4').write_bytes(b'generated voice');return {'duration':40,'has_audio':True}
    monkeypatch.setattr(audio,'assemble',assemble)
    r=client.post(f'/api/studio/projects/{pid}/dubbing',json=body(voice='ru-female'));assert r.status_code==202
    assert run_once();assert client.get(url).json()['final_id']==old
    assert run_once();assert client.get(f'/api/projects/{pid}/media/result').content==b'generated voice plus music'
    assert client.get(url).json()['voice_id']==r.json()['id']
