"""The media GPU queue waits for production work and keeps one model resident."""
import json

import pytest
from fastapi.testclient import TestClient

from backend.app import app, limits
from backend.auth import current_user
from backend.config import settings
from backend.db import connect
from backend.media_gpu import claim_next, enqueue, fail, finish, image_plan, set_model_slot


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    limits.clear()
    app.dependency_overrides[current_user] = lambda: {"id": "u", "email": "test@example.com"}
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(current_user, None)


def test_generate_image_requires_a_session(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    app.dependency_overrides.pop(current_user, None)
    with TestClient(app) as client:
        response = client.post("/internal/media/generate-image", json={
            "prompt": "a quiet apartment interior with morning light",
            "width": 768,
            "height": 1344,
            "seed": 11,
            "preset": "editorial_photography",
        })
    assert response.status_code == 401


def test_generate_image_queues_without_touching_the_gpu(client):
    response = client.post("/internal/media/generate-image", json={
        "prompt": "a quiet apartment interior with morning light",
        "negativePrompt": "text",
        "width": 770,
        "height": 1340,
        "seed": 42,
        "preset": "editorial_photography",
    })
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "queued"
    assert body["outputPath"] is None
    assert body["model"] == "stabilityai/stable-diffusion-xl-base-1.0"
    assert body["seed"] == 42
    assert body["generationMetadata"]["width"] == 768
    assert body["generationMetadata"]["height"] == 1344
    assert body["generationMetadata"]["negativeApplied"] is True
    assert body["generationMetadata"]["pipeline"] == "StableDiffusionXLPipeline"
    plan = image_plan("a quiet room", "text", 42, 768, 1344)
    assert plan["guidance_scale"] == 6.0
    assert plan["checkpoint"] == "sd_xl_base_1.0.safetensors"
    assert "text" in plan["negative_prompt"]
    assert "class_type" not in json.dumps(plan)


def test_production_jobs_block_the_media_queue(client):
    image_id = enqueue("IMAGE_GENERATION", {"prompt": "apartment", "seed": 1})
    sync_id = enqueue("MEDIA_SYNC", {"path": "library"})
    with connect() as db:
        db.execute(
            "INSERT INTO jobs(id,project_id,kind,payload,status,created,updated) VALUES (?,?,?,?,?,?,?)",
            ("job-render", None, "studio_render", "{}", "queued", 1, 1),
        )
    assert claim_next() is None
    with connect() as db:
        db.execute("UPDATE jobs SET status='complete' WHERE id='job-render'")
    claimed = claim_next()
    assert claimed["id"] == image_id
    assert claim_next() is None
    finish(image_id, {"outputPath": "out.png"})
    assert claim_next()["id"] == sync_id


def test_video_waits_until_the_image_model_is_unloaded(client):
    set_model_slot("image")
    video_id = enqueue("IMAGE_TO_VIDEO", {"source": "still.png"})
    assert claim_next() is None
    set_model_slot(None)
    claimed = claim_next()
    assert claimed["id"] == video_id
    assert fail(video_id, "oom") == "queued"
    again = claim_next()
    assert again["attempts"] == 2
    assert fail(video_id, "oom") == "failed"


def test_image_plan_uses_the_lumen_sdxl_checkpoint():
    plan = image_plan("family at a clear table", "", 7, 1024, 1024)
    assert plan["model"] == "stabilityai/stable-diffusion-xl-base-1.0"
    assert plan["pipeline"] == "StableDiffusionXLPipeline"
    assert "watermark" in plan["negative_prompt"]
    assert "comfy" not in json.dumps(plan).lower()
