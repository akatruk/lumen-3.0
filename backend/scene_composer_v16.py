"""Scene composer V16.

SCENE_COMPOSER_V16_ENABLED defaults off. When on, it rewrites the layout of
scenes that already have a semantic diagram. It does not pick new facts and
it does not replace Director.

Speaker stays the large subject. Diagrams sit in measured space that clears
the face and the caption plate. A tiny PIP and a full-frame navy plate are
rejected. Backgrounds that contradict the spoken intent are swapped for an
already-indexed cinematic clip.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

from .director_v14 import _windows

CANVAS = (1080, 1920)
CAPTION_CLEARANCE = 320
CAPTION_BOX = 200
FPS = 30
SPEAKER_WIDTH = 640

# Indexed clips. Used only when the current asset contradicts the intent.
_MEDIA = {
    "shareholder_network": ("cev6_i2v_biz_meeting_002", "motion/cinematic-env-v6/clips/cev6_i2v_biz_meeting_002.mp4"),
    "capital_flow": ("cev6_i2v_inv_glass_002", "motion/cinematic-env-v6/clips/cev6_i2v_inv_glass_002.mp4"),
    "ownership_split": ("cev6_i2v_inv_glass_002", "motion/cinematic-env-v6/clips/cev6_i2v_inv_glass_002.mp4"),
    "business_comparison": ("cev6_i2v_biz_boardroom_001", "motion/cinematic-env-v6/clips/cev6_i2v_biz_boardroom_001.mp4"),
    "document_workflow": ("cev6_i2v_biz_lobby_004", "motion/cinematic-env-v6/clips/cev6_i2v_biz_lobby_004.mp4"),
    "process_timeline": ("cev6_i2v_biz_lobby_004", "motion/cinematic-env-v6/clips/cev6_i2v_biz_lobby_004.mp4"),
}
_BANNED = {
    "shareholder_network": ("facade", "living", "passport", "harbor", "bedroom"),
    "capital_flow": ("passport", "living", "bedroom", "facade"),
    "ownership_split": ("passport", "living", "bedroom"),
    "business_comparison": ("living", "passport", "bedroom"),
    "document_workflow": ("living", "harbor", "bedroom"),
    "process_timeline": ("living", "harbor", "bedroom"),
}


def enabled() -> bool:
    raw = os.environ.get("SCENE_COMPOSER_V16_ENABLED", "0").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _overlap(a: dict, b: dict, gap: int = 0) -> bool:
    return (
        a["left"] < b["left"] + b["width"] + gap
        and a["left"] + a["width"] + gap > b["left"]
        and a["top"] < b["top"] + b["height"] + gap
        and a["top"] + a["height"] + gap > b["top"]
    )


def wrap_lines(text: str, locale: str, max_chars: int = 28) -> list[str]:
    """EN/RU break on spaces. CJK breaks on characters, keeping punctuation with the previous char."""
    raw = " ".join((text or "").split())
    if not raw:
        return []
    if str(locale).startswith("zh"):
        lines: list[str] = []
        buf = ""
        for ch in raw:
            buf += ch
            if len(buf) >= max_chars and ch not in "，。、；：！？,.!?;:":
                lines.append(buf)
                buf = ""
        if buf:
            lines.append(buf)
        return lines
    words = raw.split(" ")
    lines = []
    cur: list[str] = []
    for word in words:
        trial = " ".join(cur + [word])
        if cur and len(trial) > max_chars:
            lines.append(" ".join(cur))
            cur = [word]
        else:
            cur.append(word)
    if cur:
        lines.append(" ".join(cur))
    return lines


def caption_rect(text: str, locale: str) -> dict[str, int]:
    lines = wrap_lines(text, locale) or [""]
    height = min(CAPTION_BOX, max(72, 18 + len(lines) * 52))
    top = CANVAS[1] - CAPTION_CLEARANCE - CAPTION_BOX
    return {"left": 64, "top": top, "width": CANVAS[0] - 128, "height": CAPTION_BOX}


def geometry_from_pixels(points: list[tuple[int, int]], sample_size: tuple[int, int]) -> dict[str, int] | None:
    """Scale a measured skin/face blob from a downsampled frame into canvas pixels."""
    if len(points) < 12:
        return None
    sw, sh = sample_size
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    left = min(xs) / sw * CANVAS[0]
    right = (max(xs) + 1) / sw * CANVAS[0]
    top = min(ys) / sh * CANVAS[1]
    bottom = (max(ys) + 1) / sh * CANVAS[1]
    return {
        "left": int(left),
        "top": int(top),
        "width": max(40, int(right - left)),
        "height": max(40, int(bottom - top)),
    }


def _skin(r: int, g: int, b: int) -> bool:
    """Warm chroma only. Beige walls pass a loose RGB test and blow the box up to the frame."""
    span = max(r, g, b) - min(r, g, b)
    return r > 150 and g > 80 and b > 50 and r > g and r > b and (r - g) > 28 and span > 35 and r < 250


def _largest_blob(mask: list[list[bool]]) -> list[tuple[int, int]]:
    height = len(mask)
    width = len(mask[0]) if height else 0
    seen = [[False] * width for _ in range(height)]
    best: list[tuple[int, int]] = []
    for y in range(height):
        for x in range(width):
            if not mask[y][x] or seen[y][x]:
                continue
            stack = [(x, y)]
            seen[y][x] = True
            comp: list[tuple[int, int]] = []
            while stack:
                cx, cy = stack.pop()
                comp.append((cx, cy))
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < width and 0 <= ny < height and mask[ny][nx] and not seen[ny][nx]:
                        seen[ny][nx] = True
                        stack.append((nx, ny))
            if len(comp) > len(best):
                best = comp
    return best


def measure_speaker(source: Path, timestamp: float) -> dict[str, Any] | None:
    """One downsampled frame. Face box is the upper part of the largest skin blob."""
    try:
        proc = subprocess.run(
            [
                "ffmpeg", "-v", "error", "-ss", f"{max(0.0, timestamp):.2f}",
                "-i", str(source), "-frames:v", "1", "-vf", "scale=180:320",
                "-f", "image2pipe", "-vcodec", "png", "pipe:1",
            ],
            check=False,
            capture_output=True,
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0 or not proc.stdout:
        return None
    try:
        from PIL import Image
        import io
        image = Image.open(io.BytesIO(proc.stdout)).convert("RGB")
    except Exception:
        return None
    pixels = image.load()
    limit_y = int(image.height * 0.72)
    mask = [[False] * image.width for _ in range(limit_y)]
    for y in range(limit_y):
        for x in range(image.width):
            if _skin(*pixels[x, y]):
                mask[y][x] = True
    blob = _largest_blob(mask)
    if len(blob) < 40:
        return None
    ys = [p[1] for p in blob]
    y0, y1 = min(ys), max(ys)
    if (max(p[0] for p in blob) - min(p[0] for p in blob)) > image.width * 0.75:
        return None
    # The blob includes neck and shirt. The face is the top of it.
    face_cut = y0 + max(8, int(0.42 * (y1 - y0)))
    points = [p for p in blob if p[1] <= face_cut]
    box = geometry_from_pixels(points, image.size)
    if not box or box["width"] > int(CANVAS[0] * 0.7) or box["height"] > int(CANVAS[1] * 0.45):
        return None
    return {"method": "skin_blob", "timestamp": timestamp, "face": box}


def _safe(mode: str, speaker: dict, motion: dict, face: dict, caption: dict) -> bool:
    if _overlap(motion, caption, 12):
        return False
    if mode == "fullscreen":
        return not _overlap(motion, face, 8)
    cx = face["left"] + face["width"] / 2
    cy = face["top"] + face["height"] / 2
    inside = speaker["left"] <= cx <= speaker["left"] + speaker["width"] and speaker["top"] <= cy <= speaker["top"] + speaker["height"]
    return inside and not _overlap(motion, speaker, 8)


def _choose(face: dict, caption: dict, recent: list[str], avoid: str | None = None) -> tuple[str, str, dict, dict, str]:
    width, height = CANVAS
    mouth = face["top"] + face["height"]
    overlay_top = max(mouth + 28, int(height * 0.52))
    overlay_bottom = caption["top"] - 48
    overlay = {
        "left": 72,
        "top": overlay_top,
        "width": width - 144,
        "height": max(0, overlay_bottom - overlay_top),
    }
    overlay_ok = overlay["height"] >= 240 and not _overlap(overlay, face, 8) and not _overlap(overlay, caption, 12)
    face_cx = face["left"] + face["width"] / 2
    # Keep the speaker on the side that holds the face, unless diversity needs a flip.
    speaker_side = "right" if face_cx >= width / 2 else "left"
    mode = "fullscreen" if overlay_ok else "split"
    key = "motion_overlay" if mode == "fullscreen" else f"speaker_{speaker_side}"
    if avoid and key == avoid or (len(recent) >= 2 and recent[-1] == recent[-2] == key):
        if mode == "fullscreen":
            # Same speaker, diagram pulled to the side of the band. A cropped split
            # was showing the staged still under the number.
            key = "motion_beside"
            overlay = {**overlay, "left": 72, "width": 460}
        else:
            speaker_side = "left" if speaker_side == "right" else "right"
            key = f"speaker_{speaker_side}"
    if mode == "fullscreen":
        speaker = {"left": 0, "top": 0, "width": width, "height": height}
        why = (
            "diagram card on the lower left, speaker stays full frame"
            if key == "motion_beside"
            else "diagram under the measured mouth and above the caption plate"
        )
        return mode, key, speaker, overlay, why
    motion_width = width - 56 - 20 - SPEAKER_WIDTH
    if speaker_side == "right":
        speaker = {"left": width - 28 - SPEAKER_WIDTH, "top": 0, "width": SPEAKER_WIDTH, "height": height}
        motion = {"left": 28, "top": 140, "width": motion_width, "height": caption["top"] - 48 - 140}
    else:
        speaker = {"left": 28, "top": 0, "width": SPEAKER_WIDTH, "height": height}
        motion = {"left": 28 + SPEAKER_WIDTH + 20, "top": 140, "width": motion_width, "height": caption["top"] - 48 - 140}
    return mode, key, speaker, motion, "speaker column stays larger than the diagram; cinematic plate fills the other side"


def _swap_media(scene: dict, intent: str) -> str | None:
    bg = scene.get("background") or {}
    asset = str(bg.get("assetId") or "")
    banned = _BANNED.get(intent) or ()
    if not asset or not any(token in asset.lower() for token in banned):
        return None
    replacement = _MEDIA.get(intent)
    if not replacement or replacement[0] == asset:
        return None
    scene["background"] = {
        **bg,
        "assetId": replacement[0],
        "file": replacement[1],
        "staged": None,
    }
    return replacement[0]


def _enter_frame(scene_span: tuple[float, float], evidence: dict) -> int:
    stamp = (evidence or {}).get("sourceTimestamp") or []
    if len(stamp) < 2:
        return 0
    start = float(stamp[0])
    scene_start = scene_span[0]
    if start <= scene_start:
        return 0
    return max(0, int(round((start - scene_start) * FPS)))


def apply_scene_composer(
    plan: dict,
    transcript: list | None = None,
    *,
    locale: str | None = None,
    source: Path | None = None,
    geometry: dict | None = None,
) -> dict:
    out = dict(plan)
    if not enabled():
        out["sceneComposerV16Enabled"] = False
        return out
    locale = locale or out.get("language") or "en-US"
    rows = []
    for row in transcript or out.get("transcript") or []:
        if hasattr(row, "model_dump"):
            row = row.model_dump()
        if isinstance(row, dict):
            rows.append(row)
    spans = _windows(out, rows)
    measured = geometry
    if measured is None and source and Path(source).is_file() and rows:
        mid = rows[len(rows) // 2]
        try:
            when = (float(mid.get("start") or 0) + float(mid.get("end") or 0)) / 2
        except (TypeError, ValueError):
            when = 1.0
        measured = measure_speaker(Path(source), when)
    face = (measured or {}).get("face")
    if not face:
        # Recorded as unmeasured. Layout still refuses the tiny PIP, but the
        # explanation says the face box was not measured on this render.
        face = {"left": 250, "top": 220, "width": 580, "height": 640}
        method = "unmeasured_center"
    else:
        method = (measured or {}).get("method") or "provided"
    scenes = []
    recent: list[str] = []
    usage = []
    for index, scene in enumerate(out.get("scenes") or []):
        scene = dict(scene)
        payload = scene.get("semanticMotionV14")
        if not isinstance(payload, dict) or not payload.get("componentId"):
            speaker = scene.get("speaker") or {}
            framing = str(speaker.get("framing") or "")
            layout_name = str(speaker.get("layout") or "")
            pip = framing == "pip" or "with_media" in layout_name or scene.get("sceneId") == "proof"
            if pip:
                scene["sceneComposition"] = {
                    "layout": "speaker_fullscreen",
                    "speakerPresentation": "fullscreen",
                    "motionComponent": None,
                    "mediaAsset": (scene.get("background") or {}).get("assetId"),
                    "captionRegion": caption_rect("", locale),
                    "speakerRegion": {"left": 0, "top": 0, "width": CANVAS[0], "height": CANVAS[1]},
                    "animationTiming": None,
                    "selectionExplanation": "speaker stays full frame so the caption is not painted over a small window",
                    "speakerGeometry": {"method": method, "face": face},
                }
                usage.append({"sceneId": scene.get("sceneId"), "layout": "speaker_fullscreen", "motionComponent": None, "mediaAsset": (scene.get("background") or {}).get("assetId"), "selectionExplanation": scene["sceneComposition"]["selectionExplanation"]})
            scenes.append(scene)
            continue
        span = spans[index] if index < len(spans) else (0.0, 0.0)
        quote = ""
        for row in rows:
            try:
                seg_start = float(row.get("start") or 0)
                seg_end = float(row.get("end") or 0)
            except (TypeError, ValueError):
                continue
            if span[0] <= (seg_start + seg_end) / 2 < span[1] or index == len(spans) - 1:
                quote = str(row.get("en") or row.get("text") or row.get("original") or "")
                if span[0] <= (seg_start + seg_end) / 2 < span[1]:
                    break
        evidence_quote = str((payload.get("evidence") or {}).get("sourceQuote") or quote)
        cap = caption_rect(evidence_quote or quote, locale)
        mode, key, speaker, motion, why = _choose(face, cap, recent)
        if not _safe(mode, speaker, motion, face, cap):
            mode, key, speaker, motion, why = _choose(face, cap, recent, avoid=key)
        recent.append(key)
        intent = str(payload.get("visualIntent") or "")
        swapped = _swap_media(scene, intent)
        payload = dict(payload)
        payload["speakerMode"] = mode
        payload["motionRect"] = motion
        payload["speakerRect"] = speaker
        payload["faceRect"] = face
        payload["captionRect"] = cap
        payload["columnScrim"] = True
        payload["enterFrame"] = _enter_frame(span, payload.get("evidence") or {})
        payload["layout"] = "overlay" if mode == "fullscreen" else "speaker_visual"
        payload["mediaSide"] = "left" if key.endswith("right") else "right"
        scene["semanticMotionV14"] = payload
        composition = {
            "layout": key,
            "motionComponent": payload.get("componentId"),
            "mediaAsset": (scene.get("background") or {}).get("assetId"),
            "captionRegion": cap,
            "speakerRegion": speaker,
            "animationTiming": {
                "enterFrame": payload["enterFrame"],
                "sourceTimestamp": (payload.get("evidence") or {}).get("sourceTimestamp"),
            },
            "selectionExplanation": f"{why}. face={method}." + (f" media swapped to {swapped}." if swapped else ""),
            "speakerGeometry": {"method": method, "face": face},
        }
        scene["sceneComposition"] = composition
        usage.append({"sceneId": scene.get("sceneId"), **{k: composition[k] for k in ("layout", "motionComponent", "mediaAsset", "selectionExplanation")}})
        scenes.append(scene)
    out["scenes"] = scenes
    out["sceneComposerV16Enabled"] = True
    out["sceneComposerV16Usage"] = usage
    out["sceneComposerV16Version"] = "v16.0"
    return out
