"""Passage retrieval. Keyword overlap alone is not a match."""

from __future__ import annotations

import re
from pathlib import Path

GENERIC = {
    "business", "meeting", "video", "people", "office", "company", "corporate",
    "professional", "success", "team", "work", "the", "and", "for", "with",
    "商业", "会议", "视频", "公司", "办公室",
    "бизнес", "встреча", "видео", "офис", "компания",
}
BLOCKED_STATUS = {"quarantined", "rejected", "duplicate", "corrupt", "needs_review", "unreviewed", "restricted", "planned"}


def _meaning(text: str) -> set[str]:
    """English tags for a Chinese concept come from the library alias table."""
    words = _words(text)
    try:
        from media.library.search import _query_words, normalize_query
    except ImportError:
        return words
    expanded = {word for word in _query_words(normalize_query(text or "")) if word not in GENERIC and len(word) > 1}
    return words | expanded


def _overlap(start: float, end: float, seg_start: float, seg_end: float) -> float:
    return max(0.0, min(end, seg_end) - max(start, seg_start))


def _words(text: str) -> set[str]:
    out = set()
    token = []
    for char in (text or "").lower():
        if char.isalnum() or "\u4e00" <= char <= "\u9fff":
            token.append(char)
        elif token:
            out.add("".join(token))
            token = []
    if token:
        out.add("".join(token))
    return {word for word in out if word not in GENERIC and len(word) > 1}


def select_asset(concept: str | None, quote: str, assets: list[dict]) -> dict:
    """Return a real asset or NO_MATCH. Generic vocabulary cannot authorize footage."""
    specific = _meaning(concept or "") | _meaning(quote or "")
    rejected = []
    if not specific:
        return {"status": "NO_MATCH", "reason": "no_specific_concept", "rejected": rejected}
    chosen = None
    for asset in assets or []:
        status = str(asset.get("status") or asset.get("reviewStatus") or "reviewed")
        if status in BLOCKED_STATUS:
            rejected.append({"id": asset.get("id"), "reason": "ineligible", "status": status})
            continue
        if not asset.get("id") or not asset.get("file"):
            rejected.append({"id": asset.get("id"), "reason": "missing_file"})
            continue
        file_name = str(asset.get("file") or "")
        if file_name.endswith(".webm") or "premium3d" in file_name or str(asset.get("id") or "").startswith("l3d_"):
            rejected.append({"id": asset.get("id"), "reason": "unsupported_plate"})
            continue
        if "/layers/" in file_name.replace("\\", "/"):
            rejected.append({"id": asset.get("id"), "reason": "layer_fragment"})
            continue
        if asset.get("root") and not (Path(str(asset["root"])) / file_name).is_file():
            rejected.append({"id": asset.get("id"), "reason": "missing_file"})
            continue
        blob = " ".join(str(asset.get(key) or "") for key in ("title", "description", "tags", "caption", "category"))
        if "type is added later" in blob.casefold():
            rejected.append({"id": asset.get("id"), "reason": "unfinished_asset"})
            continue
        overlap = specific & _meaning(blob)
        if not overlap:
            rejected.append({"id": asset.get("id"), "reason": "no_meaning_overlap"})
            continue
        score = len(overlap)
        if str(asset.get("category") or "") == "metaphor":
            score -= 2
        if str(asset.get("visualFamily") or "") == "line":
            score -= 1
        candidate = {
            "status": "selected",
            "assetId": asset["id"],
            "file": asset["file"],
            "reason": "meaning_overlap:" + ",".join(sorted(overlap)),
            "_score": score,
        }
        if chosen is None or score > chosen["_score"]:
            if chosen is not None:
                rejected.append({"id": chosen["assetId"], "reason": "lower_rank"})
            chosen = candidate
        else:
            rejected.append({"id": asset.get("id"), "reason": "lower_rank"})
    if chosen is None:
        return {"status": "NO_MATCH", "reason": "no_relevant_asset", "rejected": rejected}
    chosen.pop("_score", None)
    chosen["rejected"] = rejected
    return chosen


