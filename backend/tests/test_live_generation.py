"""Explicitly opted-in paid provider smoke test using synthetic footage only."""
import os
import pytest
from backend.tests.test_studio import client,create,seed_plan
from backend.config import settings
from backend import media
REAL_PROBE=media.probe

@pytest.mark.skipif(os.environ.get('LUMEN_LIVE_GENERATION')!='1',reason='Paid provider test requires explicit opt-in')
def test_real_generated_asset_can_be_previewed(client,monkeypatch):
    pid=create(client).json()['id'];seed_plan(pid)
    source=settings.data_dir/pid/'source'
    media.ffmpeg('-f','lavfi','-i','color=blue:s=320x568:d=4:r=24','-c:v','libx264','-f','mp4',source)
    monkeypatch.setattr(media,'probe',REAL_PROBE)
    edit=client.get(f'/api/studio/projects/{pid}/manual').json()['edit']
    base=f'/api/studio/projects/{pid}/timeline-proposals'
    response=client.post(base,json={'revision':1,'clip_id':edit['clips'][0]['id'],'instruction':'An abstract blue ocean-like wave, gentle motion, no people, no buildings, no text. Clearly illustrative.','mode':'generated_broll'})
    assert response.status_code==422 and response.json()['detail']=='hypit_prompt_only'
