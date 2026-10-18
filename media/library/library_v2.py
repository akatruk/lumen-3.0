"""Director metadata and the visual gaps the current library does not already cover.

Photographs that already exist are annotated, not regenerated.
"""
import json
from pathlib import Path

GOLD = "#E0B15A"
BLUE = "#7EB6C9"
NAVY = "#0E1A2B"
ROOT = Path(__file__).resolve().parent / "out"
CREATED = "2026-10-09"

METAPHORS = {
    "choice-split": '<path d="M540 1500 C 540 1100, 540 900, 540 720"/><path d="M540 720 C 420 560, 280 420, 220 280"/><path d="M540 720 C 540 480, 540 360, 540 240"/><path d="M540 720 C 680 540, 820 400, 880 260"/><circle cx="220" cy="250" r="18"/><circle cx="540" cy="210" r="18"/><circle cx="880" cy="230" r="18"/>',
    "door-city": '<path d="M360 1500 V520 h360 v980"/><path d="M720 520 C 860 520, 900 640, 900 760 V1500"/><path d="M860 900 h80 v420 h-80 M900 700 h40 v80"/><circle cx="470" cy="980" r="10" fill="#E0B15A" stroke="none"/>',
    "two-homes": '<path d="M180 980 L340 820 L500 980 V1280 H180 Z"/><path d="M620 860 L820 680 L1020 860 V1280 H620 Z"/><path d="M500 1100 C 560 980, 580 980, 620 1040" stroke-dasharray="14 12"/>',
    "person-cities": '<circle cx="540" cy="1280" r="36"/><path d="M500 1360 C 500 1480, 580 1500, 580 1500"/><path d="M540 1240 C 360 900, 240 700, 200 420"/><path d="M540 1240 C 540 800, 540 500, 540 360"/><path d="M540 1240 C 740 900, 860 640, 900 400"/><circle cx="200" cy="380" r="16"/><circle cx="540" cy="320" r="16"/><circle cx="900" cy="360" r="16"/>',
    "passport-route": '<rect x="220" y="980" width="280" height="400" rx="16"/><circle cx="360" cy="1160" r="48"/><path d="M520 1100 C 700 860, 760 640, 860 420"/><circle cx="870" cy="390" r="18"/>',
    "residency-stack": '<path d="M250 1100 L430 940 L610 1100 V1400 H250 Z"/><rect x="680" y="980" width="260" height="180" rx="12"/><circle cx="760" cy="1070" r="28"/><path d="M610 1200 H680"/>',
    "approval-flow": '<rect x="180" y="1000" width="220" height="300" rx="12"/><rect x="430" y="1040" width="200" height="260" rx="12"/><path d="M640 1160 H760"/><circle cx="860" cy="1160" r="70"/><path d="M820 1160 l28 30 54-64"/>',
    "risk-routes": '<path d="M200 500 C 400 700, 500 900, 540 1500"/><path d="M880 500 C 700 760, 620 980, 560 1500" opacity="0.35"/><path d="M760 620 l140 40 -20 80"/>',
    "planning-path": '<circle cx="220" cy="1400" r="16"/><circle cx="420" cy="1100" r="16"/><circle cx="640" cy="860" r="16"/><circle cx="860" cy="480" r="22"/><path d="M236 1384 C 360 1240, 400 1180, 404 1116"/><path d="M436 1084 C 520 1000, 560 940, 624 876"/><path d="M656 844 C 740 700, 780 600, 844 500"/>',
    "investment-path": '<circle cx="260" cy="1200" r="70"/><circle cx="260" cy="1200" r="28"/><path d="M360 1140 C 520 1000, 600 900, 700 760"/><path d="M760 980 L920 820 L1080 980 V1240 H760 Z"/>',
    "family-future": '<circle cx="300" cy="1100" r="28"/><circle cx="390" cy="1100" r="28"/><circle cx="346" cy="1200" r="20"/><path d="M430 1140 C 620 900, 740 760, 860 560"/><path d="M760 780 L900 640 L1040 780 V1100 H760 Z"/>',
    "time-journey": '<rect x="180" y="1080" width="300" height="240" rx="16"/><path d="M180 1160 h300 M250 1080 v-40 M410 1080 v-40"/><path d="M500 1200 C 680 1000, 760 800, 900 520"/><circle cx="910" cy="490" r="18"/>',
    "cost-converge": '<circle cx="240" cy="480" r="16"/><circle cx="540" cy="400" r="16"/><circle cx="860" cy="520" r="16"/><circle cx="300" cy="1500" r="16"/><path d="M250 500 C 400 800, 460 1000, 540 1200"/><path d="M540 420 C 540 700, 540 900, 540 1200"/><path d="M850 540 C 740 800, 660 1000, 560 1200"/><path d="M310 1480 C 400 1400, 460 1320, 520 1240"/><circle cx="540" cy="1220" r="26"/>',
    "old-new": '<path d="M160 1000 L320 860 L480 1000 V1320 H160 Z" opacity="0.45"/><path d="M600 860 L820 660 L1040 860 V1320 H600 Z"/><path d="M480 1120 H600"/>',
    "opportunity": '<path d="M280 1500 V640 h280 v860"/><path d="M560 640 C 760 640, 860 820, 860 980"/><path d="M760 700 h220 v360 h-80"/>',
    "decision-paths": '<circle cx="220" cy="960" r="20"/><path d="M240 960 H420"/><path d="M420 960 C 560 960, 620 700, 780 560"/><path d="M420 960 C 620 960, 700 1200, 860 1360"/><circle cx="800" cy="540" r="16"/><circle cx="880" cy="1380" r="16"/>',
    "portfolio": '<rect x="180" y="980" width="200" height="280"/><rect x="440" y="860" width="200" height="400"/><rect x="700" y="1040" width="200" height="220"/><path d="M280 900 C 500 760, 700 760, 900 860"/>',
    "mobility-net": '<circle cx="540" cy="960" r="80"/><circle cx="260" cy="560" r="18"/><circle cx="820" cy="520" r="18"/><circle cx="240" cy="1320" r="18"/><circle cx="860" cy="1280" r="18"/><path d="M480 900 L270 580 M600 900 L810 540 M480 1020 L250 1300 M610 1020 L850 1260"/>',
    "origin-destination": '<circle cx="240" cy="1200" r="22"/><circle cx="860" cy="520" r="26"/><path d="M262 1180 C 460 900, 640 760, 838 546"/>',
    "citizenship-path": '<rect x="200" y="1040" width="240" height="340" rx="14"/><rect x="470" y="1080" width="220" height="300" rx="14"/><path d="M700 1200 C 800 1000, 840 860, 900 640"/><path d="M820 820 L940 700 L1060 820 V1080 H820 Z"/>',
}

