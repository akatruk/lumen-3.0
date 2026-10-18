"""Draw the reusable vector library: icons, marks, and backgrounds.

These are files Remotion can scale. They are not generated pictures.
"""
import json
from pathlib import Path

GOLD = "#E0B15A"
BLUE = "#7EB6C9"
MINT = "#8FCBB4"
PAPER = "#F4EFE6"
NAVY = "#0E1A2B"
GREEN = "#1C3A32"
CHARCOAL = "#16181B"
CHECK = "#3E8F62"

ROOT = Path(__file__).resolve().parent / "out"


def svg(body, color=GOLD, size=256):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="{size}" height="{size}" '
        f'fill="none" stroke="{color}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</svg>"
    )


def two(main, accent_body, color=GOLD, accent=BLUE):
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="256" height="256" fill="none" '
        'stroke-linecap="round" stroke-linejoin="round">'
        f'<g stroke="{color}" stroke-width="1.6">{main}</g>'
        f'<g stroke="{accent}" stroke-width="1.6">{accent_body}</g></svg>'
    )


# Each value is SVG inner markup on a 24 grid.
ICONS = {
    "goal": '<path d="M6 20V5h8l-2.2 3.2L14 11H6"/><path d="M6 20h4"/>',
    "target": '<circle cx="12" cy="12" r="7.2"/><circle cx="12" cy="12" r="3.4"/><circle cx="12" cy="12" r="0.8" fill="#E0B15A" stroke="none"/><path d="M14.6 9.4 18.2 5.8M16.4 5.6h2v2"/>',
    "success": '<circle cx="12" cy="12" r="7.2"/><path d="M8.4 12.2 11 14.8 15.8 9.4"/>',
    "planning": '<rect x="7" y="4.5" width="10" height="15" rx="1.6"/><path d="M9.5 4.5h5V7h-5zM9.2 11h5.6M9.2 14h5.6M9.2 17h3.4"/>',
    "strategy": '<circle cx="6" cy="16" r="2"/><circle cx="16" cy="6" r="2"/><circle cx="18" cy="16" r="2"/><path d="M7.6 14.6 14.4 7.6M16 8v6.2"/>',
    "growth": '<path d="M4 18h16"/><path d="M6 15.5 10 11l3 2.4 5-6.2"/><path d="M14.6 7.2H18V11"/>',
    "progress": '<rect x="3.5" y="9" width="17" height="6" rx="3"/><path d="M3.5 12h8" stroke-width="3.2"/>',
    "family": '<circle cx="6" cy="5.2" r="1.5"/><path d="M6 6.8v4M4.2 8.8h3.6M4.4 14.6 6 10.8l1.6 3.8"/><circle cx="18" cy="5.2" r="1.5"/><path d="M18 6.8v4M16.2 8.8h3.6M16.4 14.6 18 10.8l1.6 3.8"/><circle cx="12" cy="8.6" r="1.2"/><path d="M12 9.9v3M10.7 11.4h2.6M11 16.2 12 13l1 3.2"/>',
    "couple": '<circle cx="8" cy="7.5" r="2"/><circle cx="16" cy="7.5" r="2"/><path d="M4 19v-1c0-2.2 1.8-3.6 4-3.6s4 1.4 4 3.6V19"/><path d="M12 19v-1c0-2.2 1.8-3.6 4-3.6s4 1.4 4 3.6V19"/>',
    "children": '<circle cx="8" cy="8" r="1.8"/><circle cx="16" cy="9" r="1.5"/><path d="M4.5 19v-.6c0-2 1.5-3.2 3.5-3.2s3.5 1.2 3.5 3.2V19"/><path d="M13 19v-.5c0-1.7 1.2-2.8 2.8-2.8s2.8 1.1 2.8 2.8V19"/>',
    "home": '<path d="M4.5 11.2 12 5l7.5 6.2"/><path d="M7 10.5V19h10v-8.5"/>',
    "relocation": '<path d="M4 12.2 9.2 8l5 4"/><path d="M5.6 11.6V17h7.2v-5"/><path d="M16 14h4M18 12l2 2-2 2"/>',
    "moving": '<path d="M4 8.5h10.5v9H4z"/><path d="M14.5 11H20v6.5h-5.5M7 8.5V6.2h5V8.5M8.2 13h3"/>',
    "travel": '<rect x="6" y="7" width="12" height="11" rx="1.6"/><path d="M9 7V5.6h6V7M9 12h6"/>',
    "flight": '<path d="M4.2 11.2h13c2 0 3.4.5 3.4.9s-1.4.9-3.4.9h-13c-1 0-1.6-.4-1.6-.9s.6-.9 1.6-.9z"/><path d="M6.2 11.1 3.6 6.6h2.8L7.6 11.1"/><path d="M12.4 12.8 8.4 18.6h4.4l3-5.8"/><path d="M5.2 13 3.2 15.4h3"/>',
    "passport": '<rect x="6" y="3.8" width="12" height="16.4" rx="1.4"/><circle cx="12" cy="11" r="2.6"/><path d="M9.2 16.2h5.6"/>',
    "document": '<path d="M7 3.8h7l3 3V20H7z"/><path d="M14 3.8V7h3M9.2 11h5.6M9.2 14h5.6M9.2 17h3.5"/>',
    "contract": '<path d="M5 5h8v14H5zM11 7h8v14h-8"/><path d="M7 9h4M7 12h4M13.5 11h4M13.5 14h4"/>',
    "consultation": '<circle cx="8" cy="8" r="1.6"/><circle cx="16" cy="8" r="1.6"/><path d="M5.2 15.5c.4-2 1.6-3 2.8-3s2.3 1 2.7 3M13.4 15.5c.4-2 1.5-3 2.6-3s2.2 1 2.6 3M6 18.5h12"/>',
    "legal": '<path d="M12 3.4v16.2"/><path d="M6.6 20.6h10.8"/><path d="M3.2 7.2h17.6"/><circle cx="12" cy="3.6" r="0.9" fill="#E0B15A" stroke="none"/><path d="M5.6 7.2v2.6"/><path d="M18.4 7.2v2.6"/><path d="M3.2 9.8h4.8"/><path d="M3.2 9.8c0 3.1 1.2 4.8 2.4 4.8s2.4-1.7 2.4-4.8"/><path d="M16 9.8h4.8"/><path d="M16 9.8c0 3.1 1.2 4.8 2.4 4.8s2.4-1.7 2.4-4.8"/>',
    "application": '<path d="M5 8h14v10H5z"/><path d="M8 8V6.2h8V8M9 12h6M9 15h4"/>',
    "approval": '<circle cx="12" cy="12" r="6.5"/><path d="M8.8 12.2 11 14.4 15.4 9.8"/>',
    "filing": '<path d="M4 9h16v9.5H4z"/><path d="M4 9l2-3h12l2 3M9 13h6"/>',
    "checklist": '<path d="M9 7.2h8M9 12h8M9 16.8h8"/><path d="M5.2 7.2 6.3 8.4 8 6.4M5.2 12l1.1 1.2L8 11.2M5.2 16.8l1.1 1.2L8 16"/>',
    "calendar": '<rect x="4" y="5.5" width="16" height="14" rx="1.6"/><path d="M4 9.5h16M8 3.8v3.2M16 3.8v3.2"/><circle cx="8.5" cy="13" r="0.7" fill="#E0B15A" stroke="none"/><circle cx="12" cy="13" r="0.7" fill="#E0B15A" stroke="none"/><circle cx="15.5" cy="13" r="0.7" fill="#E0B15A" stroke="none"/><circle cx="8.5" cy="16.2" r="0.7" fill="#E0B15A" stroke="none"/>',
    "time": '<circle cx="12" cy="12" r="7.2"/><path d="M12 8.2V12l3 2"/>',
    "money": '<ellipse cx="12" cy="12" rx="6.6" ry="6.6"/><ellipse cx="12" cy="12" rx="3.2" ry="3.2"/>',
    "budget": '<circle cx="12" cy="12" r="7"/><path d="M12 12 L12 5.2 A7 7 0 0 1 17.8 9.2z"/>',
    "investment": '<path d="M5 18h14"/><path d="M12 18V9"/><path d="M12 10c-2.2 0-3.4-1.4-3.4-2.6 2.4.2 3.4 1.4 3.4 2.6zM12 10c2.2 0 3.4-1.4 3.4-2.6-2.4.2-3.4 1.4-3.4 2.6z"/>',
    "business": '<rect x="4" y="8" width="16" height="10" rx="1.4"/><path d="M9 8V6.4h6V8M4 12.2h16"/>',
    "company": '<path d="M5 20V6.5h8V20M13 20V10h6V20M7.5 9h2M7.5 12.5h2M7.5 16h2M15.2 13h1.6M15.2 16h1.6"/>',
    "entrepreneur": '<circle cx="12" cy="8" r="1.8"/><path d="M8.2 17.5c.5-2.6 2-3.8 3.8-3.8s3.3 1.2 3.8 3.8"/><path d="M17 6.2l.6 1.4 1.4.6-1.4.6L17 10.2l-.6-1.4-1.4-.6 1.4-.6z"/>',
    "global": '<circle cx="12" cy="12" r="7.2"/><path d="M4.8 12h14.4M12 4.8c2 2.2 3 4.6 3 7.2s-1 5-3 7.2c-2-2.2-3-4.6-3-7.2s1-5 3-7.2"/>',
    "world": '<circle cx="12" cy="12" r="7.2"/><path d="M5 9.2h14M5 14.8h14M8.2 5.2c1.2 2 1.8 4.4 1.8 6.8s-.6 4.8-1.8 6.8M15.8 5.2c-1.2 2-1.8 4.4-1.8 6.8s.6 4.8 1.8 6.8"/>',
    "location": '<path d="M12 21s6-5.2 6-10a6 6 0 1 0-12 0c0 4.8 6 10 6 10z"/><circle cx="12" cy="11" r="1.8"/>',
    "route": '<circle cx="6" cy="16" r="1.6"/><circle cx="17" cy="7" r="1.6"/><path d="M7.4 14.8c2-1 3.2-3 4-5.2 1 1.6 2.4 2.6 4.4 3" stroke-dasharray="1.4 1.6"/>',
    "security": '<path d="M12 3.8 19 6.4V12c0 4-2.8 6.6-7 8.2C7.8 18.6 5 16 5 12V6.4z"/>',
    "privacy": '<rect x="6" y="10" width="12" height="9" rx="1.4"/><path d="M8.5 10V8a3.5 3.5 0 0 1 7 0v2"/>',
    "support": '<path d="M8 13a4 4 0 1 1 8 0"/><path d="M8 13v2a2 2 0 0 0 2 2h1v2M16 13v1.5a2 2 0 0 1-2 2"/>',
    "communication": '<path d="M5 6.5h14v9H8.5L5 18.2z"/>',
    "phone": '<path d="M8 4.8h2.4l1.2 3-1.6 1a9 9 0 0 0 4.2 4.2l1-1.6 3 1.2V16a1.6 1.6 0 0 1-1.8 1.6A12.2 12.2 0 0 1 6.4 6.6 1.6 1.6 0 0 1 8 4.8z"/>',
    "email": '<rect x="4" y="6.5" width="16" height="11" rx="1.4"/><path d="M5 8l7 5 7-5"/>',
    "meeting": '<circle cx="7" cy="9" r="1.4"/><circle cx="12" cy="8" r="1.5"/><circle cx="17" cy="9" r="1.4"/><path d="M4.6 16.5c.3-1.7 1.2-2.6 2.2-2.6s1.9.9 2.2 2.6M9.4 16.8c.4-1.8 1.4-2.8 2.6-2.8s2.2 1 2.6 2.8M15 16.5c.3-1.7 1.1-2.6 2-2.6s1.7.9 2 2.6"/>',
    "research": '<circle cx="11" cy="11" r="5"/><path d="M14.8 14.8 19 19"/>',
    "analytics": '<path d="M4 19h16"/><path d="M7 16V11M12 16V7M17 16v-3"/>',
    "decision": '<circle cx="6" cy="12" r="1.6"/><circle cx="16" cy="7" r="1.6"/><circle cx="16" cy="17" r="1.6"/><path d="M7.6 12H12m0 0 2.6-4M12 12l2.6 4"/>',
    "risk": '<path d="M12 4.5 20 19H4z"/><path d="M12 10v4"/>',
    "opportunity": '<path d="M5 19V9l7-4 7 4v10"/><path d="M10 19v-5h4v5"/><path d="M12 8.2v.1"/>',
    "education": '<path d="M3.8 9.5 12 6l8.2 3.5L12 13z"/><path d="M7 11.2v4.2c1.6 1.2 3.2 1.6 5 1.6s3.4-.4 5-1.6v-4.2"/>',
    "healthcare": '<circle cx="12" cy="12" r="7.2"/><path d="M12 8.2v7.6M8.2 12h7.6"/>',
    "property": '<path d="M4 11.5 10 6.5l6 5"/><path d="M5.6 11V19h8.8v-8"/><circle cx="17.2" cy="15" r="2.2"/><path d="M17.2 17.2V20"/>',
    "residence": '<path d="M4.2 11.4 10 6.4l5.8 5"/><path d="M5.8 11v7.2h8.4V11"/><path d="M16.2 8.5c1.6 1.4 1.6 3.4 0 4.6"/>',
    "citizenship": '<path d="M12 3.8 19 6.4V12c0 4-2.8 6.6-7 8.2C7.8 18.6 5 16 5 12V6.4z"/><path d="M12 8.2l.7 1.6 1.7.2-1.3 1.1.4 1.7L12 12l-1.5.8.4-1.7-1.3-1.1 1.7-.2z"/>',
    "visa": '<path d="M5 8h12.5a2 2 0 0 1 0 4H8"/><path d="M7 12l-2 2 2 2h10a2 2 0 0 0 0-4"/><circle cx="15.5" cy="10" r="0.7" fill="#E0B15A" stroke="none"/>',
    "tax": '<path d="M7 4h10v16H7z"/><circle cx="12" cy="12" r="3.2"/>',
    "bank": '<path d="M4 9.5 12 5l8 4.5"/><path d="M6 10v7M10 10v7M14 10v7M18 10v7M4.5 17.2h15M4 19.5h16"/>',
    "insurance": '<path d="M12 5c-3.2 2.4-6 3.2-8 3.4 0 6 3.2 9.2 8 11 4.8-1.8 8-5 8-11-2-.2-4.8-1-8-3.4z"/>',
    "identity": '<rect x="3.8" y="6" width="16.4" height="12" rx="1.6"/><circle cx="9" cy="11.2" r="1.6"/><path d="M6.8 15.2c.4-1.3 1.2-1.9 2.2-1.9s1.8.6 2.2 1.9M13.2 10.2h4.2M13.2 13.2h4.2"/>',
    "verification": '<path d="M12 3.8 19 6.4V12c0 4-2.8 6.6-7 8.2C7.8 18.6 5 16 5 12V6.4z"/><path d="M8.8 12.1 11 14.3 15.4 9.6"/>',
    "key": '<circle cx="8" cy="12" r="3"/><path d="M11 12h9M17 12v2.4M14.2 12v1.8"/>',
    "map": '<path d="M8 5.2 3.8 6.8v12L8 17.2l4 1.6 4.2-1.6 4 1.6V6.8L16.2 5.2 12 6.8z"/><path d="M8 5.2v12M12 6.8v12"/>',
    "compass": '<circle cx="12" cy="12" r="7.2"/><path d="M14.8 9.2 13 13l-3.8 1.8L11 11z"/>',
    "boxes": '<path d="M4 13h7v6H4zM13 13h7v6h-7zM7.5 8h9v4h-9z"/>',
    "handshake": '<path fill="#E0B15A" stroke="none" d="M1.6 12.8h6.2c.7 0 1.1-.7 1.9-1.3.9-.6 2.1-.1 2.3.9.2.6-.2 1.2-.8 1.4l2.2.8c.8.3 1.1 1.1.7 1.8-.4.7-1.3.9-2 .5l-1.8-.7c-.3.9-1.1 1.6-2.1 1.7H1.6V12.8z"/><path fill="#E0B15A" stroke="none" d="M22.4 14.4v3.8h-6c-.6 0-1 .6-1.7 1.2-.8.6-2 .2-2.3-.7-.2-.6.2-1.2.8-1.4l-2-.9c-.7-.3-1-1.1-.6-1.8.4-.6 1.2-.8 1.8-.4l1.6.6c.3-.8 1-1.4 1.9-1.5h6.5z"/>',
    "chat": '<path d="M5 6h10v8H8l-3 2.4z"/><path d="M10 10h8v7h-5"/>',
    "steps": '<circle cx="7" cy="17" r="1.5"/><circle cx="12" cy="12" r="1.5"/><circle cx="17" cy="7" r="1.5"/><path d="M8.4 16.2 10.6 13.2M13.4 11.2 15.6 8.2"/>',
    "network": '<circle cx="6" cy="8" r="1.6"/><circle cx="17" cy="7" r="1.6"/><circle cx="8" cy="17" r="1.6"/><circle cx="17" cy="16" r="1.6"/><path d="M7.4 8.6 15.4 7.4M7 9.4 8 15.2M9.4 16.6 15.4 16M16.2 8.6v5.6"/>',
    "city": '<path d="M3.5 19.5h17"/><path d="M5 19.5V9h4v10.5M10 19.5V5.5h5V19.5M16 19.5v-7h3.5v7"/>',
    "shield-lock": '<path d="M12 3.8 19 6.4V12c0 4-2.8 6.6-7 8.2C7.8 18.6 5 16 5 12V6.4z"/><path d="M10 12.2V11a2 2 0 0 1 4 0v1.2M9.6 12.2h4.8V15H9.6z"/>',
    "arrival": '<path d="M4 18h16"/><path d="M12 15V6"/><path d="M8.5 9.5 12 6l3.5 3.5"/><path d="M6 18v-3M18 18v-3"/>',
    "luggage": '<rect x="7" y="7" width="10" height="12" rx="1.6"/><path d="M10 7V5.4h4V7M9 11v5M15 11v5"/>',
    "pin-set": '<path d="M7 11.5c0-2 1.2-3.4 2.6-3.4S12.2 9.5 12.2 11.5c0 2-2.6 4.2-2.6 4.2S7 13.5 7 11.5z"/><path d="M13 9.2c0-2.2 1.4-3.8 3-3.8s3 1.6 3 3.8c0 2.4-3 5-3 5s-3-2.6-3-5z"/>',
    "scale-balance": '<path d="M12 5v14M7 19h10"/><path d="M7 8h10"/><path d="M7 8 5 13h4zM17 8l-2 5h4z"/>',
    "folder": '<path d="M3.8 8.2h6l1.6 1.8H20V18H3.8z"/>',
    "certificate": '<rect x="5" y="4" width="14" height="16" rx="1.4"/><circle cx="12" cy="12.5" r="2.8"/><path d="M10.6 15.2 9.8 19l2.2-1.2L14.2 19l-.8-3.8"/>',
    "clock-forward": '<circle cx="12" cy="12" r="7"/><path d="M12 8.4V12l2.4 1.6M17.5 6.2l1.6-1.2"/>',
    "arrow-up": '<path d="M12 19V6"/><path d="M7 10.5 12 5.5l5 5"/>',
    "coins": '<ellipse cx="12" cy="8" rx="5" ry="2.2"/><path d="M7 8v3.2c0 1.2 2.2 2.2 5 2.2s5-1 5-2.2V8"/><path d="M7 11.2v3.2c0 1.2 2.2 2.2 5 2.2s5-1 5-2.2v-3.2"/>',
}


