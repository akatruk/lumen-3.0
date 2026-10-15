"""Spoken min–max bands.

SEMANTIC_NUMERIC_RANGE_ENABLED defaults off. Salary, day rate, and a bare
amount stay out of financial_metrics. Currency tokens stay as recognized:
泰国 and 泰诸 are not rewritten to 泰铢. No complement is invented.
"""
from __future__ import annotations

import os
import re
from decimal import Decimal
from typing import Any

from .director_v14 import add_semantic_events
from .locale_consistency import locale_bucket

_DIGIT = re.compile(
    r"(?P<low>\d+(?:\.\d+)?)\s*[-–~到至]\s*(?P<high>\d+(?:\.\d+)?)(?P<wan>\s*万)?"
)
_SPOKEN_THOUSAND = re.compile(r"(?P<low>[一二三四五六七八九])(?P<high>[一二三四五六七八九])千")
_UNIT = re.compile(r"泰国|泰诸|泰铢|人民币")
_WORDS = {"一": "1", "二": "2", "三": "3", "四": "4", "五": "5", "六": "6", "七": "7", "八": "8", "九": "9"}
_LABELS = {
    "salary": {"zh-CN": "月薪", "en-US": "Monthly pay", "ru-RU": "Месячная оплата"},
    "day_rate": {"zh-CN": "每天", "en-US": "Per day", "ru-RU": "В день"},
    "money": {"zh-CN": "金额", "en-US": "Amount", "ru-RU": "Сумма"},
}


def enabled() -> bool:
    raw = os.environ.get("SEMANTIC_NUMERIC_RANGE_ENABLED", "0").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def lexicon_senses(text: str) -> list[str]:
    """Separate salary, income, revenue, investment, capital, amount, ratio, ownership, company."""
    raw = text or ""
    found: list[str] = []
    if re.search(r"月薪|工资|薪酬", raw):
        found.append("salary")
    if "收入" in raw and "营收" not in raw:
        found.append("income")
    if re.search(r"营收|revenue|выручк", raw, re.I):
        found.append("revenue")
    if "投资" in raw:
        found.append("investment")
    if re.search(r"资本|出资", raw):
        found.append("capital")
    if "金额" in raw:
        found.append("amount")
    if re.search(r"比例|%", raw):
        found.append("ratio")
    if re.search(r"股东|股权", raw):
        found.append("ownership")
    if "公司" in raw:
        found.append("company")
    return found


def _kind(text: str) -> str:
    if re.search(r"月薪|工资|薪酬", text):
        return "salary"
    if re.search(r"每天|按天", text):
        return "day_rate"
    return "money"


def _unit(text: str, at: int) -> str:
    hits = list(_UNIT.finditer(text))
    if not hits:
        return ""
    return min(hits, key=lambda match: abs(match.start() - at)).group(0)


def _ends(low: str, high: str, *, scale: str, high_scale: str) -> tuple[str, str]:
    if high_scale:
        return low, f"{high}{high_scale}"
    if scale:
        return f"{low}{scale}", f"{high}{scale}"
    return low, high


def _scaled(token: str) -> int | None:
    """Expand 万 / 千. 1.5万 → 15000. A bare 8000 stays 8000. No currency is applied."""
    match = re.fullmatch(r"(\d+(?:\.\d+)?)(万|千)?", token or "")
    if not match:
        return None
    value = Decimal(match.group(1))
    scale = match.group(2) or ""
    if scale == "万":
        value *= 10000
    elif scale == "千":
        value *= 1000
    if value != value.to_integral_value():
        return None
    return int(value)


def _currency(text: str) -> str:
    if "人民币" in text:
        return "人民币"
    if "泰铢" in text:
        return "泰铢"
    return ""


def _period(text: str) -> str:
    if re.search(r"每天|按天", text):
        return "day"
    if re.search(r"月薪|工资|薪酬", text):
        return "month"
    return ""


def _band_from_digit(text: str, match: re.Match[str]) -> dict[str, Any] | None:
    low = match.group("low")
    high = match.group("high")
    try:
        low_number = float(low)
        high_number = float(high)
    except ValueError:
        return None
    wan = bool(match.group("wan"))
    scale = ""
    high_scale = ""
    if wan and low_number >= 100 and high_number < 100:
        high_scale = "万"
    elif wan:
        scale = "万"
    low_text, high_text = _ends(low, high, scale=scale, high_scale=high_scale)
    low_value = _scaled(low_text)
    high_value = _scaled(high_text)
    if low_value is None or high_value is None or low_value >= high_value:
        return None
    return {
        "lowText": low_text,
        "highText": high_text,
        "low": low_value,
        "high": high_value,
        "unit": _unit(text, match.start()),
        "kind": _kind(text),
    }


def _digit_range(text: str) -> dict[str, Any] | None:
    match = _DIGIT.search(text)
    if not match:
        return None
    return _band_from_digit(text, match)


def _spoken_thousand(text: str) -> dict[str, str] | None:
    match = _SPOKEN_THOUSAND.search(text)
    if not match or match.group("low") == match.group("high"):
        return None
    low = _WORDS[match.group("low")]
    high = _WORDS[match.group("high")]
    low_text = f"{low}千"
    high_text = f"{high}千"
    low_value = _scaled(low_text)
    high_value = _scaled(high_text)
    if low_value is None or high_value is None or low_value >= high_value:
        return None
    return {
        "lowText": low_text,
        "highText": high_text,
        "low": low_value,
        "high": high_value,
        "unit": _unit(text, match.start()),
        "kind": _kind(text),
    }


