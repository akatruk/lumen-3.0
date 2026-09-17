from backend.tests.test_studio import client,create
from backend import studio,douyin
from backend.tests.test_douyin import raw

def test_seven_minute_boundary_is_consistent(client,monkeypatch):
 monkeypatch.setattr(studio.media,'probe',lambda _:dict(duration=420,width=320,height=568,has_audio=False,size=16))
 assert create(client).status_code==201
 monkeypatch.setattr(studio.media,'probe',lambda _:dict(duration=420.1,width=320,height=568,has_audio=False,size=16))
 assert create(client).status_code==422
 assert len(douyin.parse_results({'data':[raw(duration=420000)]}))==1
 assert not douyin.parse_results({'data':[raw(duration=420001)]})

def test_long_proxy_keeps_entire_video_and_stays_bounded(tmp_path):
 from backend.media import ffmpeg,prepare,probe
 src=tmp_path/'source.mp4'
 ffmpeg('-f','lavfi','-i','testsrc2=s=160x284:r=12:d=420','-f','lavfi','-i','sine=frequency=440:duration=420','-c:v','libx264','-preset','ultrafast','-c:a','aac',src)
 prepare(src,tmp_path)
 proxy=tmp_path/'analysis.mp4';meta=probe(proxy)
 assert abs(meta['duration']-420)<.2 and meta['has_audio']
 assert proxy.stat().st_size<16*1024*1024
