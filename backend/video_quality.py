"""Machine checks for a plan. They do not judge whether the film looks directed."""

from __future__ import annotations


def validate_plan(plan: dict, transcript: list[dict]) -> dict:
    findings = []
    texts = []
    for row in transcript or []:
        if isinstance(row, dict):
            texts.append(str(row.get("text") or row.get("original") or ""))
    spoken = " ".join(texts)
    for scene in plan.get("scenes") or []:
        query = scene.get("query")
        decision = scene.get("mediaDecision") or {}
        if decision.get("status") == "NO_MATCH" and scene.get("background", {}).get("assetId"):
            findings.append({"code": "asset_on_no_match", "scene": scene.get("sceneId")})
        asset = (scene.get("background") or {}).get("assetId")
        if asset and decision.get("status") not in {None, "selected", "NO_MATCH"}:
            findings.append({"code": "unexplained_asset", "scene": scene.get("sceneId"), "asset": asset})
        caption = scene.get("caption") or scene.get("headline") or ""
        if caption and spoken and caption not in spoken and len(str(caption)) > 12:
            findings.append({"code": "caption_not_in_transcript", "scene": scene.get("sceneId")})
    return {
        "ok": not findings,
        "findings": findings,
        "humanReviewRequired": True,
        "checks": ["transcript_anchor", "no_match_keeps_speaker"],
    }
