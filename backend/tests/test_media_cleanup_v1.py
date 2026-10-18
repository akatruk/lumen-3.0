"""Unit tests for media cleanup V1 (no production writes, no GPU)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.media_cleanup_v1.classify import classify_asset, pick_best
from scripts.media_cleanup_v1.hashes import average_hash, hamming, sha256_file
from scripts.media_cleanup_v1.quarantine import (
    is_searchable,
    load_manifest,
    quarantine_ids,
    restore_ids,
)
from scripts.media_cleanup_v1.stability import is_stable


@pytest.fixture()
def tiny_library(tmp_path: Path):
    lib = tmp_path / "lib"
    (lib / "static").mkdir(parents=True)
    # sharp-ish checker
    img = Image.new("RGB", (1280, 720), (20, 30, 40))
    for x in range(0, 1280, 16):
        for y in range(0, 720, 16):
            if (x // 16 + y // 16) % 2 == 0:
                img.putpixel((x, y), (240, 240, 240))
    a = lib / "static" / "a.png"
    b = lib / "static" / "b.png"
    img.save(a)
    img.save(b)  # exact duplicate bytes
    # low-res soft image
    soft = Image.new("RGB", (64, 64), (128, 128, 128))
    soft.save(lib / "static" / "soft.png")
    (lib / "static" / "mark.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24"><circle r="8" cx="12" cy="12"/></svg>\n',
        encoding="utf-8",
    )
    assets = [
        {
            "id": "photo_a",
            "type": "image",
            "category": "people",
            "visualFamily": "photography",
            "source": "runpod",
            "file": "static/a.png",
            "qualityScore": 0.9,
            "tags": ["family"],
        },
        {
            "id": "photo_b",
            "type": "image",
            "category": "people",
            "visualFamily": "photography",
            "source": "runpod",
            "file": "static/b.png",
            "qualityScore": 0.8,
            "tags": ["family"],
        },
        {
            "id": "soft_x",
            "type": "image",
            "category": "details",
            "source": "generated",
            "file": "static/soft.png",
            "qualityScore": 0.2,
            "tags": ["detail"],
        },
        {
            "id": "icon_mark",
            "type": "image",
            "category": "icons",
            "source": "vector",
            "file": "static/mark.svg",
            "qualityScore": 0.9,
            "tags": ["mark"],
        },
        {
            "id": "missing_motion",
            "type": "motion",
            "category": "real-estate",
            "file": "motion/missing.mp4",
            "qualityScore": 0.5,
            "tags": ["price"],
        },
    ]
    manifest = {"version": 1, "assets": assets}
    (lib / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return lib


def test_sha_and_phash_duplicate(tiny_library: Path):
    a = tiny_library / "static" / "a.png"
    b = tiny_library / "static" / "b.png"
    assert sha256_file(a) == sha256_file(b)
    with Image.open(a) as im:
        ha = average_hash(im)
    with Image.open(b) as im:
        hb = average_hash(im)
    assert hamming(ha, hb) == 0


def test_classify_missing_is_legacy(tiny_library: Path):
    asset = json.loads((tiny_library / "manifest.json").read_text())["assets"][-1]
    q = classify_asset(tiny_library, asset)
    assert q.quality == "LEGACY"
    assert q.missing


def test_classify_vector_good(tiny_library: Path):
    asset = next(a for a in json.loads((tiny_library / "manifest.json").read_text())["assets"] if a["id"] == "icon_mark")
    q = classify_asset(tiny_library, asset)
    assert q.quality == "GOOD"


def test_pick_best_prefers_higher_score(tiny_library: Path):
    assets = json.loads((tiny_library / "manifest.json").read_text())["assets"][:2]
    reports = {a["id"]: classify_asset(tiny_library, a) for a in assets}
    assert pick_best(assets, reports) == "photo_a"


def test_quarantine_dry_metadata_preserves_id(tiny_library: Path):
    data = load_manifest(tiny_library / "manifest.json")
    result = quarantine_ids(data, ["soft_x"], reason="test")
    assert "soft_x" in result["changed"]
    asset = next(a for a in data["assets"] if a["id"] == "soft_x")
    assert asset["id"] == "soft_x"
    assert asset["status"] == "quarantined"
    assert asset["file"] == "static/soft.png"  # not moved
    restore_ids(data, ["soft_x"])
    assert asset["status"] == "active"


def test_is_searchable_hides_quarantined():
    assert is_searchable({"status": "quarantined"}) is False
    assert is_searchable({"status": "rejected"}) is False
    assert is_searchable({"status": "active"}) is True
    assert is_searchable({}) is True
    assert is_searchable({"status": "quarantined"}, include_hidden=True) is True


def test_stability_missing(tmp_path: Path):
    ok, why = is_stable(tmp_path / "nope.png", min_age_sec=0, settle_sec=0)
    assert ok is False
    assert why == "missing"


def test_search_skips_quarantined(tiny_library: Path, monkeypatch):
    # Import search from media.library with path override
    sys.path.insert(0, str(ROOT / "media" / "library"))
    import search as search_mod

    data = load_manifest(tiny_library / "manifest.json")
    quarantine_ids(data, ["photo_a"], reason="test")
    (tiny_library / "manifest.json").write_text(json.dumps(data), encoding="utf-8")

    hits = search_mod.search_assets("family", path=tiny_library / "manifest.json", limit=10)
    ids = [h["id"] for h in hits]
    assert "photo_a" not in ids
    assert "photo_b" in ids

    hits_all = search_mod.search_assets(
        "family", path=tiny_library / "manifest.json", limit=10, include_hidden=True
    )
    assert "photo_a" in [h["id"] for h in hits_all]


def test_audit_runs(tiny_library: Path):
    from scripts.media_cleanup_v1.audit import run_audit

    review = run_audit(tiny_library, phash_threshold=5)
    assert review["inventory"]["manifest_assets"] == 5
    assert review["inventory"]["files_missing"] == 1
    assert len(review["exact_duplicate_groups"]) >= 1
    assert review["dry_run"] is True
    assert review["recommended_quarantine_count"] >= 1
