"""Spoken-concept triggers for library search + Remotion viz presets.

Mirrors motion/src/concepts/presets.ts. Remotion owns the viz; search uses
preset ids as deterministic_motion hints so a spoken line can prefer a
matching motion preset without inventing a second search stack.
"""

# Longer phrases first.
TRIGGER_PHRASES = (
    ("планируете переезд", "route_link", "relocation route"),
    ("второй вид на жительство", "document_stamp", "residence permit"),
    ("вид на жительство", "document_stamp", "residence permit"),
    ("семьи и бюджета", "family_cluster", "family budget goals"),
    ("с учетом целей", "family_cluster", "goals planning"),
    ("подходящую программу", "comparison_columns", "program comparison"),
    ("консультация и программа", "steps_reveal", "consultation program steps"),
    ("весь процесс", "steps_reveal", "process steps"),
    ("с чего начать", "steps_reveal", "process steps"),
    ("переезд", "route_link", "relocation route"),
    ("жительство", "document_stamp", "residence permit"),
    ("программу", "comparison_columns", "program comparison"),
    ("процесс", "steps_reveal", "process steps"),
    ("бюджет", "budget_scale", "budget scale"),
    ("целей", "family_cluster", "goals planning"),
    ("семьи", "family_cluster", "family"),
    ("рост", "growth_arrow", "growth arrow"),
    ("прибыль", "growth_arrow", "growth arrow"),
    ("риск", "risk_arrow", "risk arrow"),
    ("падение", "risk_arrow", "risk arrow"),
    ("срок", "deadline_scale", "deadline scale"),
    ("дедлайн", "deadline_scale", "deadline scale"),
    ("growth", "growth_arrow", "growth arrow"),
    ("profit", "growth_arrow", "growth arrow"),
    ("risk", "risk_arrow", "risk arrow"),
    ("deadline", "deadline_scale", "deadline scale"),
    ("relocation", "route_link", "relocation route"),
    ("residence", "document_stamp", "residence permit"),
    ("budget", "budget_scale", "budget scale"),
    ("增长", "growth_arrow", "growth arrow"),
    ("风险", "risk_arrow", "risk arrow"),
    ("搬迁", "route_link", "relocation route"),
    ("居留", "document_stamp", "residence permit"),
    ("预算", "budget_scale", "budget scale"),
    ("期限", "deadline_scale", "deadline scale"),
)

PRESETS = {
    "growth_arrow": {"layout": "arrow_up", "tags": ("growth", "arrow", "up", "deterministic_motion")},
    "risk_arrow": {"layout": "arrow_down", "tags": ("risk", "arrow", "down", "deterministic_motion")},
    "big_figure": {"layout": "figure", "tags": ("number", "figure", "stat", "deterministic_motion")},
    "steps_reveal": {"layout": "steps", "tags": ("steps", "process", "deterministic_motion")},
    "comparison_columns": {"layout": "columns", "tags": ("comparison", "columns", "deterministic_motion")},
    "deadline_scale": {"layout": "scale", "tags": ("deadline", "timeline", "deterministic_motion")},
    "route_link": {"layout": "route", "tags": ("route", "relocation", "deterministic_motion")},
    "document_stamp": {"layout": "stamp", "tags": ("document", "approval", "residence", "deterministic_motion")},
    "family_cluster": {"layout": "cluster", "tags": ("family", "goals", "deterministic_motion")},
    "budget_scale": {"layout": "budget", "tags": ("budget", "scale", "deterministic_motion")},
}


def match_trigger(text: str):
    """Return (preset_id, english_hint) or None."""
    hay = (text or "").casefold()
    for phrase, preset, hint in TRIGGER_PHRASES:
        if phrase.casefold() in hay:
            return preset, hint
    return None


def expand_query(text: str) -> str:
    """Append English tags for the matched spoken concept (search-compatible)."""
    hit = match_trigger(text)
    if not hit:
        return text or ""
    preset, hint = hit
    tags = " ".join(PRESETS.get(preset, {}).get("tags", ()))
    return f"{text} {hint} {tags}".strip()
