"""Deterministic notes from a finished transcript. Not a semantic model."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

from .config import settings

_NUMBER = re.compile(r"\d+(?:\.\d+)?%?|[零一二三四五六七八九十百千万]+")
_QUESTION = re.compile(r"[?？]|吗")


def write_brief(pid: str, record: dict) -> dict:
    segments = list(record.get("segments") or [])
    questions = []
    numbers = []
    for row in segments:
        text = str(row.get("text") or "")
        if _QUESTION.search(text):
            questions.append({"start": row.get("start"), "end": row.get("end"), "text": text})
        for match in _NUMBER.findall(text):
            numbers.append({"start": row.get("start"), "text": match, "quote": text})
    brief = {
        "kind": "deterministic_baseline",
        "transcriptVersion": record.get("transcriptVersion"),
        "modelId": record.get("modelId"),
        "modelVersion": record.get("modelVersion"),
        "sourceChecksum": record.get("sourceChecksum"),
        "summary": segments[0]["text"] if segments else "",
        "sections": [
            {"start": row.get("start"), "end": row.get("end"), "text": row.get("text")}
            for row in segments
        ],
        "questions": questions,
        "numbers": numbers,
        "uncertain": list(record.get("uncertain") or []),
        "spokenClaimsAreNotVerifiedFacts": True,
        "createdAt": time.time(),
    }
    path = settings.data_dir / pid / "localization" / "source-brief.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(brief, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
    return brief
