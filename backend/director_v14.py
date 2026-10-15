"""Director V14 — semantic motion selection.

Flag SEMANTIC_MOTION_V14_ENABLED defaults off. When off, the plan is unchanged.
When on, a scene gets one evidence-backed component. Text-card stacks and
V11 BusinessMotion panels are removed on that scene so the diagram is the
explanation. Talking-head footage stays when nothing in the window is supported.

Does not invent percentages, shareholder counts, comparison sides, or steps.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import re
from typing import Any

from .director_v11_1 import extract_spoken_facts, shareholder_count_from_text
from .locale_consistency import locale_bucket

_CONTRAST = re.compile(
    r"different|differs|difference|versus|≠|不同|差异|отлич|则要求",
    re.I,
)
_AT_MOST = re.compile(r"less than|at most|不超过|не более|менее|通常不超过|generally less", re.I)
_AT_LEAST = re.compile(r"at least|至少|не менее|минимум", re.I)
_SPECIFICITY = {
    "ownership_split": 5,
    "shareholder_network": 4,
    "business_comparison": 3,
    "document_workflow": 3,
    "numeric_range": 2,
    "process_timeline": 2,
    "capital_flow": 1,
}
_MIN_GAP = 0.45
# After the last spoken step, keep the graphic up so the label can be read.
# This extends the scene window only. sourceTimestamp stays the spoken span.
_LAST_STEP_HOLD = 1.2
_INVESTOR = re.compile(r"investor|инвестор|投资人|投资者", re.I)
_LIST_EN = re.compile(
    r"([A-Z][^,.]{2,32}),\s+([^,.]{2,32})\s+and\s+([A-Za-z][^,.]{2,32}?)(?:\s+all\b|\s+watch\b|\s+would\b|,|\.|$)",
    re.I,
)
_LIST_RU = re.compile(
    r"([А-ЯЁ][^,.]{2,32}),\s+([^,.]{2,32})\s+и\s+([^,.]{2,32}?)(?=\s+(?:все|следят|смотрят|ждут)\b|,|\.|$)",
)
_ZH_KNOWN = ("银行开户", "工作证", "签证申请")
_ORD_MARK = re.compile(r"第([一二三四五六七八九十]|\d{1,2})(?:层|層|步|点|點|阶段|階段|项|項)")
_CN_ORD = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
_ORD_GAP = 18.0
_ZH_NOT_BUT = re.compile(
    r"不是(?P<rejected>[\u4e00-\u9fff]{1,12})[\s，,、]*而是(?P<asserted>[\u4e00-\u9fff]{1,18})"
)
_ZH_NOT_TAIL = re.compile(r"不是(?P<rejected>[\u4e00-\u9fff]{1,12})$")
_ZH_BUT_HEAD = re.compile(r"^而是[\u4e00-\u9fff]")
_ZH_LOCK_LATER = re.compile(
    r"(?P<locked>[\u4e00-\u9fff]{2,8})从[\u4e00-\u9fff\s]{0,20}?锁定\s*(?P<later>[\u4e00-\u9fff]{2,6})反而"
)
_LOCKED_PREFIX = re.compile(r"^(?:也就是说|就是说|也就是|就是|所以|那么)")
_CONTRAST_GAP = 1.5
_PARTIES = (
    (("中国", "泰国"), ("China", "Thailand"), ("Китай", "Таиланд")),
)


def enabled() -> bool:
    raw = os.environ.get("SEMANTIC_MOTION_V14_ENABLED", "0").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _labels(bucket: str) -> dict[str, dict[str, str]]:
    return {
        "en": {
            "capital": "Capital",
            "company": "Company",
            "investor": "Investor",
            "shareholder": "Shareholder",
            "shareholders": "Shareholders",
            "foreign": "Foreign capital",
        },
        "ru": {
            "capital": "Капитал",
            "company": "Компания",
            "investor": "Инвестор",
            "shareholder": "Акционер",
            "shareholders": "Акционеры",
            "foreign": "Иностранный капитал",
        },
        "zh": {
            "capital": "资本",
            "company": "公司",
            "investor": "投资人",
            "shareholder": "股东",
            "shareholders": "股东",
            "foreign": "外资",
        },
    }[bucket if bucket in {"en", "ru", "zh"} else "en"]


def _clean_locked(side: str) -> str:
    return _LOCKED_PREFIX.sub("", side or "")


def contrast_sides(text: str) -> tuple[str, str] | None:
    """Sides of a contrast that the quote actually says. Nothing is invented."""
    match = _ZH_NOT_BUT.search(text or "")
    if match:
        left = match.group("rejected")
        right = match.group("asserted")
        if left and right and left != right and left in text and right in text:
            return left, right
    match = _ZH_LOCK_LATER.search(text or "")
    if not match:
        return None
    left = _clean_locked(match.group("locked"))
    right = match.group("later")
    if len(left) < 2 or not right or left == right:
        return None
    if left not in text or right not in text:
        return None
    return left, right


def _comparison_payload(
    left: str,
    right: str,
    locale: str,
    evidence: dict[str, Any],
    *,
    kind: str,
) -> dict[str, Any]:
    return {
        "componentId": "motion.business_comparison.v1",
        "version": "v14.1",
        "visualIntent": "business_comparison",
        "locale": locale,
        "left": left,
        "right": right,
        "operator": "≠",
        "contrast": kind,
        "evidence": evidence,
    }


def _party_pair(text: str, bucket: str) -> tuple[str, str] | None:
    for zh, en, ru in _PARTIES:
        groups = (zh, en, ru)
        if any(all(name.lower() in text.lower() for name in group) for group in groups):
            if bucket == "zh":
                return zh
            if bucket == "ru":
                return ru
            return en
    return None


def _ord_index(token: str) -> int | None:
    if token.isdigit():
        value = int(token)
        return value if 1 <= value <= 12 else None
    return _CN_ORD.get(token)


def _label_from_span(span: str) -> str | None:
    """Label after an ordinal. It may be introduced immediately or in the next sentence."""
    span = (span or "").strip()
    if not span:
        return None
    introduced = re.match(r"(?:叫做|称为|名为|叫)\s*([\u4e00-\u9fff]{2,8})", span)
    if introduced:
        return introduced.group(1)
    marked = re.match(r"(?:：|:)\s*([\u4e00-\u9fff]{2,8})", span)
    if marked:
        return marked.group(1)
    named = re.match(r"(?:是|为)\s*([\u4e00-\u9fff]{2,8})", span)
    if named:
        label = re.split(r"[的了]", named.group(1), maxsplit=1)[0]
        if len(label) >= 2 and not label.startswith(("不", "很", "没", "楼")):
            return label
    later = re.match(r"[。．.，,、；;：:\s]+([\u4e00-\u9fff]{2,8})(?=[。．.，,、；;：:\s]|$)", span)
    if later:
        label = later.group(1)
        if label.startswith(("不", "很", "没", "楼", "如果", "这里", "今天", "但是")):
            return None
        return label
    return None


def _ordinal_labels(text: str) -> list[dict[str, Any]]:
    """Chinese 第N层 / 第N步 labels in ordinal order. First mention of an index wins. No gaps filled."""
    if not text:
        return []
    marks = list(_ORD_MARK.finditer(text))
    found: dict[int, dict[str, Any]] = {}
    for index, mark in enumerate(marks):
        ordinal = _ord_index(mark.group(1))
        if ordinal is None or ordinal in found:
            continue
        end = marks[index + 1].start() if index + 1 < len(marks) else len(text)
        span = text[mark.end():end]
        label = _label_from_span(span)
        if not label:
            continue
        found[ordinal] = {
            "ordinal": ordinal,
            "label": label,
            "clause": text[mark.start():end].strip()[:80],
        }
    return [found[key] for key in sorted(found)]


def _complete_ordinals(items: list[dict[str, Any]]) -> bool:
    indexes = [int(item["ordinal"]) for item in items]
    return len(indexes) >= 3 and indexes == list(range(1, len(indexes) + 1))


def _list_steps(match: re.Match[str] | None, *, capitalize: bool) -> list[str] | None:
    if not match:
        return None
    steps = [part.strip(" .") for part in match.groups()]
    if len(steps) < 3 or not all(len(part.split()) <= 6 for part in steps):
        return None
    if capitalize:
        return [part[:1].upper() + part[1:] if part else part for part in steps]
    return steps


def _steps_from_quote(text: str, bucket: str) -> list[str] | None:
    ordinals = _ordinal_labels(text or "")
    if _complete_ordinals(ordinals):
        return [str(item["label"]) for item in ordinals]
    en_steps = _list_steps(_LIST_EN.search(text or ""), capitalize=True)
    ru_steps = _list_steps(_LIST_RU.search(text or ""), capitalize=False)
    zh_steps = list(_ZH_KNOWN) if text and all(part in text for part in _ZH_KNOWN) else None
    if bucket == "zh":
        return zh_steps or en_steps or ru_steps
    if bucket == "en":
        return en_steps or None
    return ru_steps or en_steps or zh_steps


def _row_text(row: dict[str, Any]) -> str:
    return str(row.get("original") or row.get("text") or "").strip()


def row_texts(row: dict[str, Any], locale: str) -> list[str]:
    """Spoken line first. A translation is separate evidence, never concatenated."""
    spoken = _row_text(row)
    bucket = locale_bucket(locale) or "en"
    field = {"zh": "zh", "ru": "ru"}.get(bucket, "en")
    extra = str(row.get(field) or "").strip()
    texts: list[str] = []
    if spoken:
        texts.append(spoken)
    if extra and extra not in texts:
        texts.append(extra)
    return texts


def _ordinal_clusters(rows: list[dict[str, Any]]) -> list[list[int]]:
    """Group an ordinal with the lines up to the next ordinals while they stay near each other."""
    hits: list[tuple[int, float, float]] = []
    for index, row in enumerate(rows):
        if not _ORD_MARK.search(_row_text(row)):
            continue
        try:
            start = float(row.get("start") or 0)
            end = float(row.get("end") or start)
        except (TypeError, ValueError):
            continue
        hits.append((index, start, end))
    if not hits:
        return []
    groups: list[list[tuple[int, float, float]]] = [[hits[0]]]
    for hit in hits[1:]:
        if hit[1] - groups[-1][-1][2] > _ORD_GAP:
            groups.append([hit])
        else:
            groups[-1].append(hit)
    clusters = []
    for group in groups:
        cluster = list(range(group[0][0], group[-1][0] + 1))
        lead = cluster[0] - 1
        if lead >= 0:
            try:
                lead_start = float(rows[lead].get("start") or 0)
                first_start = float(rows[cluster[0]].get("start") or 0)
            except (TypeError, ValueError):
                lead_start = first_start = 0.0
            if 0 <= first_start - lead_start <= 4:
                cluster = [lead, *cluster]
        clusters.append(cluster)
    return clusters


def _attach_ordinal_times(payload: dict[str, Any], rows: list[dict[str, Any]], origin: float) -> dict[str, Any]:
    steps = []
    for step in payload.get("steps") or []:
        item = dict(step) if isinstance(step, dict) else {"label": step}
        label = str(item.get("label") or "")
        for row in rows:
            text = _row_text(row)
            if label and label in text and _ORD_MARK.search(text):
                try:
                    item["at"] = round(float(row.get("start") or 0) - origin, 3)
                    item["until"] = round(float(row.get("end") or 0) - origin, 3)
                except (TypeError, ValueError):
                    pass
                break
        steps.append(item)
    timed = dict(payload)
    timed["steps"] = steps
    return timed


def _row_bounds(row: dict[str, Any]) -> tuple[float, float] | None:
    try:
        start = float(row.get("start") or 0)
        end = float(row.get("end") or start)
    except (TypeError, ValueError):
        return None
    return start, end


def adjacent_contrasts(rows: list[dict[str, Any]], *, locale: str) -> list[dict[str, Any]]:
    """Pair 不是… on one line with 而是… on the next line. One line stays in classify_quote."""
    events = []
    for index, row in enumerate(rows[:-1]):
        text = _row_text(row)
        other_row = rows[index + 1]
        other = _row_text(other_row)
        if not text or not other or contrast_sides(text) or contrast_sides(other):
            continue
        if not _ZH_NOT_TAIL.search(text) or not _ZH_BUT_HEAD.search(other):
            continue
        bounds = _row_bounds(row)
        nxt = _row_bounds(other_row)
        if not bounds or not nxt:
            continue
        gap = nxt[0] - bounds[1]
        if gap < -0.05 or gap > _CONTRAST_GAP:
            continue
        joined = f"{text} {other}"
        sides = contrast_sides(joined)
        if not sides:
            continue
        segment = {
            "id": row.get("id"),
            "start": bounds[0],
            "end": nxt[1],
        }
        payload = _comparison_payload(
            sides[0],
            sides[1],
            locale,
            _evidence(segment, joined),
            kind="不是而是",
        )
        payload["evidence"] = {
            **payload["evidence"],
            "segmentIds": [row.get("id"), other_row.get("id")],
        }
        events.append(payload)
    return events


def ordinal_timeline_payloads(
    rows: list[dict[str, Any]],
    *,
    locale: str,
) -> list[tuple[list[int], dict[str, Any]]]:
    """One process_timeline per complete ordinal cluster. Other intents on the join are dropped."""
    events: list[tuple[list[int], dict[str, Any]]] = []
    for cluster in _ordinal_clusters(rows):
        joined = " ".join(_row_text(rows[index]) for index in cluster if _row_text(rows[index]))
        head = rows[cluster[0]]
        bounds = _row_bounds(head)
        closing = _row_bounds(rows[cluster[-1]])
        if not bounds or not closing:
            continue
        origin, _head_end = bounds
        _close_start, closing_end = closing
        found = classify_quote(
            joined,
            {**head, "id": head.get("id"), "start": origin, "end": closing_end},
            locale=locale,
        )
        payload = next((item for item in found if item.get("visualIntent") == "process_timeline"), None)
        if not payload:
            continue
        payload = _attach_ordinal_times(payload, [rows[index] for index in cluster], origin)
        payload["evidence"] = {
            **payload["evidence"],
            "sourceQuote": joined,
            "sourceTimestamp": [origin, closing_end],
            "segmentIds": [rows[index].get("id") for index in cluster],
        }
        events.append((cluster, payload))
    return events


def _evidence(segment: dict[str, Any], quote: str) -> dict[str, Any]:
    start = segment.get("start")
    end = segment.get("end")
    stamp: list[float] | None = None
    if start is not None and end is not None:
        stamp = [float(start), float(end)]
    return {
        "segmentId": segment.get("id"),
        "sourceTimestamp": stamp,
        "sourceQuote": quote,
        "factClass": "source_stated",
    }


def classify_quote(text: str, segment: dict[str, Any], *, locale: str) -> list[dict[str, Any]]:
    """Return zero or more payloads justified by this quote, best first."""
    if not text or not text.strip():
        return []
    bucket = locale_bucket(locale) or "en"
    labels = _labels(bucket)
    evidence = _evidence(segment, text)
    out: list[dict[str, Any]] = []
    sides = contrast_sides(text)

    facts = extract_spoken_facts(text)
    percents = [p for p in facts.get("percentages") or [] if 0 < p <= 100]
    if percents and re.search(r"capital|ownership|ratio|доля|比例|外资|капитал", text, re.I):
        qualifier = "exact"
        if _AT_MOST.search(text):
            qualifier = "at_most"
        elif _AT_LEAST.search(text):
            qualifier = "at_least"
        # One number per spoken percentage. Never add 100 - p.
        values = []
        seen: set[float] = set()
        for value in percents:
            if value in seen:
                continue
            seen.add(value)
            values.append({
                "value": value,
                "label": labels["foreign"],
                "unit": "%",
                "qualifier": qualifier,
            })
        out.append({
            "componentId": "motion.ownership_split.v1",
            "version": "v14.1",
            "visualIntent": "ownership_split",
            "locale": locale,
            "values": values,
            "labels": {},
            "evidence": evidence,
        })

    count = shareholder_count_from_text(text)
    structure = re.search(r"shareholder|акционер|股东", text, re.I)
    if count and structure:
        prefix = "≥" if _AT_LEAST.search(text) else ""
        out.append({
            "componentId": "motion.shareholder_network.v1",
            "version": "v14.1",
            "visualIntent": "shareholder_network",
            "locale": locale,
            "company": labels["company"],
            "showCount": True,
            "nodeCount": int(count),
            "countPrefix": prefix,
            "labels": {"node": labels["shareholder"], "company": labels["company"]},
            "evidence": evidence,
        })
    elif structure and not sides and re.search(r"structure|структур|结构", text, re.I):
        out.append({
            "componentId": "motion.shareholder_network.v1",
            "version": "v14.1",
            "visualIntent": "shareholder_network",
            "locale": locale,
            "company": labels["company"],
            "showCount": False,
            "labels": {"group": labels["shareholders"], "company": labels["company"]},
            "shareholders": [labels["shareholders"]],
            "evidence": evidence,
        })

    if sides:
        kind = "不是而是" if _ZH_NOT_BUT.search(text) else "锁定反而"
        out.append(_comparison_payload(sides[0], sides[1], locale, evidence, kind=kind))
    else:
        pair = _party_pair(text, bucket)
        if pair and _CONTRAST.search(text):
            out.append(_comparison_payload(pair[0], pair[1], locale, evidence, kind="parties"))

    steps = _steps_from_quote(text, bucket)
    if steps and len(steps) >= 3:
        clauses = {str(item["label"]): str(item.get("clause") or "") for item in _ordinal_labels(text)}
        out.append({
            "componentId": "motion.process_timeline.v1",
            "version": "v14.1",
            "visualIntent": "process_timeline",
            "locale": locale,
            "steps": [
                {"label": step, "evidence": clauses.get(step) or text}
                for step in steps
            ],
            "evidence": evidence,
        })

    compared = any(item.get("visualIntent") == "business_comparison" for item in out)
    capital = re.search(r"capital|注册资本|капитал|出资|投资", text, re.I)
    if capital and not percents and not compared:
        entities = []
        connections = []
        if _INVESTOR.search(text):
            entities.append({"id": "investor", "label": labels["investor"]})
        entities.append({"id": "capital", "label": labels["capital"]})
        entities.append({"id": "company", "label": labels["company"]})
        for a, b in zip(entities, entities[1:]):
            connections.append({"from": a["id"], "to": b["id"]})
        out.append({
            "componentId": "motion.capital_flow.v1",
            "version": "v14.1",
            "visualIntent": "capital_flow",
            "locale": locale,
            "entities": entities,
            "connections": connections,
            "evidence": evidence,
        })
    return out


def _windows(plan: dict, transcript: list[dict]) -> list[tuple[float, float]]:
    scenes = plan.get("scenes") or []
    weights = list(plan.get("beatWeights") or [])
    if len(weights) != len(scenes):
        weights = [1.0] * len(scenes)
    total = sum(weights) or 1.0
    horizon = 0.0
    for row in transcript:
        try:
            horizon = max(horizon, float(row.get("end") or 0))
        except (TypeError, ValueError):
            continue
    horizon = max(horizon, float(plan.get("durationSeconds") or 0) or 0, 1.0)
    cursor = 0.0
    spans = []
    for weight in weights:
        dur = horizon * (weight / total)
        spans.append((cursor, cursor + dur))
        cursor += dur
    return spans


def _choose_layout(scene: dict) -> tuple[str, str]:
    speaker = str((scene.get("speaker") or {}).get("layout") or "")
    if "split" in speaker:
        if "left" in speaker:
            return "speaker_visual", "right"
        return "speaker_visual", "left"
    # Full frame only when the speaker is already a PIP / cutaway.
    if "pip" in speaker or "cutaway" in speaker:
        return "full_frame", "left"
    # Full-bleed overlay sits on the mouth of a talking-head frame. The
    # speaker column keeps the face clear; the diagram takes the other column.
    return "speaker_visual", "left"


def _clear_inherited_plate(scene: dict) -> dict:
    """A sliced beat must not keep a plate chosen for a different interval."""
    scene = dict(scene)
    bg = dict(scene.get("background") or {})
    for key in ("assetId", "file", "staged", "conceptId"):
        bg.pop(key, None)
    scene["background"] = bg
    scene["query"] = None
    return scene


def _suppress_text_cards(scene: dict) -> dict:
    scene = dict(scene)
    typ = dict(scene.get("typography") or {})
    typ["cards"] = []
    typ["cardMode"] = "none"
    typ.pop("steps", None)
    typ.pop("stepsTitle", None)
    scene["typography"] = typ
    scene.pop("businessMotion", None)
    scene.pop("stepsTitle", None)
    scene.pop("steps", None)
    scene["criteriaCards"] = []
    motion = dict(scene.get("semanticMotion") or {})
    motion["display"] = "omit"
    scene["semanticMotion"] = motion
    comp = dict(scene.get("composition") or {})
    comp["floatObject"] = None
    comp["suppressConcepts"] = True
    comp["suppressHeadline"] = True
    scene["composition"] = comp
    return scene


def _display_bounds(payload: dict[str, Any], output_limit: float, axis: float) -> list[float] | None:
    """Scene window for the graphic.

    Comparisons use the spoken span. A timeline whose last step lands at the
    end of that span keeps _LAST_STEP_HOLD seconds so the last label can be
    read. The hold never rewrites sourceTimestamp and never crosses the next
    event; callers clip it.
    """
    stamp = _stamp(payload)
    if not stamp or stamp[0] >= output_limit:
        return None
    start = min(max(stamp[0], 0.0), axis)
    end = min(max(stamp[1], 0.0), axis)
    if payload.get("visualIntent") == "process_timeline":
        origin = stamp[0]
        last = origin
        for step in payload.get("steps") or []:
            if not isinstance(step, dict) or step.get("at") is None:
                continue
            try:
                last = max(last, origin + float(step["at"]))
            except (TypeError, ValueError):
                continue
        if end - last < 2.4:
            end = min(axis, end + _LAST_STEP_HOLD)
    if end - start < 0.05:
        return None
    return [start, end]


def _stamp(payload: dict[str, Any]) -> list[float] | None:
    raw = (payload.get("evidence") or {}).get("sourceTimestamp")
    if not isinstance(raw, (list, tuple)) or len(raw) < 2:
        return None
    try:
        start = float(raw[0])
        end = float(raw[1])
    except (TypeError, ValueError):
        return None
    if end < start:
        start, end = end, start
    return [start, end]


def _segment_ids(payload: dict[str, Any]) -> list[str]:
    evidence = payload.get("evidence") or {}
    found: list[str] = []
    for key in evidence.get("segmentIds") or []:
        if key and key not in found:
            found.append(key)
    primary = evidence.get("segmentId")
    if primary and primary not in found:
        found.insert(0, primary)
    return found


def _parameters(payload: dict[str, Any]) -> tuple:
    intent = payload.get("visualIntent")
    if intent == "business_comparison":
        return (payload.get("left"), payload.get("right"), payload.get("contrast"))
    if intent == "numeric_range":
        band = payload.get("range") or {}
        return (
            band.get("low"),
            band.get("high"),
            band.get("lowText"),
            band.get("highText"),
            band.get("unit"),
            band.get("currency"),
            band.get("period"),
        )
    if intent in {"process_timeline", "document_workflow"}:
        labels = []
        for step in payload.get("steps") or []:
            labels.append(step.get("label") if isinstance(step, dict) else step)
        return tuple(labels)
    if intent == "ownership_split":
        return tuple(
            (item.get("value"), item.get("qualifier"), item.get("unit"))
            for item in payload.get("values") or []
        )
    if intent == "shareholder_network":
        return (payload.get("nodeCount"), bool(payload.get("showCount")), payload.get("countPrefix"))
    if intent == "capital_flow":
        return tuple(item.get("id") for item in payload.get("entities") or [])
    return (payload.get("componentId"), json.dumps(payload.get("labels") or {}, ensure_ascii=False, sort_keys=True))


def _overlap_ratio(left: list[float], right: list[float]) -> float:
    overlap = min(left[1], right[1]) - max(left[0], right[0])
    if overlap <= 0:
        return 0.0
    shorter = min(left[1] - left[0], right[1] - right[0])
    if shorter <= 0:
        return 0.0
    return overlap / shorter


def same_thought(left: dict[str, Any], right: dict[str, Any]) -> bool:
    """Same intent, same parameters, and the same segment or a shared time interval.

    visualIntent alone is not identity. Two China/Thailand comparisons on
    different lines stay distinct.
    """
    if left.get("visualIntent") != right.get("visualIntent"):
        return False
    if _parameters(left) != _parameters(right):
        return False
    left_ids = set(_segment_ids(left))
    right_ids = set(_segment_ids(right))
    if left_ids and right_ids and left_ids & right_ids:
        return True
    left_stamp = _stamp(left)
    right_stamp = _stamp(right)
    if not left_stamp or not right_stamp:
        return False
    return _overlap_ratio(left_stamp, right_stamp) >= 0.5


def stamp_event_id(payload: dict[str, Any]) -> str:
    existing = payload.get("eventId")
    if existing:
        return str(existing)
    evidence = dict(payload.get("evidence") or {})
    stamp = _stamp(payload) or [0.0, 0.0]
    body = {
        "intent": payload.get("visualIntent"),
        "parameters": _parameters(payload),
        "segments": _segment_ids(payload),
        "start": round(stamp[0], 2),
    }
    digest = hashlib.sha1(json.dumps(body, ensure_ascii=False, sort_keys=True, default=str).encode()).hexdigest()[:12]
    event_id = f"evt_{digest}"
    payload["eventId"] = event_id
    evidence["eventId"] = event_id
    payload["evidence"] = evidence
    payload["provenance"] = {
        "segmentIds": _segment_ids(payload),
        "sourceQuote": evidence.get("sourceQuote"),
        "sourceTime": evidence.get("sourceTimestamp"),
    }
    return event_id


def audit_row(
    payload: dict[str, Any],
    *,
    status: str,
    reason: str | None = None,
    merged_into: str | None = None,
    scene_id: str | None = None,
    output_time: list[float] | None = None,
) -> dict[str, Any]:
    evidence = payload.get("evidence") or {}
    row = {
        "eventId": payload.get("eventId"),
        "visualIntent": payload.get("visualIntent"),
        "componentId": payload.get("componentId"),
        "status": status,
        "reason": reason,
        "mergedInto": merged_into,
        "segmentIds": _segment_ids(payload),
        "sourceQuote": evidence.get("sourceQuote"),
        "sourceTime": evidence.get("sourceTimestamp"),
        "outputTime": output_time,
        "sceneId": scene_id,
        "flags": [],
    }
    if status == "accepted":
        if not row["componentId"]:
            row["flags"].append("accepted_without_component")
        if not output_time or float(output_time[1]) <= float(output_time[0]):
            row["flags"].append("accepted_without_time_window")
    return row


def _axis(plan: dict, rows: list[dict]) -> tuple[float, float, float]:
    """Video clock matches source clock. A shorter render keeps the head, it does not compress speech."""
    source = 0.0
    for row in rows:
        try:
            source = max(source, float(row.get("end") or 0))
        except (TypeError, ValueError):
            continue
    requested = float(plan.get("durationSeconds") or 0) or 0.0
    output = requested or max(source, 1.0)
    return source, output, output


def _parent_index(windows: list[tuple[float, float]], moment: float) -> int:
    for index, (start, end) in enumerate(windows):
        if start <= moment < end or index == len(windows) - 1:
            return index
    return 0


def _dedupe(payloads: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    ordered = sorted(payloads, key=lambda item: ((_stamp(item) or [0.0, 0.0])[0], -_SPECIFICITY.get(item.get("visualIntent"), 0)))
    kept: list[dict[str, Any]] = []
    audit: list[dict[str, Any]] = []
    for payload in ordered:
        payload = copy.deepcopy(payload)
        stamp_event_id(payload)
        twin = next((item for item in kept if same_thought(item, payload)), None)
        if twin:
            audit.append(audit_row(
                payload,
                status="merged",
                reason="duplicate_thought",
                merged_into=twin.get("eventId"),
            ))
            continue
        stamp = _stamp(payload)
        if stamp:
            rival = None
            for item in kept:
                other = _stamp(item)
                if other and _overlap_ratio(stamp, other) >= 0.8:
                    rival = item
                    break
            if rival is not None:
                mine = _SPECIFICITY.get(payload.get("visualIntent"), 0)
                theirs = _SPECIFICITY.get(rival.get("visualIntent"), 0)
                if mine > theirs:
                    kept.remove(rival)
                    audit.append(audit_row(
                        rival,
                        status="rejected",
                        reason="same_speech_one_graphic",
                        merged_into=payload.get("eventId"),
                    ))
                else:
                    audit.append(audit_row(
                        payload,
                        status="rejected",
                        reason="same_speech_one_graphic",
                        merged_into=rival.get("eventId"),
                    ))
                    continue
        kept.append(payload)
    return kept, audit


def place_events(plan: dict, payloads: list[dict[str, Any]], rows: list[dict] | None = None) -> dict:
    """Give each distinct event its own scene slice on the existing beat timeline.

    Dedup uses segments, parameters, and time. A repeated visualIntent on a
    different line stays. Several events that land in one beat are split into
    sequential scenes. Remotion still plays one scene list.
    """
    out = dict(plan)
    rows = list(rows or [])
    kept, audit = _dedupe(list(payloads))
    scenes = [dict(scene) for scene in out.get("scenes") or []]
    _source, output, axis = _axis(out, rows)
    if not scenes:
        for payload in kept:
            audit.append(audit_row(payload, status="rejected", reason="no_scene"))
        out["semanticEventAudit"] = _preserve_audit(out, audit)
        return out
    windows = _windows({**out, "durationSeconds": axis}, rows)
    scale = output / axis if axis else 1.0
    if not kept:
        out["semanticEventAudit"] = _preserve_audit(out, audit)
        return out
    points = {0.0, axis}
    placeable: list[dict[str, Any]] = []
    bounds_of: dict[int, list[float]] = {}
    for payload in kept:
        stamp = _stamp(payload)
        if not stamp:
            audit.append(audit_row(payload, status="rejected", reason="missing_source_time"))
            continue
        if stamp[0] >= output:
            audit.append(audit_row(payload, status="rejected", reason="trimmed_past_output"))
            continue
        bounds = _display_bounds(payload, output, axis)
        if not bounds:
            audit.append(audit_row(payload, status="rejected", reason="missing_source_time"))
            continue
        bounds_of[id(payload)] = bounds
        placeable.append(payload)
    placeable.sort(key=lambda item: bounds_of[id(item)][0])
    for index, payload in enumerate(placeable[:-1]):
        bounds = bounds_of[id(payload)]
        nxt = bounds_of[id(placeable[index + 1])][0]
        if bounds[1] > nxt:
            bounds[1] = nxt
    for bounds in bounds_of.values():
        points.add(round(bounds[0], 4))
        points.add(round(bounds[1], 4))
    ordered_points = sorted(points)
    pieces: list[dict[str, Any]] = []
    for start, end in zip(ordered_points, ordered_points[1:]):
        if end - start < 1e-4:
            continue
        moment = (start + end) / 2
        owner = None
        for payload in placeable:
            bounds = bounds_of[id(payload)]
            if bounds[0] <= moment < bounds[1]:
                owner = payload
                break
        parent = scenes[_parent_index(windows, min(moment, axis - 1e-6))]
        pieces.append({"start": start, "end": end, "owner": owner, "parent": parent})
    merged: list[dict[str, Any]] = []
    for piece in pieces:
        if not merged:
            merged.append(piece)
            continue
        previous = merged[-1]
        both_gaps = piece["owner"] is None and previous["owner"] is None
        same_gap = both_gaps and piece["parent"].get("sceneId") == previous["parent"].get("sceneId")
        same_event = (
            piece["owner"] is not None
            and previous["owner"] is not None
            and piece["owner"].get("eventId") == previous["owner"].get("eventId")
        )
        if same_gap or same_event:
            previous["end"] = piece["end"]
            continue
        merged.append(piece)
    fitted: list[dict[str, Any]] = []
    for piece in merged:
        if (
            piece["owner"] is None
            and fitted
            and fitted[-1]["owner"] is None
            and piece["end"] - piece["start"] < _MIN_GAP
        ):
            fitted[-1]["end"] = piece["end"]
            continue
        fitted.append(piece)
    built = []
    weights = []
    usage = []
    placed: dict[str, dict[str, Any]] = {}
    for index, piece in enumerate(fitted):
        parent = piece["parent"]
        scene = copy.deepcopy(parent)
        owner = piece["owner"]
        base_id = str(parent.get("sourceSceneId") or parent.get("sceneId") or "scene")
        scene["sourceSceneId"] = base_id
        if owner:
            scene_id = f"{base_id}__{owner.get('eventId')}"
            scene["sceneId"] = scene_id
            layout, side = _choose_layout(scene)
            payload = copy.deepcopy(owner)
            motion = scene.get("businessMotion") or {}
            if isinstance(motion, dict):
                if motion.get("mediaSide"):
                    side = motion.get("mediaSide")
                if motion.get("sceneTheme"):
                    payload["sceneTheme"] = motion.get("sceneTheme")
            payload["layout"] = layout
            payload["mediaSide"] = side
            output_time = [round(piece["start"] * scale, 3), round(piece["end"] * scale, 3)]
            payload["outputTime"] = output_time
            spoken = _stamp(owner) or output_time
            # step.at is seconds after sourceOrigin. The renderer subtracts
            # sceneStart once. Do not pre-subtract sceneStart here.
            payload["timebase"] = {
                "sourceOrigin": spoken[0],
                "sceneStart": output_time[0],
                "stepClock": "sourceOrigin_plus_step_at",
            }
            payload["enterFrame"] = 0
            payload["holdFrames"] = max(1, int(round((output_time[1] - output_time[0]) * 30)))
            scene = _suppress_text_cards(scene)
            scene = _clear_inherited_plate(scene)
            scene["semanticMotionV14"] = payload
            placed[payload["eventId"]] = {"sceneId": scene_id, "outputTime": output_time, "payload": payload}
            usage.append({
                "sceneId": scene_id,
                "eventId": payload.get("eventId"),
                "componentId": payload.get("componentId"),
                "visualIntent": payload.get("visualIntent"),
                "layout": layout,
                "segmentId": (payload.get("evidence") or {}).get("segmentId"),
                "segmentIds": _segment_ids(payload),
                "sourceQuote": (payload.get("evidence") or {}).get("sourceQuote"),
                "sourceTime": (payload.get("evidence") or {}).get("sourceTimestamp"),
                "outputTime": output_time,
                "factClass": "source_stated",
            })
        else:
            scene["sceneId"] = f"{base_id}__gap{index}"
            scene.pop("semanticMotionV14", None)
            # A carved gap inherits the parent beat's diagram. That diagram
            # belongs to a different slice, so the gap stays a talking head.
            scene = _suppress_text_cards(scene)
            scene = _clear_inherited_plate(scene)
            scene["sceneId"] = f"{base_id}__gap{index}"
            scene["sourceSceneId"] = base_id
        built.append(scene)
        weights.append(max(piece["end"] - piece["start"], 0.05))
    for payload in placeable:
        found = placed.get(payload.get("eventId"))
        if not found:
            audit.append(audit_row(payload, status="rejected", reason="no_time_window"))
            continue
        audit.append(audit_row(
            found["payload"],
            status="accepted",
            scene_id=found["sceneId"],
            output_time=found["outputTime"],
        ))
    for row in audit:
        link = row.get("mergedInto")
        if link and link in placed and not row.get("sceneId"):
            row["sceneId"] = placed[link]["sceneId"]
            row["linkedSceneId"] = placed[link]["sceneId"]
    out["scenes"] = built
    out["beatWeights"] = weights
    out["semanticMotionV14Usage"] = usage
    out["semanticEventAudit"] = _preserve_audit(out, audit)
    return out


def _preserve_audit(plan: dict, fresh: list[dict[str, Any]]) -> list[dict[str, Any]]:
    prior = [
        row for row in (plan.get("semanticEventAudit") or [])
        if row.get("status") != "accepted"
    ]
    seen = {(row.get("eventId"), row.get("status"), row.get("reason")) for row in fresh}
    kept = [row for row in prior if (row.get("eventId"), row.get("status"), row.get("reason")) not in seen]
    return kept + fresh


def add_semantic_events(plan: dict, payloads: list[dict[str, Any]], rows: list[dict] | None = None) -> dict:
    existing = []
    for scene in plan.get("scenes") or []:
        payload = scene.get("semanticMotionV14")
        if isinstance(payload, dict) and payload.get("componentId"):
            existing.append(copy.deepcopy(payload))
    return place_events(plan, existing + list(payloads), rows)


def apply_semantic_motion(
    plan: dict,
    transcript: list | None = None,
    *,
    locale: str | None = None,
    force: bool = False,
) -> dict:
    out = dict(plan)
    if not enabled() and not force:
        out["semanticMotionV14Enabled"] = False
        return out
    locale = locale or out.get("language") or "en-US"
    rows = []
    for row in transcript or out.get("transcript") or []:
        if hasattr(row, "model_dump"):
            row = row.model_dump()
        if isinstance(row, dict):
            rows.append(row)
    spans = _windows(out, rows)
    proposals: list[tuple[int, int, dict[str, Any]]] = []
    consumed: set[int] = set()
    for cluster, payload in ordinal_timeline_payloads(rows, locale=locale):
        stamp = (payload.get("evidence") or {}).get("sourceTimestamp") or [0, 0]
        mid = (float(stamp[0]) + float(stamp[1])) / 2
        index = 0
        for scene_index, (start, end) in enumerate(spans):
            if start <= mid < end or scene_index == len(spans) - 1:
                index = scene_index
                if start <= mid < end:
                    break
        proposals.append((_SPECIFICITY["process_timeline"] + 1, index, payload))
        consumed.update(cluster)
    for payload in adjacent_contrasts(rows, locale=locale):
        stamp = (payload.get("evidence") or {}).get("sourceTimestamp") or [0, 0]
        mid = (float(stamp[0]) + float(stamp[1])) / 2
        index = 0
        for scene_index, (start, end) in enumerate(spans):
            if start <= mid < end or scene_index == len(spans) - 1:
                index = scene_index
                if start <= mid < end:
                    break
        proposals.append((_SPECIFICITY["business_comparison"], index, payload))
    for row_index, row in enumerate(rows):
        if row_index in consumed:
            continue
        try:
            seg_start = float(row.get("start") or 0)
            seg_end = float(row.get("end") or 0)
        except (TypeError, ValueError):
            continue
        mid = (seg_start + seg_end) / 2
        index = 0
        for i, (start, end) in enumerate(spans):
            if start <= mid < end or i == len(spans) - 1:
                index = i
                if start <= mid < end:
                    break
        texts = row_texts(row, locale)
        if not texts:
            continue
        found = []
        for text in texts:
            found.extend(classify_quote(text, {**row, "id": row.get("id")}, locale=locale))
        if not found:
            continue
        for payload in found:
            spec = _SPECIFICITY.get(payload["visualIntent"], 0)
            if payload["visualIntent"] == "shareholder_network" and payload.get("showCount"):
                spec = 6
            proposals.append((spec, index, payload))
    proposals.sort(key=lambda item: (-item[0], item[1]))
    advice = None
    try:
        from . import motion_quality_v17
        if motion_quality_v17.enabled():
            advice = motion_quality_v17.advise(out, proposals, locale)
            proposals = motion_quality_v17.apply_advice(proposals, advice)
    except Exception:
        advice = {'enabled': True, 'fallback': 'deterministic'}
    out['motionQualityV17'] = advice
    placed = place_events(out, [payload for _spec, _index, payload in proposals], rows)
    if advice and not advice.get("fallback"):
        from . import motion_quality_v17 as _motion_quality
        for scene in placed.get("scenes") or []:
            payload = scene.get("semanticMotionV14")
            if not isinstance(payload, dict):
                continue
            payload["layout"] = _motion_quality.layout_after_advice(payload.get("componentId"), payload.get("layout") or "overlay", advice)
    placed["semanticMotionV14Enabled"] = True
    placed["semanticMotionV14Version"] = "v14.2"
    placed["motionQualityV17"] = advice
    return placed
