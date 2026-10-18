"""Immigration and relocation line pack. Additive. Does not rebuild the icon set."""
import json
from pathlib import Path

GOLD = "#E0B15A"
BLUE = "#7EB6C9"
NAVY = "#0E1A2B"
ROOT = Path(__file__).resolve().parent / "out"
PACK = ROOT / "static" / "immigration"

# Missing concepts only. passport, visa, citizenship, residence, relocation,
# family, flight, document, approval, tax, and investment already exist.
ICONS = {
    "second-passport": '<rect x="5" y="5.2" width="9" height="13" rx="1.2"/><rect x="9" y="7.2" width="9" height="13" rx="1.2"/><circle cx="13.5" cy="13" r="1.6"/>',
    "dual-citizenship": '<circle cx="8" cy="12" r="3.2"/><circle cx="16" cy="12" r="3.2"/><path d="M11.2 12h1.6"/>',
    "eligibility": '<circle cx="9" cy="8" r="1.6"/><path d="M6.4 16.5c.4-2 1.5-3 2.6-3s2.2 1 2.6 3"/><path d="M15 9.2l1.2 1.2L19 8"/>',
    "biometrics": '<path d="M12 18.5c-2.4 0-4-1.6-4-4.2V9.2c0-2.2 1.8-4 4-4s4 1.8 4 4v5.1c0 2.6-1.6 4.2-4 4.2z"/><path d="M12 15.2c-1 0-1.6-.7-1.6-1.8V9.4"/>',
    "interview": '<circle cx="8" cy="8" r="1.5"/><circle cx="16" cy="8" r="1.5"/><path d="M5.4 15c.4-1.8 1.4-2.8 2.6-2.8s2.2 1 2.6 2.8M13.4 15c.4-1.8 1.4-2.8 2.6-2.8s2.2 1 2.6 2.8M6 18.2h12"/>',
    "appointment": '<rect x="5" y="6" width="14" height="12" rx="1.4"/><path d="M5 9.5h14M9 4.8v2.4M15 4.8v2.4M12 12v2.4M12 12h2.2"/>',
    "rejection": '<circle cx="12" cy="12" r="6.4"/><path d="M9.4 9.4l5.2 5.2M14.6 9.4l-5.2 5.2"/>',
    "digital-nomad": '<rect x="4.5" y="8" width="11" height="7.2" rx="1"/><path d="M7 15.2h6M15.2 6.2c1.6 1.2 2.4 2.6 2.4 4.2"/>',
    "country-comparison": '<path d="M6 16.5 9.2 8l3.2 8M6.8 14h4.6"/><path d="M14.2 8.5h4.6M16.5 8.5v8"/>',
    "mobility": '<circle cx="7" cy="8" r="1.5"/><path d="M5.2 14.5c.3-1.6 1.2-2.4 1.8-2.4s1.5.8 1.8 2.4"/><path d="M11 12c2.2-1 3.4-2.6 4.2-4.4"/><circle cx="17" cy="7" r="1.3"/>',
    "permanent-card": '<rect x="4.5" y="6.5" width="15" height="11" rx="1.4"/><path d="M7.2 14.2 10 9.2l2.4 3.2 1.4-1.6 2.8 3.4"/>',
    "stamp": '<circle cx="12" cy="12" r="5.4"/><circle cx="12" cy="12" r="2.4"/>',
    "global-access": '<rect x="4" y="6" width="8" height="12" rx="1"/><circle cx="16.2" cy="8" r="1.1"/><circle cx="19" cy="12" r="1.1"/><circle cx="16.2" cy="16" r="1.1"/><path d="M12 10.5h2.6M12 13.5h4.2"/>',
    "business-move": '<rect x="4" y="9" width="10" height="7" rx="1"/><path d="M7 9V7.4h4V9M15.2 12.5h4M17.2 10.6l2 1.9-2 1.9"/>',
}