def _bands(text: str) -> list[dict[str, Any]]:
    """Every spoken band in the quote. A later band is not folded into an earlier one."""
    raw = text or ""
    bands = []
    covered: list[tuple[int, int]] = []
    for match in _DIGIT.finditer(raw):
        found = _band_from_digit(raw, match)
        if not found:
            continue
        bands.append(found)
        covered.append((match.start(), match.end()))
    for match in _SPOKEN_THOUSAND.finditer(raw):
        if any(start <= match.start() < end for start, end in covered):
            continue
        found = _spoken_thousand(raw[match.start():])
        if not found:
            continue
        found = dict(found)
        found["unit"] = _unit(raw, match.start())
        found["kind"] = _kind(raw)
        bands.append(found)
    return bands


def normalized_grounded(quote: str, low: int, high: int) -> bool:
    """True when low/high are the unique scaled reading of one band in the quote.

    The integers do not have to appear as digits. 1.5万 grounds 15000, not 1.5 and not 1500.
    """
    if not isinstance(low, int) or not isinstance(high, int) or low >= high:
        return False
    return any(band["low"] == low and band["high"] == high for band in _bands(quote))


def parameters_grounded(payload: dict[str, Any]) -> bool:
    """Spoken endpoints and their scaled values must come from the quote.

    A scaled integer may be absent as a substring. A currency or period may not.
    """
    quote = str((payload.get("evidence") or {}).get("sourceQuote") or "")
    rng = payload.get("range") or {}
    if not quote or not normalized_grounded(quote, rng.get("low"), rng.get("high")):
        return False
    matched = next(
        (
            band
            for band in _bands(quote)
            if band["low"] == rng.get("low") and band["high"] == rng.get("high")
        ),
        None,
    )
    if not matched:
        return False
    if rng.get("lowText") != matched["lowText"] or rng.get("highText") != matched["highText"]:
        return False
    if rng.get("unit", "") != matched["unit"]:
        return False
    currency = str(rng.get("currency") or "")
    if currency and currency not in quote:
        return False
    if currency == "泰铢" and "泰铢" not in quote:
        return False
    period = str(rng.get("period") or "")
    if period == "day" and not re.search(r"每天|按天", quote):
        return False
    if period == "month" and not re.search(r"月薪|工资|薪酬", quote):
        return False
    if period and period not in {"day", "month"}:
        return False
    return True


def classify_numeric_range(text: str, segment: dict[str, Any], *, locale: str) -> dict[str, Any] | None:
    if not text or not text.strip():
        return None
    found = _digit_range(text) or _spoken_thousand(text)
    if not found:
        return None
    start = segment.get("start")
    end = segment.get("end")
    stamp = [float(start), float(end)] if start is not None and end is not None else None
    bucket = locale_bucket(locale)
    locale_key = "zh-CN" if bucket == "zh" else "ru-RU" if bucket == "ru" else "en-US"
    band = {
        "lowText": found["lowText"],
        "highText": found["highText"],
        "low": found["low"],
        "high": found["high"],
        "unit": found["unit"],
        "kind": found["kind"],
    }
    currency = _currency(text)
    period = _period(text)
    if currency:
        band["currency"] = currency
    if period:
        band["period"] = period
    return {
        "componentId": "motion.numeric_range.v1",
        "version": "v18",
        "visualIntent": "numeric_range",
        "locale": locale_key,
        "layout": "overlay",
        "columnScrim": False,
        "range": band,
        "labels": dict(_LABELS[found["kind"]]),
        "evidence": {
            "segmentId": segment.get("id"),
            "sourceTimestamp": stamp,
            "sourceQuote": text,
            "factClass": "source_stated",
        },
    }


def _spoken(row: dict[str, Any]) -> str:
    return str(row.get("original") or row.get("zh") or "")


def apply_numeric_range(plan: dict, transcript: list | None = None, *, locale: str | None = None) -> dict:
    out = dict(plan)
    if not enabled():
        out["semanticNumericRangeEnabled"] = False
        return out
    locale = locale or out.get("language") or "zh-CN"
    rows = []
    for row in transcript or out.get("transcript") or []:
        if hasattr(row, "model_dump"):
            row = row.model_dump()
        if isinstance(row, dict):
            rows.append(row)
    payloads = []
    for row in rows:
        quote = _spoken(row)
        payload = classify_numeric_range(quote, row, locale=locale)
        if payload:
            payloads.append(payload)
    out = add_semantic_events(out, payloads, rows)
    usage = []
    for scene in out.get("scenes") or []:
        payload = scene.get("semanticMotionV14")
        if not isinstance(payload, dict) or payload.get("visualIntent") != "numeric_range":
            continue
        usage.append({
            "sceneId": scene.get("sceneId"),
            "eventId": payload.get("eventId"),
            "componentId": payload["componentId"],
            "lowText": payload["range"]["lowText"],
            "highText": payload["range"]["highText"],
            "unit": payload["range"]["unit"],
            "sourceQuote": (payload.get("evidence") or {}).get("sourceQuote"),
            "sourceTime": (payload.get("evidence") or {}).get("sourceTimestamp"),
            "outputTime": payload.get("outputTime"),
        })
    out["semanticNumericRangeEnabled"] = True
    out["semanticNumericRangeUsage"] = usage
    return out
