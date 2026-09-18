from backend.editorial_pacing import diagnose
from backend.manual import Clip, Edit


def test_relabelled_splits_do_not_fake_dynamic_pacing():
    edit = Edit(clips=[Clip(start=i, end=i+3, shot_type='presenter' if i % 2 else 'close_up') for i in range(0, 12, 3)])
    d = diagnose(edit, {'pacing': 'dynamic'})
    assert d['visual_run_count'] == 1
    assert d['average_visual_run_seconds'] == 12
    assert d['artificial_boundaries'] == [1, 2, 3]
    assert d['long_runs'][0]['clip_indices'] == [0, 1, 2, 3]


def test_actual_crop_change_and_source_jump_create_runs():
    d = diagnose(Edit(clips=[Clip(start=0, end=3), Clip(start=3, end=6, zoom=1.2), Clip(start=9, end=12, zoom=1.2)]))
    assert d['visual_run_count'] == 3
    assert d['artificial_boundaries'] == []


def test_replayed_hook_counts_overlap_once_without_forbidding_it():
    d = diagnose(Edit(clips=[Clip(start=5, end=8), Clip(start=0, end=12), Clip(start=6, end=9)]))
    assert d['repeated_source_seconds'] == 6
    assert d['opening_source'] == {'start': 5, 'end': 8}


def test_contiguous_dissolve_is_a_review_hint_not_a_rejection():
    d = diagnose(Edit(clips=[Clip(start=0, end=6), Clip(start=6, end=12, transition='crossfade')]))
    assert d['continuous_transition_indices'] == [1]
    assert d['visual_run_count'] == 2


def test_long_take_diagnostic_does_not_mutate_speech_or_approval():
    edit = Edit(clips=[Clip(start=0, end=20, approved=True, locked=True)])
    before = edit.model_dump()
    assert diagnose(edit)['longest_visual_run_seconds'] == 20
    assert edit.model_dump() == before


def test_motion_is_conservatively_separate_and_ineffective_pan_is_not():
    d = diagnose(Edit(clips=[Clip(start=0,end=3,x=.1),Clip(start=3,end=6,x=.9)]))
    assert d['visual_run_count'] == 1
    d = diagnose(Edit(clips=[Clip(start=0,end=3,zoom_end=1.2),Clip(start=3,end=6,zoom=1.2,zoom_end=1.4)]))
    assert d['visual_run_count'] == 2


def test_existing_source_scene_changes_are_not_mistaken_for_fake_cuts():
    scenes = [{'start':0,'end':6},{'start':6,'end':12}]
    d = diagnose(Edit(clips=[Clip(start=0,end=6),Clip(start=6,end=12)]), scenes=scenes)
    assert d['visual_run_count'] == 2
    assert d['artificial_boundaries'] == []
    d = diagnose(Edit(clips=[Clip(start=0,end=12)]), scenes=scenes)
    assert d['longest_visual_run_seconds'] == 6