def apply_passage_media(plan: dict, pid: str, transcript: list | None = None) -> dict:
    """Clear template queries when the semantic plan says the speaker should stay."""
    from .semantic_planner import PlannerError, load_valid

    ids = set()
    times = {}
    for index, row in enumerate(transcript or [], start=1):
        if not isinstance(row, dict):
            continue
        sid = row.get("id") or f"segment_{index:03d}"
        ids.add(sid)
        times[sid] = (float(row.get("start") or 0), float(row.get("end") or 0))
    try:
        semantic = load_valid(pid, ids) if ids else None
    except PlannerError:
        raise
    if not semantic:
        return plan
    out = dict(plan)
    scenes = []
    for scene in out.get("scenes") or []:
        scene = dict(scene)
        start = float(scene.get("start") or 0)
        end = float(scene.get("end") or start)
        related = []
        for passage in semantic["passages"]:
            covered = 0.0
            for sid in passage["segment_ids"]:
                if sid not in times:
                    continue
                seg_start, seg_end = times[sid]
                covered += _overlap(start, end, seg_start, seg_end)
            if covered > 0:
                related.append(passage)
        if not related:
            scenes.append(scene)
            continue
        needs = {item["visual_need"] for item in related}
        if needs <= {"talking_head"} or all(not item.get("visual_concept") for item in related):
            scene["query"] = None
            background = dict(scene.get("background") or {})
            for key in ("assetId", "file", "conceptId"):
                background.pop(key, None)
            scene["background"] = background
            scene["mediaDecision"] = {"status": "NO_MATCH", "reason": "talking_head"}
        scenes.append(scene)
    out["scenes"] = scenes
    out["semanticPlan"] = {
        "topic": semantic.get("topic"),
        "transcriptVersion": semantic.get("transcript_version"),
        "planner": semantic.get("planner"),
    }
    return out


def _index(transcript):
    ids, times, text = set(), {}, {}
    for index, row in enumerate(transcript or [], start=1):
        if not isinstance(row, dict):
            continue
        sid = row.get("id") or f"segment_{index:03d}"
        ids.add(sid)
        times[sid] = (float(row.get("start") or 0), float(row.get("end") or 0))
        text[sid] = str(row.get("text") or "")
    return ids, times, text


def _scene_from_passage(index: int, start: float, end: float, passage: dict) -> dict:
    quote = str(passage.get("quote") or "")
    concept = passage.get("visual_concept") or None
    executed = passage.get("executed_treatment") or (
        "talking_head" if passage.get("visual_need") == "talking_head" else "supporting_broll"
    )
    scene = {
        "sceneId": f"passage_{index:02d}",
        "start": round(start, 3),
        "end": round(end, 3),
        "quote": quote,
        "intent": passage.get("intent"),
        "narrativeRole": passage.get("narrative_role"),
        "kind": executed,
        "visualTreatment": passage.get("visual_treatment") or executed,
        "fallbackTreatment": passage.get("fallback_treatment"),
        "semanticReason": passage.get("semantic_reason"),
        "rendererCapability": {
            "treatment": executed,
            "component": passage.get("renderer_capability"),
            "stagedRequired": executed in {"supporting_broll", "pip"},
        },
        "query": None,
        "background": {},
        "speaker": {"layout": "speaker_fullscreen", "framing": "fullscreen"},
    }
    folded_quote = "".join(quote.split())
    card = str(concept) if concept and "".join(str(concept).split()) in folded_quote else quote[:48]
    if executed == "talking_head":
        scene["sceneComposition"] = {"speakerPresentation": "fullscreen"}
    elif executed in {"supporting_broll", "pip"}:
        scene["speaker"] = {
            "layout": "speaker_with_media" if executed == "pip" else "speaker_split_right",
            "framing": "pip" if executed == "pip" else "split",
        }
        scene["query"] = concept
        scene["background"] = {"query": concept}
    elif executed == "kinetic_typography":
        scene["cardMode"] = "progressive_one"
        scene["typography"] = {"cardMode": "progressive_one", "animate": "pop", "cards": [{"title": card, "explanation": ""}]}
        scene["execution"] = {"cardMode": "progressive_one"}
    elif executed == "process":
        scene["typography"] = {"steps": [quote[:80]], "stepsTitle": card[:40]}
    elif executed == "comparison":
        from .semantic_planner import _sides
        parts = _sides(str(concept or ""), quote)[:2]
        scene["cardMode"] = "progressive_one"
        scene["typography"] = {"cardMode": "progressive_one", "animate": "pop", "cards": [{"title": part, "explanation": ""} for part in parts]}
    return scene


_ORDINAL_NUM = set("一二三四五六七八九十")
_ACCENT = ("四种证据链", "反洗钱", "拒签")


