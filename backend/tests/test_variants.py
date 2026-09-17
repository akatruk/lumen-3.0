import json
import pytest
from backend.tests.test_studio import client,create,seed_plan
from backend import variants
from backend.db import connect,update,project
from backend.schemas import Text
from backend import media
REAL_PROBE=media.probe

def test_five_platforms_render_and_download(client,tmp_path,monkeypatch):
    from backend.config import settings
    from backend.tests.test_studio import plan
    pid=create(client).json()['id'];seed_plan(pid)
    monkeypatch.setattr(media,'probe',REAL_PROBE)
    folder=settings.data_dir/pid/'renders'/('a'*32);folder.mkdir(parents=True)
    source=folder/'result.mp4'
    media.ffmpeg('-f','lavfi','-i','color=blue:s=160x240:d=2:r=12','-f','lavfi','-i','sine=frequency=440:duration=2','-c:v','libx264','-c:a','aac',source)
    analysis=plan();analysis.scenes[0].end=2
    master={'asset_credits':[{'title':'Music','attribution':'Creator · CC BY 4.0'}],'render_id':'a'*32,'timeline':[[0,2]],'metadata':REAL_PROBE(source)}
    update(pid,result=master,analysis=analysis.model_dump(exclude={'transfers'}),status='complete')
    planned=variants.Plans(variants=[variants.Variant(hook_seconds=.5,cta_seconds=.7,title_style='panel',aspect={'douyin':'9:16','instagram_reels':'4:5','youtube_shorts':'1:1','tiktok':'16:9','xiaohongshu':'9:16'}[p],platform=p,rationale=Text(en='Specific',zh='具体'),title='测试标题',description='测试说明',hashtags=[],cta='保存',segments=[{'start':0,'end':2}]) for p in variants.PLATFORMS])
    monkeypatch.setattr(variants.ai,'json_call',lambda *a,**k:planned)
    url=f'/api/studio/projects/{pid}/variants'
    assert client.post(url,json={'master_id':'a'*32,'reviewed':True}).status_code==200
    with connect() as db:payload=json.loads(db.execute("SELECT payload FROM jobs WHERE project_id=? AND kind='platform_variants'",(pid,)).fetchone()[0])
    variants.run_job(project(pid),payload)
    result=client.get(url).json()
    assert result['status']=='complete'
    assert client.get(url+'/files/credits.json').json()==master['asset_credits']
    assert {v['platform'] for v in result['result']['variants']}==set(variants.PLATFORMS)
    for name in variants.PLATFORMS:
        output=settings.data_dir/pid/'packages'/result['package_id']/(name+'.mp4')
        meta=REAL_PROBE(output)
        variant=next(v for v in planned.variants if v.platform==name)
        assert (meta['width'],meta['height'])==variants.DIMENSIONS[variant.aspect]
        assert meta['has_audio']
        assert output.stat().st_size>0

def ready(client):
    pid=create(client).json()['id'];seed_plan(pid)
    update(pid,result={'render_id':'a'*32,'timeline':[[0,40]],'metadata':{'duration':40}},status='complete')
    return pid

def test_package_approval_snapshot_and_ownership(client):
    pid=ready(client);url=f'/api/studio/projects/{pid}/variants'
    assert client.post(url,json={'master_id':'a'*32,'reviewed':False}).status_code==422
    assert client.post(url,json={'master_id':'b'*32,'reviewed':True}).status_code==409
    assert client.post(url,json={'master_id':'a'*32,'reviewed':True}).status_code==200
    assert client.post(url,json={'master_id':'a'*32,'reviewed':True}).status_code==409
    with connect() as db:
        payload=json.loads(db.execute("SELECT payload FROM jobs WHERE kind='platform_variants'").fetchone()[0])
    assert payload['master']['render_id']=='a'*32
    assert client.get(url).json()['status']=='queued'
    assert client.get(url+'/files/package.zip').status_code==404
    from backend.app import app
    from backend.auth import current_user
    app.dependency_overrides[current_user]=lambda:{'id':'v','email':'other@example.com'}
    assert client.get(url).status_code==404
    assert client.get(url+'/files/package.zip').status_code==404

