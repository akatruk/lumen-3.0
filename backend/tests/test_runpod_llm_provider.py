"""RunPod LLM provider — fail-closed, fast-create untouched."""

from __future__ import annotations

import json
import time
import uuid

import pytest
from fastapi.testclient import TestClient

from backend.app import app, limits
from backend.auth import current_user
from backend.config import settings
from backend.db import connect
from backend import studio
from backend.runpod_llm import RUNPOD_LLM_UNAVAILABLE, RunpodLlmError
from backend.providers.llm import get_llm_provider, RunPodLLMProvider
from backend.providers.director import get_director_provider, RunPodDirectorProvider
from backend.source_analysis import ensure_analysis


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    monkeypatch.setattr(settings, "fast_project_creation_enabled", True)
    monkeypatch.setattr(settings, "llm_provider", "none")
    monkeypatch.setattr(settings, "openrouter_api_key", "")
    monkeypatch.setattr(settings, "transcript_provider", "placeholder")
    limits.clear()
    app.dependency_overrides[current_user] = lambda: {"id": "u", "email": "test@example.com"}
    with TestClient(app) as c:
        with connect() as db:
            db.execute("INSERT INTO users VALUES(?,?,?,?)", ("u", "test@example.com", "disabled", time.time()))
            ref = dict(
                aweme_id="1234567890123456789",
                title="Reference",
                author="Author",
                share_url="https://www.douyin.com/video/1234567890123456789",
                duration=20,
            )
            db.execute("INSERT INTO douyin_results VALUES(?,?,?,?)", ("a" * 32, "u", json.dumps(ref), time.time()))
        monkeypatch.setattr(
            studio.media,
            "probe",
            lambda _: dict(
                duration=40,
                width=320,
                height=568,
                has_audio=True,
                size=16,
                codec="h264",
                fps=30.0,
                orientation="portrait",
            ),
        )
        monkeypatch.setattr(studio.media, "prepare", lambda *a, **k: None)
        yield c
    app.dependency_overrides.clear()


def _create(c):
    config = dict(
        request_id=uuid.uuid4().hex,
        references=["a" * 32],
        title="Owned project",
        script="My original script",
        creator=dict(topic="travel", audience="Families", tone="Calm", rules="No invented claims"),
        owned_rights_confirmed=True,
        language="zh",
        budget=5,
    )
    return c.post(
        "/api/studio/projects",
        data={"config": json.dumps(config)},
        files={"file": ("owned.mp4", b"owned-source-only", "video/mp4")},
    )


def test_get_llm_provider_runpod():
    assert get_llm_provider("runpod").name == "runpod"
    assert get_director_provider("runpod").name == "runpod"


def test_runpod_fail_closed_when_unavailable(client, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "llm_provider", "runpod")
    monkeypatch.setattr(RunPodLLMProvider, "available", lambda self: False)
    monkeypatch.setattr(
        RunPodLLMProvider,
        "health_check",
        lambda self: {"ok": False, "error": "down"},
    )
    pid = _create(client).json()["id"]
    with pytest.raises(RunpodLlmError) as exc:
        ensure_analysis(pid, language="zh", force=True)
    assert str(exc.value) == RUNPOD_LLM_UNAVAILABLE


def test_fast_create_ready_when_runpod_down(client, monkeypatch):
    """Upload must stay READY even if RunPod LLM is down."""
    monkeypatch.setattr(settings, "llm_provider", "runpod")
    monkeypatch.setattr(RunPodLLMProvider, "available", lambda self: False)
    monkeypatch.setattr(
        "backend.runpod_llm.health_check",
        lambda **k: {"ok": False, "error": "down"},
    )
    r = _create(client)
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "ready"
    assert body["stage"] == "ready"
    with connect() as db:
        jobs = db.execute("SELECT kind FROM jobs WHERE project_id=?", (body["id"],)).fetchall()
    assert jobs == []


def test_runpod_director_no_heuristic_swap(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "runpod")
    monkeypatch.setattr(RunPodLLMProvider, "available", lambda self: False)
    provider = get_director_provider()
    assert isinstance(provider, RunPodDirectorProvider)
    with pytest.raises(RunpodLlmError):
        provider.build_plan(duration=20, language="en", transcript=[])


def test_normalize_director_payload():
    from backend.runpod_director_normalize import normalize_director_payload
    from backend.studio import Director

    raw = {
        "summary": {"en": "a", "zh": "b", "ru": "c"},
        "strongest_moment": "x",
        "audience": "y",
        "scores": [{"category": "clarity", "value": 70, "reason": "r"}],
        "scenes": [{"start": 0, "end": 5, "title": "T", "observation": "O", "role": "hook"}],
        "transcript": [{"start": 0, "end": 5, "text": "hi"}],
        "recommendations": [{"id": "r1", "title": "t", "evidence": "e", "improvement": "i", "category": "visuals", "action": "captions", "start": 0, "end": 5}],
        "uncertainties": ["u"],
        "transfers": [],
    }
    plan = Director.model_validate(normalize_director_payload(raw, duration=20))
    assert plan.scenes[0].role == "hook"
    assert plan.recommendations == []
    assert plan.transcript[0].original == "hi"
