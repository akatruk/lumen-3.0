"""Refuse to quarantine / move files that are still being written."""
from __future__ import annotations

import time
from pathlib import Path


def file_snapshot(path: Path) -> tuple[int, float] | None:
    try:
        st = path.stat()
    except OSError:
        return None
    return (st.st_size, st.st_mtime)


def is_stable(
    path: Path,
    *,
    min_age_sec: float = 120.0,
    settle_sec: float = 1.5,
    now: float | None = None,
) -> tuple[bool, str]:
    """Return (ok, reason). Unstable files must not be quarantine-moved."""
    snap = file_snapshot(path)
    if snap is None:
        return False, "missing"
    size, mtime = snap
    clock = time.time() if now is None else now
    age = clock - mtime
    if age < min_age_sec:
        return False, f"mtime_age_{age:.0f}s<{min_age_sec:.0f}s"
    if settle_sec > 0:
        time.sleep(settle_sec)
        snap2 = file_snapshot(path)
        if snap2 is None:
            return False, "vanished"
        if snap2[0] != size or snap2[1] != mtime:
            return False, "size_or_mtime_changed"
    return True, "stable"


def recent_writes(root: Path, minutes: float = 30.0) -> list[str]:
    cutoff = time.time() - minutes * 60
    found = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        try:
            if path.stat().st_mtime >= cutoff:
                found.append(str(path.relative_to(root)))
        except OSError:
            continue
    return sorted(found)
