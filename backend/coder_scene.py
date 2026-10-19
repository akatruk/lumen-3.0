"""Experimental accepted scene. One allowlisted project. No model call and no pod rental."""
import hashlib
import json
import os
import shutil
import signal
import subprocess
import uuid
from pathlib import Path

from .config import settings
from .db import enqueue, event, project, update
from .director_v3 import (
    MEDIA_CACHE_BYTES,
    OFFTHREAD_CACHE_BYTES,
    OFFTHREAD_VIDEO_THREADS,
    REMOTION_CONCURRENCY,
    _remotion_env,
    motion_root,
)
from .media import ffmpeg, probe

ALLOW_ERROR = "coder_scene_disabled"
FAIL_ERROR = "coder_scene_failed"
ENTRY = "src/coder-scene/index.ts"
COMPOSITION = "EvidenceCut"
PLATES = (
    "ev_property_sale_contract.png",
    "ev_equity_transfer_agreement.png",
    "ev_bank_ledger.png",
)
SECRET_ENV = ("RUNPOD_API_KEY", "OPENROUTER_API_KEY", "MODEL_ACCESS_KEY", "GRADIENT_MODEL_ACCESS_KEY")


def fragment_path() -> Path:
    return motion_root() / "src" / "coder-scene" / "fragment.json"


def fragment() -> dict:
    return json.loads(fragment_path().read_text(encoding="utf-8"))


def enabled(pid: str) -> bool:
    spec = fragment()
    allowed = (settings.coder_scene_pilot_project or "").strip()
    return bool(settings.coder_scene_accepted) and bool(allowed) and pid == allowed == spec["project_id"]


def queue(db, pid: str) -> None:
    if not enabled(pid):
        raise ValueError(ALLOW_ERROR)
    spec = fragment()
    enqueue(db, pid, "coder_scene", {
        "engine": "coder_scene_accepted",
        "window": [spec["origin_seconds"], round(spec["origin_seconds"] + spec["duration_seconds"], 2)],
        "plan_hash": spec["plan_hash"],
        "paid": False,
    })


def local_render_command(binary: str, dest: Path, public_dir: Path) -> list[str]:
    return [
        binary,
        "render", ENTRY, COMPOSITION, str(dest),
        f"--public-dir={public_dir}",
        f"--concurrency={REMOTION_CONCURRENCY}",
        f"--offthreadvideo-video-threads={OFFTHREAD_VIDEO_THREADS}",
        f"--offthreadvideo-cache-size-in-bytes={OFFTHREAD_CACHE_BYTES}",
        f"--media-cache-size-in-bytes={MEDIA_CACHE_BYTES}",
        "--disallow-parallel-encoding",
    ]


def render_env(root: Path) -> dict:
    env = _remotion_env(root)
    for name in SECRET_ENV:
        env.pop(name, None)
    return env


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""


def _stage_inserts(public: Path) -> None:
    root = motion_root().parent
    plates = root / "media" / "library" / "evidence"
    route = root / "media" / "library" / "out" / "motion" / "global" / "global_route_001.webm"
    for name in PLATES:
        src = plates / name
        if not src.is_file():
            raise ValueError(FAIL_ERROR)
        shutil.copyfile(src, public / name)
    if not route.is_file():
        raise ValueError(FAIL_ERROR)
    shutil.copyfile(route, public / "global_route_001.webm")


def _trim_speaker(source: Path, dest: Path, origin: float, duration: float) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg(
        "-y", "-i", source, "-ss", str(origin), "-t", str(duration),
        "-c", "copy", "-movflags", "+faststart", dest,
        timeout=180,
    )


def _render(dest: Path, public_dir: Path) -> None:
    root = motion_root()
    command = local_render_command(str(root / "node_modules" / ".bin" / "remotion"), dest, public_dir)
    env = render_env(root)
    scratch = dest.parent / ".remotion-tmp"
    scratch.mkdir(parents=True, exist_ok=True)
    env["TMPDIR"] = str(scratch)
    proc = subprocess.Popen(
        command,
        cwd=root,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=True,
    )
    try:
        output, _ = proc.communicate(timeout=900)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.wait(timeout=10)
        raise ValueError(FAIL_ERROR)
    if proc.returncode != 0:
        tail = (output or "")[-500:]
        raise ValueError(FAIL_ERROR) if not tail else ValueError(f"{FAIL_ERROR}:{tail}")


def run_job(p, payload):
    pid = p["id"]
    if not enabled(pid):
        raise ValueError(ALLOW_ERROR)
    spec = fragment()
    if payload.get("plan_hash") not in (None, spec["plan_hash"]):
        raise ValueError(FAIL_ERROR)
    from .worker import progress
    progress(pid, "rendering", 8, note="Library inserts for this project. No new model call.")
    previous = project(pid) or {}
    previous_result = previous.get("result") or {}
    source = settings.data_dir / pid / "source"
    if not source.is_file():
        raise ValueError(FAIL_ERROR)
    render_id = uuid.uuid4().hex
    work = settings.data_dir / pid / "coder-scene" / render_id
    public = work / "public"
    speaker = public / "speaker.mp4"
    _trim_speaker(source, speaker, float(spec["origin_seconds"]), float(spec["duration_seconds"]))
    _stage_inserts(public)
    video = work / "scene.mp4"
    _render(video, public)
    try:
        meta = probe(video)
    except ValueError as exc:
        raise ValueError(FAIL_ERROR) from exc
    if (meta.get("width"), meta.get("height")) != (1080, 1920) or not meta.get("has_audio"):
        raise ValueError(FAIL_ERROR)
    if abs(float(meta.get("duration") or 0) - float(spec["duration_seconds"])) > 0.35:
        raise ValueError(FAIL_ERROR)
    folder = settings.data_dir / pid / "renders" / render_id
    folder.mkdir(parents=True)
    dest = folder / "result.mp4"
    dest.write_bytes(video.read_bytes())
    root = motion_root()
    result = {
        "render_id": render_id,
        "metadata": meta,
        "timeline": [[spec["origin_seconds"], round(spec["origin_seconds"] + spec["duration_seconds"], 2)]],
        "applied": ["library_inserts"],
        "picture_engine": "coder_scene",
        "renderer": "remotion_library_inserts",
        "directorMode": "library_inserts",
        "semanticPlanner": "cached",
        "editorialPlanHash": spec["plan_hash"],
        "graphics_component": "LibraryCut",
        "graphics_sha256": _sha(root / "src" / "coder-scene" / "LibraryCut.tsx"),
        "composition": "EvidenceCut",
        "inserts": list(PLATES) + ["global_route_001.webm"],
        "insert_review": "held_needs_review",
        "paid_calls": False,
        "previous_render_id": previous_result.get("render_id"),
        "previous_delivery_sha256": previous_result.get("delivery_sha256"),
        "duration_seconds": float(meta.get("duration") or 0),
        "delivery_sha256": hashlib.sha256(dest.read_bytes()).hexdigest(),
        "assembled": True,
        "qa": None,
        "qa_status": "unavailable",
        "generated_clips": 0,
        "music": None,
        "captions_enabled": True,
        "caption_master": False,
        "manual_transcript": [],
        "visual_review": None,
    }
    update(pid, result=result, status="complete", stage="complete", progress=100, error=None)
    event(pid, "render_complete", '{"applied":["library_inserts"],"engine":"coder_scene","paid":false}')
    progress(pid, "complete", 100, note="Library inserts are the selected picture.")
    return result
