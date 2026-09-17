"""Explicit local-only UI fixture. Never included in the production database."""
import json
import shutil
import time
import uuid
from pathlib import Path
from backend.config import settings
from backend.db import connect
from backend.media import probe,prepare
from backend.schemas import Analysis
from backend.tests.test_render import recommendation,T

def main():
    pid=uuid.uuid4().hex; rid=uuid.uuid4().hex
    folder=settings.data_dir/pid; folder.mkdir()
    source=Path('/private/tmp/lumen-render-qa/source.mp4')
    shutil.copy(source,folder/'source');prepare(folder/'source',folder)
    metadata=probe(source);metadata['preview_ready']=True
    recs=[recommendation('cut','remove',0,1),recommendation('hook','move_to_front',5,8),recommendation('subtitles','captions',0,8)]
    recs[0].category='pacing';recs[1].category='hook';recs[2].category='captions'
    recs[0].title={'en':'Remove the first second of the red test scene','zh':'删除红色测试场景的第一秒'}
    recs[1].title={'en':'Move the blue test scene to the opening','zh':'将蓝色测试场景移到开头'}
    recs[2].title={'en':'Add the test subtitles','zh':'添加测试字幕'}
    a=Analysis(summary=T,strongest_moment=T,audience=T,scores=[{'category':'hook','value':50,'reason':T}],
       scenes=[{'start':0,'end':2,'title':{'en':'Red test scene','zh':'红色测试场景'},'observation':T,'role':'context'},
               {'start':2,'end':5,'title':{'en':'Green test scene','zh':'绿色测试场景'},'observation':T,'role':'product'},
               {'start':5,'end':8,'title':{'en':'Blue test scene','zh':'蓝色测试场景'},'observation':T,'role':'hook'}],
       transcript=[{'start':1,'end':2,'original':'TEST ONLY','en':'Test captions','zh':'测试中文字幕'},
                   {'start':5,'end':7,'original':'TEST ONLY','en':'Opening scene','zh':'开场画面'}],recommendations=recs,uncertainties=[T])
    export=folder/'renders'/rid;export.mkdir(parents=True);shutil.copy('/private/tmp/lumen-render-qa/result.mp4',export/'result.mp4')
    result={'render_id':rid,'metadata':probe(export/'result.mp4'),'timeline':[[5,8],[1,5]],'applied':['cut','hook','subtitles'],
            'generated_clips':0,'qa_status':'unavailable','qa':None}
    with connect() as db:
        user=db.execute("SELECT id FROM users WHERE email='qa@lumen.test'").fetchone()[0]
        db.execute('INSERT INTO projects(id,user_id,title,brief,language,aspect,auto_render,generative,budget,status,stage,progress,metadata,analysis,result,created,updated) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
          (pid,user,'QA fixture — colour timeline (not AI analysis)','Synthetic fixture for interaction tests; no AI-generated claims.','zh','original',0,0,3,'needs_review','needs_review',100,json.dumps(metadata),a.model_dump_json(),json.dumps(result),time.time(),time.time()))
    print('Local test fixture ready:',pid)

if __name__=='__main__':main()