def _flatten_words(transcript: list | None) -> list[dict]:
    words = []
    for row in transcript or []:
        if not isinstance(row, dict):
            continue
        for token in row.get("words") or []:
            if not isinstance(token, dict):
                continue
            text = str(token.get("text") or "")
            if not text:
                continue
            try:
                start = float(token.get("start"))
                end = float(token.get("end"))
            except (TypeError, ValueError):
                continue
            if end <= start:
                continue
            words.append({"text": text, "start": start, "end": end})
    return words


def _locate_quote(words: list[dict], quote: str) -> tuple[float, float] | None:
    target = "".join(str(quote or "").split())
    if not target or not words:
        return None
    text = "".join(item["text"] for item in words)
    index = text.find(target)
    if index < 0:
        return None
    last = index + len(target) - 1
    if last >= len(words):
        return None
    return float(words[index]["start"]), float(words[last]["end"])


def _slice_text(words: list[dict], start: float, end: float) -> str:
    return "".join(
        item["text"] for item in words
        if float(item["end"]) > start + 0.001 and float(item["start"]) < end - 0.001
    )


def _chain_label(text: str) -> str | None:
    if "合法的证据" in text:
        return "合法的证据"
    for token in (
        "原始积累证明", "资产变现链条", "跨境路径合规性", "监管账户",
        "四种证据链", "反洗钱", "拒签",
    ):
        if token in text:
            return token
    body = re.sub(r"^第[一二三四五六七八九十]+叫?", "", text)
    body = re.split(r"包括|或者|以及", body)[0]
    body = body[:8]
    return body or None


def _ordinal_marks(words: list[dict], start: float, end: float) -> list[int]:
    window = [
        item for item in words
        if float(item["end"]) > start + 0.001 and float(item["start"]) < end - 0.001
    ]
    marks = []
    for index, item in enumerate(window[:-1]):
        if item["text"] == "第" and window[index + 1]["text"] in _ORDINAL_NUM:
            marks.append(index)
    return marks


# Examples that occur as contiguous text inside one evidence item. Nothing else is added.
_ITEM_EXAMPLES = {
    "原始积累证明": ("工资完税单", "分红凭证", "股东决议"),
    "资产变现链条": ("房产买卖合同", "股权转让协议", "银行完税流水"),
    "合法的证据": ("协议", "资金来源"),
    "跨境路径合规性": ("监管账户",),
    "监管账户": (),
}


def _example_cues(label: str, words: list[dict], start: float, end: float, examples: list[str] | None = None) -> list[dict]:
    window = [
        item for item in words
        if float(item["end"]) > start + 0.001 and float(item["start"]) < end - 0.001
    ]
    text = "".join(item["text"] for item in window)
    label_at = text.find(label)
    if window and 0 <= label_at < len(window):
        cue_start = float(window[label_at]["start"])
    else:
        cue_start = float(window[0]["start"]) if window else start
    cues = [{"text": label, "start": round(cue_start, 3)}]
    cursor = label_at + len(label) if label_at >= 0 else 0
    for example in (examples if examples is not None else _ITEM_EXAMPLES.get(label, ())):
        at = text.find(example, cursor)
        if at < 0 or at >= len(window):
            continue
        cues.append({"text": example, "start": round(float(window[at]["start"]), 3)})
        cursor = at + len(example)
    return cues


def _label_scene(index: int, start: float, end: float, quote: str, label: str, words: list[dict] | None = None, examples: list[str] | None = None, reason: str | None = None) -> dict:
    scene = _scene_from_passage(index, start, end, {
        "quote": quote,
        "intent": label,
        "narrative_role": "evidence",
        "executed_treatment": "process",
        "visual_treatment": "process",
        "visual_concept": label,
        "semantic_reason": reason or "spoken ordinal",
    })
    scene["kind"] = "process"
    scene["query"] = None
    scene["background"] = {}
    scene["speaker"] = {"layout": "speaker_split_right", "framing": "split", "visibility": "primary"}
    scene["sceneComposition"] = {"speakerPresentation": "split", "editorial": "spoken-split"}
    cues = _example_cues(label, words or [], start, end, examples)
    scene["typography"] = {
        "steps": [cue["text"] for cue in cues],
        "stepsTitle": label,
        "cardMode": "none",
        "stepCues": cues,
    }
    scene["steps"] = [cue["text"] for cue in cues]
    scene["spokenStructure"] = {"evidence": True}
    scene["ordinalGraphic"] = True
    scene["mediaDecision"] = {"status": "NO_ASSET", "reason": "spoken_label", "searched": False}
    return scene


