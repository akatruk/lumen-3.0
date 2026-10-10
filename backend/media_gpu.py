"""Queue image and video generation for the existing RunPod GPU.

Production speech and render jobs stay in the main jobs table and are
claimed first. This queue does not start a second GPU, and it does not
load an image model and a video model at the same time.
"""
import json
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from .auth import current_user
from .config import settings
from .database import connect

router = APIRouter()

IMAGE_MODEL = "stabilityai/stable-diffusion-xl-base-1.0"
IMAGE_CHECKPOINT = "sd_xl_base_1.0.safetensors"
IMAGE_PIPELINE = "StableDiffusionXLPipeline"
DEFAULT_NEGATIVE = (
    "text, letters, numbers, logo, watermark, signature, passport, "
    "signage, label, malformed hands, extra fingers, plastic skin"
)

PRIORITIES = {
    "IMAGE_GENERATION": 20,
    "IMAGE_TO_VIDEO": 30,
    "UPSCALE": 40,
    "QA": 50,
    "MEDIA_SYNC": 60,
}
GPU_KINDS = {"IMAGE_GENERATION", "IMAGE_TO_VIDEO", "UPSCALE"}
PRESETS = {
    "editorial_photography": (
        "realistic editorial photograph, natural color, soft daylight, "
        "plain unlettered surfaces, no logos, no watermark"
    ),
}


class ImageRequest(BaseModel):
    prompt: str = Field(min_length=8, max_length=2000)
    negativePrompt: str = ""
    width: int = 768
    height: int = 1344
    seed: int = Field(default=0, ge=0, le=2**31 - 1)
    preset: str = "editorial_photography"


def ensure_schema():
    with connect() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS media_gpu_jobs(
              id TEXT PRIMARY KEY,
              kind TEXT NOT NULL,
              priority INTEGER NOT NULL,
              status TEXT NOT NULL,
              payload TEXT NOT NULL,
              result TEXT,
              error TEXT,
              attempts INTEGER NOT NULL,
              max_attempts INTEGER NOT NULL,
              timeout_s INTEGER NOT NULL,
              created REAL NOT NULL,
              updated REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS media_gpu_queue ON media_gpu_jobs(status, priority, created);
            """
        )


def production_busy():
    """Speech, render, and every other production job keep the GPU."""
    with connect() as db:
        return db.execute(
            "SELECT 1 FROM jobs WHERE status IN ('queued','running') LIMIT 1"
        ).fetchone() is not None


def _slot_path():
    folder = settings.data_dir / "media-gpu"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / "model-slot.json"


def model_slot():
    path = _slot_path()
    if not path.is_file():
        return {"resident": None}
    return json.loads(path.read_text())


def set_model_slot(resident):
    """resident is 'image', 'video', or None. Never both."""
    if resident not in (None, "image", "video"):
        raise ValueError("model_slot")
    _slot_path().write_text(json.dumps({"resident": resident}))


def align_dimension(value, default):
    number = int(value or default)
    number = max(256, min(1344, number))
    rounded = int(round(number / 16.0)) * 16
    return max(256, min(1344, rounded))


def image_plan(prompt, negative, seed, width, height):
    """Diffusers inputs for the lumen-owned SDXL checkpoint. A negative prompt is applied."""
    extra = (negative or "").strip()
    negative_prompt = DEFAULT_NEGATIVE if not extra else DEFAULT_NEGATIVE + ", " + extra
    return {
        "pipeline": IMAGE_PIPELINE,
        "model": IMAGE_MODEL,
        "checkpoint": IMAGE_CHECKPOINT,
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "seed": int(seed),
        "width": int(width),
        "height": int(height),
        "num_inference_steps": 30,
        "guidance_scale": 6.0,
        "dtype": "float16",
    }


def enqueue(kind, payload, timeout_s=300, max_attempts=2):
    if kind not in PRIORITIES:
        raise ValueError("job_kind")
    ensure_schema()
    now = time.time()
    job_id = uuid.uuid4().hex
    with connect() as db:
        db.execute(
            """INSERT INTO media_gpu_jobs
               (id,kind,priority,status,payload,result,error,attempts,max_attempts,timeout_s,created,updated)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (job_id, kind, PRIORITIES[kind], "queued", json.dumps(payload), None, None, 0, max_attempts, timeout_s, now, now),
        )
    return job_id


