"""Editable property-sales plan. Facts are staff-supplied; the picture is owned footage.

Hypit, when installed, only captures the programme in ``hypit_package``. This
module does not invent price, area, tenure, or a city.
"""
import hashlib
import json
import re
import shutil
import uuid
from typing import Literal

from pydantic import Field

from .config import settings
from .db import connect, project, update
from .schemas import Strict

FactKey = Literal[
    'price', 'currency', 'floor_area', 'floor_area_unit', 'bedrooms', 'bathrooms',
    'floor', 'tenure', 'fees', 'availability', 'developer', 'amenities',
]
Destination = Literal['douyin', 'instagram_reels', 'youtube_shorts', 'tiktok', 'xiaohongshu']
_NUMBER = re.compile(r'\d+(?:[.,]\d+)?')
LABELS = {
    'en': {
        'price': 'Price', 'currency': 'Currency', 'floor_area': 'Floor area', 'floor_area_unit': 'Area unit',
        'bedrooms': 'Bedrooms', 'bathrooms': 'Bathrooms', 'floor': 'Floor', 'tenure': 'Tenure', 'fees': 'Fees',
        'availability': 'Availability', 'developer': 'Developer', 'amenities': 'Amenities',
    },
    'zh': {
        'price': '价格', 'currency': '币种', 'floor_area': '建筑面积', 'floor_area_unit': '面积单位',
        'bedrooms': '卧室', 'bathrooms': '卫生间', 'floor': '楼层', 'tenure': '产权', 'fees': '费用',
        'availability': '状态', 'developer': '开发商', 'amenities': '配套',
    },
    'ru': {
        'price': 'Цена', 'currency': 'Валюта', 'floor_area': 'Площадь', 'floor_area_unit': 'Единица площади',
        'bedrooms': 'Спальни', 'bathrooms': 'Санузлы', 'floor': 'Этаж', 'tenure': 'Право', 'fees': 'Платежи',
        'availability': 'Наличие', 'developer': 'Застройщик', 'amenities': 'Инфраструктура',
    },
}


class Fact(Strict):
    key: FactKey
    value: str = Field(min_length=1, max_length=200)
    source: str = Field(min_length=1, max_length=300)
    status: Literal['supplied', 'verified']


class Location(Strict):
    label: str = Field(min_length=1, max_length=160)
    show: bool = False


class CallToAction(Strict):
    text: str = Field(min_length=1, max_length=180)
    contact: str = Field(min_length=1, max_length=180)


class PropertyBrief(Strict):
    audience: str = Field(min_length=1, max_length=300)
    language: Literal['en', 'zh', 'ru'] = 'en'
    facts: list[Fact] = Field(default_factory=list, max_length=12)
    highlights: list[FactKey] = Field(default_factory=list, max_length=8)
    location: Location | None = None
    hook: str = Field(min_length=1, max_length=180)
    brand: str = Field(default='', max_length=80)
    cta: CallToAction
    destinations: list[Destination] = Field(min_length=1, max_length=5)
    music_asset_id: str = Field(default='', max_length=32)
    logo_asset_id: str = Field(default='', max_length=32)
    photo_asset_ids: list[str] = Field(default_factory=list, max_length=1)
    illustrative_asset_ids: list[str] = Field(default_factory=list, max_length=4)

    def prepared(self):
        if len(self.highlights) != len(set(self.highlights)):
            raise ValueError('unverified_claim')
        if len(self.destinations) != len(set(self.destinations)):
            raise ValueError('invalid_settings')
        known = {fact.key for fact in self.facts}
        if len(known) != len(self.facts) or any(key not in known for key in self.highlights):
            raise ValueError('unverified_claim')
        ids = [self.music_asset_id, self.logo_asset_id, *self.photo_asset_ids, *self.illustrative_asset_ids]
        if any(ident and not re.fullmatch(r'[a-f0-9]{32}', ident) for ident in ids):
            raise ValueError('asset_not_found')
        chosen = [ident for ident in ids if ident]
        if len(chosen) != len(set(chosen)):
            raise ValueError('invalid_settings')
        _grounded(self.hook, _allowed_numbers(self))
        _grounded(self.cta.text, _allowed_numbers(self))
        _grounded(self.cta.contact, _allowed_numbers(self))
        if self.location and self.location.show:
            _grounded(self.location.label, _allowed_numbers(self))
        return self


class SceneEdit(Strict):
    id: str = Field(pattern=r'^[a-z0-9_-]{1,32}$')
    caption: str = Field(min_length=1, max_length=180)


