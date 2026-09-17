import json
from backend.tests.test_studio import client,create,seed_plan
from backend.tests.test_creative_plans import proposal
from backend import creative_plans as creative
from backend.creator_style import Style,brief,measure
from backend.manual import Edit,Clip,Cutaway
from backend.db import connect,project

def test_style_changes_snapshot_and_persists_only_on_accept(client,monkeypatch):
    pid=create(client).json()['id'];seed_plan(pid)
    url=f'/api/studio/projects/{pid}/creative-plans'
    style=Style(structure='problem_solution',pacing='dynamic',presenter_percent=35,visuals='illustrated').model_dump()
    seen={}
    def fake(pid,path,prompt,*a,**kw):
        seen['prompt']=prompt;return proposal()
    monkeypatch.setattr(creative.ai,'json_call',fake)
    r=client.post(url,json={'revision':1,'style':style});assert r.status_code==202
    ident=r.json()['id'];creative.run_job(project(pid),{'id':ident})
    assert 'shot_duration_target_seconds' in seen['prompt'] and 'problem_solution' in seen['prompt']
    row=client.get(url).json()[0]
    assert 'snapshot' not in row
    assert row['style_audit']['preferences']==style
    with connect() as db:
        old=json.loads(db.execute('SELECT context FROM studio_projects WHERE project_id=?',(pid,)).fetchone()[0])
        assert old['creator'].get('style')!=style
        db.execute("UPDATE jobs SET status='complete' WHERE project_id=?",(pid,))
    assert client.post(url+'/'+ident+'/accept',json={'revision':1}).status_code==200
    with connect() as db:
        current=json.loads(db.execute('SELECT context FROM studio_projects WHERE project_id=?',(pid,)).fetchone()[0])
    assert current['creator']['style']==style

def test_measure_subtracts_cutaways_from_presenter():
    edit=Edit(clips=[Clip(start=0,end=10,cutaway=Cutaway(start=1,end=5,source_start=20)),Clip(start=10,end=20,shot_type='broll')])
    result=measure(edit,{})
    assert result['presenter_percent']==30
    assert result['broll_percent']==70
    assert brief({'pacing':'dynamic'})['shot_duration_target_seconds']==[1.5,4]

def test_legacy_music_survives_new_plan_schema():
    from backend.music import Music
    old={'asset_id':'a'*32,'source_start':0,'gain_db':-24,'fade_in':1,'fade_out':2,'duck':True}
    result=proposal();result.edit.music=Music.model_validate(old)
    creative.validate(result,40,saved_music=old)
    assert result.edit.music.levels==[]