FOREGROUNDS = {
    "passport": '<rect x="80" y="1180" width="420" height="620" rx="28"/><circle cx="290" cy="1460" r="90"/>',
    "suitcase": '<rect x="120" y="1120" width="520" height="640" rx="28"/><path d="M250 1120 v-80 h260 v80"/>',
    "keys": '<circle cx="220" cy="1360" r="70"/><path d="M280 1360 H860 M700 1360 v80 M800 1360 v60"/>',
    "document": '<path d="M160 1100 h360 l80 80 v620 H160 z"/><path d="M520 1100 v80 h80"/>',
    "plane": '<path d="M80 1500 H760 l180-40 v80 L760 1500"/><path d="M280 1500 l-80 160 h120 l80-160 M260 1500 l-40-120 h90"/>',
    "pin": '<path d="M360 1680 C 360 1400, 640 1400, 640 1680"/><path d="M500 1680 C 180 1200, 220 700, 500 420 C 780 700, 820 1200, 500 1680"/><circle cx="500" cy="980" r="70"/>',
    "building": '<path d="M160 1700 V700 h240 V980 h180 V520 h260 V1700"/>',
    "city": '<path d="M40 1700 V1100 h120 V900 h160 V1200 h80 V700 h200 V1000 h140 V800 h180 V1700"/>',
    "globe": '<circle cx="360" cy="1460" r="280"/><ellipse cx="360" cy="1460" rx="120" ry="280"/><path d="M80 1460 h560"/>',
    "box": '<path d="M120 1280 h640 v420 H120 z"/><path d="M120 1280 l80-120 h480 l80 120 M440 1160 v540"/>',
    "folder": '<path d="M80 1240 h280 l50-70 h430 v560 H80 z"/>',
    "phone": '<rect x="160" y="1080" width="280" height="560" rx="36"/>',
    "calendar": '<rect x="120" y="1120" width="560" height="480" rx="24"/><path d="M120 1260 h560 M240 1120 v-60 M520 1120 v-60"/>',
    "shield": '<path d="M500 1040 L860 1160 V1460 C 860 1680, 680 1820, 500 1900 C 320 1820, 140 1680, 140 1460 V1160 Z"/>',
    "house": '<path d="M80 1400 L360 1120 L640 1400"/><path d="M160 1360 V1760 h400 v-400"/>',
    "card": '<rect x="80" y="1280" width="720" height="420" rx="28"/><circle cx="220" cy="1490" r="48"/>',
}

