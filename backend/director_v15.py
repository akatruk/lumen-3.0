"""Director V15 — extra semantic diagrams on the V14 path.

SEMANTIC_MOTION_V15_ENABLED defaults off. When on, V14 still runs, then a
scene is upgraded only when the quote supports a more specific diagram.
Talking-head stays when nothing new is supported. No invented cells,
proportions, parties, places, or benefits.
"""
from __future__ import annotations

import os
import re
from typing import Any

from .director_v14 import _steps_from_quote, add_semantic_events, apply_semantic_motion, row_texts
from .locale_consistency import locale_bucket

_DOC = re.compile(
    r"bank|permit|visa|account|application|review|approval|документ|заявлен|проверк|одобрен|签证|银行|工作证|申请|审核|批准",
    re.I,
)
_EXPAND = re.compile(r"expand|expansion|进入|扩张|расширен", re.I)
_RISK = (
    (re.compile(r"low risk|低风险|низк\w* риск", re.I), "low"),
    (re.compile(r"high risk|高风险|высок\w* риск", re.I), "high"),
)
_ALLOC = re.compile(
    r"(operations|property|reserves|运营|物业|储备|операцион\w*|недвижимост\w*|резерв\w*)\D{0,16}(\d+(?:\.\d+)?)\s*(%|percent)?",
    re.I,
)
_PLACES = (
    (("Thailand", "泰国", "Таиланд"), "thailand"),
    (("Singapore", "新加坡", "Сингапур"), "singapore"),
    (("China", "中国", "Китай"), "china"),
)


def enabled() -> bool:
    raw = os.environ.get("SEMANTIC_MOTION_V15_ENABLED", "0").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _labels(bucket: str) -> dict[str, str]:
    table = {
        "en": {
            "low": "Low risk",
            "high": "High risk",
            "contract": "Contract",
            "investor": "Investor",
            "company": "Company",
            "partner": "Partner",
            "parent": "Parent company",
            "subsidiary": "Subsidiary",
        },
        "ru": {
            "low": "Низкий риск",
            "high": "Высокий риск",
            "contract": "Договор",
            "investor": "Инвестор",
            "company": "Компания",
            "partner": "Партнёр",
            "parent": "Материнская компания",
            "subsidiary": "Дочерняя компания",
        },
        "zh": {
            "low": "低风险",
            "high": "高风险",
            "contract": "协议",
            "investor": "投资人",
            "company": "公司",
            "partner": "伙伴",
            "parent": "母公司",
            "subsidiary": "子公司",
        },
    }
    return table[bucket if bucket in table else "en"]


def _evidence(segment: dict[str, Any], quote: str) -> dict[str, Any]:
    start = segment.get("start")
    end = segment.get("end")
    stamp = [float(start), float(end)] if start is not None and end is not None else None
    return {
        "segmentId": segment.get("id"),
        "sourceTimestamp": stamp,
        "sourceQuote": quote,
        "factClass": "source_stated",
    }


def _place_names(text: str, bucket: str) -> list[str]:
    found: list[tuple[int, str]] = []
    for names, _key in _PLACES:
        indexes = [text.lower().find(name.lower()) for name in names if name.lower() in text.lower()]
        indexes = [index for index in indexes if index >= 0]
        if not indexes:
            continue
        label = names[2] if bucket == "ru" else names[1] if bucket == "zh" else names[0]
        found.append((min(indexes), label))
    found.sort()
    return [label for _, label in found]


def _document_steps(labels: list[str]) -> bool:
    return len(labels) >= 2 and all(_DOC.search(label) for label in labels)