def _head_scene(index: int, start: float, end: float, quote: str) -> dict:
    scene = _scene_from_passage(index, start, end, {
        "quote": quote,
        "intent": "speech",
        "narrative_role": "context",
        "executed_treatment": "talking_head",
        "visual_treatment": "talking_head",
        "visual_concept": None,
    })
    scene["kind"] = "talking_head"
    scene["query"] = None
    scene["background"] = {}
    scene["speaker"] = {"layout": "speaker_fullscreen", "framing": "fullscreen"}
    scene["sceneComposition"] = {"speakerPresentation": "fullscreen"}
    scene["typography"] = {}
    scene["mediaDecision"] = {"status": "NO_ASSET", "reason": "talking_head", "searched": False}
    return scene


def _split_piece(start: float, end: float, words: list[dict]) -> list[tuple[float, float, str | None]]:
    """One primary scene per spoken ordinal. Times are the aligner tokens."""
    window = [
        item for item in words
        if float(item["end"]) > start + 0.001 and float(item["start"]) < end - 0.001
    ]
    if len(window) < 2:
        return [(start, end, None)]
    marks = []
    for index, item in enumerate(window[:-1]):
        if item["text"] == "第" and window[index + 1]["text"] in _ORDINAL_NUM:
            marks.append(index)
    pieces: list[tuple[float, float, str | None]] = []
    if not marks:
        text = "".join(item["text"] for item in window)
        accent_at = [(text.find(token), token) for token in _ACCENT if token in text]
        accent_at = [(pos, token) for pos, token in accent_at if pos >= 0]
        if not accent_at:
            return [(start, end, None)]
        accent_at.sort()
        cursor = start
        for pos, token in accent_at:
            at = float(window[pos]["start"])
            if at - cursor > 0.4:
                pieces.append((cursor, at, None))
            hold = min(end, max(float(window[min(len(window) - 1, pos + len(token) - 1)]["end"]), at + 3.2))
            nxt = next((float(window[other]["start"]) for other, _token in accent_at if float(window[other]["start"]) > at + 0.2), end)
            hold = min(hold, nxt)
            if hold - at >= 1.2:
                pieces.append((at, hold, token))
                cursor = hold
        if end - cursor > 0.4:
            pieces.append((cursor, end, None))
        return pieces or [(start, end, None)]
    if marks[0] > 0:
        pieces.extend(_split_piece(start, float(window[marks[0]]["start"]), words))
    for nth, index in enumerate(marks):
        piece_end = float(window[marks[nth + 1]]["start"]) if nth + 1 < len(marks) else end
        text = "".join(item["text"] for item in window[index:])
        if nth + 1 < len(marks):
            text = "".join(item["text"] for item in window[index:marks[nth + 1]])
        label = _chain_label(text)
        if label and piece_end - float(window[index]["start"]) >= 0.8:
            pieces.append((float(window[index]["start"]), piece_end, label))
        else:
            pieces.append((float(window[index]["start"]), piece_end, None))
    return pieces