TRANSITIONS = {
    "route": '<path d="M-20 960 C 280 720, 620 1200, 1100 860" stroke-width="18"/>',
    "door": '<path d="M760 80 V1840" stroke-width="16"/><path d="M760 200 C 980 280, 1040 600, 1000 960"/>',
    "city": '<path d="M0 1200 V700 h80 V500 h120 V860 h60 V420 h160 V760 h90 V360 h140 V1200"/>',
    "suitcase": '<rect x="820" y="700" width="280" height="520" rx="20"/><path d="M900 700 v-50 h140 v50"/>',
    "pin": '<circle cx="540" cy="960" r="80"/><circle cx="540" cy="960" r="220" opacity="0.45"/><circle cx="540" cy="960" r="400" opacity="0.25"/>',
    "passport": '<rect x="760" y="360" width="360" height="1200" rx="24"/><circle cx="940" cy="900" r="80"/>',
    "document": '<path d="M800 200 h200 l80 80 V1720 H800 z"/>',
    "plane": '<path d="M-40 1100 H980 l140-30 v50 H-40"/>',
    "building": '<path d="M860 1920 V200 h220 V700 h140 V360 h180 V1920"/>',
    "gold": '<path d="M0 1000 H1080" stroke-width="22"/>',
}

LAYERS = {
    "relocation-city": {
        "background": f'<rect width="1080" height="1920" fill="{NAVY}"/>',
        "skyline": '<path d="M40 1500 V980 h100 V760 h140 V1100 h80 V640 h180 V980 h120 V820 h160 V1500" fill="none"/>',
        "traveler": '<circle cx="780" cy="1180" r="36"/><path d="M744 1240 c20 80 40 140 36 220 M816 1240 c-10 80-20 140-16 220 M760 1280 h80"/>',
        "suitcase": '<rect x="860" y="1360" width="120" height="160" rx="10"/><path d="M890 1360 v-24 h60 v24"/>',
    },
    "apartment-arrival": {
        "background": '<rect width="1080" height="1920" fill="#101820"/>',
        "room": '<path d="M120 420 h840 v1100 H120 z"/><path d="M120 980 h840"/>',
        "door": '<path d="M700 560 h220 v960 H700 z"/>',
        "luggage": '<rect x="220" y="1180" width="180" height="240" rx="12"/><path d="M260 1180 v-30 h100 v30"/>',
    },
    "document-desk": {
        "background": '<rect width="1080" height="1920" fill="#122033"/>',
        "papers": '<rect x="180" y="980" width="420" height="560" rx="12"/><rect x="260" y="900" width="420" height="560" rx="12" opacity="0.7"/>',
        "pen": '<path d="M760 1500 l180-420" stroke-width="10"/>',
    },
    "passport-journey": {
        "background": f'<rect width="1080" height="1920" fill="{NAVY}"/>',
        "arc": '<path d="M160 1400 C 400 700, 700 700, 940 420"/>',
        "booklet": '<rect x="140" y="1180" width="220" height="320" rx="14"/><circle cx="250" cy="1320" r="36"/>',
        "pin": '<circle cx="940" cy="400" r="22"/>',
    },
    "property-balcony": {
        "background": '<rect width="1080" height="1920" fill="#0E1A2B"/>',
        "skyline": '<g opacity="0.45"><path d="M80 1100 V700 h80 V860 h100 V640 h140 V900 h90 V760 h120 V1100"/></g>',
        "rail": '<path d="M80 1280 h920 M140 1280 v120 M860 1280 v120 M80 1400 h920"/>',
    },
    "choice-paths": {
        "background": f'<rect width="1080" height="1920" fill="#081018"/>',
        "paths": '<path d="M540 1600 C 540 1100, 280 800, 220 420"/><path d="M540 1600 C 540 1000, 540 700, 540 380"/><path d="M540 1600 C 540 1100, 800 800, 880 440"/>',
        "pins": '<circle cx="220" cy="390" r="16"/><circle cx="540" cy="350" r="16"/><circle cx="880" cy="410" r="16"/>',
    },
}


