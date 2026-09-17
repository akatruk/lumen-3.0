import math,uuid
from backend.rhythm import detect
from backend.tests.test_studio import client,create,seed_plan
from backend import media,rhythm

def test_regular_pulses_and_nonrhythmic_audio():
    rate=2000
    samples=[.8*math.sin(2*math.pi*100*i/rate) if .02<i/rate% .5<.10 else 0 for i in range(rate*8)]
    result=detect(samples)
    assert result['bpm']==120
    assert len(result['accents'])>=15
    assert detect([0]*rate)['bpm'] is None
    assert detect([.3]*rate)['accents']==[]

def test_real_audio_decode_detects_click_track(tmp_path):
    import wave,array
    path=tmp_path/'clicks.wav';rate=2000
    samples=array.array('h',[int(20000*math.sin(2*math.pi*100*i/rate)) if .02<i/rate% .5<.10 else 0 for i in range(rate*8)])
    with wave.open(str(path),'wb') as f:
        f.setnchannels(1);f.setsampwidth(2);f.setframerate(rate);f.writeframes(samples.tobytes())
    result=rhythm.analyze(path)
    assert result['bpm']==120
    assert len(result['accents'])>=15

def test_music_rhythm_is_cached_and_project_private(client,tmp_path,monkeypatch):
    track=tmp_path/'track.wav';media.ffmpeg('-f','lavfi','-i','sine=frequency=220:duration=2',track)
    data=track.read_bytes();pid=create(client).json()['id'];seed_plan(pid)
    ident=client.post('/api/studio/uploads',json={'size':len(data),'token':uuid.uuid4().hex}).json()['id']
    assert client.put(f'/api/studio/uploads/{ident}?offset=0',content=data).status_code==200
    body={'asset_project_id':pid,'request_id':uuid.uuid4().hex,'title':'Music','attribution':'Synthetic','owned_rights_confirmed':True,'kind':'music'}
    aid=client.post(f'/api/studio/uploads/{ident}/asset',json=body).json()['id']
    calls=[]
    def analyze(path):
        calls.append(path)
        return {'version':1,'accents':[.5,1,1.5],'bpm':None,'regularity':1}
    monkeypatch.setattr(rhythm,'analyze',analyze)
    url=f'/api/studio/projects/{pid}/assets/{aid}/rhythm'
    assert client.post(url).json()['accents']==[.5,1,1.5]
    assert client.post(url).status_code==200
    assert len(calls)==1
    assert client.get(f'/api/studio/projects/{pid}/assets').json()[0]['metadata']['rhythm']['version']==1
    other=create(client).json()['id']
    assert client.post(f'/api/studio/projects/{other}/assets/{aid}/rhythm').status_code==404