TAGS = {
    "goal": ["goal", "planning", "priority", "aim"],
    "target": ["goal", "target", "planning", "success", "decision"],
    "success": ["success", "approval", "completion", "outcome"],
    "planning": ["planning", "plan", "process", "preparation"],
    "strategy": ["strategy", "planning", "decision", "path"],
    "growth": ["growth", "progress", "business", "investment"],
    "progress": ["progress", "timeline", "journey"],
    "family": ["family", "children", "priorities", "lifestyle"],
    "couple": ["couple", "family", "planning"],
    "children": ["children", "family", "future"],
    "home": ["home", "residence", "house"],
    "relocation": ["relocation", "moving", "home", "international"],
    "moving": ["moving", "relocation", "boxes"],
    "travel": ["travel", "relocation", "journey"],
    "flight": ["flight", "travel", "international"],
    "passport": ["passport", "travel", "identity", "document"],
    "document": ["document", "paperwork", "application"],
    "contract": ["contract", "legal", "document"],
    "consultation": ["consultation", "advice", "guidance", "meeting"],
    "legal": ["legal", "guidance", "justice"],
    "application": ["application", "filing", "process"],
    "approval": ["approval", "success", "completion"],
    "filing": ["filing", "documents", "process"],
    "checklist": ["checklist", "process", "steps", "clarity"],
    "calendar": ["calendar", "time", "planning", "timeline"],
    "time": ["time", "timeline", "planning"],
    "money": ["money", "budget", "finance"],
    "budget": ["budget", "finance", "planning"],
    "investment": ["investment", "growth", "finance"],
    "business": ["business", "work", "professional"],
    "company": ["company", "business", "office"],
    "entrepreneur": ["entrepreneur", "business", "founder"],
    "global": ["global", "international", "world"],
    "world": ["world", "global", "international"],
    "location": ["location", "destination", "place"],
    "route": ["route", "travel", "path", "international"],
    "security": ["security", "protection", "trust"],
    "privacy": ["privacy", "security", "protection"],
    "support": ["support", "help", "guidance"],
    "communication": ["communication", "conversation", "support"],
    "phone": ["phone", "consultation", "communication"],
    "email": ["email", "communication", "message"],
    "meeting": ["meeting", "consultation", "business"],
    "research": ["research", "analysis", "decision"],
    "analytics": ["analytics", "business", "growth"],
    "decision": ["decision", "choice", "planning"],
    "risk": ["risk", "caution", "decision"],
    "opportunity": ["opportunity", "future", "growth"],
    "education": ["education", "learning"],
    "healthcare": ["healthcare", "care"],
    "property": ["property", "home", "investment"],
    "residence": ["residence", "home", "relocation"],
    "citizenship": ["citizenship", "status", "identity"],
    "visa": ["visa", "travel", "status"],
    "tax": ["tax", "finance", "document"],
    "bank": ["bank", "finance", "money"],
    "insurance": ["insurance", "protection", "security"],
    "identity": ["identity", "document", "verification"],
    "verification": ["verification", "approval", "security", "identity"],
    "key": ["access", "home", "property"],
    "map": ["map", "route", "global", "location"],
    "compass": ["direction", "decision", "travel"],
    "boxes": ["moving", "packing", "relocation"],
    "handshake": ["agreement", "consultation", "trust"],
    "chat": ["communication", "support", "consultation"],
    "steps": ["process", "steps", "progress", "timeline"],
    "network": ["network", "global", "connections"],
    "city": ["city", "arrival", "destination"],
    "shield-lock": ["security", "privacy", "protection"],
    "arrival": ["arrival", "success", "relocation", "destination"],
    "luggage": ["luggage", "travel", "packing", "relocation"],
    "pin-set": ["destinations", "location", "international", "options"],
    "scale-balance": ["legal", "balance", "decision"],
    "folder": ["folder", "documents", "filing"],
    "certificate": ["certificate", "approval", "success"],
    "clock-forward": ["time", "progress", "timeline"],
    "arrow-up": ["growth", "progress", "success"],
    "coins": ["money", "budget", "finance", "stack"],
}


