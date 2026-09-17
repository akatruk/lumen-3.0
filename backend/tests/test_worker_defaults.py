from backend import worker
from backend.schemas import Analysis

def test_persisted_defaults_match_verified_auto_render(tmp_path,monkeypatch):
    monkeypatch.setattr(worker.settings,'data_dir',tmp_path)
    folder=tmp_path/'p';folder.mkdir();(folder/'source').touch()
    text={'en':'Test','zh':'测试'}
    rec=lambda id,start,end:dict(id=id,start=start,end=end,title=text,evidence=text,improvement=text,category='pacing',confidence=.99,auto_apply=True,action='remove',generation_prompt='')
    analysis=Analysis(summary=text,strongest_moment=text,audience=text,scores=[dict(category='pacing',value=50,reason=text)],scenes=[dict(start=0,end=10,title=text,observation=text,role='context')],transcript=[dict(start=4,end=5,original='speech',en='speech',zh='说话')],recommendations=[rec('safe',1,2),rec('speech',4,5),rec('not_silent',7,8)],uncertainties=[])
    monkeypatch.setattr(worker.media,'probe',lambda _:dict(duration=10,has_audio=True))
    monkeypatch.setattr(worker.media,'prepare',lambda *args:None)
    monkeypatch.setattr(worker.media,'silence_ranges',lambda *args:[dict(start=1,end=2),dict(start=4,end=5)])
    monkeypatch.setattr(worker.ai,'analyze',lambda *args:analysis)
    updates=[]
    monkeypatch.setattr(worker,'update',lambda pid,**fields:updates.append(fields))
    monkeypatch.setattr(worker,'event',lambda *args:None)
    worker.analyze_job(dict(id='p',brief='',language='zh',generative=False,auto_render=False))
    saved=next(u['analysis'] for u in updates if 'analysis' in u)
    assert [r['id'] for r in saved['recommendations'] if r['auto_apply']]==['safe']