def _scenes_from_supplied_labels(passages: list[dict], words: list[dict]) -> list[dict] | None:
    """Use labels the plan copied from each quote. Gaps stay a talking head."""
    located = []
    for passage in passages:
        span = _locate_quote(words, str(passage.get("quote") or ""))
        if span is None:
            return None
        located.append((span[0], span[1], passage))
    located.sort(key=lambda item: (item[0], item[1]))
    duration = float(words[-1]["end"])
    scenes = []
    cursor = 0.0
    index = 1
    for start, end, passage in located:
        nxt = None
        for other_start, _other_end, _other in located:
            if other_start > start + 0.05:
                nxt = other_start
                break
        if nxt is not None:
            end = min(end, nxt)
        if start - cursor > 0.45:
            scenes.append(_head_scene(index, cursor, start, _slice_text(words, cursor, start)))
            index += 1
        if end - start < 0.45:
            cursor = max(cursor, end)
            continue
        labels = [str(item) for item in (passage.get("labels") or []) if str(item)]
        quote = _slice_text(words, start, end) or str(passage.get("quote") or "")
        executed = passage.get("executed_treatment") or passage.get("visual_treatment") or "talking_head"
        reason = str(passage.get("semantic_reason") or "") or None
        if executed == "process" and labels:
            scenes.append(_label_scene(index, start, end, quote, labels[0], words, labels[1:], reason=reason))
        elif executed in {"comparison", "kinetic_typography"} and labels:
            scene = _scene_from_passage(index, start, end, {**passage, "quote": quote, "semantic_reason": reason or passage.get("semantic_reason")})
            cards = [{"title": label, "explanation": ""} for label in labels]
            scene["cardMode"] = "progressive_one"
            scene["criteriaCards"] = cards
            scene["typography"] = {"cardMode": "progressive_one", "animate": "pop", "cards": cards}
            scene["start"] = round(start, 3)
            scene["end"] = round(end, 3)
            scenes.append(scene)
        elif executed in {"supporting_broll", "pip"}:
            scene = _scene_from_passage(index, start, end, {**passage, "quote": quote})
            scene["start"] = round(start, 3)
            scene["end"] = round(end, 3)
            asset_id = str(passage.get("visual_concept") or "")
            if asset_id:
                scene["assetId"] = asset_id
                scene["background"] = {"assetId": asset_id}
            scenes.append(scene)
        else:
            scenes.append(_head_scene(index, start, end, quote))
        index += 1
        cursor = end
    if duration - cursor > 0.35 and scenes:
        scenes.append(_head_scene(index, cursor, duration, _slice_text(words, cursor, duration)))
    elif scenes:
        last = scenes[-1]
        last["end"] = max(float(last["end"]), duration)
    return scenes or None


def _scenes_from_word_times(passages: list[dict], words: list[dict]) -> list[dict] | None:
    if any(passage.get("labels") for passage in passages):
        labeled = _scenes_from_supplied_labels(passages, words)
        if labeled:
            return labeled
    located = []
    for passage in passages:
        span = _locate_quote(words, str(passage.get("quote") or ""))
        if span is None:
            return None
        located.append((span[0], span[1], passage))
    located.sort(key=lambda item: (item[0], item[1]))
    duration = float(words[-1]["end"])
    clipped = []
    for index, (start, end, passage) in enumerate(located):
        nxt = located[index + 1][0] if index + 1 < len(located) else duration
        end = min(end, nxt)
        if end - start >= 0.45:
            clipped.append((start, end, passage))
    scenes = []
    cursor = 0.0
    pieces: list[tuple[float, float, str | None, str]] = []

    def _add_span(start: float, end: float) -> None:
        for piece_start, piece_end, label in _split_piece(start, end, words):
            pieces.append((piece_start, piece_end, label, _slice_text(words, piece_start, piece_end)))

    for start, end, passage in clipped:
        if start - cursor > 0.55:
            _add_span(cursor, start)
        _add_span(start, end)
        cursor = end
    if duration - cursor > 0.55:
        _add_span(cursor, duration)
    elif pieces:
        start, _end, label, quote = pieces[-1]
        pieces[-1] = (start, duration, label, quote)
    # A clause after 第N that does not open the next item still belongs to that item.
    folded: list[tuple[float, float, str | None, str]] = []
    for start, end, label, quote in pieces:
        if (
            folded and label is None and folded[-1][2] == "跨境路径合规性"
            and "监管账户" in (quote or "")
        ):
            folded.append((start, end, "监管账户", quote))
            continue
        if folded and label is None and folded[-1][2] in {
            "原始积累证明", "资产变现链条", "合法的证据", "跨境路径合规性",
        }:
            prev = folded[-1]
            folded[-1] = (prev[0], end, prev[2], (prev[3] or "") + (quote or ""))
            continue
        folded.append((start, end, label, quote))
    pieces = folded
    # Abut so a breath between phrases is not an empty frame.
    abutted = []
    for index, (start, end, label, quote) in enumerate(pieces):
        if abutted and start - abutted[-1][1] < 0.8:
            prev = abutted[-1]
            abutted[-1] = (prev[0], start, prev[2], prev[3])
        if end - start < 0.35:
            continue
        abutted.append((start, end, label, quote))
    if abutted:
        start, _end, label, quote = abutted[-1]
        abutted[-1] = (start, max(_end, duration), label, quote)
    for index, (start, end, label, quote) in enumerate(abutted, start=1):
        if label and label in (quote or ""):
            scenes.append(_label_scene(index, start, end, quote, label, words))
        else:
            scenes.append(_head_scene(index, start, end, quote))
    return scenes or None