class PlanEdit(Strict):
    revision: int = Field(ge=1)
    scenes: list[SceneEdit] = Field(min_length=2, max_length=12)


class PlanApproval(Strict):
    revision: int = Field(ge=1)


class RenderRequest(Strict):
    revision: int = Field(ge=1)
    request_id: str = Field(pattern=r'^[a-f0-9]{32}$')


class DeliveryApproval(Strict):
    render_id: str = Field(pattern=r'^[a-f0-9]{32}$')


def _allowed_numbers(brief: PropertyBrief):
    """Numbers the picture may show. The hook and the call-to-action line are not sources."""
    chunks = [brief.cta.contact, brief.brand]
    chunks.extend(fact.value for fact in brief.facts)
    if brief.location and brief.location.show:
        chunks.append(brief.location.label)
    found = set()
    for chunk in chunks:
        found.update(_NUMBER.findall(chunk))
    return found


def _grounded(text, allowed):
    extra = set(_NUMBER.findall(text)) - set(allowed)
    if extra:
        raise ValueError('unverified_claim')


def _slice(pid, db):
    row = db.execute('SELECT context FROM studio_projects WHERE project_id=?', (pid,)).fetchone()
    if not row:
        return None, None
    context = json.loads(row['context'])
    return context, context.get('property')


def load(pid):
    with connect() as db:
        _context, prop = _slice(pid, db)
    return prop


def _save(db, pid, context):
    db.execute('UPDATE studio_projects SET context=? WHERE project_id=?', (json.dumps(context, ensure_ascii=False), pid))


def _asset_meta(db, pid, ident):
    row = db.execute('SELECT metadata FROM studio_assets WHERE id=? AND project_id=?', (ident, pid)).fetchone()
    if not row:
        raise ValueError('asset_not_found')
    return json.loads(row['metadata'])


def _check_media(db, pid, brief: PropertyBrief):
    """Music, a logo, and a photo must be the owned file of that role. An illustration stays out."""
    if brief.music_asset_id and _asset_meta(db, pid, brief.music_asset_id).get('kind') != 'music':
        raise ValueError('invalid_media_path')
    if brief.logo_asset_id:
        meta = _asset_meta(db, pid, brief.logo_asset_id)
        if meta.get('kind') != 'image' or meta.get('role') != 'logo':
            raise ValueError('invalid_media_path')
    for ident in brief.photo_asset_ids:
        meta = _asset_meta(db, pid, ident)
        if meta.get('kind') != 'image' or meta.get('role') != 'photo':
            raise ValueError('invalid_media_path')
    for ident in brief.illustrative_asset_ids:
        meta = _asset_meta(db, pid, ident)
        if meta.get('kind') == 'music' or meta.get('role') in ('logo', 'photo'):
            raise ValueError('invalid_media_path')


def save_brief(pid, brief: PropertyBrief):
    brief = brief.prepared()
    with connect() as db:
        db.lock()
        context, prop = _slice(pid, db)
        if context is None:
            raise ValueError('not_found')
        if (context.get('creator') or {}).get('topic') != 'real_estate':
            raise ValueError('property_workflow')
        _check_media(db, pid, brief)
        previous = (prop or {}).get('brief')
        dumped = brief.model_dump()
        prop = prop or {}
        prop['brief'] = dumped
        if previous != dumped:
            prop.pop('plan', None)
            prop['plan_revision'] = 0
            prop['approved_revision'] = None
        context['property'] = prop
        _save(db, pid, context)
    return prop


def _layout(duration, highlight_count):
    if duration < 4:
        raise ValueError('property_too_short')
    hook = min(6.0, max(1.5, duration * 0.22))
    closing = min(6.0, max(1.5, duration * 0.18))
    if hook + closing >= duration - 0.4:
        hook = round(duration * 0.34, 3)
        closing = round(duration * 0.28, 3)
    body_start = round(hook, 3)
    body_end = round(duration - closing, 3)
    if body_end <= body_start + 0.2:
        raise ValueError('property_too_short')
    slots = []
    if highlight_count:
        span = (body_end - body_start) / highlight_count
        for index in range(highlight_count):
            start = round(body_start + span * index, 3)
            end = round(body_end if index == highlight_count - 1 else body_start + span * (index + 1), 3)
            slots.append((start, end))
    return round(hook, 3), slots, round(duration - closing, 3), round(duration, 3)


