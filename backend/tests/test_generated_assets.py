import json
from backend.tests.test_studio import client,create,seed_plan
from backend import ai,timeline_proposals,media
from backend.db import connect,project
from backend.config import settings

def test_generation_is_reviewable_private_asset_and_not_applied(client,monkeypatch,tmp_path):
    pid=create(client).json()['id'];seed_plan(pid)
    url=f'/api/studio/projects/{pid}/manual';edit=client.get(url).json()['edit']
    revision=client.put(url,json={'revision':1,'edit':edit}).json()['revision']
    generated=tmp_path/'generated.mp4';generated.write_bytes(b'synthetic-provider-output')
    calls=[]
    def generate(*args):
        calls.append(args)
        assert 'Segment context' in args[3].generation_prompt
        return {'path':generated}
    monkeypatch.setattr(ai,'generate_broll',generate)
    base=f'/api/studio/projects/{pid}/timeline-proposals'
    response=client.post(base,json={'revision':revision,'clip_id':edit['clips'][0]['id'],'instruction':'Illustrate the narrated scene','mode':'generated_broll'})
    assert response.status_code==202,response.text
    ident=response.json()['id'];timeline_proposals.run_job(project(pid),{'id':ident})
    proposal=client.get(base).json()[0]
    assert proposal['status']=='ready'
    assert client.get(url).json()['edit']['clips'][0]['external_broll'] is None
    asset=proposal['result']['clip']['external_broll']['asset_id']
    assert (settings.data_dir/pid/'assets'/asset).read_bytes()==b'synthetic-provider-output'
    assert client.get(f'/api/studio/projects/{pid}/assets').json()[0]['metadata']['generated']
    with connect() as db:db.execute("UPDATE jobs SET status='complete' WHERE project_id=?",(pid,))
    assert client.post(base+'/'+ident+'/accept',json={'revision':revision}).status_code==200
    clip=client.get(url).json()['edit']['clips'][0]
    assert not clip['approved'] and clip['external_broll']['asset_id']==asset