def apply_semantic_beats(plan: dict, pid: str, transcript: list | None = None) -> dict:
    """Replace heuristic scene slices with passage windows taken from real segment times."""
    from .semantic_planner import PlannerError, load_valid, planner_required

    ids, times, _text = _index(transcript)
    try:
        semantic = load_valid(pid, ids) if ids else None
    except PlannerError:
        raise
    if not semantic:
        if planner_required():
            raise PlannerError("PLANNER_UNAVAILABLE")
        return plan
    words = _flatten_words(transcript)
    labeled = any(passage.get("labels") for passage in semantic.get("passages") or [])
    if semantic.get("planner") == "openrouter" and labeled and not words:
        raise PlannerError("PLANNER_INVALID", "aligner_words_missing")
    word_scenes = _scenes_from_word_times(semantic["passages"], words) if words else None
    if semantic.get("planner") == "openrouter" and labeled and words and not word_scenes:
        raise PlannerError("PLANNER_INVALID", "quote_not_in_words")
    if word_scenes:
        out = dict(plan)
        out["scenes"] = word_scenes
        out["beatWeights"] = [round((scene["end"] - scene["start"]) * 1000) for scene in word_scenes]
        out["form"] = "semantic"
        out["director"] = "semantic_openrouter"
        out["directorMode"] = "semantic_openrouter"
        out.pop("heroObject", None)
        out["semanticPlan"] = {
            "topic": semantic.get("topic"),
            "model": semantic.get("model"),
            "planner": semantic.get("planner"),
            "planHash": semantic.get("planHash"),
            "transcriptVersion": semantic.get("transcript_version"),
            "timing": "aligner_words",
        }
        if semantic.get("planner") == "openrouter":
            out["editorialAuthority"] = "openrouter"
            out["durationSeconds"] = word_scenes[-1]["end"]
        return out
    scenes = []
    ordered = []
    for passage in semantic["passages"]:
        span = [times[sid] for sid in passage["segment_ids"] if sid in times]
        if not span:
            raise PlannerError("PLANNER_INVALID")
        start = min(item[0] for item in span)
        end = max(item[1] for item in span)
        if end <= start:
            raise PlannerError("PLANNER_INVALID")
        ordered.append((start, end, passage))
    ordered.sort(key=lambda item: item[0])
    for index, (start, end, passage) in enumerate(ordered, start=1):
        scenes.append(_scene_from_passage(index, start, end, passage))
    out = dict(plan)
    out["scenes"] = scenes
    out["beatWeights"] = [round((scene["end"] - scene["start"]) * 1000) for scene in scenes]
    out["form"] = "semantic"
    out["director"] = "semantic_openrouter"
    out["directorMode"] = "semantic_openrouter"
    out.pop("heroObject", None)
    out["semanticPlan"] = {
        "topic": semantic.get("topic"),
        "model": semantic.get("model"),
        "planner": semantic.get("planner"),
        "planHash": semantic.get("planHash"),
        "transcriptVersion": semantic.get("transcript_version"),
        "timing": "segment_times",
    }
    if semantic.get("planner") == "openrouter":
        out["editorialAuthority"] = "openrouter"
        out["durationSeconds"] = scenes[-1]["end"]
    return out


