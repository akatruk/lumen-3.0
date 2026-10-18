"""Search ranking for Cinematic Env Factory V6 vs V5 abstract plates."""
from __future__ import annotations

import json
from pathlib import Path

from media.library.search import search_assets


def _tiny_manifest(tmp_path: Path) -> Path:
    assets = [
        {
            "id": "pmv5_bg_teal_depth",
            "type": "motion",
            "category": "backgrounds",
            "tags": ["cinematic", "plate", "teal_depth", "v5", "background"],
            "file": "remotion://premium-media-v5/pmv5_bg_teal_depth",
            "qualityScore": 0.82,
            "visualFamily": "deterministic_motion",
            "status": "needs_review",
            "batch": "premium-media-factory-v5-batch1",
            "sceneRoles": ["background", "hero"],
        },
        {
            "id": "cev6_i2v_biz_meeting_002",
            "type": "video",
            "category": "backgrounds",
            "tags": [
                "premium",
                "business",
                "meeting",
                "consultation",
                "office",
                "cinematic",
                "background",
                "video",
            ],
            "tags_ru": ["премиум", "бизнес", "встреча", "фон"],
            "tags_zh": ["高端", "商务", "会议", "背景"],
            "file": "motion/cinematic-env-v6/clips/cev6_i2v_biz_meeting_002.mp4",
            "qualityScore": 0.9,
            "visualFamily": "cinematic_environment",
            "status": "approved",
            "batch": "cinematic-env-v6-batch1",
            "sceneRoles": ["background", "hero"],
            "matchMode": "situational",
            "situations": ["business", "cinematic_environment", "premium_background"],
        },
        {
            "id": "cev6_i2v_city_skyline_001",
            "type": "video",
            "category": "backgrounds",
            "tags": [
                "premium",
                "city",
                "skyline",
                "financial",
                "district",
                "cinematic",
                "background",
            ],
            "file": "motion/cinematic-env-v6/clips/cev6_i2v_city_skyline_001.mp4",
            "qualityScore": 0.9,
            "visualFamily": "cinematic_environment",
            "status": "approved",
            "batch": "cinematic-env-v6-batch1",
            "sceneRoles": ["background", "hero"],
            "situations": ["international", "cinematic_environment"],
        },
        {
            "id": "cev6_re_condo_001",
            "type": "image",
            "category": "backgrounds",
            "tags": [
                "premium",
                "real estate",
                "condominium",
                "apartment",
                "interior",
                "cinematic",
                "background",
            ],
            "file": "motion/cinematic-env-v6/stills/cev6_re_condo_001.png",
            "qualityScore": 0.88,
            "visualFamily": "cinematic_environment",
            "status": "approved",
            "batch": "cinematic-env-v6-batch1",
            "sceneRoles": ["background", "hero"],
        },
    ]
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({"assets": assets}), encoding="utf-8")
    return path


def test_business_meeting_prefers_v6_over_v5_abstract(tmp_path):
    path = _tiny_manifest(tmp_path)
    hits = search_assets(
        "premium business meeting background",
        limit=3,
        path=path,
        preferred_scene_role="background",
        include_hidden=True,
    )
    ids = [h["id"] for h in hits]
    assert "cev6_i2v_biz_meeting_002" in ids
    assert ids[0].startswith("cev6_")
    assert "pmv5_bg_teal_depth" not in ids[:1]


def test_skyline_and_condo_queries_multilingual(tmp_path):
    path = _tiny_manifest(tmp_path)
    en = search_assets("financial district skyline", limit=2, path=path, include_hidden=True)
    ru = search_assets("скайлайн финансового района", limit=2, path=path, include_hidden=True)
    zh = search_assets("金融区天际线", limit=2, path=path, include_hidden=True)
    assert any(h["id"] == "cev6_i2v_city_skyline_001" for h in en)
    assert any(h["id"] == "cev6_i2v_city_skyline_001" for h in ru)
    assert any(h["id"] == "cev6_i2v_city_skyline_001" for h in zh)
    condo = search_assets("modern condominium interior", limit=2, path=path, include_hidden=True)
    assert any(h["id"] == "cev6_re_condo_001" for h in condo)


def test_planned_status_held_from_default_search(tmp_path):
    path = tmp_path / "manifest.json"
    path.write_text(
        json.dumps(
            {
                "assets": [
                    {
                        "id": "cev6_planned_only",
                        "type": "image",
                        "tags": ["premium", "business", "meeting", "background"],
                        "file": "motion/cinematic-env-v6/stills/missing.png",
                        "qualityScore": 0.9,
                        "visualFamily": "cinematic_environment",
                        "status": "planned",
                        "sceneRoles": ["background"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    hits = search_assets("premium business meeting background", limit=3, path=path)
    assert hits == []