OBJECTS = {
    "booklet": '<rect x="7" y="3.5" width="10" height="17" rx="1.2"/><circle cx="12" cy="11" r="2.2"/>',
    "card": '<rect x="3.5" y="7" width="17" height="10" rx="1.4"/><circle cx="8" cy="12" r="1.6"/>',
    "sheet": '<path d="M6 4h8l4 4v12H6z"/><path d="M14 4v4h4M8.5 12h7M8.5 15h5"/>',
    "stack": '<path d="M6 7h10v12H6z"/><path d="M8 5h10v2M10 3h8v2"/>',
    "folder": '<path d="M4 8h6l1.4-2H20v12H4z"/>',
    "suitcase": '<rect x="6" y="7" width="12" height="11" rx="1.4"/><path d="M9 7V5.4h6V7"/>',
    "box": '<path d="M4 9h16v9H4z"/><path d="M4 9l2.2-3h11.6L20 9M12 9v9"/>',
    "key": '<circle cx="8" cy="10" r="2.4"/><path d="M10.2 10H18M15.2 10v2"/>',
    "plane": '<path d="M3 12h14l3-1.2v2.4L17 12"/><path d="M8 12l-2 5h3l2-5M8 12l-1.2-4h2.4"/>',
    "pin": '<path d="M12 20s5-4.4 5-8.4a5 5 0 1 0-10 0C7 15.6 12 20 12 20z"/><circle cx="12" cy="11.4" r="1.4"/>',
    "globe": '<circle cx="12" cy="12" r="7"/><path d="M5 12h14M12 5c1.8 2 2.6 4.4 2.6 7S13.8 17 12 19c-1.8-2-2.6-4.4-2.6-7S10.2 7 12 5"/>',
    "door": '<path d="M7 4h10v16H7z"/><circle cx="14.2" cy="12" r="0.6" fill="#E0B15A" stroke="none"/>',
    "route": '<circle cx="6" cy="16" r="1.4"/><circle cx="17" cy="7" r="1.4"/><path d="M7.2 14.8C10 12 12 9.5 15.6 8.2" stroke-dasharray="1.2 1.4"/>',
    "two-books": '<rect x="4.5" y="6" width="8" height="12" rx="1"/><rect x="10" y="6" width="8" height="12" rx="1"/>',
    "book-globe": '<rect x="3.5" y="6" width="8" height="12" rx="1"/><circle cx="16" cy="12" r="4"/><path d="M12.2 12h7.6"/>',
    "book-home": '<rect x="3.5" y="7" width="8" height="11" rx="1"/><path d="M13 16.5V11l3.2-2.4L19.4 11v5.5"/>',
    "shield": '<path d="M12 3.6 19 6.2V12c0 3.6-2.6 6-7 7.6C7.6 18 5 15.6 5 12V6.2z"/>',
    "check": '<circle cx="12" cy="12" r="6.2"/><path d="M8.6 12.2 11 14.6 15.6 9.6"/>',
    "calendar": '<rect x="4" y="5.5" width="16" height="14" rx="1.4"/><path d="M4 9.5h16M8 3.8v3M16 3.8v3"/>',
    "list": '<path d="M9 7h8M9 12h8M9 17h8"/><path d="M5.2 7.2l1.1 1.1L8 6.4M5.2 12l1.1 1.1L8 11.2"/>',
    "city": '<path d="M4 19h16M6 19V9h4v10M12 19V6h6v13"/>',
    "home": '<path d="M4.5 11.2 12 5l7.5 6.2"/><path d="M7 10.5V19h10v-8.5"/>',
    "truck": '<path d="M3 14h10V8h4l3 4v2h-2"/><circle cx="7" cy="16.2" r="1.3"/><circle cx="16" cy="16.2" r="1.3"/>',
    "flag": '<path d="M6 20V4"/><path d="M6 5h9l-1.6 2.4L15 10H6"/>',
    "rings": '<circle cx="12" cy="12" r="3"/><circle cx="12" cy="12" r="6.2"/>',
    "bars": '<path d="M5 18V12M10 18V8M15 18v-6M20 18V6"/>',
    "nodes": '<circle cx="6" cy="8" r="1.4"/><circle cx="16" cy="6" r="1.4"/><circle cx="18" cy="15" r="1.4"/><circle cx="8" cy="16" r="1.4"/><path d="M7.2 8.6 14.8 6.6M16.4 7.2 17.6 13.6M16.8 15.4 9.4 16"/>',
    "sun": '<circle cx="12" cy="12" r="3"/><path d="M12 5v2M12 17v2M5 12h2M17 12h2M7 7l1.4 1.4M15.6 15.6 17 17M17 7l-1.4 1.4M8.4 15.6 7 17"/>',
    "wave": '<path d="M3 14c2-2 3-2 5 0s3 2 5 0 3-2 5 0 3 2 3 0"/>',
    "laptop": '<rect x="4" y="6" width="16" height="10" rx="1"/><path d="M3 18h18"/>',
    "plus": '<circle cx="12" cy="12" r="6"/><path d="M12 9v6M9 12h6"/>',
    "cup": '<path d="M7 7h8v6a4 4 0 0 1-8 0z"/><path d="M15 8.5h2.2a2 2 0 0 1 0 4H15"/>',
    "window": '<rect x="5" y="4" width="14" height="16" rx="1"/><path d="M12 4v16M5 12h14"/>',
    "person": '<circle cx="12" cy="7" r="2"/><path d="M7 19c.6-3 2.2-4.6 5-4.6s4.4 1.6 5 4.6"/>',
    "family-marks": '<circle cx="8" cy="9" r="1.6"/><circle cx="16" cy="9" r="1.6"/><circle cx="12" cy="14" r="1.3"/>',
    "couple-marks": '<circle cx="9" cy="9" r="1.8"/><circle cx="15" cy="9" r="1.8"/><path d="M6.5 16.5c.4-2 1.5-3 2.5-3s2.1 1 2.5 3M12.5 16.5c.4-2 1.5-3 2.5-3s2.1 1 2.5 3"/>',
    "school": '<path d="M4 11 12 6l8 5"/><path d="M7 11.2V17h10v-5.8"/>',
    "briefcase": '<rect x="4" y="8" width="16" height="10" rx="1.2"/><path d="M9 8V6.2h6V8"/>',
    "columns": '<path d="M5 18V8M10 18V8M14 18V8M19 18V8M4 8h16M4 18h16"/>',
    "squares": '<rect x="4" y="4" width="6" height="6"/><rect x="14" y="4" width="6" height="6"/><rect x="4" y="14" width="6" height="6"/><rect x="14" y="14" width="6" height="6"/>',
    "triangle": '<path d="M12 5 20 19H4z"/>',
    "arrow-up": '<path d="M12 19V6M7 10l5-5 5 5"/>',
    "arrow-down": '<path d="M12 5v13M7 14l5 5 5-5"/>',
    "coin": '<circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="3"/>',
    "house-card": '<rect x="3.5" y="8" width="8" height="10" rx="1"/><path d="M13 17v-5l3-2.2 3 2.2V17"/>',
    "plane-route": '<path d="M4 16c4-6 8-8 16-9"/><path d="M14 6.2l2.2 1.2-2 .8"/>',
    "pin-home": '<path d="M12 19s4-3.4 4-6.4a4 4 0 1 0-8 0C8 15.6 12 19 12 19z"/><path d="M10.2 12.2h3.6v2.4h-3.6z"/>',
    "balcony": '<rect x="5" y="4" width="14" height="10"/><path d="M5 16h14M7 16v3M17 16v3M5 19h14"/>',
    "clock": '<circle cx="12" cy="12" r="6.5"/><path d="M12 8.5V12l2.4 1.6"/>',
    "stamp-doc": '<path d="M5 4h9l4 4v12H5z"/><circle cx="12" cy="13" r="2.4"/>',
    "two-pins": '<path d="M8 16s2.6-2.2 2.6-4.2a2.6 2.6 0 1 0-5.2 0C5.4 13.8 8 16 8 16z"/><path d="M16 16s2.6-2.2 2.6-4.2a2.6 2.6 0 1 0-5.2 0C13.4 13.8 16 16 16 16z"/>',
    "globe-route": '<circle cx="12" cy="12" r="6.5"/><path d="M6.5 14.5c3-3 6-4 10-5"/>',
    "door-key": '<path d="M4 5h8v14H4z"/><circle cx="16.5" cy="12" r="2"/><path d="M18.2 12H21"/>',
    "box-key": '<path d="M4 9h10v8H4z"/><circle cx="17" cy="11" r="2"/><path d="M18.6 11H21"/>',
    "scribble": '<path d="M5 14c2-3 3 2 5-1s2 3 4 0 3 2 5-1"/>',
    "network-person": '<circle cx="12" cy="7" r="1.8"/><path d="M9 13c.4-1.6 1.4-2.4 3-2.4s2.6.8 3 2.4"/><circle cx="5" cy="17" r="1.2"/><circle cx="19" cy="17" r="1.2"/><path d="M12 13v2M7 16.2 10 14M17 16.2 14 14"/>',
    "folder-check": '<path d="M4 8h6l1.4-2H18v10H4z"/><path d="M8 12l2 2 4-4"/>',
    "card-check": '<rect x="3.5" y="7" width="17" height="10" rx="1.4"/><path d="M8 12l2 2 4-4"/>',
    "plane-pin": '<path d="M4 14h8"/><path d="M10 14l4-2"/><path d="M16 18s2.4-2 2.4-4a2.4 2.4 0 1 0-4.8 0C13.6 16 16 18 16 18z"/>',
    "home-pin": '<path d="M5 12 10 8l5 4"/><path d="M6.5 11.5V16h7v-4.5"/><circle cx="17.5" cy="8" r="2"/>',
    "sun-house": '<circle cx="16" cy="7" r="2"/><path d="M4 13 10 8l6 5"/><path d="M6 12.5V18h8v-5.5"/>',
    "scale": '<path d="M12 5v14M6 19h12M12 8H6l-2 4h8zM12 8h6l2 4h-8z"/>',
}

