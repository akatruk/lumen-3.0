#!/usr/bin/env python3
"""validate_media_library --multilingual

Legacy gaps print and exit 0. Strict rows (multilingualContract=required or
qualityStatus=production_ready) fail the process. Does not rewrite assets.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "media" / "library"))
from contract import validate_library  # noqa: E402
from search import load as load_assets  # noqa: E402

MANIFEST = ROOT / "media" / "library" / "out" / "manifest.json"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--multilingual", action="store_true")
    parser.add_argument("--manifest", default=str(MANIFEST))
    parser.add_argument("--report", default="")
    args = parser.parse_args()
    if not args.multilingual:
        raise SystemExit("pass --multilingual")
    assets = load_assets(args.manifest)
    result = validate_library(assets)
    text = json.dumps({
        "ok": result["ok"],
        "assets": result["assets"],
        "duplicateIds": result["duplicateIds"][:20],
        "duplicateCount": len(result["duplicateIds"]),
        "legacyViolations": result["legacyViolations"],
        "legacyLocaleGaps": result["legacyLocaleGaps"],
        "strictFailures": result["strictFailures"][:20],
        "strictFailureCount": len(result["strictFailures"]),
    }, ensure_ascii=False, indent=2)
    print(text)
    if args.report:
        Path(args.report).write_text(text + "\n")
    raise SystemExit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
