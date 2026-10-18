"""8-second original2 excerpt for the salary-band prototype.

Trims 15.20–23.20 of data/original2/source. Stamps the range payload in this
process only. SEMANTIC_NUMERIC_RANGE_ENABLED is left unset.
Does not write original2-v18.mp4.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from backend.director_v3 import _public_director, render_assembly
from backend.semantic_numeric_range import classify_numeric_range, enabled

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "original2" / "source"
TRANSCRIPT = ROOT / "data" / "original2" / "source.transcript.json"
OUT_DIR = ROOT / "output" / "semantic-coverage"
DEST = OUT_DIR / "original2-range-proof.mp4"
OFFSET = 15.20
DURATION = 8


def _scene(scene_id: str, payload: dict, enter: int) -> dict:
    payload = dict(payload)
    payload["enterFrame"] = enter
    payload["layout"] = "overlay"
    payload["version"] = "v18"
    payload["columnScrim"] = False
    payload["sceneTheme"] = "photo"
    # This host's chin sits below the nominal face band. Park the band on the
    # collar, above the caption plate (top ~1400).
    payload["motionRect"] = {"left": 48, "top": 1210, "width": 984, "height": 200}
    return {
        "sceneId": scene_id,
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
    }


def main() -> None:
    if enabled():
        raise SystemExit("refusing to render while SEMANTIC_NUMERIC_RANGE_ENABLED is set")
    rows = json.loads(TRANSCRIPT.read_text(encoding="utf-8"))
    by_id = {row["id"]: row for row in rows}
    first = classify_numeric_range(by_id["seg_006"]["original"], by_id["seg_006"], locale="zh-CN")
    second = classify_numeric_range(by_id["seg_007"]["original"], by_id["seg_007"], locale="zh-CN")
    if not first or not second:
        raise SystemExit("range classifier missed seg_006 or seg_007")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    excerpt = OUT_DIR / "excerpt-source.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y", "-ss", str(OFFSET), "-i", str(SOURCE), "-t", str(DURATION),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-movflags", "+faststart",
            str(excerpt),
        ],
        check=True,
    )
    speaker = _public_director() / "semantic-coverage-speaker.mp4"
    shutil.copyfile(excerpt, speaker)
    first_end = float(by_id["seg_006"]["end"]) - OFFSET
    frames = DURATION * 30
    first_frames = int(round(first_end * 30))
    plan = {
        "generationId": "semantic-coverage-range",
        "visualSeed": 42,
        "artDirection": "source",
        "language": "zh-CN",
        "conceptTriggers": False,
        "backgroundPlate": None,
        "heroObject": None,
        "compositionPolicy": "v9_clean",
        "beatWeights": [first_frames, frames - first_frames],
        "captions": [
            {
                "start": float(by_id["seg_006"]["start"]) - OFFSET,
                "end": float(by_id["seg_006"]["end"]) - OFFSET,
                "text": by_id["seg_006"]["original"],
            },
            {
                "start": float(by_id["seg_007"]["start"]) - OFFSET,
                "end": min(DURATION, float(by_id["seg_007"]["end"]) - OFFSET),
                "text": by_id["seg_007"]["original"],
            },
        ],
        "captionSource": "source_transcript",
        "scenes": [
            _scene("range-salary", first, enter=8),
            _scene("range-cny", second, enter=0),
        ],
    }
    (OUT_DIR / "original2-range-proof.plan.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    digest = render_assembly(DEST, seconds=DURATION, speaker=speaker.name, visual_plan=plan)
    print(json.dumps({"out": str(DEST), "sha256": digest, "flag": False}))


if __name__ == "__main__":
    main()