def svg_plate(body, width=1080, height=1920):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
        f'fill="none" stroke="{GOLD}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round">{body}</svg>'
    )


def annotate(asset):
    if asset.get("sceneRoles"):
        return False
    tags = set(asset.get("tags") or [])
    family = asset.get("visualFamily") or ""
    category = asset.get("category") or ""
    ident = asset.get("id") or ""
    roles = ["supporting_broll"]
    energy = "low"
    emotion = []
    motion = "medium"
    treatments = ["slow_push"]
    if category == "backgrounds" or family == "background":
        roles, energy, motion = ["background"], "low", "low"
        treatments = ["behind_type"]
    elif category == "decorative":
        roles, energy, motion = ["transition"], "medium", "high"
        treatments = ["foreground_wipe", "kinetic_overlay"]
    elif family == "generative_motion":
        roles, energy, motion = ["supporting_broll", "hero"], "medium", "high"
        treatments = ["cutaway"]
    elif family == "deterministic_motion":
        roles, energy, motion = ["explanation", "process"], "medium", "high"
        treatments = ["kinetic_overlay"]
    elif family == "photography":
        roles, energy, motion = ["hero", "supporting_broll"], "medium", "medium"
        treatments = ["slow_push", "speaker_split"]
        if tags & {"consultation", "advice", "advisor"}:
            roles, energy, emotion = ["explanation", "emotional"], "low", ["trust", "focus"]
        elif tags & {"packing", "luggage", "suitcase"}:
            roles, energy, emotion = ["supporting_broll", "insert", "emotional"], "medium", ["anticipation"]
        elif tags & {"arrival"} or "door" in ident:
            roles, emotion = ["hook", "emotional", "hero"], ["hope", "relief"]
        elif "viewing" in tags:
            roles, emotion = ["proof", "hero"], ["curiosity", "focus"]
        elif tags & {"city", "skyline"}:
            roles, energy, emotion = ["hook", "hero"], "high", ["curiosity", "hope"]
        elif tags & {"planning", "couple", "buyer"}:
            emotion = ["curiosity", "uncertainty", "focus"]
    elif category in ("icons", "immigration", "real_estate", "concepts") or family == "line":
        roles, energy, motion = ["explanation", "insert"], "low", "high"
        treatments = ["kinetic_overlay", "scale"]
        if tags & {"approval", "success", "certificate"}:
            roles, emotion = ["proof", "cta"], ["success", "confidence"]
    elif "document" in tags or category == "documents":
        roles, emotion, motion = ["process", "proof", "insert"], ["focus"], "high"
        treatments = ["parallax", "scale"]
    if tags & {"approval", "success"} and "success" not in emotion:
        emotion = emotion + ["success", "confidence"]
    asset["sceneRoles"] = roles
    asset["energy"] = energy
    asset["emotion"] = emotion
    asset["motionPotential"] = motion
    asset["recommendedTreatments"] = treatments
    return True


