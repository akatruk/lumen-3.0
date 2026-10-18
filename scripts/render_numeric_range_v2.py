"""Isolated numeric-range v2 previews.

Trims original2 15.20–23.20 and stamps range payloads in this process only.
SEMANTIC_NUMERIC_RANGE_ENABLED stays unset. Does not render a full original2 cut.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.semantic_numeric_range import classify_numeric_range, enabled

SOURCE = ROOT / "data" / "original2" / "source"
TRANSCRIPT = ROOT / "data" / "original2" / "source.transcript.json"
OUT = ROOT / "output" / "numeric-range-v2"
MOTION = ROOT / "motion"
EXPECTED_SHA = "5de8bd17e9ae75a51a804a05a441f5dd73b2814a643e8e933bdbe87ee0956efa"
OFFSET = 15.20
DURATION = 8.0
FPS = 30

VARIANTS = ("finance", "editorial", "split")
FILES = {"finance": "variant-a.mp4", "editorial": "variant-b.mp4", "split": "variant-c.mp4"}


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _frame(time: float) -> int:
    return int(round((time - OFFSET) * FPS))


def _parse_time(stderr: str) -> dict:
    real = None
    match = re.search(r"([\d.]+)\s+real", stderr)
    if match:
        real = float(match.group(1))
    rss = None
    rss_match = re.search(r"(\d+)\s+maximum resident set size", stderr)
    if rss_match:
        rss = int(rss_match.group(1))
    return {"wallSeconds": real, "peakRssBytes": rss}


def _render(variant: str, props: dict, public: Path) -> dict:
    dest = OUT / FILES[variant]
    if dest.exists():
        dest.unlink()
    remotion = MOTION / "node_modules" / ".bin" / "remotion"
    command = [
        "/usr/bin/time",
        "-l",
        str(remotion),
        "render",
        "src/index.ts",
        "NumericRangeV2Preview",
        str(dest),
        "--props",
        json.dumps(props),
        f"--public-dir={public}",
        "--concurrency=1",
    ]
    completed = subprocess.run(
        command,
        cwd=MOTION,
        capture_output=True,
        text=True,
        timeout=900,
    )
    stats = _parse_time(completed.stderr or "")
    stats["returncode"] = completed.returncode
    stats["variant"] = variant
    stats["out"] = str(dest)
    if completed.returncode != 0 or not dest.is_file() or dest.stat().st_size < 100_000:
        tail = (completed.stderr or completed.stdout or "")[-2500:]
        raise SystemExit(f"render failed for {variant}\n{tail}")
    stats["bytes"] = dest.stat().st_size
    return stats


def main() -> None:
    if enabled():
        raise SystemExit("refusing to render while SEMANTIC_NUMERIC_RANGE_ENABLED is set")
    if os.environ.get("SEMANTIC_NUMERIC_RANGE_ENABLED", "").strip() not in {"", "0"}:
        raise SystemExit("refusing to render while SEMANTIC_NUMERIC_RANGE_ENABLED is set")
    digest = _sha(SOURCE)
    if digest != EXPECTED_SHA:
        raise SystemExit(f"source sha mismatch: {digest}")
    rows = json.loads(TRANSCRIPT.read_text(encoding="utf-8"))
    by_id = {row["id"]: row for row in rows}
    for seg_id, start, end, text in (
        ("seg_006", 15.46, 20.66, "月薪差不多在1.5-2.5万泰国左右吧"),
        ("seg_007", 20.66, 22.66, "折合人民币三四千"),
    ):
        row = by_id[seg_id]
        if abs(float(row["start"]) - start) > 0.001 or abs(float(row["end"]) - end) > 0.001:
            raise SystemExit(f"timing drift on {seg_id}")
        if row["original"] != text:
            raise SystemExit(f"quote drift on {seg_id}")
    salary = classify_numeric_range(by_id["seg_006"]["original"], by_id["seg_006"], locale="zh-CN")
    amount = classify_numeric_range(by_id["seg_007"]["original"], by_id["seg_007"], locale="zh-CN")
    if not salary or not amount:
        raise SystemExit("classifier missed seg_006 or seg_007")
    if salary["range"]["unit"] != "泰国" or amount["range"]["unit"] != "人民币":
        raise SystemExit("unit was rewritten")
    if salary["range"]["lowText"] != "1.5万" or amount["range"]["highText"] != "4千":
        raise SystemExit("endpoint drift")
    OUT.mkdir(parents=True, exist_ok=True)
    public = OUT / "public"
    media = public / "director-v3"
    media.mkdir(parents=True, exist_ok=True)
    excerpt = OUT / "excerpt.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(SOURCE), "-ss", str(OFFSET), "-t", str(DURATION),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-movflags", "+faststart",
            str(excerpt),
        ],
        check=True,
    )
    staged = media / "excerpt.mp4"
    staged.write_bytes(excerpt.read_bytes())
    segments = [
        {"startFrame": 0, "endFrame": _frame(15.46), "caption": by_id["seg_005"]["original"]},
        {
            "startFrame": _frame(15.46),
            "endFrame": _frame(20.66),
            "caption": by_id["seg_006"]["original"],
            "payload": salary,
        },
        {
            "startFrame": _frame(20.66),
            "endFrame": _frame(22.66),
            "caption": by_id["seg_007"]["original"],
            "payload": amount,
        },
        {
            "startFrame": _frame(22.66),
            "endFrame": int(DURATION * FPS),
            "caption": by_id["seg_008"]["original"],
        },
    ]
    runs = []
    for variant in VARIANTS:
        props = {
            "variant": variant,
            "speakerFile": "director-v3/excerpt.mp4",
            "durationSeconds": DURATION,
            "locale": "zh-CN",
            "segments": segments,
        }
        runs.append(_render(variant, props, public))
        print(json.dumps(runs[-1]), flush=True)
    (OUT / "render-stats.json").write_text(json.dumps({"flag": False, "runs": runs}, indent=2), encoding="utf-8")
    (OUT / "payloads.json").write_text(
        json.dumps({"salary": salary, "amount": amount, "segments": segments}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
