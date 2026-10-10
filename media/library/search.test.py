import unittest
from pathlib import Path

from search import normalize_query, search_assets

MANIFEST = Path(__file__).resolve().parent / "out" / "manifest.json"


class SearchTest(unittest.TestCase):
    def test_family_relocation_finds_a_relevant_picture(self):
        hits = search_assets("family planning international relocation", type="image", limit=5, path=MANIFEST)
        blob = " ".join(
            hit["id"] + " " + " ".join(hit.get("tags") or [])
            for hit in hits
        )
        self.assertIn("family", blob)
        self.assertIn("relocation", blob)
        self.assertEqual(hits[0].get("visualFamily"), "photography")

    def test_three_languages_point_at_the_same_terms(self):
        russian = normalize_query("семья покупает квартиру").lower()
        chinese = normalize_query("家庭购买公寓").lower()
        english = normalize_query("family buying an apartment").lower()
        self.assertIn("family", russian)
        self.assertIn("apartment", russian)
        self.assertIn("family", chinese)
        self.assertIn("apartment", chinese)
        self.assertIn("family", english)
        self.assertIn("apartment", english)

    def test_second_passport_is_found_in_three_languages(self):
        for query in ("second passport", "второй паспорт", "第二护照"):
            hits = search_assets(query, limit=5, path=MANIFEST)
            ids = " ".join(hit["id"] for hit in hits)
            self.assertIn("passport", ids)

    def test_immigration_domain_stays_in_the_same_manifest(self):
        hits = search_assets("relocation", domain="immigration", limit=5, path=MANIFEST)
        self.assertTrue(hits)
        self.assertTrue(all(hit["domain"] == "immigration" for hit in hits))

    def test_arrival_does_not_open_on_a_decorative_arrow(self):
        hits = search_assets("arriving in new city", limit=10, path=MANIFEST)
        self.assertTrue(hits)
        self.assertFalse(hits[0]["id"].startswith("mark_arrow"))
        self.assertIn(hits[0].get("visualFamily"), ("photography", "generative_motion"))

    def test_uncertainty_can_find_a_planning_photograph(self):
        hits = search_assets("relocation uncertainty", limit=5, path=MANIFEST)
        self.assertTrue(any("uncertainty" in (hit.get("emotion") or []) for hit in hits))

    def test_used_assets_can_be_left_out(self):
        first = search_assets("family relocation arrival", limit=1, path=MANIFEST)[0]
        again = search_assets("family relocation arrival", limit=5, path=MANIFEST, exclude_ids=[first["id"]])
        self.assertNotIn(first["id"], [hit["id"] for hit in again])

    def test_sixty_queries_stay_on_the_concept_in_three_languages(self):
        from concepts import CONCEPTS
        self.assertGreaterEqual(len(CONCEPTS), 20)
        for concept in CONCEPTS:
            tops = []
            for locale in ("en", "ru", "zh"):
                hits = search_assets(concept[locale], limit=3, locale={"en": "en-US", "ru": "ru-RU", "zh": "zh-CN"}[locale])
                self.assertTrue(hits, concept["id"] + " " + locale)
                self.assertFalse(hits[0]["id"].startswith("mark_arrow"), hits[0]["id"])
                tops.append(hits[0]["id"])
            self.assertGreaterEqual(len(set(tops)), 1)

    def test_a_recent_asset_loses_to_an_equal_alternative(self):
        first = search_assets("consultation meeting", limit=2)
        self.assertGreaterEqual(len(first), 2)
        again = search_assets("consultation meeting", limit=1, recent_ids=[first[0]["id"]])
        self.assertNotEqual(again[0]["id"], first[0]["id"])

    def test_an_unknown_phrase_does_not_dump_the_icon_set(self):
        self.assertEqual(search_assets("完全未知的符号"), [])

    def test_route_can_prefer_video_when_present(self):
        hits = search_assets("animated international route", limit=3, path=MANIFEST)
        self.assertTrue(hits)
        self.assertTrue(any("route" in hit["id"] or "global" in hit["id"] for hit in hits))


if __name__ == "__main__":
    unittest.main()
