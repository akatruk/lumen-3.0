import json,time
from backend.tests.test_studio import client,create,seed_plan,T
from backend.db import connect,project
from backend import music_plans
from backend.music import Music,MusicLevel

def test_candidate_reel_keeps_audio(tmp_path,monkeypatch):
    from backend.config import settings
    from backend import media
    monkeypatch.setattr(settings,'data_dir',tmp_path)
    pid='c'*32;aid='d'*32
    folder=tmp_path/pid/'assets';folder.mkdir(parents=True)
    media.ffmpeg('-f','lavfi','-i','sine=frequency=220:duration=3','-f','wav',folder/aid)
    reel=music_plans.build_reel(pid,[{'id':aid,'samples':[{'start':0,'end':1},{'start':2,'end':3}]}],tmp_path/'reel')
    metadata=media.probe(reel)
    assert metadata['has_audio'] and abs(metadata['duration']-2)<.2

def test_music_proposal_review_lock_and_isolation(client,monkeypatch,tmp_path):
    pid=create(client).json()['id'];seed_plan(pid)
    url=f'/api/studio/projects/{pid}/manual';edit=client.get(url).json()['edit']
    revision=client.put(url,json={'revision':1,'edit':edit}).json()['revision']
    aid='a'*32
    with connect() as db:db.execute('INSERT INTO studio_assets VALUES(?,?,?,?,?,?,?)',(aid,pid,'b'*32,'Owned music','Owned',json.dumps({'kind':'music','duration':10}),time.time()))
    monkeypatch.setattr(music_plans,'build_reel',lambda *a:tmp_path/'samples.mp4')
    suggestion=music_plans.Suggestion(music=Music(asset_id=aid,levels=[MusicLevel(at=0,gain_db=-30),MusicLevel(at=10,gain_db=-24)]),reason=T,emotional_curve=[T])
    monkeypatch.setattr(music_plans.ai,'json_call',lambda *a,**k:suggestion)
    base=f'/api/studio/projects/{pid}/music-plans'
    response=client.post(base,json={'revision':revision,'asset_ids':[aid]});assert response.status_code==202,response.text
    music_plans.run_job(project(pid),response.json())
    assert client.get(url).json()['edit']['music'] is None
    assert client.get(base).json()[0]['status']=='ready'
    with connect() as db:db.execute("UPDATE jobs SET status='complete' WHERE project_id=?",(pid,))
    response=client.post(base+'/'+response.json()['id']+'/accept',json={'revision':revision})
    assert response.status_code==200,response.text
    saved=client.get(url).json();edit=saved['edit'];edit['music']['locked']=True
    revision=client.put(url,json={'revision':saved['revision'],'edit':edit}).json()['revision']
    assert client.post(base,json={'revision':revision,'asset_ids':[aid]}).status_code==409
    edit['music']['gain_db']=-12
    assert client.put(url,json={'revision':revision,'edit':edit}).status_code==409
    other=create(client).json()['id'];seed_plan(other)
    other_url=f'/api/studio/projects/{other}/manual';other_edit=client.get(other_url).json()['edit']
    other_revision=client.put(other_url,json={'revision':1,'edit':other_edit}).json()['revision']
    assert client.post(f'/api/studio/projects/{other}/music-plans',json={'revision':other_revision,'asset_ids':[aid]}).status_code==422
