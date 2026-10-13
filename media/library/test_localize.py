import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import search
from localize import ensure_locales, locale_complete


class LocalizeTest(unittest.TestCase):
    def test_same_id_three_locales(self):
        asset = ensure_locales({
            "id": "business_meeting_042",
            "tags": ["business", "meeting", "investment"],
        })
        self.assertTrue(locale_complete(asset))
        self.assertEqual(asset["id"], "business_meeting_042")
        self.assertIn("встреча", asset["tags_ru"])
        self.assertIn("会议", asset["tags_zh"])
        self.assertIn("en-US", asset["localized"])
        self.assertIn("ru-RU", asset["localized"])
        self.assertIn("zh-CN", asset["localized"])

    def test_does_not_overwrite_existing_ru(self):
        asset = ensure_locales({
            "id": "kept",
            "tags": ["family"],
            "tags_ru": ["ручная метка"],
        })
        self.assertEqual(asset["tags_ru"], ["ручная метка"])

    def test_search_locale_is_not_dropped(self):
        manifest = {
            "assets": [
                {
                    "id": "biz_a",
                    "type": "image",
                    "file": "static/biz_a.png",
                    "tags": ["business", "meeting", "investment"],
                    "tags_ru": ["деловая", "встреча", "инвесторов"],
                    "tags_zh": ["投资者", "商务", "会议"],
                    "qualityScore": 0.9,
                    "status": "approved",
                    "visualFamily": "photography",
                }
            ]
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "manifest.json"
            path.write_text(json.dumps(manifest))
            saved = search._overlay_path
            search._overlay_path = lambda: Path(tmp) / "missing.json"
            try:
                for locale, query in (
                    ("en-US", "business investment meeting"),
                    ("ru-RU", "деловая встреча инвесторов"),
                    ("zh-CN", "投资者商务会议"),
                ):
                    hits = search.search_assets(query, path=path, locale=locale, limit=3)
                    self.assertEqual(hits[0]["id"], "biz_a", locale)
            finally:
                search._overlay_path = saved


if __name__ == "__main__":
    unittest.main()
