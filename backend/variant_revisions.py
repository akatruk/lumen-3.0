"""Immutable package revisions: manual edits, review/lock decisions, history."""
import json,time,uuid,shutil
from typing import Literal
from fastapi import Depends,HTTPException
from pydantic import Field
from .schemas import Strict,Span
from .auth import current_user
from .config import settings
from .db import connect,enqueue,project
from . import media
from .variants import router,owned,Variant,Plans,validate,PLATFORMS

class Base(Strict):
    package_id: str=Field(pattern=r'^[a-f0-9]{32}$')
    platform: Literal['douyin','instagram_reels','youtube_shorts','tiktok','xiaohongshu']
class Edit(Base):
    aspect: Literal['9:16','16:9','1:1','4:5']='9:16'
    cover_time: float=Field(default=1,ge=0,le=840)
    title: str=Field(min_length=1,max_length=80)
    description: str=Field(min_length=1,max_length=1600)
    hashtags: list[str]=Field(max_length=8)
    cta: str=Field(min_length=1,max_length=160)
    segments: list[Span]=Field(min_length=1,max_length=12)
class Review(Base):
    approved: bool
    locked: bool

def init(db):
    db.executescript('''CREATE TABLE IF NOT EXISTS platform_history(
    package_id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    master_id TEXT NOT NULL, result TEXT NOT NULL, created REAL NOT NULL);
    CREATE INDEX IF NOT EXISTS platform_history_project ON platform_history(project_id,created);''')
    db.execute("INSERT INTO platform_history SELECT package_id,project_id,master_id,result,? FROM platform_packages WHERE status='complete' AND result IS NOT NULL ON CONFLICT(package_id) DO NOTHING",(time.time(),))

def history_package(pid,package_id,db):
    row=db.execute('SELECT * FROM platform_history WHERE project_id=? AND package_id=?',(pid,package_id)).fetchone()
    if not row:raise HTTPException(404,'not_found')
    return dict(row)|{'status':'complete','result':json.loads(row['result'])}

@router.get('/projects/{pid}/variants/history')
def history(pid:str,user=Depends(current_user)):
    owned(pid,user)
    with connect() as db:return [dict(r) for r in db.execute('SELECT package_id,master_id,created FROM platform_history WHERE project_id=? ORDER BY created DESC',(pid,))]

@router.get('/projects/{pid}/variants/history/{package_id}')
def historic(pid:str,package_id:str,user=Depends(current_user)):
    p=owned(pid,user)
    with connect() as db:s=history_package(pid,package_id,db)
    s['stale']=s['master_id']!=(p['result'] or {}).get('render_id')
    return s

def locked_state(db,pid,body,user):
    db.lock();p=project(pid,user['id'])
    row=db.execute('SELECT * FROM platform_packages WHERE project_id=?',(pid,)).fetchone()
    if not row or row['status']!='complete' or row['package_id']!=body.package_id:raise HTTPException(409,'package_changed')
    if not p['result'] or row['master_id']!=p['result'].get('render_id'):raise HTTPException(409,'master_changed')
    if db.execute("SELECT 1 FROM jobs WHERE project_id=? AND status IN ('queued','running')",(pid,)).fetchone():raise HTTPException(409,'job_already_running')
    manifest=json.loads(row['result']);selected=next((v for v in manifest['variants'] if v['platform']==body.platform),None)
    if not selected:raise HTTPException(404,'not_found')
    return p,manifest,selected

