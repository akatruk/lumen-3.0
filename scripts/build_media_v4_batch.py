"""Build JSONL plans for multilingual media library expansion V4.

Stills only. Language-neutral prompts (no baked text). Seeds start at 52000
so they do not collide with the RunPod V1 batch (51000+).
"""
from __future__ import annotations

import json
from pathlib import Path

PRESET = (
    "realistic editorial photograph, natural color, soft daylight, "
    "plain unlettered surfaces, no logos, no watermark"
)
NEG = (
    "text, letters, numbers, logo, watermark, signature, passport, "
    "signage, label, malformed hands, extra fingers, plastic skin"
)
MODEL = "stabilityai/stable-diffusion-xl-base-1.0"
CHECKPOINT = "sd_xl_base_1.0.safetensors"
PIPELINE = "StableDiffusionXLPipeline"

# Gap-first concepts from V4 audit / multilingual coverage weak hits.
PHOTOS = [
    ("immigration.citizenship_planning", "two adults at a clear oak table with a closed leather folder, quiet discussion, no paper visible, correct hands"),
    ("immigration.citizenship_planning", "a person standing by a tall window with a closed leather portfolio under one arm, city soft beyond, no signs"),
    ("immigration.second_passport", "hands holding a closed plain navy booklet with blank cover, soft desk light, no markings, no letters"),
    ("immigration.second_passport", "a closed plain navy booklet on pale oak beside a ceramic cup, no printing, shallow depth of field"),
    ("immigration.residency_application", "an advisor and a client at a bright office table, closed folder between them, natural faces, no screens"),
    ("immigration.residency_application", "hands arranging a closed leather folder and a pen on a clear table, no writing visible"),
    ("immigration.approval", "two people smiling slightly after a meeting, empty bright office, closed folder on the table, no paper"),
    ("immigration.approval", "a handshake across a clear table in soft daylight, closed leather folder beside them, no logos"),
    ("immigration.country_comparison", "two adults looking at a large blank wall map without labels, pointing gently, soft office light"),
    ("immigration.country_comparison", "hands hovering over a blank paper globe on a table, no country names, calm daylight"),
    ("relocation.remote_work", "a person working on a closed laptop lid at a sunlit desk by a window, city soft beyond, no screens on"),
    ("relocation.remote_work", "a bright home office desk with closed laptop, plant, and coffee, empty chair, no screens, no paper"),
    ("relocation.remote_work", "a digital nomad at a cafe table with closed notebook and cup, window light, no logos, no screens"),
    ("relocation.couple", "a couple standing in an empty bright apartment looking at each other thoughtfully, no paper"),
    ("relocation.couple", "a couple packing a plain suitcase on a bed, folded clothes only, natural hands, no tags"),
    ("relocation.couple", "a couple walking a tree-lined residential street toward a modern house, backs partly turned, no signs"),
    ("relocation.family_home", "a family of three in a sunlit living room with linen sofa, quiet moment, no screens, no paper"),
    ("relocation.family_home", "exterior of a modern low house among trees at golden hour, empty driveway, no signage"),
    ("relocation.family_home", "a parent and child sitting on stairs inside a bright entryway, coats on hooks, calm"),
    ("travel.city_arrival", "a traveler with a plain backpack arriving at a bright apartment entry, suitcase beside, no labels"),
    ("travel.city_arrival", "morning view from a hotel-like window over a soft city skyline, no signs, empty sill"),
    ("travel.city_arrival", "a person stepping out of a taxi silhouette into soft street light, luggage plain, no logos"),
    ("real_estate.investor_meeting", "three professionals around a clear glass table in a bright meeting room, closed notebooks, daylight"),
    ("real_estate.investor_meeting", "two investors looking out a floor-to-ceiling window over a city, conversation stance, no screens"),
    ("real_estate.property_investment", "daylight exterior of a mid-rise glass residential building among trees, realistic architecture, no signage"),
    ("real_estate.property_investment", "empty modern living room staged for sale, oak floor, tall windows, soft morning light"),
    ("real_estate.property_viewing", "a couple and an agent standing in an empty bright room gesturing toward the window, no brochures"),
    ("real_estate.property_viewing", "interior of an empty luxury condo living room with city view through glass, no people, no signs"),
    ("relocation.business", "small team of three walking through a bright empty office floor with boxes sealed plain, no printing"),
    ("immigration.global_mobility", "a traveler seated by a large airport window with a plain backpack, distant planes blurred, no signs"),
]

DETAILS = [
    ("immigration.second_passport", "close-up of a closed plain navy booklet edge and soft shadow, blank cover, no letters"),
    ("immigration.approval", "close-up of two hands completing a handshake, natural skin, soft office light"),
    ("immigration.residency_application", "close-up of a closed leather folder corner and a matte pen, no writing"),
    ("immigration.citizenship_planning", "close-up of eyeglasses resting on a closed folder, soft desk light"),
    ("immigration.country_comparison", "close-up of a blank paper globe surface with soft shadow, no labels"),
    ("relocation.remote_work", "close-up of a closed laptop edge and a ceramic cup on oak, no logos"),
    ("relocation.remote_work", "close-up of a keyboard-free desk corner with plant shadow, soft daylight"),
    ("relocation.couple", "close-up of two coffee cups side by side on a sunlit table"),
    ("relocation.couple", "close-up of hands packing a folded sweater into a suitcase, no tags"),
    ("relocation.family_home", "close-up of a front door lock and soft morning light on wood"),
    ("relocation.family_home", "close-up of linen curtain and window light inside a living room"),
    ("travel.city_arrival", "close-up of a suitcase handle and soft hotel carpet, no labels"),
    ("travel.city_arrival", "close-up of a backpack zipper and canvas texture, no logos"),
    ("real_estate.investor_meeting", "close-up of a glass table corner and two closed notebooks"),
    ("real_estate.property_investment", "close-up of a glass balcony rail and soft city bokeh, no signs"),
    ("real_estate.property_viewing", "close-up of a light switch plate and pale wall, soft shadow"),
    ("real_estate.key_handover", "close-up of a brass key lying on marble, soft reflection"),
    ("immigration.document_consultation", "close-up of a closed leather portfolio flap, empty desk beyond"),
    ("relocation.business", "close-up of a sealed plain cardboard box edge in an empty office"),
    ("immigration.global_mobility", "close-up of an airplane window frame and soft cloud blur, no text"),
]

