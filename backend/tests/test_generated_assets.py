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
    assert response.status_code==422 and response.json()['detail']=='hypit_prompt_only'
    assert calls==[]
