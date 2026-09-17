from backend.timeline import compile_timeline
from backend.manual import Edit,Clip
from backend.sound_effects import SoundEffect
from backend.music import Music

def test_effect_endpoints_follow_output_order_and_skip_unapproved():
    edit=Edit(clips=[Clip(start=8,end=10,approved=True),Clip(start=0,end=3,approved=False),Clip(start=4,end=8,approved=True,sound_effects=[SoundEffect(kind='click',at=1),SoundEffect(kind='whoosh',at=2)])],music=Music(asset_id='a'*32,loop_fade_ms=30))
    tracks=compile_timeline(edit)['tracks']
    assert [(e['at'],e['end'],e['duration']) for e in tracks['sound_effects']]==[(3,3.08,.08),(4,4.4,.4)]
    assert tracks['music'][0]['loop_fade_ms']==30 and tracks['music'][0]['end']==6
