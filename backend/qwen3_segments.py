"""Group aligner tokens into spoken lines. Times come only from the aligner."""

from __future__ import annotations

_BREAKS = set("。！？!?；;")


def group_tokens(tokens: list[dict], raw: str = "", *, gap: float = 0.45) -> tuple[list[dict], list[dict]]:
    """Split on punctuation the aligner already timed, or on a silence gap."""
    del raw
    segments: list[dict] = []
    uncertain: list[dict] = []
    words: list[dict] = []

    def close() -> None:
        nonlocal words
        if not words:
            return
        segments.append({
            "text": "".join(word["text"] for word in words).strip(),
            "start": words[0]["start"],
            "end": words[-1]["end"],
            "words": list(words),
        })
        words = []

    for token in tokens or []:
        text = str(token.get("text") or "")
        if not text:
            continue
        start = round(float(token.get("start") or 0), 3)
        end = round(float(token.get("end") or 0), 3)
        if end <= start:
            uncertain.append({"text": text, "start": start, "end": end, "reason": "zero_duration"})
            continue
        if words and start - words[-1]["end"] >= gap:
            close()
        words.append({"text": text, "start": start, "end": end})
        if any(char in _BREAKS for char in text):
            close()
    close()
    return segments, uncertain