BACKGROUNDS = {
    "map-navy": f'<rect width="1080" height="1920" fill="{NAVY}"/><g fill="none" stroke="{BLUE}" stroke-width="1.4" opacity="0.22"><ellipse cx="540" cy="900" rx="300" ry="300"/><ellipse cx="540" cy="900" rx="160" ry="300"/><path d="M240 900h600M540 600v600"/></g>',
    "routes": f'<rect width="1080" height="1920" fill="{NAVY}"/><g fill="none" stroke="{GOLD}" stroke-width="2" opacity="0.35"><path d="M220 1200 C 400 900, 680 1100, 860 640" stroke-dasharray="10 14"/><circle cx="220" cy="1200" r="8" fill="{GOLD}" stroke="none"/><circle cx="860" cy="640" r="8" fill="{GOLD}" stroke="none"/></g>',
    "globe-dark": f'<rect width="1080" height="1920" fill="#081018"/><g fill="none" stroke="{BLUE}" stroke-width="1.2" opacity="0.28"><circle cx="540" cy="960" r="340"/><ellipse cx="540" cy="960" rx="160" ry="340"/><path d="M200 960h680M540 620v680"/></g>',
    "window": f'<rect width="1080" height="1920" fill="#101820"/><rect x="140" y="280" width="800" height="1200" rx="24" fill="none" stroke="{BLUE}" stroke-width="2" opacity="0.25"/><path d="M540 280v1200M140 880h800" stroke="{BLUE}" stroke-width="1.4" opacity="0.2"/>',
    "city-lights": f'<rect width="1080" height="1920" fill="{NAVY}"/><g fill="{GOLD}" opacity="0.35"><circle cx="180" cy="1500" r="4"/><circle cx="260" cy="1420" r="3"/><circle cx="340" cy="1560" r="4"/><circle cx="480" cy="1380" r="3"/><circle cx="620" cy="1480" r="5"/><circle cx="760" cy="1360" r="3"/><circle cx="880" cy="1520" r="4"/></g>',
    "paper-lines": f'<rect width="1080" height="1920" fill="#122033"/><g stroke="#F4EFE6" stroke-width="2" opacity="0.12" fill="none"><path d="M180 700h720M180 780h640M180 860h700M180 940h520"/></g>',
    "green-editorial": '<rect width="1080" height="1920" fill="#0C1A14"/><rect width="1080" height="1920" fill="url(#g)"/>',
    "travel-depth": f'<rect width="1080" height="1920" fill="#101820"/><ellipse cx="540" cy="1500" rx="420" ry="80" fill="none" stroke="{BLUE}" opacity="0.2"/><ellipse cx="540" cy="1500" rx="260" ry="46" fill="none" stroke="{GOLD}" opacity="0.18"/>',
    "connections": f'<rect width="1080" height="1920" fill="{NAVY}"/><g fill="none" stroke="{BLUE}" stroke-width="1.4" opacity="0.28"><path d="M180 700 L540 980 L900 640"/><path d="M260 1300 L540 980 L820 1400"/><circle cx="180" cy="700" r="8" fill="{GOLD}" stroke="none"/><circle cx="540" cy="980" r="10" fill="{GOLD}" stroke="none"/><circle cx="900" cy="640" r="8" fill="{GOLD}" stroke="none"/><circle cx="260" cy="1300" r="7" fill="{GOLD}" stroke="none"/><circle cx="820" cy="1400" r="7" fill="{GOLD}" stroke="none"/></g>',
    "arc-routes": f'<rect width="1080" height="1920" fill="#081018"/><g fill="none" stroke="{GOLD}" stroke-width="1.6" opacity="0.3"><path d="M120 1100 C 400 700, 700 700, 960 1100"/><path d="M180 1280 C 420 980, 680 980, 900 1280"/></g>',
    "document-grain": f'<rect width="1080" height="1920" fill="#122033"/><g stroke="#F4EFE6" stroke-width="1.5" opacity="0.1" fill="none"><path d="M160 640h760M160 720h680M160 800h740M160 880h600M160 960h720"/></g>',
    "horizon": f'<rect width="1080" height="1920" fill="#101820"/><path d="M0 1180h1080" stroke="{BLUE}" stroke-width="1.5" opacity="0.25"/><path d="M0 1500 C 360 1420, 720 1580, 1080 1460" fill="none" stroke="{GOLD}" stroke-width="2" opacity="0.28"/>',
}


