"""The accepted coder scene stays local and closed unless one project is named."""
import json
from pathlib import Path

from backend import coder_scene
from backend.config import settings


def test_gate_is_closed_without_the_accepted_flag(monkeypatch):
    monkeypatch.setattr(settings, "coder_scene_accepted", False)
    monkeypatch.setattr(settings, "coder_scene_pilot_project", coder_scene.fragment()["project_id"])
    assert coder_scene.enabled(coder_scene.fragment()["project_id"]) is False


def test_gate_matches_only_the_fragment_project(monkeypatch):
    pid = coder_scene.fragment()["project_id"]
    monkeypatch.setattr(settings, "coder_scene_accepted", True)
    monkeypatch.setattr(settings, "coder_scene_pilot_project", pid)
    assert coder_scene.enabled(pid) is True
    assert coder_scene.enabled("other") is False
    monkeypatch.setattr(settings, "coder_scene_pilot_project", "other")
    assert coder_scene.enabled("other") is False


def test_render_command_does_not_rent_or_call_a_model():
    command = coder_scene.local_render_command("remotion", Path("out.mp4"), Path("public"))
    text = " ".join(command)
    assert "src/coder-scene/index.ts" in command
    assert "QwenScene" in command
    assert "runpod" not in text.lower()
    assert "orchestrate" not in text
    source = Path(coder_scene.__file__).read_text(encoding="utf-8")
    assert "studio_run" not in source
    assert "orchestrate.py" not in source
    env = coder_scene.render_env(coder_scene.motion_root())
    assert "OPENROUTER_API_KEY" not in env
    assert "RUNPOD_API_KEY" not in env


def test_fragment_files_name_the_same_project_and_plan():
    spec = coder_scene.fragment()
    text = (coder_scene.motion_root() / "src" / "coder-scene" / "fragment.ts").read_text(encoding="utf-8")
    assert spec["project_id"] in text
    assert spec["plan_hash"] in text
    assert json.loads((coder_scene.motion_root() / "src" / "coder-scene" / "fragment.json").read_text()) == spec
