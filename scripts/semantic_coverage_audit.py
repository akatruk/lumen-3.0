"""Coverage of original1 and original2 against the 15 semantic components.

Spoken text is original/zh. English glosses are recorded aside and not used
as evidence. This is an audit, not a director.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

from backend.director_v14 import classify_quote
from backend.director_v15 import classify_v15
from media.library.semantic_motion_registry import components

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "semantic-coverage" / "coverage.json"

_RANGE = re.compile(r"\d+(?:\.\d+)?\s*[-–~到至]\s*\d+(?:\.\d+)?|[一二三四五六七八九][一二三四五六七八九]千")
_PERCENT = re.compile(r"\d+(?:\.\d+)?\s*%|比例")
_COUNT = re.compile(r"三名|至少三|at least three", re.I)
_MONEY = re.compile(r"月薪|工资|人民币|泰诸|泰铢|万|资本|出资|金额|钱")
_COMPARE = re.compile(r"差异|不同|比价|对比|而是|则要求|甚至|更看重|强调")
_SEQUENCE = re.compile(r"第一步|流程|步骤|然后|都会")
_TIMELINE = re.compile(r"每天|节奏|那一刻|时间|认缴")
_CONDITION = re.compile(r"如果|只要|需要|通常|一般|不超过|至少|不用")
_CAUSE = re.compile(r"所以|因为|才能|不到位")
_ENTITY = re.compile(r"股东|董事|法人|有限公司|股权|公司")
_GEO = re.compile(r"泰国|中国|中泰|国外")
_DOC = re.compile(r"银行|签证|工作证|文件|公章|签字")
_PROCESS = re.compile(r"注册|申请|开户|陪同|按天|谈判|出资")
_QUAL = re.compile(r"划算|一般|专业|问题|特别的大|最好|直白|以为|看重|学历")

RULES = (
    ("numeric_range", _RANGE),
    ("percentage", _PERCENT),
    ("numeric_value", _COUNT),
    ("money", _MONEY),
    ("comparison", _COMPARE),
    ("sequence", _SEQUENCE),
    ("timeline", _TIMELINE),
    ("condition", _CONDITION),
    ("cause_effect", _CAUSE),
    ("entity_relationship", _ENTITY),
    ("geographic_relationship", _GEO),
    ("document", _DOC),
    ("process", _PROCESS),
    ("qualitative_statement", _QUAL),
)


def _tags(text: str) -> list[str]:
    found = [name for name, pattern in RULES if pattern.search(text or "")]
    if "numeric_range" in found and "numeric_value" in found:
        found = [name for name in found if name != "numeric_value"]
    return found


def _support(tag: str, text: str, intents: set[str]) -> tuple[str, str]:
    if tag == "numeric_range":
        return "unsupported", "financial_metrics matches 营收|revenue only, and only one number"
    if tag == "percentage":
        if "ownership_split" in intents:
            return "supported", "ownership_split uses the spoken percent and does not add a complement"
        return "unsupported", "a percent is spoken and ownership_split did not fire"
    if tag == "numeric_value":
        if "shareholder_network" in intents:
            return "supported", "shareholder_network uses the spoken count"
        return "unsupported", "a count is spoken and no component took it"
    if tag == "money":
        if _RANGE.search(text):
            return "unsupported", "the amount is a band, not a revenue counter"
        if "ownership_split" in intents:
            return "supported", "the money fact is the spoken percent"
        if "capital_flow" in intents:
            return "partially_supported", "capital_flow draws capital → company and does not show an amount"
        if "financial_metrics" in intents:
            return "supported", "financial_metrics matched a revenue figure"
        if re.search(r"月薪|工资|人民币|泰诸|泰铢", text):
            return "unsupported", "salary or currency wording is outside financial_metrics"
        return "visualization_not_needed", "money is the topic and no amount is spoken"
    if tag == "comparison":
        if "business_comparison" in intents:
            return "supported", "business_comparison has both named sides"
        if "中泰" in text and "中国" not in text:
            return "partially_supported", "中泰 is a contrast; the matcher requires the separate words 中国 and 泰国"
        if "中国" in text and "泰国" in text:
            return "unsupported", "both countries are named and business_comparison did not fire"
        return "visualization_not_needed", "a difference is claimed without two named sides"
    if tag == "sequence":
        if "document_workflow" in intents or "process_timeline" in intents:
            return "supported", "named steps are on a timeline"
        return "visualization_not_needed", "order is mentioned without three named steps"
    if tag == "timeline":
        if _RANGE.search(text):
            return "unsupported", "每天 is the unit of a band, and no component shows that band"
        return "visualization_not_needed", "time is mentioned without dated milestones"
    if tag == "condition":
        return "visualization_not_needed", "如果/通常 is connective; business_decision needs an either/or"
    if tag == "cause_effect":
        return "visualization_not_needed", "所以/才能 does not name two states for before_after"
    if tag == "entity_relationship":
        if "shareholder_network" in intents:
            return "supported", "shareholder_network matches 股东结构 or a spoken count"
        if re.search(r"股东|股权", text):
            return "unsupported", "股东 or 股权 is spoken without 结构 and without a count"
        return "visualization_not_needed", "公司, 董事, or 法人 is not an ownership diagram"
    if tag == "geographic_relationship":
        if "geographic_expansion" in intents:
            return "supported", "geographic_expansion has the named places"
        if "business_comparison" in intents:
            return "supported", "the places are the two sides of the comparison"
        return "visualization_not_needed", "a place is setting, not an expansion path"
    if tag == "document":
        if "document_workflow" in intents:
            return "supported", "document_workflow lists the named filings"
        return "visualization_not_needed", "a document is mentioned and the steps are not listed"
    if tag == "process":
        if "document_workflow" in intents or "process_timeline" in intents or "capital_flow" in intents:
            return "partially_supported", "a process component fired; it only shows named steps or a capital link"
        return "visualization_not_needed", "the action is an example, not a named procedure"
    if tag == "qualitative_statement":
        return "visualization_not_needed", "evaluation without a stated structure"
    return "visualization_not_needed", "no component is required"


def _rollup(pairs: list[tuple[str, str, str]]) -> tuple[str, str]:
    rank = {"unsupported": 3, "partially_supported": 2, "supported": 1, "visualization_not_needed": 0}
    if not pairs:
        return "visualization_not_needed", "no information structure"
    best = max(pairs, key=lambda item: rank[item[1]])
    bits = [f"{tag}: {status}" for tag, status, _reason in pairs if status != "visualization_not_needed"]
    reason = best[2]
    if bits:
        reason = "; ".join(bits)
    return best[1], reason


def _audit(name: str, path: Path) -> list[dict]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    out = []
    for row in rows:
        spoken = str(row.get("original") or row.get("zh") or "")
        v14 = classify_quote(spoken, row, locale="zh-CN")
        v15 = classify_v15(spoken, row, locale="zh-CN")
        intents = [item["visualIntent"] for item in v14 + v15]
        tags = _tags(spoken)
        pairs = [(tag, *_support(tag, spoken, set(intents))) for tag in tags]
        status, reason = _rollup(pairs)
        gloss = str(row.get("en") or "")
        gloss_intents = []
        if gloss and gloss != spoken:
            gloss_intents = [
                item["visualIntent"]
                for item in classify_quote(gloss, row, locale="en-US") + classify_v15(gloss, row, locale="en-US")
            ]
        out.append({
            "source": name,
            "id": row.get("id"),
            "start": row.get("start"),
            "end": row.get("end"),
            "quote": spoken,
            "types": tags,
            "existingIntents": intents,
            "glossOnlyIntents": [item for item in gloss_intents if item not in intents],
            "tagSupport": [{"type": tag, "status": status, "reason": why} for tag, status, why in pairs],
            "status": status,
            "reason": reason,
        })
    return out


def main() -> None:
    library = []
    semantic = (ROOT / "motion/src/semantic/SemanticMotion.tsx").read_text(encoding="utf-8")
    v15 = (ROOT / "motion/src/semantic/componentsV15.tsx").read_text(encoding="utf-8")
    mounted = set(re.findall(r'case "([a-z0-9_]+)":', semantic + "\n" + v15))
    director = (ROOT / "motion/src/preview/DirectorV3.tsx").read_text(encoding="utf-8")
    mounts = "semanticMotionV14?.componentId" in director and "<SemanticMotion" in director
    for row in components():
        intent = row["visualIntent"]
        library.append({
            "componentId": row["componentId"],
            "visualIntent": intent,
            "semanticTypes": row.get("supportedConcepts"),
            "requiredParameters": row.get("requiredParameters"),
            "locales": row.get("supportedLocales"),
            "layouts": row.get("supportedLayouts"),
            "remotionMounted": intent in mounted and mounts,
        })
    segments = _audit("original1", ROOT / "data/director_v5_original1/source.transcript.json")
    segments += _audit("original2", ROOT / "data/original2/source.transcript.json")
    unsupported = Counter()
    for row in segments:
        for tag in row["tagSupport"]:
            if tag["status"] == "unsupported":
                unsupported[tag["type"]] += 1
    payload = {
        "library": library,
        "mountedIntents": sorted(mounted),
        "segments": segments,
        "unsupportedFrequency": unsupported.most_common(),
        "original2ExistingHits": sum(1 for row in segments if row["source"] == "original2" and row["existingIntents"]),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"segments": len(segments), "unsupported": payload["unsupportedFrequency"], "original2Hits": payload["original2ExistingHits"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