def build_plan(pid):
    p = project(pid)
    if not p or not p.get('metadata'):
        raise ValueError('not_found')
    with connect() as db:
        db.lock()
        context, prop = _slice(pid, db)
        if not prop or not prop.get('brief'):
            raise ValueError('property_not_approved')
        brief = PropertyBrief.model_validate(prop['brief']).prepared()
        duration = float(p['metadata']['duration'])
        hook_end, slots, cta_start, end = _layout(duration, len(brief.highlights))
        labels = LABELS[brief.language]
        facts = {fact.key: fact for fact in brief.facts}
        scenes = [{
            'id': 'hook', 'role': 'hook', 'start': 0, 'end': hook_end, 'caption': brief.hook,
            'fact_keys': [], 'source': 'owned_footage',
        }]
        if brief.location and brief.location.show:
            scenes[0]['location'] = brief.location.label
        for index, key in enumerate(brief.highlights):
            fact = facts[key]
            start, stop = slots[index]
            scenes.append({
                'id': f'fact_{key}', 'role': 'highlight', 'start': start, 'end': stop,
                'caption': f'{labels[key]}: {fact.value}', 'fact_keys': [key],
                'source': 'owned_footage', 'fact_status': fact.status, 'fact_source': fact.source,
            })
        scenes.append({
            'id': 'cta', 'role': 'cta', 'start': cta_start, 'end': end,
            'caption': f'{brief.cta.text} {brief.cta.contact}'.strip(),
            'fact_keys': [], 'source': 'owned_footage',
        })
        plan = {
            'schema': 'lumen.property.plan.v1',
            'language': brief.language,
            'audience': brief.audience,
            'brand': brief.brand,
            'show_location': bool(brief.location and brief.location.show),
            'scenes': scenes,
            'illustrative_asset_ids': list(brief.illustrative_asset_ids),
            'illustrative_in_picture': False,
            'logo_asset_id': brief.logo_asset_id,
            'photo_asset_ids': list(brief.photo_asset_ids),
            'reference_media': 'technique_only' if context.get('reference_file') or context.get('references') else 'none',
            'destinations': list(brief.destinations),
            'music_asset_id': brief.music_asset_id,
            'duration': end,
        }
        for scene in scenes:
            _grounded(scene['caption'], _allowed_numbers(brief))
            if scene['role'] == 'highlight' and facts[scene['fact_keys'][0]].value not in scene['caption']:
                raise ValueError('unverified_claim')
        revision = int(prop.get('plan_revision') or 0) + 1
        prop['plan'] = plan
        prop['plan_revision'] = revision
        prop['approved_revision'] = None
        context['property'] = prop
        _save(db, pid, context)
    return prop


def edit_plan(pid, body: PlanEdit):
    with connect() as db:
        db.lock()
        context, prop = _slice(pid, db)
        if not prop or not prop.get('plan') or int(prop.get('plan_revision') or 0) != body.revision:
            raise ValueError('property_plan_changed')
        brief = PropertyBrief.model_validate(prop['brief']).prepared()
        plan = prop['plan']
        current = {scene['id']: scene for scene in plan['scenes']}
        incoming = [scene.id for scene in body.scenes]
        if incoming[0] != 'hook' or incoming[-1] != 'cta' or set(incoming) != set(current) or len(incoming) != len(current):
            raise ValueError('property_plan_changed')
        facts = {fact.key: fact for fact in brief.facts}
        allowed = _allowed_numbers(brief)
        ordered = []
        for item in body.scenes:
            scene = dict(current[item.id])
            scene['caption'] = item.caption.strip()
            _grounded(scene['caption'], allowed)
            if scene['role'] == 'highlight' and facts[scene['fact_keys'][0]].value not in scene['caption']:
                raise ValueError('unverified_claim')
            ordered.append(scene)
        middles = [scene for scene in ordered if scene['role'] == 'highlight']
        if middles:
            start = ordered[0]['end']
            stop = ordered[-1]['start']
            span = (stop - start) / len(middles)
            for index, scene in enumerate(middles):
                scene['start'] = round(start + span * index, 3)
                scene['end'] = round(stop if index == len(middles) - 1 else start + span * (index + 1), 3)
        plan['scenes'] = ordered
        prop['plan'] = plan
        prop['plan_revision'] = body.revision + 1
        prop['approved_revision'] = None
        context['property'] = prop
        _save(db, pid, context)
    return prop


def approve_plan(pid, revision):
    with connect() as db:
        db.lock()
        context, prop = _slice(pid, db)
        if not prop or not prop.get('plan') or int(prop.get('plan_revision') or 0) != revision:
            raise ValueError('property_plan_changed')
        prop['approved_revision'] = revision
        context['property'] = prop
        _save(db, pid, context)
    return prop