def queue(db,pid,p,body,manifest,selected,action,user):
    if shutil.disk_usage(settings.data_dir).free<2*1024**3:raise HTTPException(507,'storage_full')
    package_id=uuid.uuid4().hex
    # Archive the current complete package before replacing the current pointer.
    db.execute('INSERT INTO platform_history VALUES(?,?,?,?,?) ON CONFLICT(package_id) DO NOTHING',(body.package_id,pid,p['result']['render_id'],json.dumps(manifest,ensure_ascii=False),time.time()))
    payload={'master':p['result'],'package_id':package_id,'base_package':body.package_id,'base_manifest':manifest,'changed_platform':body.platform if action=='edit' else None,'override':selected,'revision_action':action}
    db.execute("UPDATE platform_packages SET package_id=?,status='queued',result=NULL WHERE project_id=?",(package_id,pid))
    enqueue(db,pid,'platform_variants',payload)
    db.execute('INSERT INTO events(project_id,kind,detail,created) VALUES(?,?,?,?)',(pid,'variant_'+action,json.dumps({'platform':body.platform,'base_package':body.package_id,'package_id':package_id,'actor':user['id']}),time.time()))
    return {'ok':True,'package_id':package_id}

@router.post('/projects/{pid}/variants/edit')
def edit(pid:str,body:Edit,user=Depends(current_user)):
    owned(pid,user)
    with connect() as db:
        p,manifest,current=locked_state(db,pid,body,user)
        if current.get('locked'):raise HTTPException(409,'variant_locked')
        changed=current|body.model_dump(exclude={'package_id','platform'})|{'review_status':'needs_human_review','locked':False,'reviewed_at':None,'rationale':{'en':'Manually edited by the producer. Review the updated cut and copy.','zh':'由制作人手动编辑。请审核更新后的剪辑与文案。'}}
        plans=Plans(variants=[Variant.model_validate({k:v[k] for k in Variant.model_fields if k in v}) for v in [changed if v['platform']==body.platform else v for v in manifest['variants']]])
        master=p['result'];speech=[span for c in p['analysis']['transcript'] for span in media.remap_span(c['start'],c['end'],master['timeline'])]
        boundaries=sorted({0.0,master['metadata']['duration'],*(t for c in p['analysis']['scenes'] for span in media.remap_span(c['start'],c['end'],master['timeline']) for t in span)})
        try:validate(plans,master['metadata']['duration'],speech,p['language'],boundaries,tuple(v['platform'] for v in manifest['variants']))
        except ValueError:raise HTTPException(422,'invalid_variant_edit') from None
        return queue(db,pid,p,body,manifest,changed,'edit',user)

@router.post('/projects/{pid}/variants/review')
def review(pid:str,body:Review,user=Depends(current_user)):
    owned(pid,user)
    with connect() as db:
        p,manifest,current=locked_state(db,pid,body,user)
        approved=current.get('review_status')=='approved'
        if current.get('locked') and approved!=body.approved:raise HTTPException(409,'variant_locked')
        if body.locked and not body.approved:raise HTTPException(422,'lock_requires_approval')
        if approved==body.approved and bool(current.get('locked'))==body.locked:return {'ok':True,'package_id':body.package_id}
        selected=current|{'review_status':'approved' if body.approved else 'needs_human_review','locked':body.locked,'reviewed_at':time.time() if body.approved else None}
        return queue(db,pid,p,body,manifest,selected,'review',user)

class Restore(Strict):
    package_id: str=Field(pattern=r'^[a-f0-9]{32}$')

@router.post('/projects/{pid}/variants/restore')
def restore(pid:str,body:Restore,user=Depends(current_user)):
    owned(pid,user)
    with connect() as db:
        db.lock();p=project(pid,user['id']);s=history_package(pid,body.package_id,db)
        if not p['result'] or s['master_id']!=p['result'].get('render_id'):raise HTTPException(409,'master_changed')
        if db.execute("SELECT 1 FROM jobs WHERE project_id=? AND status IN ('queued','running')",(pid,)).fetchone():raise HTTPException(409,'job_already_running')
        db.execute("UPDATE platform_packages SET package_id=?,master_id=?,status='complete',result=? WHERE project_id=?",(s['package_id'],s['master_id'],json.dumps(s['result'],ensure_ascii=False),pid))
        db.execute('INSERT INTO events(project_id,kind,detail,created) VALUES(?,?,?,?)',(pid,'variant_restore',body.package_id,time.time()))
    return {'ok':True}
