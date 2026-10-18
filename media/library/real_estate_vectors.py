"""Real-estate line objects. Additive. Does not rebuild the general icon set."""
import json
from pathlib import Path

GOLD = "#E0B15A"
BLUE = "#7EB6C9"
ROOT = Path(__file__).resolve().parent / "out" / "static" / "real-estate"

# 24-grid, same stroke family as the approved icons.
OBJECTS = {
    "condo": '<path d="M7 20V6h10v14"/><path d="M5 20h14"/><path d="M9 9h2M13 9h2M9 12.5h2M13 12.5h2M9 16h2M13 16h2"/>',
    "villa": '<path d="M3.5 12 12 5l8.5 7"/><path d="M6 11.2V19h12v-7.8"/><path d="M4 19h16"/><path d="M10.5 19v-4h3v4"/>',
    "floorplan": '<rect x="4" y="4" width="16" height="16" rx="1"/><path d="M4 12h9M13 4v8M13 12h7M10 12v8"/>',
    "balcony": '<path d="M4 8h16v8H4z"/><path d="M4 12h16M7 12v4M12 12v4M17 12v4"/><path d="M8 8V5h8v3"/>',
    "crane": '<path d="M7 20V6"/><path d="M3.2 6H20"/><path d="M3.2 6v2.4h2.4V6"/><path d="M15.5 6v7.5"/><path d="M13.6 13.5h3.8"/><path d="M15.5 13.5v1.6"/>',
    "door": '<path d="M7 4h10v16H7z"/><path d="M15 12h.1"/><circle cx="14.2" cy="12" r="0.7" fill="#E0B15A" stroke="none"/>',
    "keys": '<circle cx="6.5" cy="8" r="2.2"/><path d="M8.6 8H16M14.2 8v1.8"/><circle cx="6.5" cy="16" r="2.2"/><path d="M8.6 16H18M15.4 16v1.8"/>',
    "mortgage": '<path d="M4 11 10 6l6 5"/><path d="M5.5 10.5V18h9V10.5"/><ellipse cx="17.5" cy="15" rx="3" ry="3"/>',
    "yield": '<path d="M4 18h6V9h4v9"/><path d="M14 16c2-1 3-3 6-6"/><path d="M17 10h3v3"/>',
    "inspection": '<path d="M5 4h9l3 3v13H5z"/><path d="M8 10h6M8 13h6"/><path d="M8 16l1.2 1.2L12 14"/>',
    "pool": '<rect x="4" y="7" width="16" height="10" rx="2"/><path d="M6 12c1.2-1 2-1 3.2 0s2 1 3.2 0 2-1 3.2 0 2 1 3.2 0"/>',
    "gym": '<path d="M4 10h3v4H4zM17 10h3v4h-3zM7 11.2h10M7 12.8h10"/>',
    "parking": '<path d="M7 11h10l-1.2-2.4H8.2z"/><path d="M6 11h12v4H6z"/><circle cx="8.5" cy="16" r="1.2" fill="#E0B15A" stroke="none"/><circle cx="15.5" cy="16" r="1.2" fill="#E0B15A" stroke="none"/>',
    "elevator": '<rect x="6" y="3.5" width="12" height="17" rx="1"/><path d="M12 3.5v17M9 9l3-2 3 2M9 15l3 2 3-2"/>',
    "tenant": '<circle cx="8" cy="7.5" r="1.7"/><path d="M5.2 18v-.5c0-2.1 1.2-3.3 2.8-3.3s2.8 1.2 2.8 3.3V18"/><circle cx="15.2" cy="11.2" r="1.8"/><path d="M16.8 11.2H21M19.2 11.2v1.6"/>',
    "agent": '<circle cx="9" cy="8" r="1.7"/><path d="M6 16.5c.4-2 1.6-3 3-3s2.6 1 3 3"/><path d="M14 8h5v8h-5z"/>',
    "renovation": '<path d="M5 17l8-8 3 3-8 8z"/><path d="M12 10l2-3 3 2-2 3"/>',
    "transit": '<rect x="4" y="6" width="16" height="10" rx="2"/><circle cx="8" cy="16" r="1.2" fill="#E0B15A" stroke="none"/><circle cx="16" cy="16" r="1.2" fill="#E0B15A" stroke="none"/><path d="M8 6V4.5h8V6M12 6v10"/>',
    "shopping": '<path d="M7 9h10l-1 9H8z"/><path d="M9 9V7.5a3 3 0 0 1 6 0V9"/>',
    "tree": '<path d="M12 20v-6"/><path d="M12 14c-3 0-4-2-4-4 2 0 3-2 4-4 1 2 2 4 4 4 0 2-1 4-4 4z"/>',
    "occupancy": '<path d="M6 20V8h12v12"/><path d="M4 20h16"/><rect x="8.5" y="11" width="2.2" height="2.2" fill="#E0B15A" stroke="none"/><rect x="13" y="11" width="2.2" height="2.2"/><rect x="8.5" y="15" width="2.2" height="2.2"/><rect x="13" y="15" width="2.2" height="2.2" fill="#E0B15A" stroke="none"/>',
}