def queue_render(db, pid, body: RenderRequest):
    context, prop = _slice(pid, db)
    if not prop or int(prop.get('approved_revision') or 0) != body.revision or int(prop.get('plan_revision') or 0) != body.revision:
        raise ValueError('property_not_approved')
    if db.execute("SELECT 1 FROM jobs WHERE project_id=? AND status IN ('queued','running')", (pid,)).fetchone():
        raise ValueError('job_already_running')
    for row in db.execute("SELECT payload,status FROM jobs WHERE project_id=? AND kind='property_render'", (pid,)):
        payload = json.loads(row['payload'])
        if payload.get('request_id') != body.request_id or row['status'] not in ('queued', 'running', 'complete'):
            continue
        folder = settings.data_dir / pid / 'renders' / payload['render_id'] / 'result.mp4'
        if row['status'] != 'complete' or folder.is_file():
            return {'ok': True, 'render_id': payload['render_id'], 'duplicate': True}
    render_id = uuid.uuid4().hex
    from .db import enqueue
    enqueue(db, pid, 'property_render', {'revision': body.revision, 'request_id': body.request_id, 'render_id': render_id})
    return {'ok': True, 'render_id': render_id, 'duplicate': False}


def render_job(p, payload):
    """Capture one new file. The selected delivery stays until staff approve it."""
    pid = p['id']
    render_id = payload['render_id']
    if not re.fullmatch(r'[a-f0-9]{32}', render_id):
        raise ValueError('invalid_media_path')
    folder = settings.data_dir / pid / 'renders' / render_id
    result_path = folder / 'result.mp4'
    with connect() as db:
        context, prop = _slice(pid, db)
    if not prop or int(prop.get('approved_revision') or 0) != payload['revision']:
        raise ValueError('property_not_approved')
    if result_path.is_file() and result_path.stat().st_size > 32:
        _mark_pending(pid, render_id, payload['revision'])
        return
    folder.mkdir(parents=True, exist_ok=True)
    try:
        from .hypit_package import render_package
        manifest = render_package(p, prop, folder)
    except Exception:
        shutil.rmtree(folder, ignore_errors=True)
        raise
    _mark_pending(pid, render_id, payload['revision'], manifest)


def _mark_pending(pid, render_id, revision, manifest=None):
    with connect() as db:
        db.lock()
        context, prop = _slice(pid, db)
        if not prop:
            raise ValueError('property_not_approved')
        prop['pending_render_id'] = render_id
        prop['pending_revision'] = revision
        if manifest:
            prop['pending_package_id'] = manifest['package_id']
            prop['pending_cost'] = manifest['cost']
        context['property'] = prop
        _save(db, pid, context)
    update(pid, status='ready', stage='property_pending', progress=100, error=None)


def approve_delivery(pid, render_id):
    path = settings.data_dir / pid / 'renders' / render_id / 'result.mp4'
    manifest_path = settings.data_dir / pid / 'renders' / render_id / 'manifest.json'
    if not path.is_file() or not manifest_path.is_file():
        raise ValueError('property_delivery_missing')
    manifest = json.loads(manifest_path.read_text())
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != manifest.get('sha256'):
        raise ValueError('property_delivery_missing')
    with connect() as db:
        db.lock()
        context, prop = _slice(pid, db)
        if not prop or prop.get('pending_render_id') != render_id:
            raise ValueError('property_delivery_missing')
        prop['selected_render_id'] = render_id
        context['property'] = prop
        _save(db, pid, context)
    previous = project(pid).get('result') or {}
    # Match the result fields the existing project screen reads. This cut has
    # no AI quality review; the staff approval is the property delivery itself.
    selected = {
        'render_id': render_id,
        'applied': ['property_plan'],
        'generated_clips': 0,
        'timeline': [[0, manifest['duration']]],
        'metadata': {
            'duration': manifest['duration'],
            'width': manifest['width'],
            'height': manifest['height'],
            'has_audio': bool(manifest['has_audio']),
            'size': path.stat().st_size,
        },
        'qa': None,
        'qa_status': 'unavailable',
        'property_package': manifest['package_id'],
        'duration': manifest['duration'],
        'sha256': digest,
        'plan_revision': prop['pending_revision'],
        'previous_render_id': previous.get('render_id') or '',
    }
    update(pid, result=selected, status='complete', stage='complete', progress=100, error=None)
    return selected