def test_completed_package_idempotency_and_staleness(client):
    pid=ready(client);url=f'/api/studio/projects/{pid}/variants'
    client.post(url,json={'master_id':'a'*32,'reviewed':True})
    with connect() as db:
        db.execute("UPDATE jobs SET status='complete' WHERE project_id=?",(pid,))
        db.execute("UPDATE platform_packages SET status='complete',result=? WHERE project_id=?",(json.dumps({'variants':[]}),pid))
    old=client.get(url).json()['package_id']
    assert client.post(url,json={'master_id':'a'*32,'reviewed':True}).status_code==200
    assert client.get(url).json()['package_id']==old
    update(pid,result={'render_id':'b'*32})
    assert client.get(url).json()['stale'] is True

def test_timeline_validation():
    def make():return variants.Plans(variants=[variants.Variant(platform=p,rationale=Text(en='Specific',zh='具体'),title='Title',description='Description',hashtags=[],cta='Save',segments=[{'start':0,'end':10}]) for p in variants.PLATFORMS])
    p=make();variants.validate(p,10)
    p.variants[0].segments[0].start=6
    with pytest.raises(ValueError):variants.validate(p,10,boundaries=[0,10])
    p=make()
    p.variants[0].title="中文标题"
    with pytest.raises(ValueError):variants.validate(p,10,language="en")
    p=make()
    p.variants[0].segments[0].start=2
    with pytest.raises(ValueError):variants.validate(p,10,[(1,3)])
    p=make()
    p.variants[0].segments[0].end=11
    with pytest.raises(ValueError):variants.validate(p,10)
    p=make();p.variants[0].segments.append(p.variants[0].segments[0])
    with pytest.raises(ValueError):variants.validate(p,10)
    p=make();p.variants[0].platform='youtube_shorts'
    with pytest.raises(ValueError):variants.validate(p,10)

def test_duration_targets_and_shorts_shape():
    def make():return variants.Plans(variants=[variants.Variant(platform=p,rationale=Text(en='Specific',zh='具体'),title='Title',description='Description',hashtags=[],cta='Save',segments=[{'start':0,'end':120}]) for p in variants.PLATFORMS])
    p=make();variants.validate(p,420)
    with pytest.raises(ValueError):variants.validate(p,420,max_seconds={'douyin':60})
    shorts=next(v for v in p.variants if v.platform=='youtube_shorts');shorts.aspect='16:9'
    with pytest.raises(ValueError):variants.validate(p,420)
    shorts.aspect='9:16';shorts.segments[0].end=181
    with pytest.raises(ValueError):variants.validate(p,420)

def test_request_rejects_overlong_shorts_target(client):
    pid=ready(client);url=f'/api/studio/projects/{pid}/variants'
    assert client.post(url,json={'master_id':'a'*32,'reviewed':True,'max_seconds':{'youtube_shorts':420}}).status_code==422
    assert client.post(url,json={'master_id':'a'*32,'reviewed':True,'max_seconds':{'youtube_shorts':60,'douyin':90}}).status_code==200
    with connect() as db:payload=json.loads(db.execute("SELECT payload FROM jobs WHERE project_id=? AND kind='platform_variants'",(pid,)).fetchone()[0])
    assert payload['max_seconds']=={'youtube_shorts':60,'douyin':90}

def test_variant_failure_does_not_fail_approved_master(client,monkeypatch):
    pid=ready(client)
    client.post(f'/api/studio/projects/{pid}/variants',json={'master_id':'a'*32,'reviewed':True})
    def fail(*args):raise ValueError('provider_request_failed')
    monkeypatch.setattr(variants,'run_job',fail)
    from backend.worker import run_once
    assert run_once()
    assert project(pid)['status']=='complete'
    assert project(pid)['result']['render_id']=='a'*32
    with connect() as db:assert db.execute("SELECT status FROM jobs WHERE kind='platform_variants'").fetchone()[0]=='failed'
