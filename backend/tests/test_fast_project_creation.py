"""Fast project creation: no AI on upload; deferred analysis at create-video."""

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
from backend.source_analysis import ensure_analysis, source_checksum


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


def create(c, **overrides):
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
    config.update(overrides)
    return c.post(
        "/api/studio/projects",
        data={"config": json.dumps(config)},
        files={"file": ("owned.mp4", b"owned-source-only", "video/mp4")},
    )


def test_create_ready_without_analyze_job(client):
    r = create(client)
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "ready"
    assert body["stage"] == "ready"
    meta = body["metadata"]
    assert meta["duration"] == 40
    assert meta["orientation"] == "portrait"
    assert meta.get("source_checksum")
    with connect() as db:
        jobs = db.execute("SELECT kind FROM jobs WHERE project_id=?", (body["id"],)).fetchall()
    assert jobs == []


def test_create_no_openrouter_when_key_empty(client, monkeypatch):
    calls = []

    def boom(*a, **k):
        calls.append(1)
        raise AssertionError("OpenRouter must not run on create")

    monkeypatch.setattr(studio.ai, "json_call", boom)
    monkeypatch.setattr(studio.ai, "reference_dna", boom)
    assert create(client).status_code == 201
    assert calls == []


def test_deferred_analysis_on_create_video(client, monkeypatch):
    pid = create(client).json()["id"]
    # Lightweight prepare stub already set; avoid real ffmpeg in ensure.
    monkeypatch.setattr("backend.source_analysis.media.prepare", lambda *a, **k: None)
    monkeypatch.setattr(
        "backend.source_analysis.media.probe",
        lambda _: dict(duration=40, width=320, height=568, has_audio=True, size=16, codec="h264", fps=30, orientation="portrait"),
    )
    monkeypatch.setattr("backend.source_analysis.media.validate_analysis", lambda analysis, duration: analysis)
    monkeypatch.setattr(
        "backend.providers.transcript.PlaceholderTranscriptProvider.transcribe",
        lambda self, video_path, language=None, duration=None: [
            {"start": 0.0, "end": 40.0, "text": "hello"}
        ],
    )

    started = client.post(
        f"/api/studio/projects/{pid}/create-video",
        json={"animation_percent": 50, "intensity_percent": 60, "motion_percent": 80, "density_percent": 70},
    )
    assert started.status_code == 200, started.text
    with connect() as db:
        plan = db.execute("SELECT plan FROM studio_projects WHERE project_id=?", (pid,)).fetchone()["plan"]
        job = db.execute(
            "SELECT kind,status FROM jobs WHERE project_id=? AND kind='studio_render'",
            (pid,),
        ).fetchone()
    assert plan
    assert json.loads(plan)["recommendations"] == []
    assert job["status"] == "queued"
    assert started.json().get("director_mode") == "heuristic"
    assert started.json().get("analysis_quality") == "local_baseline"


def test_analysis_cache_reuse(client, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    monkeypatch.setattr(settings, "transcript_provider", "placeholder")
    monkeypatch.setattr("backend.source_analysis.media.prepare", lambda *a, **k: None)
    monkeypatch.setattr(
        "backend.source_analysis.media.probe",
        lambda _: dict(duration=40, width=320, height=568, has_audio=True, size=16, codec="h264", fps=30, orientation="portrait"),
    )
    monkeypatch.setattr("backend.source_analysis.media.validate_analysis", lambda analysis, duration: analysis)
    monkeypatch.setattr(
        "backend.providers.transcript.PlaceholderTranscriptProvider.transcribe",
        lambda self, video_path, language=None, duration=None: [
            {"start": 0.0, "end": 40.0, "text": "cached"}
        ],
    )
    pid = create(client).json()["id"]
    first = ensure_analysis(pid, language="zh")
    assert first["reused"] is False
    second = ensure_analysis(pid, language="zh")
    assert second["reused"] is True


def test_legacy_flag_enqueues_analyze(client, monkeypatch):
    monkeypatch.setattr(settings, "fast_project_creation_enabled", False)
    r = create(client)
    assert r.status_code == 201
    pid = r.json()["id"]
    assert r.json()["status"] == "queued"
    with connect() as db:
        kind = db.execute("SELECT kind FROM jobs WHERE project_id=?", (pid,)).fetchone()[0]
    assert kind == "studio_analyze"


def test_source_checksum_stable(tmp_path):
    f = tmp_path / "source"
    f.write_bytes(b"abc")
    assert source_checksum(f) == source_checksum(f)
