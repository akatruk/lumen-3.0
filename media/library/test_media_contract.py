import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import search
from contract import validate_asset, validate_library
from ingest import register_approved


class ContractTest(unittest.TestCase):
    def test_legacy_missing_locale_is_not_strict(self):
        errors = validate_asset({"id": "old", "file": "a.png", "type": "image"})
        self.assertEqual(errors, [])

    def test_new_asset_without_copy_is_pending(self):
        with tempfile.TemporaryDirectory() as tmp:
            overlay = Path(tmp) / "localized_overlay.json"
            import ingest
            saved = ingest.OVERLAY
            ingest.OVERLAY = overlay
            try:
                row = register_approved({"id": "bare_001", "type": "image", "file": "x.png", "tags": []})
            finally:
                ingest.OVERLAY = saved
        self.assertEqual(row["qualityStatus"], "PENDING_LOCALIZATION")
        self.assertTrue(row["contractErrors"])
        self.assertFalse(overlay.exists())

    def test_complete_asset_publishes_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            overlay = Path(tmp) / "localized_overlay.json"
            import ingest
            saved = ingest.OVERLAY
            ingest.OVERLAY = overlay
            try:
                asset = {
                    "id": "business_meeting_042",
                    "type": "image",
                    "file": "static/business_meeting_042.png",
                    "conceptId": "business.investment_meeting",
                    "tags": ["business", "meeting", "investment"],
                    "localized": {
                        "en-US": {"title": "Investment meeting", "description": "Partners discuss investment"},
                        "ru-RU": {"title": "Инвестиционная встреча", "description": "Партнёры обсуждают инвестиции"},
                        "zh-CN": {"title": "投资会议", "description": "商务人士正在讨论投资"},
                    },
                }
                first = register_approved(asset)
                second = register_approved(asset)
            finally:
                ingest.OVERLAY = saved
            self.assertEqual(first["qualityStatus"], "production_ready")
            payload = json.loads(overlay.read_text())
            self.assertEqual(len(payload["assets"]), 1)
            self.assertEqual(second["id"], "business_meeting_042")

    def test_rejected_cannot_be_production(self):
        errors = validate_asset({
            "id": "bad",
            "file": "a.png",
            "status": "rejected",
            "qualityStatus": "production_ready",
            "multilingualContract": "required",
        })
        self.assertIn("rejected_marked_production", errors)

    def test_unapproved_3d_blocked(self):
        errors = validate_asset({
            "id": "l3d_x",
            "file": "a.webm",
            "visualFamily": "premium_3d",
            "qualityStatus": "production_ready",
        })
        self.assertIn("unapproved_3d", errors)

    def test_three_locales_hit_same_id(self):
        manifest = {
            "assets": [{
                "id": "business_meeting_042",
                "type": "image",
                "file": "static/business_meeting_042.png",
                "conceptId": "business.investment_meeting",
                "tags": ["business", "meeting", "investment"],
                "qualityScore": 0.9,
                "status": "approved",
                "visualFamily": "photography",
                "localized": {
                    "en-US": {"title": "Investment meeting", "description": "discussion"},
                    "ru-RU": {"title": "Инвестиционная встреча", "description": "обсуждение"},
                    "zh-CN": {"title": "投资会议", "description": "讨论"},
                },
            }]
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "manifest.json"
            path.write_text(json.dumps(manifest))
            saved = search._overlay_path
            search._overlay_path = lambda: Path(tmp) / "none.json"
            try:
                ids = []
                for locale, query in (
                    ("en-US", "business investment meeting"),
                    ("ru-RU", "деловая встреча инвесторов"),
                    ("zh-CN", "投资者商务会议"),
                ):
                    hits = search.search_assets(query, path=path, locale=locale, limit=3)
                    self.assertTrue(hits, locale)
                    ids.append(hits[0]["id"])
            finally:
                search._overlay_path = saved
        self.assertEqual(set(ids), {"business_meeting_042"})

    def test_library_report_shape(self):
        report = validate_library([
            {"id": "a", "file": "a.png"},
            {"id": "a", "file": "b.png"},
        ])
        self.assertFalse(report["ok"])
        self.assertEqual(report["duplicateIds"], ["a"])


if __name__ == "__main__":
    unittest.main()
