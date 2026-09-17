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
    monkeypatch.setattr('backend.music_dynamics.enrich',lambda *args:None)
    monkeypatch.setattr(music_plans,'build_reel',lambda *a:tmp_path/'samples.mp4')
    suggestion=music_plans.Suggestion(music=Music(asset_id=aid,levels=[MusicLevel(at=0,gain_db=-30),MusicLevel(at=10,gain_db=-24)]),reason=T,emotional_curve=[T])
    prompts=[]
    def propose(*args,**kwargs):
        prompts.append(args[2]);return suggestion
    monkeypatch.setattr(music_plans.ai,'json_call',propose)
    base=f'/api/studio/projects/{pid}/music-plans'
    response=client.post(base,json={'revision':revision,'asset_ids':[aid]});assert response.status_code==202,response.text
    music_plans.run_job(project(pid),response.json())
    assert '"output_timeline"' in prompts[0] and 'OUTPUT times' in prompts[0]
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


def test_mix_only_preserves_track_and_alignment(client,monkeypatch,tmp_path):
    pid=create(client).json()['id'];seed_plan(pid)
    aid='a'*32
    with connect() as db:db.execute('INSERT INTO studio_assets VALUES(?,?,?,?,?,?,?)',(aid,pid,'b'*32,'Music','Owned',json.dumps({'kind':'music','duration':60}),time.time()))
    url=f'/api/studio/projects/{pid}/manual';edit=client.get(url).json()['edit']
    edit['music']=Music(asset_id=aid,source_start=17).model_dump()
    revision=client.put(url,json={'revision':1,'edit':edit}).json()['revision']
    base=f'/api/studio/projects/{pid}/music-plans'
    response=client.post(base,json={'revision':revision,'mode':'mix_only'});assert response.status_code==202,response.text
    monkeypatch.setattr('backend.music_dynamics.enrich',lambda *a:None)
    def reel(pid,candidates,folder):
        assert any(s['start']==17 for s in candidates[0]['samples'])
        return tmp_path/'sample.mp4'
    monkeypatch.setattr(music_plans,'build_reel',reel)
    def model(*args,**kw):
        assert 'MIX ONLY' in args[2]
        return music_plans.Suggestion(music=Music(asset_id=aid,source_start=17,gain_db=-28),reason=T,emotional_curve=[T])
    monkeypatch.setattr(music_plans.ai,'json_call',model)
    music_plans.run_job(project(pid),response.json())
    assert client.get(url).json()['edit']['music']['gain_db']==-24
    with connect() as db:db.execute("UPDATE jobs SET status='complete' WHERE project_id=?",(pid,))
    assert client.post(base+'/'+response.json()['id']+'/accept',json={'revision':revision}).status_code==200
    saved=client.get(url).json()['edit']
    assert saved['music']['asset_id']==aid and saved['music']['source_start']==17 and saved['music']['gain_db']==-28
    assert saved['clips']==edit['clips']


def test_mix_only_rejects_track_or_offset_change():
    import pytest
    snapshot={'mode':'mix_only','edit':{'music':Music(asset_id='a'*32,source_start=1).model_dump(),'clips':[{'start':0,'end':20,'approved':True}]},'candidates':[{'id':'a'*32,'duration':30,'samples':[{'start':0,'end':4}]}]}
    for track,offset in [('b'*32,1),('a'*32,2)]:
        result=music_plans.Suggestion(music=Music(asset_id=track,source_start=offset),reason=T,emotional_curve=[])
        with pytest.raises(ValueError,match='provider_invalid_analysis'):music_plans.validate(result,snapshot)
