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
