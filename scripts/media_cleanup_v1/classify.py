"""CPU quality classification: PREMIUM … UNCERTAIN."""
from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path

from PIL import Image, ImageFilter, ImageStat

from .hashes import IMAGE_EXTS, VECTOR_EXTS, VIDEO_EXTS

QUALITY_ORDER = {
    "PREMIUM": 5,
    "GOOD": 4,
    "ACCEPTABLE": 3,
    "LOW": 2,
    "LEGACY": 1,
    "UNCERTAIN": 0,
}


@dataclass
class QualityReport:
    id: str
    file: str
    quality: str
    reasons: list[str] = field(default_factory=list)
    width: int | None = None
    height: int | None = None
    bytes: int | None = None
    sharp_var: float | None = None
    duration_sec: float | None = None
    codec: str | None = None
    missing: bool = False
    kind: str = "unknown"

    def to_dict(self) -> dict:
        return asdict(self)


def _laplacian_var(image: Image.Image) -> float:
    gray = image.convert("L")
    # Pillow edge filter as a cheap sharpness proxy (CPU only).
    edges = gray.filter(ImageFilter.FIND_EDGES)
    return float(ImageStat.Stat(edges).var[0])


def _probe_video(path: Path) -> dict:
    try:
        out = subprocess.check_output(
            [
                "ffprobe", "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height,codec_name,duration,bit_rate",
                "-show_entries", "format=duration,bit_rate,size",
                "-of", "json",
                str(path),
            ],
            timeout=45,
        )
        data = json.loads(out.decode("utf-8", errors="replace"))
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return {}
    stream = (data.get("streams") or [{}])[0]
    fmt = data.get("format") or {}
    dur = stream.get("duration") or fmt.get("duration")
    try:
        duration = float(dur) if dur is not None else None
    except (TypeError, ValueError):
        duration = None
    return {
        "width": stream.get("width"),
        "height": stream.get("height"),
        "codec": stream.get("codec_name"),
        "duration": duration,
        "bit_rate": stream.get("bit_rate") or fmt.get("bit_rate"),
    }


def classify_image(path: Path, asset: dict) -> QualityReport:
    report = QualityReport(
        id=asset.get("id") or path.stem,
        file=asset.get("file") or str(path),
        quality="UNCERTAIN",
        kind="image",
    )
    try:
        st = path.stat()
        report.bytes = st.st_size
    except OSError:
        report.missing = True
        report.quality = "LEGACY"
        report.reasons.append("file_missing")
        return report

    try:
        with Image.open(path) as im:
            im = ImageOps_exif(im)
            report.width, report.height = im.size
            short = min(im.size)
            long = max(im.size)
            report.sharp_var = _laplacian_var(im)
            mean = ImageStat.Stat(im.convert("L")).mean[0]
    except OSError as exc:
        report.quality = "UNCERTAIN"
        report.reasons.append(f"decode_fail:{exc}")
        return report

    reasons = []
    source = (asset.get("source") or "").lower()
    family = (asset.get("visualFamily") or "").lower()
    category = (asset.get("category") or "").lower()

    if report.bytes is not None and report.bytes < 8_000 and path.suffix.lower() != ".svg":
        reasons.append("tiny_bytes")
    if short < 256:
        reasons.append("tiny_resolution")
    if report.sharp_var is not None and report.sharp_var < 12 and short >= 400:
        reasons.append("soft_blur")
    if mean < 8 or mean > 247:
        reasons.append("near_flat_exposure")

    # Photography / RunPod stills get stricter premium bar.
    photo_like = family == "photography" or source == "runpod" or category in {
        "people", "photographs", "real-estate", "real_estate", "immigration",
    }

    if "tiny_resolution" in reasons or "decode_fail" in "".join(reasons):
        quality = "LOW"
    elif "soft_blur" in reasons and "tiny_bytes" in reasons:
        quality = "LOW"
    elif photo_like and long >= 1280 and short >= 720 and report.sharp_var and report.sharp_var >= 40 and report.bytes and report.bytes >= 200_000:
        quality = "PREMIUM"
    elif photo_like and short >= 512 and (report.sharp_var or 0) >= 25:
        quality = "GOOD"
    elif not photo_like and short >= 512 and (report.sharp_var or 0) >= 20:
        quality = "GOOD"
    elif short >= 320 and "soft_blur" not in reasons:
        quality = "ACCEPTABLE"
    elif reasons:
        quality = "LOW"
    else:
        quality = "ACCEPTABLE"

    # Legacy heuristics: orphan remotion motion ids, rejected path, empty tags + old icons.
    file_s = str(asset.get("file") or "")
    if "rejected/" in file_s or asset.get("status") == "rejected":
        quality = "LEGACY"
        reasons.append("rejected_status_or_path")
    if asset.get("type") == "motion" and report.missing:
        quality = "LEGACY"
        reasons.append("motion_placeholder")

    report.quality = quality
    report.reasons = reasons
    return report


