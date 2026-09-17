from backend import ai
from backend.manual import Edit, Clip, ExternalBroll
from backend.music import Music


def test_review_context_uses_approved_output_order_and_preserves_locks():
    edit = Edit(clips=[
        Clip(id='hook', start=20, end=24, locked=True, text='Proof'),
        Clip(id='omitted', start=5, end=9, approved=False),
        Clip(id='body', start=0, end=6, external_broll=ExternalBroll(
            start=1, end=3, source_start=10, asset_id='a'*32)),
    ], music=Music(asset_id='b'*32))
    context = ai.quality_edit_context(edit.model_dump())
    timeline = context['final_output_timeline']
    assert timeline['duration'] == 10
    assert [(s['id'], s['start'], s['end'], s['source_start']) for s in timeline['tracks']['video']] == [
        ('hook', 0, 4, 20), ('body', 4, 10, 0)]
    assert timeline['tracks']['video'][0]['locked']
    insert = timeline['tracks']['cutaways'][0]
    assert (insert['start'], insert['end'], insert['source_start']) == (5, 7, 10)
    assert timeline['tracks']['music'][0]['end'] == 10
    assert context['caption_style']['enabled'] is False


def test_legacy_recommendations_are_explicitly_source_timed():
    recommendations = [{'start': 20, 'end': 24, 'action': 'move_to_front'}]
    assert ai.quality_edit_context(recommendations) == {'source_time_recommendations': recommendations}


def test_review_uses_dedicated_system_and_both_videos(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(ai, 'ffmpeg', lambda *args: None)
    monkeypatch.setattr(ai, 'json_call', lambda *args, **kw: calls.append((args, kw)) or 'review')
    assert ai.review('project', tmp_path, 'brief', Edit(clips=[Clip(start=10, end=15)]).model_dump()) == 'review'
    args, kwargs = calls[0]
    assert args[1] == tmp_path/'qa.mp4'
    assert args[4] == 'quality_review'
    assert kwargs['reference'] == ai.settings.data_dir/'project'/'analysis.mp4'
    assert kwargs['system'] == ai.QUALITY_SYSTEM
    assert 'final_output_timeline' in args[2]
    assert 'required editor unlock' in kwargs['system']