def write_icons(assets):
    folder = ROOT / "static" / "icons"
    folder.mkdir(parents=True, exist_ok=True)
    for name, body in ICONS.items():
        path = folder / f"{name}.svg"
        # Calendar and a few icons set their own fill; default stroke is gold via svg().
        if name in {"calendar", "target", "visa", "citizenship"}:
            text = (
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="256" height="256" '
                f'fill="none" stroke="{GOLD}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">{body}</svg>'
            )
        else:
            text = svg(body)
        path.write_text(text)
        assets.append(entry(
            f"icon_{name}",
            "image",
            "icons",
            TAGS[name],
            f"static/icons/{name}.svg",
            "1:1",
            "center",
            "transparent",
            0.9,
            "Line icon, one stroke weight, for rows and lists.",
        ))


def entry(ident, kind, category, tags, file, aspect, composition, background, score, description, **extra):
    row = {
        "id": ident,
        "type": kind,
        "category": category,
        "tags": tags,
        "description": description,
        "file": file,
        "aspectRatio": aspect,
        "composition": composition,
        "background": background,
        "qualityScore": score,
        "textSafe": True,
        "source": "vector",
    }
    row.update(extra)
    return row


def write_marks(assets):
    folder = ROOT / "static" / "decorative"
    folder.mkdir(parents=True, exist_ok=True)
    marks = {
        "arrow-right": '<path d="M3 12h16M14 6l6 6-6 6"/>',
        "arrow-curve": '<path d="M4 16c6 0 8-8 14-8"/><path d="M14 4l4 4-4 4"/>',
        "arrow-down": '<path d="M12 4v16M6 14l6 6 6-6"/>',
        "arrow-return": '<path d="M18 7v6a4 4 0 0 1-4 4H6"/><path d="M10 13l-4 4 4 4"/>',
        "route-dash": '<path d="M4 16c4-1 6-6 8-8s5-2 8-1" stroke-dasharray="1.2 1.5"/>',
        "route-arc": '<path d="M3 17c4-8 14-8 18-2"/><circle cx="3" cy="17" r="1" fill="#E0B15A" stroke="none"/><circle cx="21" cy="15" r="1" fill="#E0B15A" stroke="none"/>',
        "ring": '<circle cx="12" cy="12" r="7"/>',
        "ring-soft": '<circle cx="12" cy="12" r="8" stroke-width="0.8" opacity="0.7"/><circle cx="12" cy="12" r="4.5" stroke-width="0.8" opacity="0.45"/>',
        "dot": '<circle cx="12" cy="12" r="2.2" fill="#E0B15A" stroke="none"/>',
        "underline": '<path d="M4 16c4-3 12-3 16 0" stroke-width="1.2"/>',
        "marker": '<path d="M12 20s5-4.4 5-8a5 5 0 1 0-10 0c0 3.6 5 8 5 8z"/>',
        "divider": '<path d="M3 12h18" stroke-width="1"/>',
        "connector": '<path d="M5 12h4M15 12h4"/><circle cx="12" cy="12" r="2"/>',
        "frame": '<rect x="3.5" y="3.5" width="17" height="17" rx="3"/>',
        "frame-open": '<path d="M8 4H5.5A1.5 1.5 0 0 0 4 5.5V8M16 4h2.5A1.5 1.5 0 0 1 20 5.5V8M8 20H5.5A1.5 1.5 0 0 1 4 18.5V16M16 20h2.5a1.5 1.5 0 0 0 1.5-1.5V16"/>',
        "spark": '<path d="M12 4v4M12 16v4M4 12h4M16 12h4M6.5 6.5l2.4 2.4M15.1 15.1l2.4 2.4M17.5 6.5l-2.4 2.4M8.9 15.1l-2.4 2.4"/>',
        "check": f'<path d="M5 12.5 10 17.5 19 7" stroke="{CHECK}"/>',
    }
    colors = {"gold": GOLD, "blue": BLUE, "mint": MINT}
    for name, body in marks.items():
        for color_name, color in colors.items():
            if name == "check" and color_name != "gold":
                continue
            file_name = f"{name}-{color_name}.svg" if name != "check" else "check.svg"
            text = svg(body, color if name != "check" else CHECK)
            (folder / file_name).write_text(text)
            assets.append(entry(
                f"mark_{file_name.replace('.svg','')}",
                "image",
                "decorative",
                ["motion", "mark", name.split("-")[0], color_name, "overlay"],
                f"static/decorative/{file_name}",
                "1:1",
                "center",
                "transparent",
                0.92,
                f"Animatable {name.replace('-', ' ')} in {color_name}.",
            ))
    blobs = [
        ("blob-a", "M8 14c0-6 4-9 8-6s6 2 5 6-4 7-8 6-5-2-5-6z"),
        ("blob-b", "M6 12c1-5 6-7 10-4 4 2 4 8 1 10s-8 1-10-2-2-2-1-4z"),
        ("blob-c", "M12 5c5 1 8 5 7 9s-5 6-9 5-6-4-5-8 3-7 7-6z"),
    ]
    for name, d in blobs:
        for color_name, color in (("gold", GOLD), ("blue", BLUE)):
            file_name = f"{name}-{color_name}.svg"
            text = (
                f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="256" height="256">'
                f'<path d="{d}" fill="{color}" opacity="0.22"/></svg>'
            )
            (folder / file_name).write_text(text)
            assets.append(entry(
                f"mark_{name}_{color_name}",
                "image",
                "decorative",
                ["blob", "background", "atmosphere", color_name],
                f"static/decorative/{file_name}",
                "1:1",
                "center",
                "transparent",
                0.88,
                "Soft shape for slow drift behind type.",
            ))


