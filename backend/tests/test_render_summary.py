from backend.manual import Edit, Clip
from backend.render_summary import summarize
from backend.tests.test_studio import client, create, seed_plan


def test_split_original_and_small_trim_are_not_visual_improvements():
    s = summarize(Edit(clips=[Clip(start=0,end=80),Clip(start=80,end=160.5)],normalize=True),162.1)
    assert s['near_original']
    assert s['removed_ranges'] == [[160.5,162.1]]
    assert s['output_duration'] == 160.5
    assert all(not c['operations'] for c in s['clips'])


def test_visible_effects_and_approved_render_ranges():
    s = summarize(Edit(clips=[Clip(start=10,end=20,zoom_end=1.2),Clip(start=0,end=5),Clip(start=20,end=30,approved=False)]),30)
    assert not s['near_original']
    assert s['output_duration'] == 15
    assert s['removed_ranges'] == [[5,10],[20,30]]
    assert s['clips'][0]['operations'] == ['motion']
    assert 'reorder' in s['global_operations']
    assert len(s['clips']) == 2


def test_summary_requires_saved_edit_and_reports_current_revision(client):
    pid=create(client).json()['id'];seed_plan(pid)
    url=f'/api/studio/projects/{pid}/manual'
    assert client.get(url+'/summary').status_code == 422
    edit=client.get(url).json()['edit']
    assert client.put(url,json={'revision':1,'edit':edit}).status_code == 200
    data=client.get(url+'/summary').json()
    assert data['revision'] == 2
    assert data['near_original']
    assert data['pending_proposals'] == {'creative':0,'music':0,'individual':0}


def test_pending_proposals_are_not_applied_and_summary_is_owned(client):
    from backend.db import connect
    from backend.auth import current_user
    from backend.app import app
    pid=create(client).json()['id'];seed_plan(pid)
    url=f'/api/studio/projects/{pid}/manual'
    edit=client.get(url).json()['edit']
    client.put(url,json={'revision':1,'edit':edit})
    with connect() as db:
        db.execute("INSERT INTO creative_plans VALUES(?,?,?,?,?,?,?,?)",('p',pid,1,'{}','ready',None,None,1))
    data=client.get(url+'/summary').json()
    assert data['pending_proposals']['creative'] == 1
    assert data['near_original']
    assert client.get(url).json()['edit'] == edit
    app.dependency_overrides[current_user]=lambda:{'id':'other','email':'other@example.com'}
    assert client.get(url+'/summary').status_code == 404