OBJECTS = [
    ("immigration.second_passport", "one closed plain navy booklet centered on seamless warm gray, blank cover, product photograph"),
    ("immigration.approval", "one simple gold check-mark sculpture without letters, centered, seamless warm gray"),
    ("immigration.residency_application", "one closed leather portfolio centered on seamless warm gray, no markings"),
    ("immigration.citizenship_planning", "one pair of eyeglasses and a closed folder, centered, seamless warm gray"),
    ("immigration.country_comparison", "one blank paper globe centered on seamless warm gray, no country names"),
    ("relocation.remote_work", "one closed laptop centered on seamless warm gray, no logos, lid shut"),
    ("relocation.couple", "one pair of ceramic cups side by side, centered, seamless warm gray"),
    ("relocation.family_home", "one small wooden house model without window text, centered, seamless warm gray"),
    ("travel.city_arrival", "one plain taupe suitcase centered on seamless warm gray, no labels"),
    ("real_estate.investor_meeting", "one closed notebook and pen set, centered, seamless warm gray, no writing"),
    ("real_estate.property_investment", "one glass building model without signage, centered, seamless warm gray"),
    ("real_estate.property_viewing", "one empty picture frame, blank, centered, seamless warm gray"),
    ("immigration.document_consultation", "one matte fountain pen centered on seamless warm gray"),
    ("relocation.business", "one sealed plain cardboard box, centered, seamless warm gray, no printing"),
    ("immigration.global_mobility", "one compact travel pillow in neutral fabric, centered, seamless warm gray"),
]

FOREGROUNDS = [
    ("immigration.citizenship_planning", "a closed leather folder large in the left foreground, bright office soft behind, open space on the right"),
    ("immigration.second_passport", "a plain navy booklet large in the lower foreground, soft desk and window behind, space above"),
    ("immigration.approval", "two hands mid-handshake large in the foreground, bright empty office behind"),
    ("relocation.remote_work", "a closed laptop corner in the left foreground, sunlit home office behind, space on the right"),
    ("relocation.couple", "a suitcase edge in the lower foreground, bright empty apartment behind"),
    ("relocation.family_home", "a plant soft in the left foreground, bright living room behind"),
    ("travel.city_arrival", "a backpack strap in the foreground, bright entryway and window behind, no signs"),
    ("real_estate.investor_meeting", "a glass table edge in the foreground, soft meeting room beyond"),
    ("real_estate.property_viewing", "a door frame along the left edge, empty bright room beyond, open space on the right"),
    ("immigration.country_comparison", "a blank globe large in the lower foreground, soft office light behind"),
]


def plan(asset_id, kind, concept, prompt, seed, width, height):
    return {
        "id": asset_id,
        "kind": kind,
        "concept": concept,
        "prompt": f"{prompt}, {PRESET}",
        "negative_prompt": NEG,
        "seed": seed,
        "width": width,
        "height": height,
        "num_inference_steps": 30,
        "guidance_scale": 6.0,
        "dtype": "float16",
        "model": MODEL,
        "checkpoint": CHECKPOINT,
        "pipeline": PIPELINE,
    }


def build():
    rows = []
    seed = 52000
    for index, (concept, prompt) in enumerate(PHOTOS, start=31):
        rows.append(plan(f"rp_photo_{index:03d}", "photograph", concept, prompt, seed, 768, 1344))
        seed += 1
    for index, (concept, prompt) in enumerate(DETAILS, start=21):
        rows.append(plan(f"rp_detail_{index:03d}", "detail", concept, prompt, seed, 768, 1344))
        seed += 1
    for index, (concept, prompt) in enumerate(OBJECTS, start=16):
        rows.append(plan(f"rp_object_{index:03d}", "object", concept, prompt, seed, 1024, 1024))
        seed += 1
    for index, (concept, prompt) in enumerate(FOREGROUNDS, start=11):
        rows.append(plan(f"rp_fg_{index:03d}", "foreground", concept, prompt, seed, 768, 1344))
        seed += 1
    return rows


def main():
    out = Path(__file__).resolve().parent.parent / "media" / "library" / "out" / "v4-batch1.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    rows = build()
    out.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows))
    kinds = {}
    for row in rows:
        kinds[row["kind"]] = kinds.get(row["kind"], 0) + 1
    print("WROTE", out, "count", len(rows), "kinds", kinds)
    # Rough cost at ~4s/still + 2 min load on ~$0.91/hr RTX 4090
    seconds = len(rows) * 4.1 + 120
    dollars = seconds / 3600 * 0.91
    print("EST_COST_USD", round(dollars, 2), "EST_SECONDS", int(seconds))


if __name__ == "__main__":
    main()