PATHS = {
    "path-straight": (
        '<circle cx="4" cy="12" r="1.25" fill="#E0B15A" stroke="none"/>'
        '<circle cx="20" cy="12" r="1.25" fill="#E0B15A" stroke="none"/>'
        '<path d="M5.4 12h13.2"/>'
    ),
    "path-curved": (
        '<circle cx="4" cy="16.2" r="1.25" fill="#E0B15A" stroke="none"/>'
        '<circle cx="20" cy="7.8" r="1.25" fill="#E0B15A" stroke="none"/>'
        '<path d="M5.3 15.4C8.2 15.2 10.4 12 12 10.2 14 8 16.6 7.6 18.6 7.8"/>'
    ),
    "path-dotted": (
        '<circle cx="4.2" cy="16" r="1.15" fill="#E0B15A" stroke="none"/>'
        '<circle cx="7.6" cy="14.4" r="0.55" fill="#E0B15A" stroke="none"/>'
        '<circle cx="10.6" cy="12.6" r="0.55" fill="#E0B15A" stroke="none"/>'
        '<circle cx="13.4" cy="10.8" r="0.55" fill="#E0B15A" stroke="none"/>'
        '<circle cx="16.2" cy="9.2" r="0.55" fill="#E0B15A" stroke="none"/>'
        '<circle cx="19.8" cy="7.6" r="1.15" fill="#E0B15A" stroke="none"/>'
    ),
    "path-stops": (
        '<circle cx="3.6" cy="16.4" r="1.15" fill="#E0B15A" stroke="none"/>'
        '<circle cx="9.2" cy="12.2" r="1.15" fill="#E0B15A" stroke="none"/>'
        '<circle cx="14.8" cy="9.2" r="1.15" fill="#E0B15A" stroke="none"/>'
        '<circle cx="20.2" cy="6.4" r="1.15" fill="#E0B15A" stroke="none"/>'
        '<path d="M4.7 15.6 8.1 13M10.3 11.5 13.7 9.9M15.9 8.5 19.1 7.1"/>'
    ),
    "path-route": (
        '<circle cx="4.2" cy="17" r="1.2" fill="#E0B15A" stroke="none"/>'
        '<circle cx="12" cy="12.2" r="1.05" fill="#E0B15A" stroke="none"/>'
        '<circle cx="18.6" cy="7.4" r="1.2" fill="#E0B15A" stroke="none"/>'
        '<path d="M5.4 16.1C7.2 14.8 9.2 13.6 10.8 12.8"/>'
        '<path d="M13.1 11.5C14.8 10.2 16.2 8.8 17.4 7.9"/>'
        '<path d="M16.8 6.2 19.4 5.2 18.8 7.8"/>'
    ),
}

