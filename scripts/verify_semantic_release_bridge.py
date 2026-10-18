# coding: utf-8
"""Isolated release bridge: synthetic ASR/LLM fixtures, real HTTP/worker/Remotion.
Never run from production. Requires an empty DATABASE_URL and DATA_DIR under /tmp.
"""
import hashlib,json,os,shutil,sys,threading,time,uuid
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from backend.config import ROOT,settings
assert not settings.database_url and str(settings.data_dir).startswith('/tmp/lumen-release-'), 'isolated checkout required'
assert not (ROOT/'.env').exists(), 'production env prohibited'
from backend import ai,media,source_analysis,semantic_planner,director_v3
from backend.db import init_db,connect,project
from backend.app import app
from backend.worker import run_once
import uvicorn
bridge=ROOT/'acceptance';bridge.mkdir(exist_ok=True)
settings.semantic_planner_required=True
settings.remotion_engine_enabled=True
settings.openrouter_api_key='fixture-only-no-provider-call'
settings.google_sso_only=False
settings.secure_cookies=False
port=int(os.environ.get('RELEASE_PORT','8094'))
settings.public_origin=os.environ.get('RELEASE_ORIGIN',f'http://127.0.0.1:{port}')
settings.max_storage_gb=20
init_db()
rows=[{'id':'segment_001','start':0.,'end':10.,'text':'很多人以为境外投资很难。'},
      {'id':'segment_002','start':10.,'end':20.,'text':'第二个护照需要哪些文件？'},
      {'id':'segment_003','start':20.,'end':30.,'text':'审批通常需要六个月。'}]
def fixture_transcript(source,**kwargs):return rows,'release_fixture'
source_analysis._transcribe_source=fixture_transcript
fixture_calls=[]
def fixture_plan(pid,transcript,language,version=1):
    fixture_calls.append(pid)
    plan=semantic_planner.validate_semantic_plan({'planner':'release_fixture','topic':'passport fixture','language':language,'transcript_version':version,'passages':[
        {'segment_ids':['segment_001'],'intent':'statement','visual_treatment':'talking_head','quote':rows[0]['text']},
        {'segment_ids':['segment_002'],'intent':'question','visual_treatment':'supporting_broll','visual_concept':'护照','quote':rows[1]['text']},
        {'segment_ids':['segment_003'],'intent':'statement','visual_treatment':'kinetic_typography','visual_concept':'六个月','quote':rows[2]['text']},
    ]},{r['id'] for r in rows})
    path=semantic_planner.plan_path(pid);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(plan,ensure_ascii=False))
    return plan
semantic_planner.plan_semantics=fixture_plan
def no_external(*a,**kw):raise RuntimeError('external provider call prohibited in fixture acceptance')
ai.json_call=no_external
public=ROOT/'qa-public'/'director-v3';public.mkdir(parents=True,exist_ok=True)
for base in [Path('/mnt/volume_nyc1_1791446889637/lumen-motion/public/director-v3'),Path('/opt/lumen-rebuild/motion/public/director-v3')]:
    if (base/'bed.mp3').is_file():shutil.copy2(base/'bed.mp3',public/'bed.mp3');break
assert (public/'bed.mp3').is_file()
director_v3._public_director=lambda:public
media.ffmpeg('-f','lavfi','-i','testsrc2=s=180x320:d=30:r=30','-f','lavfi','-i','sine=frequency=110:duration=30','-c:v','libx264','-c:a','aac','-shortest','-y',bridge/'upload.mp4')
token=uuid.uuid4().hex
with connect() as db:
    db.execute('INSERT INTO users VALUES(?,?,?,?)',('qa','qa-release@example.invalid','disabled',time.time()))
    db.execute('INSERT INTO sessions(token,user_id,expires) VALUES(?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),'qa',time.time()+3600))
server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=port,log_level='warning'))
thread=threading.Thread(target=server.run,daemon=True);thread.start()
while not server.started:time.sleep(.1)
ready=bridge/'ready.json';ready.write_text(json.dumps({'token':token,'source':str(bridge/'upload.mp4')}));ready.chmod(0o600)
print('READY',flush=True)
try:
    deadline=time.monotonic()+1800
    while not (bridge/'done.json').exists() and time.monotonic()<deadline:
        if not run_once():time.sleep(.2)
    report=json.loads((bridge/'done.json').read_text());assert report.get('passed'),report
    p=project(report['pid']);assert p['result']['directorMode']=='semantic_openrouter'
    plan_dir=settings.data_dir/p['id']/'remotion-plans'
    latest=json.loads((plan_dir/'latest.json').read_text())
    plan=json.loads((plan_dir/(latest['generationId']+'.json')).read_text())
    assert plan['form']=='semantic',plan.get('form')
    scenes=plan['visualPlan']['scenes'] if 'visualPlan' in plan else plan['scenes']
    assert [(s['start'],s['end']) for s in scenes]==[(0.,10.),(10.,20.),(20.,30.)]
    final=settings.data_dir/p['id']/'renders'/p['result']['render_id']/'result.mp4'
    assert abs(media.probe(final)['duration']-30)<.15
    shutil.copy2(final,bridge/'verified-final.mp4')
    report.update({'fixture':'synthetic ASR and semantic plan; no live LLM/TTS call','fixture_calls':len(fixture_calls),'bounds':[[s['start'],s['end']] for s in scenes],'video_sha256':hashlib.sha256(final.read_bytes()).hexdigest()})
    (bridge/'verified.json').write_text(json.dumps(report,indent=2))
    print('PASS',flush=True)
finally:
    ready.unlink(missing_ok=True);server.should_exit=True;thread.join(timeout=10)
