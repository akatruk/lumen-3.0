#!/usr/bin/env python3
"""Image-to-video via lumen-owned Stable Video Diffusion weights.

Expects PYTHONPATH=/workspace/lumen-media-v1/py and SVD weights under
/workspace/lumen-media-v1/models/svd-xt (diffusers snapshot) or HF cache.
Does not use ComfyUI or foreign checkpoints.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
import time
from pathlib import Path

import torch
from diffusers import StableVideoDiffusionPipeline
from diffusers.utils import load_image
from PIL import Image


DEFAULT_MODEL = "/workspace/lumen-media-v1/models/svd-xt"
DEFAULT_HF_ID = "stabilityai/stable-video-diffusion-img2vid-xt"


def resolve_model(path: str) -> str:
    p = Path(path)
    if p.is_dir() and (p / "model_index.json").is_file():
        return str(p)
    # allow HF id or local incomplete → caller downloads separately
    return path


def load_pipeline(model: str):
    dtype = torch.float16
    resolved = resolve_model(model)
    try:
        pipe = StableVideoDiffusionPipeline.from_pretrained(
            resolved,
            torch_dtype=dtype,
            variant="fp16",
        )
    except Exception:
        pipe = StableVideoDiffusionPipeline.from_pretrained(
            resolved,
            torch_dtype=dtype,
        )
    pipe.to("cuda")
    return pipe


def frames_to_mp4(frames, output: Path, fps: int, target_w: int, target_h: int) -> None:
    """Write frames via ffmpeg only — no opencv / imageio required on the pod."""
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="svd_frames_") as tmp:
        tmp_path = Path(tmp)
        for i, frame in enumerate(frames):
            if isinstance(frame, Image.Image):
                img = frame.convert("RGB")
            else:
                img = Image.fromarray(frame).convert("RGB")
            img.save(tmp_path / f"frame_{i:04d}.png")
        pattern = str(tmp_path / "frame_%04d.png")
        cmd = [
            "ffmpeg", "-y",
            "-framerate", str(min(fps, 24)),
            "-i", pattern,
            "-vf", f"scale={target_w}:{target_h}:flags=lanczos",
            "-r", str(fps),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an",
            str(output),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError("ffmpeg failed: " + (proc.stderr or proc.stdout or "")[-800:])


def render(pipe, plan: dict, still: Path, output: Path) -> dict:
    image = load_image(str(still))
    w = int(plan.get("width") or 768)
    h = int(plan.get("height") or 1344)
    # SVD expects multiple of 64; resize preserving portrait
    image = image.resize((w, h))
    generator = torch.Generator(device="cuda").manual_seed(int(plan["seed"]))
    num_frames = max(14, min(25, int(round(float(plan.get("seconds", 4)) * 6))))
    started = time.time()
    frames = pipe(
        image,
        decode_chunk_size=int(plan.get("decode_chunk_size") or 4),
        generator=generator,
        num_frames=num_frames,
        motion_bucket_id=int(plan.get("motion_bucket_id") or 90),
        noise_aug_strength=float(plan.get("noise_aug_strength") or 0.02),
    ).frames[0]
    fps = int(plan.get("fps") or 30)
    target_w = int(plan.get("out_width") or 1080)
    target_h = int(plan.get("out_height") or 1920)
    frames_to_mp4(frames, output, fps=fps, target_w=target_w, target_h=target_h)
    meta = dict(plan)
    meta["seconds_wall"] = round(time.time() - started, 2)
    meta["output"] = str(output)
    meta["provider"] = "runpod_svd"
    meta["num_frames"] = num_frames
    output.with_suffix(".json").write_text(json.dumps(meta, indent=2))
    return meta


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--batch", required=True)
    parser.add_argument("--stills-dir", required=True)
    parser.add_argument("--outdir", required=True)
    args = parser.parse_args()
    model = args.model
    if not Path(model).exists() and model == DEFAULT_MODEL:
        model = DEFAULT_HF_ID
    pipe = load_pipeline(model)
    outdir = Path(args.outdir)
    stills = Path(args.stills_dir)
    for line in Path(args.batch).read_text().splitlines():
        if not line.strip():
            continue
        plan = json.loads(line)
        dest = outdir / (plan["id"] + ".mp4")
        if dest.is_file() and dest.stat().st_size > 0:
            print("SKIP", plan["id"], flush=True)
            continue
        still = stills / (plan["source_still"] + ".png")
        if not still.is_file():
            print("MISSING_STILL", plan["id"], still, flush=True)
            continue
        meta = render(pipe, plan, still, dest)
        print("DONE", plan["id"], meta["seconds_wall"], flush=True)
    print("BATCH_DONE", flush=True)


if __name__ == "__main__":
    main()
