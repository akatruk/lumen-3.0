"""Generate an illustrative asset and propose insertion without applying the edit."""
import json,time,uuid,shutil
from .config import settings
from .db import connect
from . import ai,media
from .schemas import Recommendation,Text
from .manual import Clip,ExternalBroll

def propose(p,row,snapshot):
    from .timeline_proposals import Proposal
    clip=Clip.model_validate(next(c for c in snapshot['edit']['clips'] if c['id']==row['target']))
    folder=settings.data_dir/p['id']/'generated'/row['id'];folder.mkdir(parents=True,exist_ok=True)
    speech=[c for c in snapshot.get('transcript',[]) if c['start']<clip.end and c['end']>clip.start]
    prompt='Create illustrative B-roll supporting this script segment. Keep the source visual style. Do not fabricate documents, news evidence, statistics, readable text, or claims that synthetic locations/properties are real. No speaking presenter; no audio. Editor direction: '+row['instruction'][:450]+'\nSegment context: '+json.dumps(speech,ensure_ascii=False)[:450]
    rec=Recommendation(id='insert',start=clip.start,end=min(clip.end,clip.start+4),title=Text(en='Illustrative B-roll',zh='示意补充镜头'),evidence=Text(en='Editor request',zh='编辑请求'),improvement=Text(en='Visual support',zh='视觉辅助'),category='broll',confidence=1,auto_apply=False,action='generate_broll',generation_prompt=prompt[:1200])
    generated=ai.generate_broll(p['id'],folder,settings.data_dir/p['id']/'source',rec,'9:16' if p['metadata']['height']>p['metadata']['width'] else '16:9')
    metadata=media.probe(generated['path']);metadata.update(kind='video',mime='video/mp4',generated=True,model=settings.generation_model)
    with connect() as db:
        db.lock()
        existing=db.execute('SELECT id FROM studio_assets WHERE project_id=? AND request_id=?',(p['id'],row['id'])).fetchone()
        ident=existing['id'] if existing else uuid.uuid4().hex
        if not existing:
            target=settings.data_dir/p['id']/'assets'/ident;target.parent.mkdir(exist_ok=True)
            shutil.copyfile(generated['path'],target)
            db.execute('INSERT INTO studio_assets VALUES(?,?,?,?,?,?,?)',(ident,p['id'],row['id'],'AI illustrative B-roll','AI-generated illustration; verify before use',json.dumps(metadata),time.time()))
        snapshot['candidates']=[{'id':ident,'samples':[{'start':0,'end':metadata['duration']}]}]
        db.execute('UPDATE timeline_proposals SET snapshot=? WHERE id=?',(json.dumps(snapshot,ensure_ascii=False),row['id']))
    clip.cutaway=None;clip.external_broll=ExternalBroll(asset_id=ident,start=0,end=min(4,clip.end-clip.start,metadata['duration']),source_start=0)
    return Proposal(clip=clip,reason=Text(en='Generated illustration for this segment. Check factual fit and visual quality before replacing the clip. Original audio is retained.',zh='为此片段生成的示意画面。替换前请检查内容匹配与画质，保留原有声音。'))
