from backend.edit_audit import audit_edit
from backend.manual import Clip, Edit


def test_splitting_and_relabeling_are_not_improvements():
    edit = Edit(clips=[Clip(start=0,end=5,shot_type='close_up'),Clip(start=5,end=10,x=.2,x_end=.8)])
    result = audit_edit(edit,10)
    assert not result['has_changes']
    assert result['removed_seconds'] == 0
    assert all(not c['operations'] for c in result['clips'])


def test_reorder_is_not_trim_and_overlap_does_not_hide_removed_footage():
    result = audit_edit(Edit(clips=[Clip(start=5,end=10),Clip(start=0,end=5)]),10)
    assert result['global_operations'] == ['reorder']
    result = audit_edit(Edit(clips=[Clip(start=0,end=6),Clip(start=4,end=8)]),10)
    assert result['removed_seconds'] == 2
    assert result['global_operations'] == ['trim']


def test_concrete_operations_are_reported_independently_of_ai_text():
    edit = Edit(clips=[Clip(start=0,end=10,zoom_end=1.2,text='Bangkok',transition='fade')],normalize=True)
    result = audit_edit(edit,10)
    assert result['clips'][0]['operations'] == ['motion','fade','title']
    assert result['global_operations'] == ['normalize']
    assert result['has_changes']