def svg_icon(body):
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="256" height="256" '
        f'fill="none" stroke="{GOLD}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">{body}</svg>'
    )


def plate(name, body):
    extra = ""
    if name == "green-editorial":
        extra = f'<defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1C3A32"/><stop offset="1" stop-color="#0C1A14"/></linearGradient></defs>'
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1080 1920" width="1080" height="1920">{extra}{body}</svg>'
    )


def asset(ident, file, tags, description, aspect, family, category):
    return {
        "id": ident,
        "domain": "immigration",
        "type": "image",
        "category": category,
        "visualFamily": family,
        "tags": tags,
        "subjects": [],
        "action": "marks",
        "environment": "graphic",
        "region": "generic",
        "description": description,
        "file": file,
        "aspectRatio": aspect,
        "composition": "center" if aspect == "1:1" else "full",
        "textSafeAreas": ["around"] if aspect == "1:1" else ["top", "center"],
        "background": "transparent" if aspect == "1:1" else "plate",
        "mood": ["premium", "restrained"],
        "qualityScore": 0.9,
        "textSafe": True,
        "source": "vector",
    }


THAILAND = {
    "river-dusk": f'<rect width="1080" height="1920" fill="#101820"/><path d="M0 1280 C 280 1180, 520 1400, 1080 1240 L 1080 1920 L 0 1920 Z" fill="#163044"/><g fill="{GOLD}" opacity="0.4"><circle cx="220" cy="980" r="4"/><circle cx="360" cy="900" r="3"/><circle cx="540" cy="940" r="5"/><circle cx="760" cy="860" r="3"/><circle cx="900" cy="980" r="4"/></g>',
    "condo-grid": f'<rect width="1080" height="1920" fill="{NAVY}"/><g stroke="{BLUE}" stroke-width="1.2" opacity="0.25" fill="none"><rect x="180" y="420" width="280" height="980"/><rect x="620" y="280" width="240" height="1120"/><path d="M180 700h280M180 980h280M620 560h240M620 840h240"/></g>',
    "balcony-depth": f'<rect width="1080" height="1920" fill="#0E1A2B"/><path d="M120 1500h840" stroke="{GOLD}" stroke-width="3" opacity="0.45"/><path d="M160 1500v80M920 1500v80M120 1580h840" stroke="{GOLD}" stroke-width="2" opacity="0.3"/><g fill="{BLUE}" opacity="0.35"><circle cx="300" cy="1100" r="3"/><circle cx="520" cy="980" r="4"/><circle cx="780" cy="1080" r="3"/></g>',
    "neighborhood": f'<rect width="1080" height="1920" fill="#122033"/><g fill="none" stroke="#F4EFE6" stroke-width="2" opacity="0.18"><path d="M140 1200h800"/><rect x="180" y="860" width="160" height="340"/><rect x="400" y="700" width="200" height="500"/><rect x="680" y="920" width="180" height="280"/></g>',
    "window-arrival": f'<rect width="1080" height="1920" fill="#101820"/><rect x="160" y="360" width="760" height="980" rx="20" fill="none" stroke="{BLUE}" stroke-width="2" opacity="0.3"/><path d="M540 360v980" stroke="{BLUE}" stroke-width="1.4" opacity="0.22"/>',
    "luggage-still": f'<rect width="1080" height="1920" fill="#141820"/><g fill="none" stroke="{GOLD}" stroke-width="3" opacity="0.55"><rect x="390" y="980" width="300" height="420" rx="16"/><path d="M470 980v-70h140v70"/></g>',
    "work-corner": f'<rect width="1080" height="1920" fill="{NAVY}"/><g fill="none" stroke="{BLUE}" stroke-width="2" opacity="0.3"><rect x="220" y="1100" width="640" height="360" rx="12"/><path d="M220 1220h640"/></g>',
    "skyline-quiet": f'<rect width="1080" height="1920" fill="#0C1A14"/><g fill="#1C3A32"><rect x="80" y="1100" width="120" height="520"/><rect x="240" y="860" width="160" height="760"/><rect x="440" y="980" width="140" height="640"/><rect x="640" y="760" width="180" height="860"/><rect x="860" y="1040" width="120" height="580"/></g>',
}

