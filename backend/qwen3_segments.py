"""Group character timings into spoken lines. No model and no invented times."""

from __future__ import annotations

_BREAKS = set("。！？!?；;")


def group_tokens(tokens: list[dict], raw: str = "", *, gap: float = 0.45) -> tuple[list[dict], list[dict]]:
    """Split on the recognizer's punctuation. Token times are not invented."""
    segments: list[dict] = []
    uncertain: list[dict] = []
    timed: list[dict] = []
    for token in tokens or []:
        text = str(token.get("text") or "")
        if not text:
            continue
        start = round(float(token.get("start") or 0), 3)
        end = round(float(token.get("end") or 0), 3)
        if end <= start:
            uncertain.append({"text": text, "start": start, "end": end, "reason": "zero_duration"})
            continue
        timed.append({"text": text, "start": start, "end": end})
    if not raw:
        raw = "".join(token["text"] for token in timed)
    words: list[dict] = []
    pieces: list[str] = []

    def close() -> None:
        nonlocal words, pieces
        if not words:
            pieces = []
            return
        segments.append({
            "text": "".join(pieces),
            "start": words[0]["start"],
            "end": words[-1]["end"],
            "words": words,
        })
        words = []
        pieces = []

    index = 0
    for char in raw:
        if index < len(timed) and timed[index]["text"] == char:
            if words and timed[index]["start"] - words[-1]["end"] >= gap:
                close()
            words.append(timed[index])
            pieces.append(timed[index]["text"])
            index += 1
            continue
        if char.isspace():
            continue
        pieces.append(char)
        if char in _BREAKS:
            close()
    while index < len(timed):
        words.append(timed[index])
        pieces.append(timed[index]["text"])
        index += 1
    close()
    return segments, uncertain