HOUSE = (
    '<path d="M3.8 11.5 12 4.6l8.2 6.9"/>'
    '<path d="M6.2 10.8V19.4h11.6V10.8"/>'
    '<path d="M10.5 19.4v-4.4h3v4.4"/>'
    '<path d="M14.8 13.2h2.3v2.2h-2.3z"/>'
    '<path d="M15.6 7.6V5.2h1.8v4"/>'
)


def write_paths(assets):
    """Gold route marks. Same stroke as the icons: 24 grid, weight 1.6, round caps."""
    folder = ROOT / "static" / "decorative"
    folder.mkdir(parents=True, exist_ok=True)
    labels = {
        "path-straight": "Straight gold path between two stops.",
        "path-curved": "One curved gold path between two stops.",
        "path-dotted": "Dotted gold path between two stops.",
        "path-stops": "Gold path with four stops.",
        "path-route": "Gold route with three stops and a direction.",
    }
    for name, body in PATHS.items():
        file_name = f"{name}-gold.svg"
        (folder / file_name).write_text(svg(body))
        assets.append(entry(
            name.replace("-", "_"),
            "image",
            "decorative",
            ["path", "route", "process", "planning", name.split("-")[-1], "gold"],
            f"static/decorative/{file_name}",
            "1:1",
            "center",
            "transparent",
            0.92,
            labels[name],
            visualFamily="line",
            mood="restrained",
            subjects=["path", "stops"],
            action="connects",
            environment="transparent",
        ))
    concepts = ROOT / "static" / "concepts"
    concepts.mkdir(parents=True, exist_ok=True)
    (concepts / "concept_house_001.svg").write_text(svg(HOUSE))
    assets.append(entry(
        "concept_path_001",
        "image",
        "concepts",
        ["process", "steps", "path", "planning", "route"],
        "static/decorative/path-route-gold.svg",
        "1:1",
        "center",
        "transparent",
        0.92,
        "Gold route with three stops. Same stroke as the icon set.",
        source="vector",
        visualFamily="line",
        mood="restrained",
        subjects=["path", "stops"],
        action="connects",
        environment="transparent",
    ))
    assets.append(entry(
        "concept_house_001",
        "image",
        "concepts",
        ["home", "house", "residence", "architecture"],
        "static/concepts/concept_house_001.svg",
        "1:1",
        "center",
        "transparent",
        0.9,
        "Line house in the same stroke family as the home icon.",
        source="vector",
        visualFamily="line",
        mood="quiet",
        subjects=["house"],
        action="stands",
        environment="transparent",
    ))