def classify_v15(text: str, segment: dict[str, Any], *, locale: str) -> list[dict[str, Any]]:
    if not text or not text.strip():
        return []
    bucket = locale_bucket(locale) or "en"
    labels = _labels(bucket)
    evidence = _evidence(segment, text)
    out: list[dict[str, Any]] = []

    risks = [key for pattern, key in _RISK if pattern.search(text)]
    if len(risks) >= 2:
        cells = []
        for index, key in enumerate(risks):
            cells.append({"label": labels[key], "row": 0, "col": index, "highlight": key == "high"})
        payload: dict[str, Any] = {
            "componentId": "motion.risk_matrix.v1",
            "version": "v15.0",
            "visualIntent": "risk_matrix",
            "locale": locale,
            "cells": cells,
            "evidence": evidence,
        }
        if re.search(r"impact|影响|влиян", text, re.I):
            payload["axisX"] = {"en": "Impact", "ru": "Влияние", "zh": "影响"}[bucket if bucket in {"en", "ru", "zh"} else "en"]
        out.append(payload)

    alloc = _ALLOC.findall(text)
    if len(alloc) >= 2:
        out.append({
            "componentId": "motion.capital_allocation.v1",
            "version": "v15.0",
            "visualIntent": "capital_allocation",
            "locale": locale,
            "segments": [
                {"label": name.strip().capitalize() if bucket == "en" else name.strip(), "value": float(value), "unit": "%" if unit else ""}
                for name, value, unit in alloc
            ],
            "evidence": evidence,
        })

    roles = []
    if re.search(r"parent company|母公司|материнск", text, re.I):
        roles.append(("parent", labels["parent"]))
    if re.search(r"subsidiar|子公司|дочерн", text, re.I):
        roles.append(("subsidiary", labels["subsidiary"]))
    if re.search(r"\binvestor\b|投资人|инвестор", text, re.I):
        roles.append(("investor", labels["investor"]))
    if re.search(r"\bpartner\b|伙伴|партн", text, re.I):
        roles.append(("partner", labels["partner"]))
    if len(roles) >= 2:
        out.append({
            "componentId": "motion.company_ecosystem.v1",
            "version": "v15.0",
            "visualIntent": "company_ecosystem",
            "locale": locale,
            "nodes": [{"id": key, "label": label, "role": key} for key, label in roles],
            "connections": [{"from": roles[0][0], "to": roles[1][0]}],
            "evidence": evidence,
        })

    steps = _steps_from_quote(text, bucket) or []
    if _document_steps(steps):
        out.append({
            "componentId": "motion.document_workflow.v1",
            "version": "v15.0",
            "visualIntent": "document_workflow",
            "locale": locale,
            "steps": [{"label": step, "evidence": text} for step in steps],
            "evidence": evidence,
        })

    if not re.search(r"ownership|ratio|доля|比例|外资", text, re.I):
        metric = re.search(
            r"(revenue|营收|выручк\w*)\D{0,24}(\d[\d\s,]*)\s*(USD|THB|CNY|美元|元|泰铢|руб)?",
            text,
            re.I,
        )
        if metric:
            raw = metric.group(2).replace(" ", "").replace(",", "")
            try:
                value = float(raw)
            except ValueError:
                value = None
            if value is not None:
                out.append({
                    "componentId": "motion.financial_metrics.v1",
                    "version": "v15.0",
                    "visualIntent": "financial_metrics",
                    "locale": locale,
                    "metrics": [{
                        "label": metric.group(1),
                        "value": value,
                        "unit": metric.group(3) or "",
                        "format": "currency" if metric.group(3) else "number",
                    }],
                    "evidence": evidence,
                })

    decision = re.search(r"either\s+(.{2,32}?)\s+or\s+(.{2,40})", text, re.I)
    if decision:
        branches = [part.strip(" .") for part in decision.groups()]
        out.append({
            "componentId": "motion.business_decision.v1",
            "version": "v15.0",
            "visualIntent": "business_decision",
            "locale": locale,
            "branches": branches,
            "evidence": evidence,
        })

    if _EXPAND.search(text):
        places = _place_names(text, bucket)
        if len(places) >= 2:
            directed = bool(re.search(r"\bfrom\b.+\bto\b|从.+到", text, re.I))
            out.append({
                "componentId": "motion.geographic_expansion.v1",
                "version": "v15.0",
                "visualIntent": "geographic_expansion",
                "locale": locale,
                "places": places,
                "directed": directed,
                "evidence": evidence,
            })

    parts = [part.strip(" .") for part in re.split(r"\s*,?\s+then\s+|，然后", text, flags=re.I) if part.strip()]
    if len(parts) >= 3 and all(len(part.split()) <= 4 for part in parts):
        out.append({
            "componentId": "motion.investment_milestones.v1",
            "version": "v15.0",
            "visualIntent": "investment_milestones",
            "locale": locale,
            "milestones": parts[:4],
            "evidence": evidence,
        })

    if re.search(r"\bcontract\b|协议|договор", text, re.I):
        parties = []
        if re.search(r"\binvestor\b|投资人|инвестор", text, re.I):
            parties.append({"id": "investor", "label": labels["investor"], "kind": "entity"})
        if re.search(r"\bcompany\b|公司|компани", text, re.I):
            parties.append({"id": "company", "label": labels["company"], "kind": "entity"})
        parties.append({"id": "contract", "label": labels["contract"], "kind": "document"})
        if re.search(r"\bpartner\b|伙伴|партн", text, re.I):
            parties.append({"id": "partner", "label": labels["partner"], "kind": "entity"})
        if len(parties) >= 2:
            out.append({
                "componentId": "motion.contract_relationship.v1",
                "version": "v15.0",
                "visualIntent": "contract_relationship",
                "locale": locale,
                "parties": parties,
                "evidence": evidence,
            })

    before = re.search(r"before\s+(.{3,40}?)\s+and\s+after\s+(.{3,40})", text, re.I)
    zh_before = re.search(r"(.{2,12})之前.{0,8}(.{2,12})之后", text)
    if before:
        out.append({
            "componentId": "motion.before_after.v1",
            "version": "v15.0",
            "visualIntent": "before_after",
            "locale": locale,
            "before": before.group(1).strip(" ."),
            "after": before.group(2).strip(" ."),
            "evidence": evidence,
        })
    elif zh_before:
        out.append({
            "componentId": "motion.before_after.v1",
            "version": "v15.0",
            "visualIntent": "before_after",
            "locale": locale,
            "before": zh_before.group(1),
            "after": zh_before.group(2),
            "evidence": evidence,
        })
    return out


