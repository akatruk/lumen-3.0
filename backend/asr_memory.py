"""Refuse to start Qwen when the host cannot hold the measured weight."""

from __future__ import annotations

from pathlib import Path

# 2026-10-18 lumen-fix: Qwen3-ASR-1.7B bf16 peaked at 6,051,720 kB VmHWM.
MEASURED_ASR_PEAK_MB = 5908
SAFE_FREE_MB = 6200


def available_mb(meminfo: str | None = None) -> int | None:
    text = meminfo
    if text is None:
        path = Path("/proc/meminfo")
        if not path.is_file():
            return None
        text = path.read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) // 1024
    return None


def assert_can_load(available: int | None, *, minimum_mb: int = SAFE_FREE_MB) -> None:
    if available is None:
        return
    if available < minimum_mb:
        raise RuntimeError(
            f"TRANSCRIPTION_MEMORY available_mb={available} required_mb={minimum_mb} "
            f"measured_peak_mb={MEASURED_ASR_PEAK_MB}"
        )