def row(ident, file, tags, description, roles, composition, areas, energy, emotion, motion, treatments, domain, family, category, action, subjects):
    return {
        "id": ident,
        "domain": domain,
        "type": "image",
        "category": category,
        "visualFamily": family,
        "sceneRoles": roles,
        "tags": tags,
        "subjects": subjects,
        "action": action,
        "environment": "graphic",
        "region": "generic",
        "description": description,
        "file": file,
        "aspectRatio": "9:16",
        "composition": composition,
        "textSafeAreas": areas,
        "background": "transparent",
        "mood": ["premium", "restrained"],
        "emotion": emotion,
        "energy": energy,
        "motionPotential": motion,
        "recommendedTreatments": treatments,
        "qualityScore": 0.9,
        "textSafe": True,
        "source": "vector",
        "provider": "vector",
        "model": "svg",
        "prompt": description,
        "negativePrompt": "text, letters, logos, watermarks, government emblems",
        "seed": None,
        "created": CREATED,
    }


def build_new():
    made = []
    folder = ROOT / "static" / "v2"
    folder.mkdir(parents=True, exist_ok=True)
    for name, body in METAPHORS.items():
        file = f"static/v2/meta_{name}.svg"
        (ROOT / file).write_text(svg_plate(body))
        made.append(row(
            f"v2_meta_{name}", file,
            ["metaphor", "immigration", "relocation", name.replace("-", "_")],
            f"Conceptual {name.replace('-', ' ')}. No legal claim and no writing.",
            ["hero", "explanation"], "center", ["top", "left"],
            "medium", ["curiosity", "focus"], "high",
            ["parallax", "kinetic_overlay"], "immigration", "line", "metaphor",
            "connects", [name.replace("-", "_")],
        ))
    for name, body in FOREGROUNDS.items():
        file = f"static/v2/fg_{name}.svg"
        (ROOT / file).write_text(svg_plate(body))
        made.append(row(
            f"v2_fg_{name}", file,
            ["foreground", "overlay", name, "relocation"],
            f"Foreground {name} for parallax. Empty space stays clear for type.",
            ["insert", "transition"], "subject_left", ["right", "top"],
            "medium", ["anticipation"], "high",
            ["parallax", "foreground_wipe", "slide_in"], "relocation", "line", "foreground",
            "sits", [name],
        ))
    for name, body in TRANSITIONS.items():
        file = f"static/v2/tr_{name}.svg"
        (ROOT / file).write_text(svg_plate(body))
        made.append(row(
            f"v2_tr_{name}", file,
            ["transition", "wipe", name],
            f"Transition shape, {name}. Type stays off the stroke.",
            ["transition"], "full", ["center"],
            "high", ["anticipation"], "high",
            ["foreground_wipe"], "relocation", "line", "transition",
            "passes", [name],
        ))
    for pack, layers in LAYERS.items():
        pack_dir = folder / "layers" / pack
        pack_dir.mkdir(parents=True, exist_ok=True)
        for layer, body in layers.items():
            file = f"static/v2/layers/{pack}/{layer}.svg"
            (ROOT / file).write_text(svg_plate(body))
            role = "background" if layer == "background" else ("hero" if layer in ("skyline", "paths", "arc") else "insert")
            made.append(row(
                f"v2_layer_{pack}_{layer}", file,
                ["layer", pack.replace("-", "_"), layer, "parallax"],
                f"Separate {layer} layer for {pack.replace('-', ' ')} parallax.",
                [role], "full", ["top"],
                "low" if layer == "background" else "medium",
                ["curiosity"], "high" if layer != "background" else "low",
                ["parallax"], "relocation", "line" if layer != "background" else "background",
                "layers" if layer != "background" else "backgrounds",
                "holds", [layer],
            ))
            made[-1]["layerPack"] = pack
            made[-1]["layer"] = layer
    return made


def merge():
    path = ROOT / "manifest.json"
    data = json.loads(path.read_text())
    annotated = sum(annotate(item) for item in data["assets"])
    have = {item["id"] for item in data["assets"]}
    added = [item for item in build_new() if item["id"] not in have]
    data["assets"].extend(added)
    path.write_text(json.dumps(data, indent=2) + "\n")
    record = ROOT / "v2-generation.json"
    record.write_text(json.dumps({
        "created": CREATED,
        "provider": "vector",
        "model": "svg",
        "added": [item["id"] for item in added],
        "annotated": annotated,
    }, indent=2) + "\n")
    print("annotated", annotated, "added", len(added), "total", len(data["assets"]))


if __name__ == "__main__":
    merge()
