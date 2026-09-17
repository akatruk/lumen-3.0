import pytest
import httpx
from backend.config import settings
from backend.db import init_db,connect
from backend.schemas import QA
from backend import ai

@pytest.fixture
def context(tmp_path,monkeypatch):
    monkeypatch.setattr(settings,'data_dir',tmp_path)
    monkeypatch.setattr(settings,'openrouter_api_key','synthetic-test-key')
    init_db()
    with connect() as db:
        db.execute("INSERT INTO users VALUES('u','qa@test','unused',0)")
        db.execute("INSERT INTO projects(id,user_id,title,brief,language,aspect,auto_render,generative,budget,status,stage,created,updated) VALUES('p','u','QA','','en','original',0,0,3,'queued','queued',0,0)")
    video=tmp_path/'test.mp4';video.write_bytes(b'test-only-bytes')
    return video

def mock_response(monkeypatch,status,payload):
    client=httpx.Client
    requests=[]
    def handler(request):
        requests.append(request)
        return httpx.Response(status,json=payload)
    monkeypatch.setattr(ai.httpx,'Client',lambda **kw:client(transport=httpx.MockTransport(handler),**kw))
    return requests

def test_402_does_not_charge_or_fabricate_results(context,monkeypatch):
    requests=mock_response(monkeypatch,402,{'error':{'message':'No credits'}})
    with pytest.raises(ValueError,match='provider_credits_required'):
        ai.json_call('p',context,'Review fixture',QA,'test')
    assert len(requests)==1
    with connect() as db: assert db.execute('SELECT actual FROM spend').fetchone()[0]==0

def test_missing_key_does_not_reserve(context,monkeypatch):
    monkeypatch.setattr(settings,'openrouter_api_key','')
    with pytest.raises(ValueError,match='provider_not_configured'):
        ai.json_call('p',context,'Review fixture',QA,'test')
    with connect() as db: assert db.execute('SELECT COUNT(*) FROM spend').fetchone()[0]==0

def test_malformed_output_fails_closed(context,monkeypatch):
    mock_response(monkeypatch,200,{'choices':[{'message':{'content':'Not JSON'}}],'usage':{'cost':.01}})
    with pytest.raises(ValueError,match='provider_invalid_analysis'):
        ai.json_call('p',context,'Review fixture',QA,'test')
    with connect() as db: assert db.execute('SELECT actual FROM spend').fetchone()[0]==.01

def test_review_compares_original_and_output(context,monkeypatch):
    import json
    requests=mock_response(monkeypatch,200,{'choices':[{'message':{'content':'{"passed":true,"observations":[],"issues":[]}'}}],'usage':{'cost':.02}})
    review=ai.json_call('p',context,'Review fixture',QA,'test',reference=context)
    assert review.passed
    body=json.loads(requests[0].content)
    parts=body['messages'][1]['content']
    assert sum(p['type']=='video_url' for p in parts)==2

def test_truncated_json_is_not_accepted(context,monkeypatch):
    requests=mock_response(monkeypatch,200,{'choices':[{'finish_reason':'length','message':{'content':'{"passed":true,"observations":[],"issues":[]}'}}],'usage':{'cost':.03}})
    with pytest.raises(ValueError,match='provider_analysis_truncated'):
        ai.json_call('p',context,'Review fixture',QA,'test')
    assert len(requests)==1
    with connect() as db:
        assert 'output_limit' in db.execute("SELECT detail FROM events WHERE kind='analysis_validation'").fetchone()[0]
        assert db.execute('SELECT actual FROM spend').fetchone()[0]==.03

def test_schema_diagnostics_exclude_model_content(context,monkeypatch):
    mock_response(monkeypatch,200,{'choices':[{'message':{'content':'{"passed":"private source words","observations":[],"issues":[]}'}}]})
    with pytest.raises(ValueError,match='provider_invalid_analysis'):
        ai.json_call('p',context,'Review fixture',QA,'test')
    with connect() as db:
        detail=db.execute("SELECT detail FROM events WHERE kind='analysis_validation'").fetchone()[0]
        assert 'bool_parsing' in detail
        assert 'private source words' not in detail

def test_reference_task_does_not_inherit_editing_instructions(context,monkeypatch):
    import json
    from backend.studio import DNA
    text={'en':'Observed technique','zh':'观察到的方法'}
    shot={key:text for key in ['observation','visual_type','narrative_role','motion','transition','subtitle_emphasis','music','emotion','information_density','reusable_method']}
    shot.update(start=0,end=10)
    output={'summary':text,'shots':[shot],'uncertainties':[]}
    requests=mock_response(monkeypatch,200,{'choices':[{'message':{'content':json.dumps(output)}}]})
    result=ai.reference_dna('p',context,10,DNA)
    assert len(result.shots)==1
    payload=json.loads(requests[0].content)
    assert payload['messages'][0]['content']==ai.REFERENCE_SYSTEM
    assert 'auto_apply=true' not in payload['messages'][0]['content']
    assert '10 seconds' in payload['messages'][1]['content'][0]['text']

