"""Second V4 still batch — fill remaining gaps toward +150 approved.

Seeds from 53000. Ids continue after batch1 (photo 061+, detail 041+, object 031+, fg 021+).
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
    "signage, label, malformed hands, extra fingers, plastic skin, readable map labels"
)
MODEL = "stabilityai/stable-diffusion-xl-base-1.0"
CHECKPOINT = "sd_xl_base_1.0.safetensors"
PIPELINE = "StableDiffusionXLPipeline"

PHOTOS = [
    ("immigration.citizenship_planning", "an older advisor and a younger client seated with a closed portfolio, calm office, no paper visible"),
    ("immigration.citizenship_planning", "hands resting on a closed leather folder beside eyeglasses, soft window light, empty desk"),
    ("immigration.second_passport", "a closed plain burgundy booklet on linen next to a ceramic cup, blank cover, no markings"),
    ("immigration.second_passport", "two closed plain booklets stacked on oak, navy and burgundy, blank covers, shallow depth"),
    ("immigration.residency_application", "a client signing posture over a closed folder, pen poised, advisor opposite, no writing visible"),
    ("immigration.residency_application", "waiting area chairs by a bright window in a modern office, empty, no signs"),
    ("immigration.approval", "a couple smiling lightly outside a modern glass office entrance, soft daylight, no signs"),
    ("immigration.approval", "a person walking away down a bright corridor after a meeting, closed folder in hand"),
    ("immigration.country_comparison", "blank cork board with three empty frames of different sizes, soft office light, no pins text"),
    ("immigration.country_comparison", "two adults gesturing toward a large blank whiteboard, no writing, calm discussion"),
    ("relocation.remote_work", "a man at a standing desk with closed laptop, plant, city soft through glass, no screens on"),
    ("relocation.remote_work", "a woman on a balcony with a closed notebook and coffee, distant city, no signs"),
    ("relocation.couple", "a couple measuring a wall in an empty apartment with a tape, natural hands, no paper"),
    ("relocation.couple", "a couple sitting on the floor of an empty bright room with pizza box plain, no printing"),
    ("relocation.family_home", "family of four at a kitchen island, fruit bowl, morning light, no screens"),
    ("relocation.family_home", "children shoes and adult shoes lined at a bright entry, coats on hooks"),
    ("travel.city_arrival", "taxi dropping a traveler with plain luggage at a modern building entrance at dusk, no logos"),
    ("travel.city_arrival", "hotel-like corridor with a suitcase left by a door, soft lamps, no numbers readable"),
    ("real_estate.investor_meeting", "investor pointing at a blank large screen that is off, two colleagues listening, daylight"),
    ("real_estate.investor_meeting", "rooftop terrace meeting of three people with city behind, no drinks logos"),
    ("real_estate.property_investment", "street-level view of a mid-rise residential building with trees, overcast soft light, no signage"),
    ("real_estate.property_investment", "empty loft living space with concrete and oak, tall windows, soft light"),
    ("real_estate.property_viewing", "agent opening a closet in an empty bedroom while a couple looks on, no brochures"),
    ("real_estate.property_viewing", "luxury empty kitchen with island and pendant lights, morning, no people"),
    ("relocation.business", "movers carrying a plain sealed box into a bright office, no printing on box"),
    ("relocation.business", "empty open-plan office with a few chairs stacked, soft daylight, no screens"),
    ("immigration.document_consultation", "phone consult: woman gesturing while speaking, empty desk, soft office"),
    ("immigration.global_mobility", "traveler silhouette against airport glass, planes soft beyond, no signs"),
    ("immigration.global_mobility", "passport control style corridor empty and bright, no signage, soft light"),
    ("real_estate.key_handover", "new resident turning a key in an apartment door, soft interior glow"),
]

DETAILS = [
    ("immigration.second_passport", "close-up of blank burgundy booklet spine and soft shadow"),
    ("immigration.approval", "close-up of a relieved smile mid-frame, soft bokeh office"),
    ("immigration.residency_application", "close-up of a pen tip above a closed folder, no ink marks"),
    ("immigration.citizenship_planning", "close-up of folded hands on a clear table"),
    ("immigration.country_comparison", "close-up of blank sticky notes in soft stack, no writing"),
    ("relocation.remote_work", "close-up of a coffee cup and closed notebook on a balcony rail"),
    ("relocation.couple", "close-up of two hands holding a tape measure, empty room beyond"),
    ("relocation.family_home", "close-up of children's shoes by a door, soft morning light"),
    ("travel.city_arrival", "close-up of suitcase wheels on polished stone floor"),
    ("real_estate.investor_meeting", "close-up of a wristwatch and sleeve on a glass table, no brand"),
    ("real_estate.property_investment", "close-up of building facade glass reflection, soft trees, no signs"),
    ("real_estate.property_viewing", "close-up of an open empty closet interior, soft light"),
    ("relocation.business", "close-up of packing tape on a plain cardboard box"),
    ("immigration.document_consultation", "close-up of a headset earcup without logos, soft bokeh"),
    ("immigration.global_mobility", "close-up of boarding-pass-sized blank card, completely blank"),
    ("real_estate.key_handover", "close-up of a key turning in a lock cylinder"),
    ("relocation.remote_work", "close-up of a plant leaf and laptop corner, lid closed"),
    ("immigration.approval", "close-up of two coffee cups after a meeting, soft steam"),
    ("travel.city_arrival", "close-up of a hotel keycard blank white, no printing"),
    ("real_estate.property_viewing", "close-up of a window latch and soft city bokeh"),
]

OBJECTS = [
    ("immigration.second_passport", "one closed plain burgundy booklet centered, seamless warm gray, blank"),
    ("immigration.approval", "one small gold star object without letters, centered, seamless warm gray"),
    ("immigration.residency_application", "one stamp pad closed, no ink marks visible, centered, seamless warm gray"),
    ("immigration.citizenship_planning", "one closed leather portfolio with a thin strap, centered, seamless warm gray"),
    ("immigration.country_comparison", "three blank card stands of different heights, centered, seamless warm gray"),
    ("relocation.remote_work", "one closed silver laptop angled, centered, seamless warm gray, no logos"),
    ("relocation.couple", "one measuring tape coiled, centered, seamless warm gray, no numbers readable"),
    ("relocation.family_home", "one houseplant in a ceramic pot, centered, seamless warm gray"),
    ("travel.city_arrival", "one rolling suitcase upright, centered, seamless warm gray, no labels"),
    ("real_estate.investor_meeting", "one closed tablet with black screen, centered, seamless warm gray, no logos"),
    ("real_estate.property_investment", "one miniature apartment building model, no signage, centered, seamless warm gray"),
    ("real_estate.property_viewing", "one set of empty picture frames nested, blank, centered, seamless warm gray"),
    ("relocation.business", "one sealed plain moving box with tape, centered, seamless warm gray"),
    ("immigration.document_consultation", "one simple desk lamp, centered, seamless warm gray"),
    ("immigration.global_mobility", "one pair of noise-cancelling headphones without logos, centered, seamless warm gray"),
]

FOREGROUNDS = [
    ("immigration.citizenship_planning", "eyeglasses large in the foreground, soft office conversation behind"),
    ("immigration.second_passport", "blank burgundy booklet large lower left, soft desk light behind, space right"),
    ("immigration.approval", "coffee cups large in foreground, smiling couple soft behind"),
    ("relocation.remote_work", "closed laptop large left, balcony city soft behind, space right"),
    ("relocation.couple", "tape measure large in foreground, empty apartment behind"),
    ("relocation.family_home", "shoes large in lower foreground, bright entry behind"),
    ("travel.city_arrival", "suitcase large left, modern lobby soft behind"),
    ("real_estate.investor_meeting", "glass of water large foreground, meeting soft behind, no logos"),
    ("real_estate.property_viewing", "door handle large left, empty bright room beyond"),
    ("relocation.business", "sealed box large foreground, bright office behind"),
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
    seed = 53000
    for index, (concept, prompt) in enumerate(PHOTOS, start=61):
        rows.append(plan(f"rp_photo_{index:03d}", "photograph", concept, prompt, seed, 768, 1344))
        seed += 1
    for index, (concept, prompt) in enumerate(DETAILS, start=41):
        rows.append(plan(f"rp_detail_{index:03d}", "detail", concept, prompt, seed, 768, 1344))
        seed += 1
    for index, (concept, prompt) in enumerate(OBJECTS, start=31):
        rows.append(plan(f"rp_object_{index:03d}", "object", concept, prompt, seed, 1024, 1024))
        seed += 1
    for index, (concept, prompt) in enumerate(FOREGROUNDS, start=21):
        rows.append(plan(f"rp_fg_{index:03d}", "foreground", concept, prompt, seed, 768, 1344))
        seed += 1
    return rows


def main():
    out = Path(__file__).resolve().parent.parent / "media" / "library" / "out" / "v4-batch2.jsonl"
    rows = build()
    out.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows))
    print("WROTE", out, len(rows), "EST_COST_USD", round((len(rows) * 4.1 + 30) / 3600 * 0.91, 2))


if __name__ == "__main__":
    main()
