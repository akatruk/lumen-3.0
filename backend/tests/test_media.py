from types import SimpleNamespace
import pytest
from backend.media import build_timeline,remap_span,subtitle_text,ass_time

def rec(action,start,end): return SimpleNamespace(action=action,start=start,end=end)

def test_removal_union_and_hook_order():
    timeline=build_timeline(20,[rec('remove',0,2),rec('remove',1,3),rec('move_to_front',10,13)])
    assert timeline==[(10,13),(3,10),(13,20)]
    assert sum(b-a for a,b in timeline)==17
    assert remap_span(10,12,timeline)==[(0,2)]
    assert remap_span(8,11,timeline)==[(0,1),(8,10)]

def test_hook_conflict_is_rejected():
    with pytest.raises(ValueError,match='hook_overlaps_cut'):
        build_timeline(20,[rec('remove',4,10),rec('move_to_front',8,12)])

def test_reject_destructive_plan():
    with pytest.raises(ValueError,match='too_much_removed'):
        build_timeline(20,[rec('remove',0,19.5)])

def test_split_caption_across_cut():
    assert remap_span(1,8,[(0,3),(6,10)])==[(1,3),(3,5)]

def test_subtitle_injection_and_time_rounding():
    cleaned=subtitle_text(r'{\pos(0,0)}Hello\Nworld','en')
    assert '{' not in cleaned and '}' not in cleaned and '\\pos' not in cleaned
    assert ass_time(59.999)=='0:01:00.00'
    assert subtitle_text('测试中文字幕不应超过每一行的安全长度而且不能溢出边缘','zh').count('\\N')>=1

@pytest.mark.parametrize('duration',[float('nan'),float('inf')])
def test_pydantic_rejects_nonfinite_span(duration):
    from backend.schemas import Span
    with pytest.raises(ValueError): Span(start=duration,end=duration)

def test_caption_cards_do_not_orphan_a_word():
    from backend.media import caption_chunks
    cards=caption_chunks('Next, the green panel gives the viewer a moment to follow the story.','en')
    assert all(len(c.replace('\\N',' ').split())>=2 for c in cards)
    assert all(len(c.split('\\N'))<=2 for c in cards)
    assert ' '.join(c.replace('\\N',' ') for c in cards)=='Next, the green panel gives the viewer a moment to follow the story.'

def test_caption_lines_are_balanced():
    from backend.media import subtitle_text
    lines=subtitle_text('viewer a moment to follow the story.','en').split('\\N')
    assert len(lines)==2
    assert all(len(line.split())>=2 for line in lines)
    assert abs(len(lines[0])-len(lines[1]))<=8

@pytest.mark.parametrize('text',[
    '这里需要提前检查自己的工作证和护照，确保所有证件有效。',
    '首先了解当地房地产市场，然后比较交通、学校和管理逻辑。',
    '旅行前核对2026年的签证要求，准备好工作证、护照和机票。',
])
def test_chinese_word_boundaries_and_text_preservation(text):
    from backend.media import caption_chunks
    cards=caption_chunks(text,'zh')
    lines=[line for card in cards for line in card.split('\\N')]
    assert ''.join(lines)==text
    assert all(len(line)<=16 for line in lines)
    assert all(not line.startswith(tuple('，。！？；：、）》】')) for line in lines)
    for term in ['工作证','房地产','管理','逻辑','护照','2026']:
        if term in text:assert any(term in line for line in lines)
    assert all(len(card.split('\\N'))<=2 for card in cards)


def test_chinese_long_caption_does_not_resplit_words_between_cards():
    from backend.media import caption_chunks
    text='这里需要提前检查自己的工作证和护照，确保所有证件有效。'*4
    cards=caption_chunks(text,'zh')
    assert len(cards)>1
    assert ''.join(cards).replace('\\N','')==text
    assert sum(card.count('工作证') for card in cards)==4