def svg(body):
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="256" height="256" '
        f'fill="none" stroke="{GOLD}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">{body}</svg>'
    )


META = {
    "condo": (["condo", "apartment", "building", "property", "real_estate"], "condominium", ["condo"]),
    "villa": (["villa", "house", "luxury", "property", "real_estate"], "house", ["villa", "house"]),
    "floorplan": (["floorplan", "plan", "apartment", "layout", "property"], "plan", ["apartment"]),
    "balcony": (["balcony", "condo", "view", "property"], "feature", ["condo"]),
    "crane": (["construction", "development", "crane", "property"], "development", ["development"]),
    "door": (["door", "entrance", "home", "handover", "property"], "entrance", ["home"]),
    "keys": (["keys", "handover", "purchase", "closing", "property"], "handover", ["home"]),
    "mortgage": (["mortgage", "loan", "finance", "property", "buying"], "finance", ["home"]),
    "yield": (["yield", "rental", "income", "investment", "roi", "property"], "investment", ["property"]),
    "inspection": (["inspection", "due_diligence", "checklist", "document", "documents", "legal", "buying", "apartment", "property"], "check", ["document"]),
    "pool": (["pool", "amenity", "condo", "lifestyle", "property"], "amenity", ["condo"]),
    "gym": (["gym", "amenity", "condo", "fitness", "property"], "amenity", ["condo"]),
    "parking": (["parking", "amenity", "car", "property"], "amenity", ["building"]),
    "elevator": (["elevator", "condo", "building", "amenity"], "amenity", ["condo"]),
    "tenant": (["tenant", "rent", "occupant", "property"], "renting", ["apartment"]),
    "agent": (["agent", "realtor", "consultation", "property"], "showing", ["property"]),
    "renovation": (["renovation", "repair", "before_after", "property"], "renovation", ["home"]),
    "transit": (["transport", "commute", "transit", "location", "neighborhood"], "access", ["neighborhood"]),
    "shopping": (["shopping", "amenity", "neighborhood", "retail"], "amenity", ["neighborhood"]),
    "tree": (["park", "neighborhood", "green", "lifestyle"], "amenity", ["neighborhood"]),
    "occupancy": (["occupancy", "rental", "tenant", "investment", "property"], "occupancy", ["building"]),
}


def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    assets = []
    for name, body in OBJECTS.items():
        (ROOT / f"re_{name}.svg").write_text(svg(body))
        tags, action, property_type = META[name]
        assets.append({
            "id": f"re_obj_{name}",
            "domain": "real_estate",
            "type": "image",
            "category": "real_estate",
            "visualFamily": "line",
            "tags": tags,
            "propertyType": property_type,
            "subjects": [],
            "action": action,
            "environment": "graphic",
            "region": "generic",
            "description": f"Gold line {name} for real-estate scenes. No numbers.",
            "file": f"static/real-estate/re_{name}.svg",
            "aspectRatio": "1:1",
            "composition": "center",
            "textSafeAreas": ["around"],
            "background": "transparent",
            "mood": ["premium", "restrained"],
            "qualityScore": 0.9,
            "textSafe": True,
            "source": "vector",
        })
    fragment = Path(__file__).resolve().parent / "out" / "real-estate-objects.json"
    fragment.write_text(json.dumps(assets, indent=2) + "\n")
    print(len(assets))


if __name__ == "__main__":
    main()