def claim_next():
    """Take the next media job only when production is idle and one GPU job is enough."""
    if production_busy():
        return None
    ensure_schema()
    with connect() as db:
        running = db.execute(
            "SELECT kind FROM media_gpu_jobs WHERE status='running' LIMIT 1"
        ).fetchone()
        if running:
            return None
        row = db.execute(
            """SELECT * FROM media_gpu_jobs
               WHERE status='queued' ORDER BY priority, created LIMIT 1"""
        ).fetchone()
        if not row:
            return None
        job = dict(row)
        if job["kind"] in GPU_KINDS:
            resident = model_slot().get("resident")
            needed = "video" if job["kind"] == "IMAGE_TO_VIDEO" else "image"
            if resident not in (None, needed):
                return None
        db.execute(
            "UPDATE media_gpu_jobs SET status='running', attempts=attempts+1, updated=? WHERE id=?",
            (time.time(), job["id"]),
        )
        job["attempts"] = job["attempts"] + 1
        job["status"] = "running"
        return job


def finish(job_id, result):
    with connect() as db:
        db.execute(
            "UPDATE media_gpu_jobs SET status='complete', result=?, updated=? WHERE id=?",
            (json.dumps(result), time.time(), job_id),
        )


def fail(job_id, error):
    with connect() as db:
        row = db.execute("SELECT attempts, max_attempts FROM media_gpu_jobs WHERE id=?", (job_id,)).fetchone()
        if row and row["attempts"] < row["max_attempts"]:
            db.execute(
                "UPDATE media_gpu_jobs SET status='queued', error=?, updated=? WHERE id=?",
                (error[:500], time.time(), job_id),
            )
            return "queued"
        db.execute(
            "UPDATE media_gpu_jobs SET status='failed', error=?, updated=? WHERE id=?",
            (error[:500], time.time(), job_id),
        )
        return "failed"


def job_view(job_id):
    ensure_schema()
    with connect() as db:
        row = db.execute("SELECT * FROM media_gpu_jobs WHERE id=?", (job_id,)).fetchone()
    if not row:
        return None
    payload = json.loads(row["payload"])
    result = json.loads(row["result"]) if row["result"] else {}
    return {
        "jobId": row["id"],
        "status": row["status"],
        "outputPath": result.get("outputPath"),
        "model": payload.get("model") or IMAGE_MODEL,
        "seed": payload.get("seed"),
        "generationMetadata": {
            "kind": row["kind"],
            "preset": payload.get("preset"),
            "width": payload.get("width"),
            "height": payload.get("height"),
            "negativeApplied": True,
            "pipeline": payload.get("pipeline") or IMAGE_PIPELINE,
            "attempts": row["attempts"],
            "error": row["error"],
            "provider": "runpod",
        },
    }


@router.post("/internal/media/generate-image")
def generate_image(body: ImageRequest, user=Depends(current_user)):
    if body.preset not in PRESETS:
        raise HTTPException(422, "preset")
    width = align_dimension(body.width, 768)
    height = align_dimension(body.height, 1344)
    seed = body.seed or int(time.time()) % 1_000_000_000
    prompt = body.prompt.strip()
    if body.preset in PRESETS:
        prompt = prompt + ", " + PRESETS[body.preset]
    payload = {
        "prompt": prompt,
        "negativePrompt": body.negativePrompt,
        "width": width,
        "height": height,
        "seed": seed,
        "preset": body.preset,
        "model": IMAGE_MODEL,
        "pipeline": IMAGE_PIPELINE,
        "checkpoint": IMAGE_CHECKPOINT,
        "requestedBy": user["id"],
        "plan": image_plan(prompt, body.negativePrompt, seed, width, height),
    }
    job_id = enqueue("IMAGE_GENERATION", payload)
    return job_view(job_id)
