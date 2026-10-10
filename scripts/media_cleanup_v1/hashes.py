"""SHA256 + average perceptual hash (Pillow only, no imagehash dep)."""
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

from PIL import Image, ImageOps


IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff"}
VIDEO_EXTS = {".mp4", ".webm", ".mov", ".mkv", ".m4v"}
VECTOR_EXTS = {".svg"}


def sha256_file(path: Path, chunk: int = 1024 * 1024) -> str | None:
    try:
        h = hashlib.sha256()
        with path.open("rb") as fh:
            while True:
                block = fh.read(chunk)
                if not block:
                    break
                h.update(block)
        return h.hexdigest()
    except OSError:
        return None


def average_hash(image: Image.Image, hash_size: int = 16) -> str:
    gray = ImageOps.exif_transpose(image).convert("L").resize(
        (hash_size, hash_size), Image.Resampling.LANCZOS
    )
    if hasattr(gray, "get_flattened_data"):
        pixels = list(gray.get_flattened_data())
    else:
        pixels = list(gray.getdata())
    mean = sum(pixels) / len(pixels)
    bits = "".join("1" if px >= mean else "0" for px in pixels)
    # compact hex
    return f"{int(bits, 2):0{hash_size * hash_size // 4}x}"


def hamming(a: str, b: str) -> int:
    if not a or not b or len(a) != len(b):
        return 10**9
    xa, xb = int(a, 16), int(b, 16)
    return (xa ^ xb).bit_count()


def phash_image_path(path: Path, hash_size: int = 16) -> str | None:
    try:
        with Image.open(path) as im:
            return average_hash(im, hash_size=hash_size)
    except OSError:
        return None


def extract_video_frame(path: Path, dest: Path, ss: str = "0.5") -> Path | None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(
            [
                "ffmpeg", "-y", "-ss", ss, "-i", str(path),
                "-frames:v", "1", "-q:v", "3", str(dest),
            ],
            check=True,
            capture_output=True,
            timeout=60,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None
    return dest if dest.is_file() else None


def phash_asset_file(path: Path, frame_dir: Path | None = None) -> str | None:
    ext = path.suffix.lower()
    if ext in VECTOR_EXTS:
        return None
    if ext in IMAGE_EXTS:
        return phash_image_path(path)
    if ext in VIDEO_EXTS:
        if frame_dir is None:
            return None
        frame = frame_dir / f"{path.stem}_phash.jpg"
        got = extract_video_frame(path, frame)
        if not got:
            return None
        return phash_image_path(got)
    return None
