from backend.platform_titles import write
from backend.variants import Variant

def variant(**changes):
    return Variant(platform='tiktok',title='Opening',description='Description',cta='Save this guide',hashtags=[],rationale={'en':'Test','zh':'测试'},segments=[{'start':0,'end':10}],**changes)

def test_hook_and_cta_have_separate_windows_and_style(tmp_path):
    path=tmp_path/'titles.ass'
    write(path,variant(hook_seconds=2,cta_seconds=3,title_style='panel',title_position='center'),'en',1080,1920,10)
    text=path.read_text()
    assert '0:00:02.00,Default,Opening' in text
    assert '0:00:07.00,0:00:10.00,Default,Save this guide' in text
    assert ',-1,3,3,1,5,' in text

def test_short_cut_does_not_stack_titles_and_off_is_empty(tmp_path):
    path=tmp_path/'titles.ass'
    write(path,variant(hook_seconds=3,cta_seconds=3),'en',1080,1920,2)
    assert path.read_text().count('Dialogue:')==1
    write(path,variant(hook_seconds=0,cta_seconds=0),'en',1080,1920,2)
    assert 'Dialogue:' not in path.read_text()


def test_cta_is_sanitized_before_ass_render(tmp_path):
    path=tmp_path/'titles.ass';v=variant(hook_seconds=0,cta_seconds=2)
    v.cta=r'{\pos(0,0)}Save'
    write(path,v,'en',1080,1920,10)
    assert '{' not in path.read_text() and '\\pos' not in path.read_text()
