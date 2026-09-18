import json,time
from pathlib import Path
from backend.tests.test_api import clients
from backend.tests.test_douyin import raw
from backend import douyin, douyin_preview as preview
from backend.db import connect
from backend.config import settings


def test_preview_is_owned_cached_and_does_not_import(clients,monkeypatch):
 a,b=clients;monkeypatch.setattr(douyin,'provider',lambda *args:{'data':[raw()]})
 rid=a.post('/api/douyin/search',json={'keyword':'coffee'}).json()['items'][0]['id'];url='/api/douyin/results/'+rid+'/preview'
 monkeypatch.setattr(douyin,'download',lambda u,p,n:Path(p).write_bytes(b'original'))
 monkeypatch.setattr(preview.media,'probe',lambda p:{'duration':21,'codec':'h264'})
 monkeypatch.setattr(preview.media,'ffmpeg',lambda *args,**kw:Path(args[-1]).write_bytes(b'playable'))
 assert b.post(url).status_code==404
 assert a.post(url).status_code==200
 assert a.get(url).content==b'playable'
 assert a.get(url,headers={'Range':'bytes=0-3'}).status_code==206
 monkeypatch.setattr(douyin,'download',lambda *args:(_ for _ in ()).throw(AssertionError('cached')))
 assert a.post(url).status_code==200
 assert b.get(url).status_code==404
 with connect() as db:
  assert db.execute('SELECT count(*) FROM projects').fetchone()[0]==0
  assert db.execute('SELECT count(*) FROM jobs').fetchone()[0]==0
  db.execute('UPDATE douyin_results SET created=? WHERE id=?',(time.time()-3700,rid))
 assert a.get(url).status_code==404
 a.post('/api/logout');assert a.post(url).status_code==401


def test_failure_keeps_no_partial_preview(clients,monkeypatch):
 a,_=clients;monkeypatch.setattr(douyin,'provider',lambda *args:{'data':[raw()]})
 rid=a.post('/api/douyin/search',json={'keyword':'coffee'}).json()['items'][0]['id']
 monkeypatch.setattr(douyin,'download',lambda u,p,n:Path(p).write_bytes(b'bad'))
 monkeypatch.setattr(preview.media,'probe',lambda p:(_ for _ in ()).throw(ValueError('bad')))
 assert a.post('/api/douyin/results/'+rid+'/preview').status_code==503
 assert not list(preview.folder(rid).iterdir())


def test_full_length_browser_compatible_preview(clients,monkeypatch,tmp_path):
 import shutil,pytest
 if not shutil.which('ffmpeg'):pytest.skip('FFmpeg required')
 a,_=clients
 source=tmp_path/'fixture.mp4'
 preview.media.ffmpeg('-f','lavfi','-i','color=blue:size=64x96:rate=10:duration=46.2','-f','lavfi','-i','sine=frequency=400:duration=46.2','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac',source)
 monkeypatch.setattr(douyin,'provider',lambda *args:{'data':[raw(duration=46200)]})
 monkeypatch.setattr(douyin,'download',lambda url,path,limit:shutil.copyfile(source,path))
 rid=a.post('/api/douyin/search',json={'keyword':'coffee'}).json()['items'][0]['id']
 assert a.post('/api/douyin/results/'+rid+'/preview').status_code==200
 meta=preview.media.probe(preview.folder(rid)/'preview.mp4')
 assert abs(meta['duration']-46.2)<.2 and meta['has_audio'] and meta['codec']=='h264'
