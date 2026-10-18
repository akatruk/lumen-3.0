#!/usr/bin/env python3
"""Entry point: python scripts/media_library_cleanup_v1.py audit|apply-quarantine|restore"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.media_cleanup_v1.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
