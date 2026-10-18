"""Keyword search for capital cinematic V7 with intelligence off."""
from __future__ import annotations

import json
from pathlib import Path

from media.library.search import search_assets


def _manifest(tmp_path: Path) -> Path:
    path = tmp_path / "manifest.json"
    path.write_text(
        json.dumps(
            {
                "assets": [
                    {
                        "id": "pmv5_bg_teal_depth",
                        "type": "motion",
                        "category": "backgrounds",
                        "tags": ["cinematic", "background", "capital"],
                        "file": "remotion://premium-media-v5/pmv5_bg_teal_depth",
                        "qualityScore": 0.82,
                        "visualFamily": "deterministic_motion",
                        "status": "needs_review",
                        "batch": "premium-media-factory-v5-batch1",
                        "sceneRoles": ["background"],
                    },
                    {
                        "id": "cev7_i2v_cap_shareholders_004",
                        "type": "video",
                        "category": "backgrounds",
                        "tags": ["capital", "shareholder", "investment", "meeting", "cinematic", "background"],
                        "tags_ru": ["капитал", "акционер", "инвестиции", "встреча", "фон"],
                        "tags_zh": ["资本", "股东", "投资", "会议", "背景"],
                        "localized": {
                            "en-US": {"title": "shareholders", "description": "capital shareholder meeting", "terms": ["shareholder"]},
                            "ru-RU": {"title": "акционеры", "description": "встреча акционеров капитал", "terms": ["акционер"]},
                            "zh-CN": {"title": "股东", "description": "股东会议 资本", "terms": ["股东"]},
                        },
                        "file": "motion/cinematic-env-v7/clips/cev7_i2v_cap_shareholders_004.mp4",
                        "qualityScore": 0.9,
                        "visualFamily": "cinematic_environment",
                        "status": "approved",
                        "batch": "cinematic-env-v7-batch1",
                        "sceneRoles": ["background", "hero"],
                        "situations": ["capital", "business", "cinematic_environment"],
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    return path


def test_director_plate_pool_includes_one_capital_clip(tmp_path, monkeypatch):
    import backend.visual_variation as vv

    library = tmp_path / "out"
    clip_dir = library / "motion" / "cinematic-env-v7" / "clips"
    clip_dir.mkdir(parents=True)
    (clip_dir / "cev7_i2v_cap_shareholders_004.mp4").write_bytes(b"not-a-real-movie")
    (clip_dir / "cev7_i2v_fam_should_not_force.mp4").write_bytes(b"not-a-real-movie")
    (library / "manifest.json").write_text(
        json.dumps(
            {
                "assets": [
                    {
                        "id": "cev7_i2v_cap_shareholders_004",
                        "type": "video",
                        "tags": ["capital", "shareholder", "investment", "meeting", "background"],
                        "file": "motion/cinematic-env-v7/clips/cev7_i2v_cap_shareholders_004.mp4",
                        "qualityScore": 0.9,
                        "visualFamily": "cinematic_environment",
                        "status": "approved",
                        "sceneRoles": ["background"],
                        "situations": ["capital", "investment"],
                    },
                    {
                        "id": "cev7_i2v_fam_should_not_force",
                        "type": "video",
                        "tags": ["family", "packing", "relocation"],
                        "file": "motion/cinematic-env-v7/clips/cev7_i2v_fam_should_not_force.mp4",
                        "qualityScore": 0.9,
                        "visualFamily": "cinematic_environment",
                        "status": "approved",
                        "sceneRoles": ["background"],
                        "situations": ["family"],
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(vv, "LIBRARY", library)
    hits = vv._candidates(
        "capital shareholder investment meeting",
        exclude=(),
        preferred_scene_role="background",
        limit=8,
    )
    ids = [hit["id"] for hit in hits]
    assert ids == ["cev7_i2v_cap_shareholders_004"]


def test_capital_queries_three_locales(tmp_path, monkeypatch):
    monkeypatch.setenv("VISUAL_INTELLIGENCE_ENABLED", "0")
    path = _manifest(tmp_path)
    en = search_assets("capital shareholder meeting", limit=3, path=path, preferred_scene_role="background")
    ru = search_assets("акционер капитал", limit=3, path=path, locale="ru-RU")
    zh = search_assets("股东 资本", limit=3, path=path, locale="zh-CN")
    assert en and en[0]["id"] == "cev7_i2v_cap_shareholders_004"
    assert any(hit["id"] == "cev7_i2v_cap_shareholders_004" for hit in ru)
    assert any(hit["id"] == "cev7_i2v_cap_shareholders_004" for hit in zh)