def ImageOps_exif(im: Image.Image) -> Image.Image:
    from PIL import ImageOps
    return ImageOps.exif_transpose(im)


def classify_vector(path: Path, asset: dict) -> QualityReport:
    report = QualityReport(
        id=asset.get("id") or path.stem,
        file=asset.get("file") or str(path),
        quality="GOOD",
        kind="vector",
    )
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
        report.bytes = path.stat().st_size
    except OSError:
        report.missing = True
        report.quality = "LEGACY"
        report.reasons.append("file_missing")
        return report
    if "<svg" not in raw.lower():
        report.quality = "UNCERTAIN"
        report.reasons.append("not_svg_markup")
        return report
    if report.bytes is not None and report.bytes < 40:
        report.quality = "LOW"
        report.reasons.append("empty_svg")
        return report
    # Deterministic line icons / decorative marks are intentional library stock.
    report.quality = "GOOD"
    report.reasons.append("vector_ok")
    return report


def classify_video(path: Path, asset: dict) -> QualityReport:
    report = QualityReport(
        id=asset.get("id") or path.stem,
        file=asset.get("file") or str(path),
        quality="UNCERTAIN",
        kind="video",
    )
    try:
        report.bytes = path.stat().st_size
    except OSError:
        report.missing = True
        report.quality = "LEGACY"
        report.reasons.append("file_missing")
        return report

    probe = _probe_video(path)
    if not probe:
        report.quality = "UNCERTAIN"
        report.reasons.append("ffprobe_fail")
        return report

    report.width = probe.get("width")
    report.height = probe.get("height")
    report.duration_sec = probe.get("duration")
    report.codec = probe.get("codec")
    reasons = []
    w, h = report.width or 0, report.height or 0
    short, long = min(w, h), max(w, h)
    if w < 2 or h < 2:
        reasons.append("no_video_stream")
        report.quality = "LOW"
        report.reasons = reasons
        return report
    if report.bytes is not None and report.bytes < 20_000:
        reasons.append("tiny_bytes")
    if report.duration_sec is not None and report.duration_sec < 0.2:
        reasons.append("too_short")
    if short >= 720 and long >= 1280 and (report.bytes or 0) >= 200_000:
        quality = "PREMIUM"
    elif short >= 480:
        quality = "GOOD"
    elif short >= 320:
        quality = "ACCEPTABLE"
    else:
        quality = "LOW"
        reasons.append("low_resolution")
    if "tiny_bytes" in reasons or "too_short" in reasons:
        quality = "LOW"
    report.quality = quality
    report.reasons = reasons
    return report


def classify_asset(library: Path, asset: dict) -> QualityReport:
    rel = asset.get("file") or ""
    path = library / rel
    if not rel:
        return QualityReport(
            id=asset.get("id") or "unknown",
            file="",
            quality="LEGACY",
            reasons=["no_file_field"],
            missing=True,
        )
    if not path.is_file():
        return QualityReport(
            id=asset.get("id") or path.stem,
            file=rel,
            quality="LEGACY",
            reasons=["file_missing"],
            missing=True,
            kind=str(asset.get("type") or "unknown"),
        )
    ext = path.suffix.lower()
    if ext in VECTOR_EXTS:
        return classify_vector(path, asset)
    if ext in VIDEO_EXTS or asset.get("type") in {"video", "motion"}:
        if ext in VIDEO_EXTS:
            return classify_video(path, asset)
        return QualityReport(
            id=asset.get("id") or path.stem,
            file=rel,
            quality="LEGACY",
            reasons=["motion_without_media"],
            missing=True,
            kind="motion",
        )
    if ext in IMAGE_EXTS:
        return classify_image(path, asset)
    return QualityReport(
        id=asset.get("id") or path.stem,
        file=rel,
        quality="UNCERTAIN",
        reasons=[f"unknown_ext:{ext}"],
        kind="unknown",
    )


def better_quality(a: str, b: str) -> str:
    return a if QUALITY_ORDER.get(a, 0) >= QUALITY_ORDER.get(b, 0) else b


def pick_best(candidates: list[dict], quality_by_id: dict[str, QualityReport]) -> str:
    """Prefer higher quality, then larger bytes, then higher qualityScore, then stable id."""
    def key(asset: dict):
        q = quality_by_id.get(asset["id"])
        qn = QUALITY_ORDER.get(q.quality if q else "UNCERTAIN", 0)
        bytes_ = (q.bytes if q and q.bytes else 0)
        qs = float(asset.get("qualityScore") or 0)
        # Prefer photography / runpod over decorative when tied.
        family_bonus = 1 if (asset.get("visualFamily") == "photography" or asset.get("source") == "runpod") else 0
        return (qn, family_bonus, bytes_, qs, asset.get("id") or "")

    ranked = sorted(candidates, key=key, reverse=True)
    return ranked[0]["id"]
