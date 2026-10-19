"""Release regressions for semantic activation and short source delivery."""
import pytest
from backend.tests.test_studio import client, create, seed_plan
from backend.config import settings


def test_semantic_activation_does_not_reuse_cached_heuristic(client, monkeypatch):
    from backend import source_analysis
    pid = create(client).json()["id"]
    seed_plan(pid)
    monkeypatch.setattr(settings, "llm_provider", "openrouter")
    monkeypatch.setattr(settings, "semantic_planner_required", True)
    monkeypatch.setattr(source_analysis, "_cache_valid", lambda *args: True)
    called = []
    def build(*args, **kwargs):
        called.append(True)
        raise ValueError("semantic_rebuild_required")
    monkeypatch.setattr(source_analysis, "build_local_plan", build)
    with pytest.raises(ValueError, match="semantic_rebuild_required"):
        source_analysis.ensure_analysis(pid)
    assert called == [True]


def test_saved_openrouter_plan_is_reused_without_a_provider_call(client, monkeypatch):
    import json
    from backend import source_analysis
    from backend.db import connect
    from backend.semantic_planner import plan_path
    from backend.tests.test_studio import create, seed_plan

    pid = create(client).json()["id"]
    seed_plan(pid)
    monkeypatch.setattr(settings, "llm_provider", "openrouter")
    monkeypatch.setattr(settings, "openrouter_api_key", "test-key")
    source = settings.data_dir / pid / "source"
    checksum = source_analysis.source_checksum(source)
    with connect() as db:
        row = db.execute("SELECT metadata FROM projects WHERE id=?", (pid,)).fetchone()
        meta = json.loads(row["metadata"] or "{}")
        meta.update({
            "director_mode": "semantic_openrouter",
            "analysis_version": source_analysis.ANALYSIS_VERSION,
            "source_checksum": checksum,
            "analysis_stale": False,
        })
        db.execute("UPDATE projects SET metadata=? WHERE id=?", (json.dumps(meta), pid))
        state = db.execute("SELECT context FROM studio_projects WHERE project_id=?", (pid,)).fetchone()
        context = json.loads(state["context"] or "{}")
        context["director_mode"] = "semantic_openrouter"
        stored = json.loads(db.execute("SELECT plan FROM studio_projects WHERE project_id=?", (pid,)).fetchone()["plan"])
        stored["transcript"] = [{
            "start": 0, "end": 1, "original": "包括工资完税单",
            "en": "包括工资完税单", "zh": "包括工资完税单", "ru": "包括工资完税单",
        }]
        db.execute(
            "UPDATE studio_projects SET context=?, plan=? WHERE project_id=?",
            (json.dumps(context), json.dumps(stored), pid),
        )
    path = plan_path(pid)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "planner": "openrouter",
        "model": "qwen/qwen3-30b-a3b-instruct-2507",
        "planHash": "reuse-hash",
        "language": "zh",
        "topic": "documents",
        "transcript_version": 1,
        "passages": [{
            "segment_ids": ["segment_001"],
            "intent": "enumeration",
            "narrative_role": "evidence",
            "visual_treatment": "process",
            "visual_need": "explanatory_graphic",
            "visual_concept": "",
            "semantic_reason": "The sentence names the document.",
            "confidence": 0.9,
            "quote": "包括工资完税单",
            "labels": ["工资完税单"],
            "review_note": "",
        }],
    }), encoding="utf-8")

    def forbidden(*_args, **_kwargs):
        raise AssertionError("provider_called")

    monkeypatch.setattr("backend.ai.json_call", forbidden)
    reused = source_analysis.ensure_analysis(pid)
    assert reused["reused"] is True
    assert json.loads(path.read_text())["planHash"] == "reuse-hash"


def test_short_cut_stages_uploaded_source(tmp_path, monkeypatch):
    from backend import director_v3
    public = tmp_path / "public"
    public.mkdir()
    source = tmp_path / "uploaded.mp4"
    source.write_bytes(b"uploaded-source-not-the-demo-host")
    monkeypatch.setattr(director_v3, "_public_director", lambda: public)
    assert director_v3.speaker_for(10, source) == "source-edit.mp4"
    assert (public / "source-edit.mp4").read_bytes() == source.read_bytes()


def test_semantic_duration_clips_later_passages_without_stretching():
    from backend.passage_retrieval import bound_semantic_duration
    plan = {"form": "semantic", "scenes": [
        {"sceneId": "passage_01", "start": 0, "end": 9},
        {"sceneId": "passage_02", "start": 10, "end": 20},
    ]}
    short = bound_semantic_duration(plan, 15)
    assert [(s["start"], s["end"]) for s in short["scenes"]] == [(0, 9), (10, 15)]
    full = bound_semantic_duration(plan, 30)
    assert full["scenes"] == plan["scenes"]