def test_director_plan_has_room_for_bilingual_transcript(context,monkeypatch):
    import json
    requests=mock_response(monkeypatch,200,{'choices':[{'finish_reason':'stop','message':{'content':'{"passed":true,"observations":[],"issues":[]}'}}],'usage':{'cost':.01}})
    ai.json_call('p',context,'Plan',QA,'director_plan')
    ai.json_call('p',context,'Reference',QA,'reference_dna')
    assert json.loads(requests[0].content)['max_tokens']==32000
    assert json.loads(requests[1].content)['max_tokens']==32000

def test_strict_schema_is_sent_to_provider(context,monkeypatch):
    import json
    from backend.studio import Director
    requests=mock_response(monkeypatch,200,{'choices':[{'message':{'content':'{"passed":true,"observations":[],"issues":[]}'}}]})
    ai.json_call('p',context,'Review',QA,'test')
    payload=json.loads(requests[0].content)
    assert payload['provider']['require_parameters'] is True
    assert payload['response_format']['json_schema']['strict'] is True
    spec=ai.strict_schema(Director)
    caption=spec['$defs']['Caption']
    assert 'emphasis_en' in caption['required']
    assert 'default' not in caption['properties']['emphasis_en']

@pytest.mark.parametrize('purpose',['director_plan','timeline_proposal','stock_discovery','stock_ranking'])
def test_completed_invalid_analysis_recovers_once(context,monkeypatch,purpose):
    client=httpx.Client
    calls=[]
    def handler(request):
        calls.append(request)
        content='invalid' if len(calls)==1 else '{"passed":true,"observations":[],"issues":[]}'
        return httpx.Response(200,json={'choices':[{'message':{'content':content}}],'usage':{'cost':.01}})
    monkeypatch.setattr(ai.httpx,'Client',lambda **kw:client(transport=httpx.MockTransport(handler),**kw))
    assert ai.json_call('p',context,'Plan',QA,purpose).passed
    assert len(calls)==2
    with connect() as db:assert round(db.execute('SELECT SUM(actual) FROM spend').fetchone()[0],2)==.02

def test_invalid_analysis_retry_is_bounded(context,monkeypatch):
    calls=mock_response(monkeypatch,200,{'choices':[{'message':{'content':'invalid'}}],'usage':{'cost':.01}})
    with pytest.raises(ValueError,match='provider_invalid_analysis'):
        ai.json_call('p',context,'Plan',QA,'director_plan')
    assert len(calls)==2

def test_ambiguous_provider_failure_is_not_retried(context,monkeypatch):
    calls=mock_response(monkeypatch,504,{'error':{}})
    with pytest.raises(ValueError,match='provider_request_failed'):
        ai.json_call('p',context,'Plan',QA,'director_plan')
    assert len(calls)==1

def test_schema_property_named_title_is_preserved():
    from backend.studio import Director
    scene=ai.strict_schema(Director)['$defs']['Scene']
    assert 'title' in scene['properties'] and 'title' in scene['required']

@pytest.mark.parametrize("purpose", ["director_plan", "platform_planning"])
def test_semantic_validation_is_repaired_and_never_skipped(context,monkeypatch,purpose):
    calls=mock_response(monkeypatch,200,{'choices':[{'message':{'content':'{"passed":true,"observations":[],"issues":[]}'}}],'usage':{'cost':.01}})
    validations=[]
    def validate(result):
        validations.append(result)
        raise ValueError('analysis_timestamps_invalid')
    with pytest.raises(ValueError,match='analysis_timestamps_invalid'):
        ai.json_call('p',context,'Plan',QA,purpose,validator=validate)
    assert len(calls)==len(validations)==2

def test_repair_obeys_remaining_budget(context,monkeypatch):
    with connect() as db:db.execute("UPDATE projects SET budget=.5 WHERE id='p'")
    calls=mock_response(monkeypatch,200,{'choices':[{'message':{'content':'invalid'}}],'usage':{'cost':.1}})
    with pytest.raises(ValueError,match='budget_limit'):
        ai.json_call('p',context,'Plan',QA,'director_plan')
    assert len(calls)==1


@pytest.mark.parametrize('purpose',['timeline_proposal','stock_discovery','stock_ranking'])
def test_new_editorial_repairs_are_bounded(context,monkeypatch,purpose):
    calls=mock_response(monkeypatch,200,{'choices':[{'message':{'content':'invalid'}}],'usage':{'cost':.01}})
    with pytest.raises(ValueError,match='provider_invalid_analysis'):ai.json_call('p',context,'Plan',QA,purpose)
    assert len(calls)==2


def test_timeline_semantic_validator_can_trigger_repair(context,monkeypatch):
    calls=mock_response(monkeypatch,200,{'choices':[{'message':{'content':'{"passed":true,"observations":[],"issues":[]}'}}],'usage':{'cost':.01}})
    checked=[]
    def validate(result):
        checked.append(result)
        if len(checked)==1:
            error=ValueError('analysis_timestamps_invalid');error.feedback='Use the supplied sample range.';raise error
    assert ai.json_call('p',context,'Plan',QA,'timeline_proposal',validator=validate).passed
    assert len(calls)==2
    assert b'Use the supplied sample range.' in calls[1].content