def revalidate_assets(plan: dict, pid: str, transcript: list | None = None, catalog: list[dict] | None = None) -> dict:
    """Drop assets that V11 query rewriting no longer supports."""
    from .semantic_planner import PlannerError, load_valid, planner_required

    ids, times, _text = _index(transcript)
    semantic = load_valid(pid, ids) if ids else None
    if not semantic:
        if planner_required():
            raise PlannerError("PLANNER_UNAVAILABLE")
        return plan
    out = dict(plan)
    scenes = []
    for scene in out.get("scenes") or []:
        scene = dict(scene)
        steps = list((scene.get("typography") or {}).get("steps") or scene.get("steps") or [])
        if steps:
            _clear(scene, "spoken_label")
            scene["typography"] = {**(scene.get("typography") or {}), "steps": steps, "cardMode": "none"}
            scene["steps"] = steps
            scene["sceneComposition"] = {
                **(scene.get("sceneComposition") or {}),
                "speakerPresentation": "split",
                "editorial": "spoken-split",
            }
            scenes.append(scene)
            continue
        start = float(scene.get("start") or 0)
        end = float(scene.get("end") or start)
        related = []
        for passage in semantic["passages"]:
            covered = sum(
                _overlap(start, end, *times[sid]) for sid in passage["segment_ids"] if sid in times
            )
            if covered > 0:
                related.append((covered, passage))
        related.sort(key=lambda item: item[0], reverse=True)
        passage = related[0][1] if related else None
        concept = (passage or {}).get("visual_concept") or None
        quote = (passage or {}).get("quote") or scene.get("quote") or ""
        executed = (passage or {}).get("executed_treatment") or (passage or {}).get("visual_need")
        if not passage or executed not in {"supporting_broll", "pip"} or not concept:
            reason = "no_passage" if not passage else (executed or "talking_head")
            _clear(scene, reason)
            if passage and executed not in {"supporting_broll", "pip"}:
                scene["mediaDecision"] = {"status": "NO_ASSET", "reason": reason, "searched": False}
            scenes.append(scene)
            continue
        assets = list(catalog or [])
        if catalog is None:
            assets = _library(concept)
        decision = select_asset(concept, quote, assets)
        scene["mediaDecision"] = decision
        if decision.get("status") != "selected":
            _clear(scene, decision.get("reason") or "NO_MATCH")
            scene["mediaDecision"] = decision
        else:
            background = dict(scene.get("background") or {})
            background["assetId"] = decision["assetId"]
            background["file"] = decision.get("file")
            background["query"] = concept
            scene["background"] = background
            scene["assetId"] = decision["assetId"]
            scene["query"] = concept
        scenes.append(scene)
    out["scenes"] = scenes
    return out


def _clear(scene: dict, reason: str) -> None:
    scene["query"] = None
    scene.pop("assetId", None)
    background = dict(scene.get("background") or {})
    for key in ("assetId", "file", "query", "conceptId"):
        background.pop(key, None)
    scene["background"] = background
    scene["mediaDecision"] = {"status": "NO_MATCH", "reason": reason}


def absolute_bounds(scenes: list[dict], duration: float, fps: int = 30) -> tuple[int, list[tuple[int, int]]]:
    """Same cut math as DirectorV3 beatsFromBounds. One frame is the tolerance."""
    frames = max(fps, round(float(duration) * fps))
    beats = []
    for scene in scenes:
        start = int(round(float(scene["start"]) * fps))
        end = int(round(float(scene["end"]) * fps))
        start = max(0, min(start, max(0, frames - 1)))
        end = max(start + 1, min(frames, end))
        beats.append((start, end))
    return frames, beats


def _library(concept: str) -> list[dict]:
    try:
        from search import search_assets
    except ImportError:
        return []
    root = Path(__file__).resolve().parent.parent / "media" / "library" / "out"
    found = search_assets(concept, limit=24) or []
    assets = []
    for hit in found:
        if not isinstance(hit, dict):
            continue
        file_name = hit.get("file") or hit.get("path")
        if not file_name or not (root / str(file_name)).is_file():
            continue
        description = hit.get("description") or hit.get("caption")
        if isinstance(description, dict):
            description = " ".join(str(value) for value in description.values())
        assets.append({
            "id": hit.get("id"),
            "file": file_name,
            "title": hit.get("title"),
            "description": description,
            "tags": " ".join(hit.get("tags") or []) if isinstance(hit.get("tags"), list) else hit.get("tags"),
            "status": hit.get("status") or hit.get("reviewStatus") or "reviewed",
            "category": hit.get("category"),
            "visualFamily": hit.get("visualFamily"),
        })
    return assets


def bound_semantic_duration(plan: dict, seconds: float) -> dict:
    """Respect the requested picture length without stretching speech windows."""
    from .semantic_planner import PlannerError
    scenes = []
    for scene in plan.get("scenes") or []:
        start = max(0.0, float(scene.get("start") or 0))
        end = min(float(seconds), float(scene.get("end") or 0))
        if end > start:
            scenes.append({**scene, "start": start, "end": end})
    if not scenes:
        raise PlannerError("PLANNER_INVALID", "no_passage_in_requested_duration")
    # The picture is longer than the last aligner token by a few frames.
    # Leaving that gap paints the empty stage color as a dark end frame.
    tail = float(seconds) - float(scenes[-1]["end"])
    if 0 < tail <= 0.5:
        scenes[-1] = {**scenes[-1], "end": float(seconds)}
    return {**plan, "scenes": scenes, "beatWeights": [round((s["end"] - s["start"]) * 1000) for s in scenes]}
