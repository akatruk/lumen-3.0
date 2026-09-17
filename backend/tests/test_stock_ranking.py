import pytest
from backend import ai,stock_ranking as ranking
from backend.tests.test_studio import T

def test_reject_weak_and_sort_with_reasons(monkeypatch):
    items=[{'page_id':n,'title':str(n),'media_url':'private-url'} for n in range(4)]
    def model(*args,**kw):
        assert 'private-url' not in args[2]
        return ranking.Ranking(reviews=[ranking.CandidateReview(page_id=n,score=score,suitability=kind,reason=T) for n,score,kind in [(0,70,'illustration'),(1,95,'reject'),(2,90,'evidence'),(3,40,'illustration')]])
    monkeypatch.setattr(ai,'json_call',model)
    result=ranking.rank('project',{'transcript':[]},items)
    assert [r['page_id'] for r in result]==[2,0]
    assert result[0]['relevance']['reason']==T

@pytest.mark.parametrize('ids',[[1],[1,1],[1,3]])
def test_ranking_must_cover_exact_candidates(ids):
    result=ranking.Ranking(reviews=[ranking.CandidateReview(page_id=n,score=80,suitability='illustration',reason=T) for n in ids])
    with pytest.raises(ValueError):ranking.validate(result,[{'page_id':1},{'page_id':2}])