def write_backgrounds(assets):
    folder = ROOT / "static" / "backgrounds"
    folder.mkdir(parents=True, exist_ok=True)
    plates = [
        ("navy", NAVY, "#16304A"),
        ("navy-deep", "#081018", "#143044"),
        ("green", GREEN, "#0E2418"),
        ("green-deep", "#0C1A14", "#1E4634"),
        ("charcoal", CHARCOAL, "#2A241C"),
        ("ink", "#12110F", "#2A241C"),
        ("paper", "#E7E0D4", "#F7F3EC"),
        ("slate", "#1A2428", "#314047"),
    ]
    for name, top, bottom in plates:
        for variant, extra in (("flat", ""), ("lift", f'<radialGradient id="g2" cx="70%" cy="20%" r="55%"><stop offset="0" stop-color="#F6F1E8" stop-opacity="0.08"/><stop offset="1" stop-opacity="0"/></radialGradient><rect width="1080" height="1920" fill="url(#g2)"/>')):
            file_name = f"{name}-{variant}.svg"
            text = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1080 1920" width="1080" height="1920">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="{top}"/>
      <stop offset="1" stop-color="{bottom}"/>
    </linearGradient>
  </defs>
  <rect width="1080" height="1920" fill="url(#g)"/>
  {extra}
