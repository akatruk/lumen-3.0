import json
import pytest
from backend.tests.test_studio import client,create,seed_plan,plan,T
from backend.schemas import QualityReview,Score
from backend.db import connect,project,update
from backend import studio,worker

def test_quality_contract_requires_unique_scores_and_low_score_corrections():
    scores=[Score(category=c,value=60,reason=T) for c in ['hook','clarity','pacing','visuals','audio']]
    with pytest.raises(ValueError):QualityReview(passed=True,observations=[],issues=[],scores=scores,revisions=[])
    scores[-1]=scores[0]
    with pytest.raises(ValueError):QualityReview(passed=False,observations=[],issues=[],scores=scores,revisions=[T])

@pytest.mark.parametrize('locked',[False,True])
def test_low_quality_drafts_preserve_render_and_respect_locks(client,monkeypatch,locked):
    pid=create(client).json()['id'];seed_plan(pid)
    url=f'/api/studio/projects/{pid}/manual';edit=client.get(url).json()['edit']
    edit['clips'][0]['approved']=True;edit['clips'][0]['locked']=locked
    revision=client.put(url,json={'revision':1,'edit':edit}).json()['revision']
    result={'render_id':'a'*32,'timeline':[[0,40]],'qa_status':'needs_review','qa':{'revisions':[T]},'quality_score':50}
    monkeypatch.setattr(worker,'render_job',lambda p,payload:update(pid,result=result,status='needs_review'))
    studio.render_job(project(pid),{'revision':revision,'manual':edit,'plan':plan().model_dump(),'decisions':[],'quality_review':True})
    current=project(pid)['result']
    assert current['render_id']=='a'*32
    assert client.get(url).json()['edit']==edit
    with connect() as db:
        drafts=db.execute('SELECT * FROM creative_plans WHERE project_id=?',(pid,)).fetchall()
    assert len(drafts)==1 and current['quality_revision_id']==drafts[0]['id']
    snapshot=json.loads(drafts[0]['snapshot'])
    assert snapshot['current_edit']==edit
    assert snapshot['quality_feedback']['revisions']==[T]
    assert snapshot['quality_feedback']['render_id']=='a'*32
    assert snapshot['quality_feedback']['output_timeline']['tracks']['video'][0]['locked']==locked
    listed=client.get(f'/api/studio/projects/{pid}/creative-plans').json()[0]
    assert listed['quality_revisions']==[T]


def test_quality_feedback_coverage_rejects_missing_duplicate_and_invented_items():
    from backend import creative_plans as creative
    from backend.tests.test_creative_plans import proposal
    value=proposal();feedback={'revisions':[T,T]}
    with pytest.raises(ValueError,match='provider_invalid_analysis'):
        creative.validate_quality_reviews(value,feedback)
    row=lambda index:creative.QualityRevisionReview(revision_index=index,outcome='not_applied',reason=T)
    for indices in ([0,0],[0,2],[0]):
        value.quality_revision_reviews=[row(i) for i in indices]
        with pytest.raises(ValueError):creative.validate_quality_reviews(value,feedback)
    value.quality_revision_reviews=[row(0),row(1)]
    creative.validate_quality_reviews(value,feedback)
    with pytest.raises(ValueError):creative.validate_quality_reviews(value,None)
    value.quality_revision_reviews=[]
    creative.validate_quality_reviews(value,None)
