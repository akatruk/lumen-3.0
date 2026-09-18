from backend.manual import Edit,Clip
from backend.timeline import compile_timeline
from backend.render_state import delivery_state
from backend.render_summary import summarize


def test_saved_zoom_is_pending_even_if_scene_is_unapproved_and_audio_is_updated():
    old=Edit(clips=[Clip(start=0,end=162.1)])
    result={'render_id':'old','director_timeline':compile_timeline(old)}
    edit=old.model_copy(deep=True)
    edit.clips[0].zoom_end=1.2;edit.clips[0].approved=False
    state=delivery_state(edit,result,True)
    assert state['picture_pending'] and state['separate_audio']
    assert state['unapproved_scenes']==1 and state['rendered_scenes']==1
    edit.clips[0].approved=True
    assert summarize(edit,162.1)['slow_motion_scenes']==[1]
    edit.clips[0].motion_seconds=4
    assert summarize(edit,162.1)['slow_motion_scenes']==[]


def test_audio_review_ids_and_lock_changes_do_not_claim_picture_is_stale():
    edit=Edit(clips=[Clip(start=0,end=20,zoom_end=1.2)])
    old=compile_timeline(edit)
    del old['tracks']['video'][0]['motion']['duration'] # legacy render
    edit.clips[0].id='new';edit.clips[0].locked=True;edit.normalize=True
    assert delivery_state(edit,{'director_timeline':old})['picture_pending'] is False
    edit.clips[0].motion_seconds=4
    assert delivery_state(edit,{'director_timeline':old})['picture_pending'] is True
    assert delivery_state(edit,{'director_timeline':compile_timeline(edit)})['picture_pending'] is False
    assert delivery_state(edit,{})['picture_pending'] is None


def test_caption_style_counts_only_with_visible_captions():
    edit=Edit(clips=[Clip(start=0,end=10)])
    result={'director_timeline':compile_timeline(edit)}
    edit.color='yellow'
    assert not delivery_state(edit,result)['picture_pending']


def test_quality_signature_compares_executable_movement_duration():
    from backend.creative_plans import rendered_edit_signature
    edit=Edit(clips=[Clip(start=0,end=20)])
    before=rendered_edit_signature(edit)
    edit.clips[0].motion_seconds=4
    assert rendered_edit_signature(edit)==before # still shot
    edit.clips[0].zoom_end=1.2
    quick=rendered_edit_signature(edit)
    edit.clips[0].motion_seconds=None
    assert rendered_edit_signature(edit)!=quick
    full=rendered_edit_signature(edit)
    edit.clips[0].motion_seconds=20
    assert rendered_edit_signature(edit)==full
