"""original3 excerpt 42.80–76.00s. Stamps the extracted process timeline.

Does not flip SEMANTIC_MOTION_V14_ENABLED. Does not render the 151s source.
Writes only output/original3/timeline-layers-proof.mp4.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.director_v3 import _public_director, render_assembly
from backend.director_v14 import apply_semantic_motion
from backend.scene_composer_v16 import caption_rect, measure_speaker

SOURCE = ROOT / "data" / "original3" / "source"
ASR = ROOT / "data" / "original3" / "asr.json"
OUT = ROOT / "output" / "original3"
DEST = OUT / "timeline-layers-proof.mp4"
OFFSET = 42.80
DURATION = 33.20  # through 76.00s


def _motion_rect(source: Path) -> tuple[dict, dict, dict]:
    faces = []
    for stamp in (44.0, 46.5, 60.0, 68.0, 74.0):
        measured = measure_speaker(source, stamp)
        if measured and measured.get("face"):
            faces.append(measured["face"])
    if not faces:
        raise SystemExit("speaker face was not measured")
    left = min(face["left"] for face in faces)
    top = min(face["top"] for face in faces)
    right = max(face["left"] + face["width"] for face in faces)
    bottom = max(face["top"] + face["height"] for face in faces)
    face = {"left": left, "top": max(0, top - 40), "width": right - left, "height": bottom - max(0, top - 40)}
    motion_left = right + 8
    motion_bottom = max(top - 12, 520)
    motion = {
        "left": motion_left,
        "top": 220,
        "width": max(300, min(340, 1080 - motion_left - 8)),
        "height": max(240, motion_bottom - 220),
    }
    cap = caption_rect("第一层叫使用场景", "zh-CN")
    return face, motion, cap


def main() -> None:
    if os.environ.get("SEMANTIC_MOTION_V14_ENABLED", "").strip().lower() in {"1", "true", "yes", "on"}:
        raise SystemExit("refusing to render while SEMANTIC_MOTION_V14_ENABLED is set")
    if DEST.exists():
        raise SystemExit(f"refusing to overwrite {DEST}")
    rows = json.loads(ASR.read_text(encoding="utf-8"))["segments"]
    window = [row for row in rows if OFFSET <= float(row["start"]) < OFFSET + DURATION]
    os.environ["SEMANTIC_MOTION_V14_ENABLED"] = "1"
    try:
        plan = apply_semantic_motion(
            {
                "language": "zh-CN",
                "durationSeconds": OFFSET + DURATION,
                "beatWeights": [1],
                "scenes": [{
                    "sceneId": "layers",
                    "speaker": {"layout": "speaker_fullscreen"},
                    "typography": {"cards": [{"title": "unused"}]},
                }],
            },
            window,
            locale="zh-CN",
        )
    finally:
        os.environ.pop("SEMANTIC_MOTION_V14_ENABLED", None)
    payload = plan["scenes"][0].get("semanticMotionV14")
    if not payload or payload.get("componentId") != "motion.process_timeline.v1":
        raise SystemExit("extractor did not select process_timeline")
    labels = [step["label"] for step in payload["steps"]]
    if labels != ["使用场景", "家庭结构", "代价"]:
        raise SystemExit(f"unexpected labels {labels}")
    face, motion, cap = _motion_rect(SOURCE)
    payload = dict(payload)
    payload["layout"] = "overlay"
    payload["speakerMode"] = "fullscreen"
    payload["columnScrim"] = False
    payload["sceneTheme"] = "photo"
    payload["enterFrame"] = 0
    payload["motionRect"] = motion
    payload["faceRect"] = face
    payload["captionRect"] = cap
    OUT.mkdir(parents=True, exist_ok=True)
    excerpt = OUT / "excerpt-source.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y", "-ss", f"{OFFSET:.2f}", "-i", str(SOURCE), "-t", f"{DURATION:.2f}",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-movflags", "+faststart",
            str(excerpt),
        ],
        check=True,
    )
    speaker = _public_director() / "original3-timeline-speaker.mp4"
    shutil.copyfile(excerpt, speaker)
    captions = [
        {
            "start": float(row["start"]) - OFFSET,
            "end": min(DURATION, float(row["end"]) - OFFSET),
            "text": row["text"],
        }
        for row in window
    ]
    visual = {
        "generationId": "original3-timeline-layers",
        "visualSeed": 42,
        "artDirection": "source",
        "language": "zh-CN",
        "conceptTriggers": False,
        "backgroundPlate": None,
        "heroObject": None,
        "compositionPolicy": "v9_clean",
        "beatWeights": [1],
        "captions": captions,
        "captionSource": "source_transcript",
        "scenes": [{
            "sceneId": "layers",
            "speaker": {"layout": "speaker_fullscreen"},
            "background": {"treatment": "static_editorial"},
            "foreground": {"treatment": "none"},
            "typography": {"animate": "fade", "cards": [], "cardMode": "none"},
            "transition": "cut",
            "motionIntensity": "low",
            "animateGraphics": True,
            "semanticMotion": {"display": "omit"},
            "composition": {"suppressConcepts": True, "suppressHeadline": True, "suppressHero": True},
            "semanticMotionV14": payload,
        }],
    }
    (OUT / "timeline-layers-proof.plan.json").write_text(json.dumps(visual, ensure_ascii=False, indent=2), encoding="utf-8")
    digest = render_assembly(DEST, seconds=DURATION, speaker=speaker.name, visual_plan=visual)
    print(json.dumps({
        "out": str(DEST),
        "sha256": digest,
        "labels": labels,
        "at": [step.get("at") for step in payload["steps"]],
        "componentId": payload["componentId"],
        "motionRect": motion,
        "faceRect": face,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