ENRICH = {
    "people_consult_001": ["immigration", "advisor", "residency", "citizenship"],
    "people_couple_001": ["immigration", "relocation", "planning", "documents"],
    "people_review_001": ["immigration", "documents", "application", "paperwork"],
    "people_meeting_001": ["immigration", "business", "consultation", "investor"],
    "people_door_001": ["immigration", "arrival", "family", "new_home"],
    "people_phone_001": ["immigration", "consultation", "phone"],
    "people_property_001": ["relocation", "apartment", "arrival", "new_home"],
    "people_property_002": ["relocation", "apartment", "couple", "abroad"],
    "people_packing_001": ["immigration", "packing", "departure", "suitcase"],
    "people_apartment_001": ["relocation", "new_home", "abroad", "settling"],
    "people_travel_001": ["immigration", "departure", "luggage", "terminal"],
    "doc_book_001": ["immigration", "passport", "second_passport", "booklet"],
    "doc_folder_001": ["immigration", "application", "documents", "filing"],
    "doc_calendar_001": ["immigration", "timeline", "appointment", "planning"],
    "doc_seal_001": ["immigration", "approval", "certificate"],
    "still_luggage_001": ["immigration", "relocation", "packing", "suitcase"],
    "still_city_001": ["immigration", "arrival", "new_city", "skyline"],
    "concept_shield_001": ["immigration", "security", "trust"],
    "global_route_001": ["immigration", "route", "mobility", "relocation"],
    "document_approval_001": ["immigration", "approval", "documents"],
    "location_pins_001": ["immigration", "destinations", "comparison", "relocation"],
    "i2v_consult_001": ["immigration", "consultation", "advisor"],
    "i2v_couple_001": ["immigration", "planning", "couple", "relocation"],
    "i2v_review_001": ["immigration", "documents", "application"],
    "i2v_door_001": ["immigration", "arrival", "family", "new_home"],
    "i2v_packing_001": ["immigration", "packing", "suitcase"],
    "i2v_apartment_001": ["immigration", "new_home", "apartment"],
    "i2v_phone_001": ["immigration", "consultation", "phone"],
}