</svg>'''
            (folder / file_name).write_text(text)
            assets.append(entry(
                f"bg_{name}_{variant}",
                "image",
                "backgrounds",
                ["background", "plate", name, "editorial"],
                f"static/backgrounds/{file_name}",
                "9:16",
                "full",
                "plate",
                0.9,
                "Quiet full-frame plate. Type sits on top.",
            ))
    # A faint map grid, no labels.
    grid = folder / "grid-navy.svg"
    grid.write_text(f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1080 1920" width="1080" height="1920">
  <rect width="1080" height="1920" fill="{NAVY}"/>
  <g stroke="{BLUE}" stroke-width="1" opacity="0.18" fill="none">
    <ellipse cx="540" cy="860" rx="280" ry="280"/>
    <ellipse cx="540" cy="860" rx="180" ry="280"/>
    <path d="M260 860h560M540 580v560"/>
  </g>
</svg>''')
    assets.append(entry(
        "bg_grid_navy",
        "image",
        "backgrounds",
        ["background", "global", "map", "navy"],
        "static/backgrounds/grid-navy.svg",
        "9:16",
        "full",
        "plate",
        0.86,
        "Faint globe lines, no place names.",
    ))


def main():
    assets = []
    write_icons(assets)
    write_marks(assets)
    write_paths(assets)
    write_backgrounds(assets)
    manifest = {"version": 1, "assets": assets}
    (ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("assets", len(assets))


if __name__ == "__main__":
    main()
