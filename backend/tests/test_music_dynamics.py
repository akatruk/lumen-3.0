import math
from backend.music_dynamics import describe,sample_ranges

def test_track_dynamics_identify_rise_drop_and_quiet_without_claiming_emotion():
    rate=100
    samples=[level*math.sin(2*math.pi*10*i/rate) for level in [0,.03,.3,.03] for i in range(rate*2)]
    result=describe(samples,rate)
    assert result['quiet_ranges']==[{'start':0.,'end':2.}]
    assert {c['kind'] for c in result['changes']}=={'rise','drop'}
    assert len(result['sections'])==4
    assert all(math.isfinite(s['db']) for s in result['sections'])

def test_adaptive_samples_are_bounded_and_cover_dynamic_region():
    result={'sections':[{'start':20,'db':-5},{'start':12,'db':-60}], 'changes':[{'at':22,'kind':'drop','delta_db':-20}]}
    spans=sample_ranges(40,result)
    assert len(spans)<=6
    assert all(0<=s['start']<s['end']<=40 for s in spans)
    assert any(s['start']<=22<s['end'] for s in spans)
    assert sample_ranges(1,result)==[{'start':0.,'end':1}]


def test_real_decode_and_sampling(tmp_path):
    from backend.media import ffmpeg
    from backend.music_dynamics import analyze
    path=tmp_path/'dynamics.wav'
    ffmpeg('-f','lavfi','-i','sine=frequency=220:duration=8','-af',"volume='if(lt(t,4),0.01,1)':eval=frame",path)
    measured=analyze(path)
    assert len(measured['sections'])==4
    assert measured['sections'][2]['db']>measured['sections'][0]['db']+30
    assert any(c['kind']=='rise' for c in measured['changes'])
