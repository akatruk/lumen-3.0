"""Reviewed pictures for the original4 checks. Query text is not acceptance."""
import json
from pathlib import Path

from backend.director_v8 import LONG_BEATS
from backend.editorial_decision import apply_editorial_decision, relevance
from backend.remotion_engine import resolve_scene_plan
from backend.visual_review import picture_supports

QUOTE = "海报上的租金回报率是毛收益还是净收益"
ORIGINAL4 = [
    (0.0, 3.84, "买房送身份听起来是不是特别诱人"),
    (3.84, 6.68, "钱没花掉还白得个绿卡"),
    (6.68, 11.36, "甜美的陷阱往往就藏在这种占便宜的心理里"),
    (11.36, 15.76, "今天只没帮你们把移民价值和房厂价值"),
    (15.76, 18.92, "彻底路撥开来算比民白账"),
    (18.92, 21.12, "所谓的买房移民"),
    (21.12, 27.84, "房厂挂牌价里通常包含了高额的移民液水和开发商用金"),
    (27.84, 29.84, "在签字刷卡前"),
    (29.84, 33.72, "你必须理性问自己三个硬核问题"),
    (33.72, 38.84, "第一,去查当地人的真实二手房程交数据"),
    (38.84, 42.68, "这套房子真实市场价值打击折"),
    (42.68, 48.92, "第二,海报上的诸经回报率是毛售益还是扣除物业"),
    (48.92, 53.84, "管理费,控制损耗核税后的金售益"),
    (53.84, 56.72, "第三,持满法定年县后"),
    (56.72, 59.34, "當地本地人會借盤嗎?"),
    (59.34, 62.68, "還是只能賣給下一個中國買家?"),
    (62.68, 64.68, "如果為了湊門檻"),
    (64.68, 67.48, "買到偏遠地區的垃圾盤"),
    (67.48, 69.3, "未來不緊注不出"),
    (69.3, 70.22, "賣不掉"),
    (70.22, 74.08, "每年還要被搶至徵收高額持有稅"),
    (74.08, 75.3, "真想賣房"),
    (75.3, 77.48, "選核心地段資產"),
    (77.48, 79.18, "想便宜哪身份"),
    (79.18, 81.82, "考慮存款或捐贈模式"),
    (81.82, 83.02, "關注自美"),
    (83.02, 85.38, "做理智的商業決策者"),
]


def _scene(scene_id):
    return {
        "sceneId": scene_id,
        "query": "document review desk paperwork",
        "speaker": {"layout": "speaker_split_right", "framing": "split"},
        "background": {"assetId": "cev6_biz_boardroom_001", "file": "boardroom.png"},
        "foreground": {},
        "typography": {},
        "execution": {},
    }


def test_query_overlap_does_not_accept_boardroom_blank_laptop_or_rising_bar():
    assert relevance(QUOTE, QUOTE, "cev6_biz_boardroom_001") == 0
    assert picture_supports("cev6_biz_boardroom_001", QUOTE) is False
    assert picture_supports("re_inv_laptop", QUOTE) is False
    assert picture_supports("re_obj_yield", QUOTE) is False
    assert picture_supports("re_neg_rising_bar", QUOTE) is False
    assert picture_supports("re_neg_blank_laptop", QUOTE) is False
    assert picture_supports("re_neg_empty_apartment", QUOTE) is False
    assert picture_supports("re_neg_boardroom", QUOTE) is False
    assert picture_supports("re_view_empty_walk", QUOTE) is False
    assert picture_supports("re_ai_rent_window", QUOTE) is False


def test_original4_checks_keep_reviewed_pictures_and_reach_remotion_props():
    transcript = [
        {"start": start, "end": end, "zh": text, "original": text}
        for start, end, text in ORIGINAL4
    ]
    plan = {
        "scenes": [_scene(beat["id"]) for beat in LONG_BEATS],
        "beatWeights": [beat["weight"] for beat in LONG_BEATS],
        "durationSeconds": 85.5,
    }
    out = apply_editorial_decision(
        plan, transcript, locale="zh-CN", target_seconds=85.5, source_seconds=85.5, duration_mode="full",
    )
    assert out["durationContract"]["sourceSeconds"] == 85.5
    assert out["durationContract"]["targetSeconds"] == 85.5
    ids = [scene["background"]["assetId"] for scene in out["scenes"]]
    assert ids[4] == "re_mkt_comparable_masses"
    assert ids[5] == "re_rent_column_remainder"
    assert ids[6] == "re_liq_two_paths"
    assert "cev6_biz_boardroom_001" not in ids
    assert "re_inv_laptop" not in ids
    assert "re_obj_yield" not in ids
    blob = json.dumps(out, ensure_ascii=False)
    assert "泰国" not in blob
    assert "85万" not in blob
    props = resolve_scene_plan(visual_plan=out, locale="zh-CN", duration_seconds=85.5, speaker_file="speaker.mp4")
    stored = [scene["background"]["assetId"] for scene in props["scenes"]]
    assert stored[4:7] == [
        "re_mkt_comparable_masses",
        "re_rent_column_remainder",
        "re_liq_two_paths",
    ]
    assert props["scenes"][5]["background"]["visualGrounding"]["reviewed"] is True


def test_a_missing_file_is_not_selected(tmp_path, monkeypatch):
    from backend import director_v8
    library = tmp_path / "out"
    library.mkdir()
    (library / "manifest.json").write_text(json.dumps({"assets": [
        {"id": "re_rent_column_remainder", "file": "re-residency/clips/re_rent_column_remainder.mp4", "status": "active", "qualityScore": 0.9, "visualFamily": "deterministic_motion", "tags": ["gross yield", "net yield"]},
    ]}), encoding="utf-8")
    monkeypatch.setattr(director_v8, "fill_media_for_scenes", director_v8.fill_media_for_scenes)
    import backend.visual_variation as vv
    monkeypatch.setattr(vv, "LIBRARY", library)
    plan = {
        "scenes": [{
            "sceneId": "steps",
            "query": "gross yield versus net yield after unnamed costs",
            "visualRole": "gross_vs_net_asr",
            "passageQuote": "毛售益还是金售益",
            "background": {},
        }],
        "visualSeed": 1,
    }
    out = director_v8.fill_media_for_scenes(plan, seed=1)
    assert out["scenes"][0]["background"].get("assetId") in (None, "")
