"""Attach live job / locale fields to project GET for Studio status UI."""
from __future__ import annotations

import json


def _payload(raw):
    if isinstance(raw, dict):
        return raw
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return {}


def attach_job_status(project: dict) -> dict:
    """Add latest_job, active_job, video_language without mutating source media."""
    from .db import connect

    pid = project.get('id')
    latest = None
    active = None
    try:
        if not pid:
            raise ValueError('no project id')
        with connect() as db:
            row = db.execute(
                "SELECT id, kind, status, created, updated, payload FROM jobs "
                "WHERE project_id=? ORDER BY updated DESC LIMIT 1",
                (pid,),
            ).fetchone()
            if row:
                data = dict(row)
                payload = _payload(data.get('payload'))
                latest = {
                    'id': data['id'],
                    'kind': data['kind'],
                    'status': data['status'],
                    'created': data['created'],
                    'updated': data['updated'],
                    'language': payload.get('target_language') or payload.get('language'),
                    'duration_seconds': payload.get('duration_seconds'),
                    'composition': payload.get('composition'),
                    'picture_engine': payload.get('picture_engine'),
                }
            busy = db.execute(
                "SELECT id, kind, status, updated, payload FROM jobs "
                "WHERE project_id=? AND kind!='transcribe' AND status IN ('queued','running') "
                "ORDER BY updated DESC LIMIT 1",
                (pid,),
            ).fetchone()
            if busy:
                data = dict(busy)
                payload = _payload(data.get('payload'))
                active = {
                    'id': data['id'],
                    'kind': data['kind'],
                    'status': data['status'],
                    'updated': data['updated'],
                    'language': payload.get('target_language') or payload.get('language'),
                }
    except Exception:
        latest = None
        active = None
    video_language = None
    try:
        from .studio import state
        context = (state(pid) or {}).get('context') or {}
        video_language = context.get('video_language')
    except Exception:
        video_language = None
    if not video_language and project.get('language'):
        code = str(project['language'])
        video_language = {
            'ru': 'ru-RU', 'en': 'en-US', 'zh': 'zh-CN',
            'ru-RU': 'ru-RU', 'en-US': 'en-US', 'zh-CN': 'zh-CN',
        }.get(code, code)
    project['latest_job'] = latest
    project['active_job'] = active
    project['video_language'] = video_language
    return project
