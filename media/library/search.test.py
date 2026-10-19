import unittest
from pathlib import Path

from search import normalize_query, search_assets, specific_asks, specific_block

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
            self.assertTrue(hits, query)
            blob = " ".join(
                hit["id"]
                + " "
                + str(hit.get("conceptId") or "")
                + " "
                + " ".join(hit.get("tags") or [])
                + " "
                + " ".join((hit.get("description") or {}).values() if isinstance(hit.get("description"), dict) else [])
                for hit in hits
            ).lower()
            self.assertTrue(
                "passport" in blob or "second_passport" in blob,
                query + " -> " + blob,
            )

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
        hits = search_assets("animated international route", limit=10, path=MANIFEST)
        self.assertTrue(hits)
        # Photography may rank above motion; still must not open on decorative marks.
        self.assertFalse(hits[0]["id"].startswith("mark_"))
        self.assertFalse(hits[0].get("category") == "decorative")
        self.assertTrue(
            any("route" in hit["id"] or "global" in hit["id"] for hit in hits),
            [h["id"] for h in hits],
        )

    def test_runpod_still_is_found_in_three_languages(self):
        import json
        import tempfile

        from runpod_assets import row_for

        plan = {
            "id": "rp_photo_001",
            "kind": "photograph",
            "concept": "relocation.family_planning",
            "prompt": "a family at a clear oak table",
            "negative_prompt": "text",
            "seed": 51000,
            "width": 768,
            "height": 1344,
            "num_inference_steps": 30,
            "guidance_scale": 6.0,
            "model": "stabilityai/stable-diffusion-xl-base-1.0",
            "checkpoint": "sd_xl_base_1.0.safetensors",
            "pipeline": "StableDiffusionXLPipeline",
            "dtype": "float16",
        }
        row = row_for(plan, "static/runpod/photographs/rp_photo_001.png", "abc", 4.0)
        self.assertEqual(row["generation"]["provider"], "runpod")
        self.assertNotIn("comfy", json.dumps(row).lower())
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "manifest.json"
            path.write_text(json.dumps({"version": 1, "assets": [row]}))
            for query in (
                "family planning international relocation",
                "семья планирует международный переезд",
                "家庭计划移居国外",
            ):
                hits = search_assets(query, type="image", limit=3, path=path)
                self.assertEqual([hit["id"] for hit in hits], ["rp_photo_001"], query)


class SpecificInstrumentTest(unittest.TestCase):
    def test_a_building_is_not_a_sale_contract(self):
        house = {"id": "l3d_apartment_building__reveal", "visualFamily": "premium_3d", "tags": ["property"]}
        sheet = {"id": "ev_property_sale_contract", "visualAdmits": ["property_sale_contract"]}
        self.assertEqual(specific_block("房产买卖合同", house), "NO_MATCH:property_sale_contract")
        self.assertIsNone(specific_block("房产买卖合同", sheet))
        self.assertIsNone(specific_block("family relocation", house))

    def test_real_library_does_not_substitute_these_instruments(self):
        forbidden = ("l3d_", "re_ext_", "re_int_", "people_", "cev6_", "icon_coins", "pm_hero_", "document_approval", "pm_concept_check", "pm_scene_approval", "re_agent")
        queries = ("房产买卖合同", "股权转让协议", "银行完税流水", "证据协议", "property sale contract", "equity transfer agreement", "bank ledger")
        for query in queries:
            hits = search_assets(query, limit=8, path=MANIFEST)
            ids = [hit["id"] for hit in hits]
            for asset_id in ids:
                self.assertFalse(any(asset_id.startswith(prefix) or prefix in asset_id for prefix in forbidden), query + " -> " + asset_id)
            for hit in hits:
                admits = set(hit.get("visualAdmits") or [])
                for ask in specific_asks(query):
                    self.assertIn(ask, admits, query + " -> " + hit["id"])


if __name__ == "__main__":
    unittest.main()
