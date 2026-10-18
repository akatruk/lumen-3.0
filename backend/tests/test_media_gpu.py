"""The media GPU queue waits for production work and keeps one model resident."""
import json

import pytest
from fastapi.testclient import TestClient

from backend.app import app, limits
from backend.auth import current_user
from backend.config import settings
from backend.db import connect
from backend.media_gpu import claim_next, enqueue, fail, finish, image_plan, index_generated_before_stage, job_view, set_model_slot


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


def _generated_plan(asset_id="rp_photo_099"):
    return {
        "id": asset_id,
        "kind": "photograph",
        "concept": "relocation.family_planning",
        "prompt": "a family at a clear oak table",
        "negative_prompt": "text",
        "seed": 51099,
        "width": 768,
        "height": 1344,
        "num_inference_steps": 30,
        "guidance_scale": 6.0,
        "model": "stabilityai/stable-diffusion-xl-base-1.0",
        "checkpoint": "sd_xl_base_1.0.safetensors",
        "pipeline": "StableDiffusionXLPipeline",
        "dtype": "float16",
    }


def test_generated_plan_is_indexed_before_it_can_be_staged(client, tmp_path):
    from backend.visual_variation import stage_backgrounds

    library = tmp_path / "library"
    (library / "static").mkdir(parents=True)
    (library / "static" / "kept.png").write_bytes(b"kept-bytes")
    (library / "manifest.json").write_text(json.dumps({
        "version": 1,
        "assets": [{"id": "kept", "type": "image", "file": "static/kept.png"}],
    }))
    source = tmp_path / "batch"
    source.mkdir()
    still = b"\x89PNG\r\n\x1a\nfresh-still"
    (source / "rp_photo_099.png").write_bytes(still)
    (source / "rp_photo_099.json").write_text(json.dumps({"seconds": 4.1}))
    visual = {"scenes": [{"background": {
        "assetId": "rp_photo_099",
        "file": "static/runpod/photographs/rp_photo_099.png",
    }}]}
    public = tmp_path / "public"
    blocked = stage_backgrounds(json.loads(json.dumps(visual)), public, library)
    assert blocked["scenes"][0]["background"]["staged"] is None
    assert not (public / "picked" / "rp_photo_099.png").exists()

    job_id = enqueue("IMAGE_GENERATION", {"prompt": "family at a table", "seed": 51099})
    finish(job_id, {
        "outputPath": "rp_photo_099.png",
        "plans": [_generated_plan()],
        "sourceDir": str(source),
        "library": str(library),
    })
    view = job_view(job_id)
    assert view["status"] == "complete"
    assert view["generationMetadata"]["provider"] == "runpod"
    stored = json.loads((library / "manifest.json").read_text())
    assert [item["id"] for item in stored["assets"]] == ["kept", "rp_photo_099"]
    row = stored["assets"][1]
    assert row["generation"]["provider"] == "runpod"
    assert row["generation"]["model"] == "stabilityai/stable-diffusion-xl-base-1.0"
    assert row["generation"]["seed"] == 51099
    assert row["generation"]["seconds"] == 4.1
    assert row["generation"]["gpu"] == "NVIDIA GeForce RTX 4090"
    assert row["description"]["en"] and row["description"]["ru"] and row["description"]["zh"]
    assert (library / "static/kept.png").read_bytes() == b"kept-bytes"

    clash = library / "static/runpod/photographs/rp_photo_100.png"
    clash.parent.mkdir(parents=True, exist_ok=True)
    clash.write_bytes(b"already-there")
    (source / "rp_photo_100.png").write_bytes(b"different-still")
    assert index_generated_before_stage([_generated_plan("rp_photo_100")], source, library) == []
    assert clash.read_bytes() == b"already-there"
    assert "rp_photo_100" not in {item["id"] for item in json.loads((library / "manifest.json").read_text())["assets"]}

    staged = stage_backgrounds(json.loads(json.dumps(visual)), public, library)
    assert staged["scenes"][0]["background"]["staged"] == "picked/rp_photo_099.png"
    assert (public / "picked" / "rp_photo_099.png").read_bytes() == still

    import sys
    from pathlib import Path
    repo_library = Path(__file__).resolve().parents[2] / "media" / "library"
    if str(repo_library) not in sys.path:
        sys.path.insert(0, str(repo_library))
    from search import search_assets
    for query in (
        "family planning international relocation",
        "семья планирует международный переезд",
        "家庭计划移居国外",
    ):
        hits = search_assets(query, type="image", limit=3, path=library / "manifest.json")
        assert hits[0]["id"] == "rp_photo_099", query


def test_image_plan_uses_the_lumen_sdxl_checkpoint():
    plan = image_plan("family at a clear table", "", 7, 1024, 1024)
    assert plan["model"] == "stabilityai/stable-diffusion-xl-base-1.0"
    assert plan["pipeline"] == "StableDiffusionXLPipeline"
    assert "watermark" in plan["negative_prompt"]
    assert "comfy" not in json.dumps(plan).lower()
