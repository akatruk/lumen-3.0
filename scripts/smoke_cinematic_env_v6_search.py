#!/usr/bin/env python3
"""Multilingual Director-style search smoke for V6 cinematic environments."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "media" / "library"))

from search import search_assets  # noqa: E402

QUERIES = [
    ("en", "premium business meeting background"),
    ("ru", "премиальный фон деловой встречи"),
    ("zh", "高端商务会议背景"),
    ("en", "modern condominium interior"),
    ("ru", "современный интерьер кондоминиума"),
    ("zh", "现代公寓室内"),
    ("en", "financial district skyline"),
    ("ru", "скайлайн финансового района"),
    ("zh", "金融区天际线"),
]


def main() -> int:
    manifest = ROOT / "media" / "library" / "out" / "manifest.json"
    rows = []
    for locale, q in QUERIES:
        hits = search_assets(q, limit=5, path=manifest, preferred_scene_role="background")
        top = [
            {
                "id": h.get("id"),
                "family": h.get("visualFamily"),
                "batch": h.get("batch"),
                "type": h.get("type"),
                "origin1Fit": h.get("origin1Fit"),
            }
            for h in hits
        ]
        v6 = [t for t in top if (t.get("batch") or "").startswith("cinematic-env-v6")]
        abstract = [t for t in top if str(t.get("id") or "").startswith("pmv5_bg_")]
        rows.append(
            {
                "locale": locale,
                "query": q,
                "top": top,
                "v6_hits": len(v6),
                "v5_abstract_in_top": [t["id"] for t in abstract],
            }
        )
        print(f"[{locale}] {q}")
        print("  top:", [t["id"] for t in top])
        print("  v6:", len(v6), "v5_abstract:", [t["id"] for t in abstract])
    out = ROOT / "output" / "cinematic-env-v6" / "search-smoke.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("wrote", out)
    # Fail if any env query returns V5 abstract as #1 when V6 exists in manifest
    assets = json.loads(manifest.read_text(encoding="utf-8")).get("assets") or []
    has_v6 = any((a.get("batch") or "") == "cinematic-env-v6-batch1" and a.get("status") == "approved" for a in assets)
    if has_v6:
        for row in rows:
            if row["top"] and str(row["top"][0]["id"]).startswith("pmv5_bg_"):
                print("FAIL: V5 abstract ranked first for", row["query"])
                return 1
    else:
        print("NOTE: no approved V6 assets yet — ranking smoke is informational")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