def build():
    PACK.mkdir(parents=True, exist_ok=True)
    made = []
    for name, body in ICONS.items():
        file = f"static/immigration/imm_icon_{name}.svg"
        (ROOT / file).write_text(svg_icon(body))
        tags = ["immigration", "relocation", name.replace("-", "_")]
        made.append(asset(
            f"imm_icon_{name}", file, tags,
            f"Gold line {name.replace('-', ' ')} for immigration scenes. No letters.",
            "1:1", "line", "immigration",
        ))
    for name, body in OBJECTS.items():
        file = f"static/immigration/imm_obj_{name}.svg"
        (ROOT / file).write_text(svg_icon(body))
        tags = ["immigration", "relocation", name.replace("-", "_")]
        made.append(asset(
            f"imm_obj_{name}", file, tags,
            f"Generic {name.replace('-', ' ')} object. No official marks and no writing.",
            "1:1", "line", "immigration",
        ))
    for name, body in BACKGROUNDS.items():
        file = f"static/immigration/imm_bg_{name}.svg"
        (ROOT / file).write_text(plate(name, body))
        made.append(asset(
            f"imm_bg_{name}", file,
            ["background", "immigration", "relocation", name.replace("-", "_")],
            "Quiet immigration plate. No place names and no type.",
            "9:16", "background", "backgrounds",
        ))
    thai = PACK / "thailand"
    thai.mkdir(parents=True, exist_ok=True)
    for name, body in THAILAND.items():
        file = f"static/immigration/thailand/imm_th_{name}.svg"
        (ROOT / file).write_text(plate(name, body))
        row = asset(
            f"imm_th_{name}", file,
            ["thailand", "bangkok", "relocation", "immigration", name.replace("-", "_")],
            "Abstract Bangkok plate. No signage, no shop names, and no readable type.",
            "9:16", "background", "backgrounds",
        )
        row["region"] = "thailand"
        made.append(row)
    return made


def enrich(assets):
    touched = 0
    for item in assets:
        extra = ENRICH.get(item["id"])
        if not extra:
            continue
        tags = list(item.get("tags") or [])
        for tag in extra:
            if tag not in tags:
                tags.append(tag)
                touched += 1
        item["tags"] = tags
    return touched


def merge(made):
    path = ROOT / "manifest.json"
    data = json.loads(path.read_text())
    have = {item["id"] for item in data["assets"]}
    added = [item for item in made if item["id"] not in have]
    data["assets"].extend(added)
    retagged = enrich(data["assets"])
    path.write_text(json.dumps(data, indent=2) + "\n")
    print("added", len(added), "retagged", retagged, "total", len(data["assets"]))


if __name__ == "__main__":
    merge(build())