def _upgrade_documents(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("visualIntent") != "process_timeline":
        return payload
    labels = []
    for step in payload.get("steps") or []:
        labels.append(step if isinstance(step, str) else str(step.get("label") or ""))
    if not _document_steps(labels):
        return payload
    upgraded = dict(payload)
    upgraded["componentId"] = "motion.document_workflow.v1"
    upgraded["visualIntent"] = "document_workflow"
    upgraded["version"] = "v15.0"
    return upgraded


def _drop_unspoken_complement(scene: dict) -> dict:
    """V11.1 equity panels still write 100 - spoken%. Drop that panel."""
    motion = scene.get("businessMotion")
    if not isinstance(motion, dict) or motion.get("localRatio") is None:
        return scene
    text = str(motion.get("originalSourceText") or "")
    local = motion.get("localRatio")
    spoken = str(int(local)) if isinstance(local, (int, float)) and float(local).is_integer() else str(local)
    if spoken in text:
        return scene
    cleaned = dict(scene)
    cleaned.pop("businessMotion", None)
    return cleaned


def apply_semantic_motion_v15(plan: dict, transcript: list | None = None, *, locale: str | None = None) -> dict:
    out = dict(plan)
    if not enabled():
        out["semanticMotionV15Enabled"] = False
        return out
    locale = locale or out.get("language") or "en-US"
    if not out.get("semanticMotionV14Enabled"):
        out = apply_semantic_motion(out, transcript, locale=locale, force=True)
    scenes = [_drop_unspoken_complement(dict(scene)) for scene in out.get("scenes") or []]
    for scene in scenes:
        payload = scene.get("semanticMotionV14")
        if isinstance(payload, dict):
            upgraded = _upgrade_documents(dict(payload))
            scene["semanticMotionV14"] = upgraded
            if upgraded.get("visualIntent") != payload.get("visualIntent"):
                for row in out.get("semanticEventAudit") or []:
                    if row.get("status") == "accepted" and row.get("eventId") == upgraded.get("eventId"):
                        row["visualIntent"] = upgraded.get("visualIntent")
                        row["componentId"] = upgraded.get("componentId")
    out["scenes"] = scenes
    rows = []
    for row in transcript or out.get("transcript") or []:
        if hasattr(row, "model_dump"):
            row = row.model_dump()
        if isinstance(row, dict):
            rows.append(row)
    fresh: list[dict[str, Any]] = []
    for row in rows:
        texts = row_texts(row, locale)
        found = []
        for text in texts:
            found.extend(classify_v15(text, row, locale=locale))
        for payload in found:
            fresh.append(dict(payload))
    out = add_semantic_events(out, fresh, rows)
    usage = []
    for scene in out.get("scenes") or []:
        payload = scene.get("semanticMotionV14")
        if not isinstance(payload, dict):
            continue
        usage.append({
            "sceneId": scene.get("sceneId"),
            "eventId": payload.get("eventId"),
            "componentId": payload.get("componentId"),
            "visualIntent": payload.get("visualIntent"),
            "layout": payload.get("layout"),
            "segmentId": (payload.get("evidence") or {}).get("segmentId"),
            "sourceQuote": (payload.get("evidence") or {}).get("sourceQuote"),
            "sourceTime": (payload.get("evidence") or {}).get("sourceTimestamp"),
            "outputTime": payload.get("outputTime"),
            "factClass": "source_stated",
        })
    out["semanticMotionV15Enabled"] = True
    out["semanticMotionV15Usage"] = usage
    out["semanticMotionV15Version"] = "v15.1"
    return out
