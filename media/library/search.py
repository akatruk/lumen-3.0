"""Find a library asset from a meaning, not a filename."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "out"
MANIFEST = ROOT / "manifest.json"


# Meaning in Russian or Chinese points at the same English-tagged asset. Files stay language-neutral.
_QUERY_ALIASES = (
    ("семья покупает квартиру", "family buyer apartment"),
    ("家庭购买公寓", "family purchase apartment"),
    ("недвижимость", "property real estate"),
    ("квартир", "apartment"),
    ("семья", "family"),
    ("покупа", "buyer purchase"),
    ("локац", "location"),
    ("расположен", "location"),
    ("доходность", "yield"),
    ("аренда", "rental"),
    ("документы", "documents"),
    ("инвест", "investor investment"),
    ("переезд", "relocation"),
    ("планир", "planning"),
    ("неуверен", "uncertainty decision"),
    ("одобрен", "approval success"),
    ("чемодан", "suitcase packing"),
    ("город", "city"),
    ("计划", "planning"),
    ("国际", "international"),
    ("второй паспорт", "second passport citizenship"),
    ("второе гражданство", "second citizenship passport"),
    ("иммиграц", "immigration"),
    ("консультац", "consultation"),
    ("эмиграц", "emigration relocation"),
    ("гражданств", "citizenship"),
    ("резидент", "residency residence"),
    ("внж", "residence permit"),
    ("пмж", "permanent residence"),
    ("виз", "visa"),
    ("паспорт", "passport"),
    ("релокац", "relocation"),
    ("номад", "digital nomad"),
    ("налогов", "tax residency"),
    ("第二护照", "second passport"),
    ("移民", "immigration relocation"),
    ("海外移居", "overseas immigration relocation"),
    ("海外移民", "overseas immigration relocation"),
    ("移居", "relocation immigration"),
    ("居留", "residence permit"),
    ("公民", "citizenship"),
    ("签证", "visa"),
    ("护照", "passport"),
    ("搬家", "relocation moving"),
    ("税务", "tax residency"),
    ("公寓", "apartment"),
    ("家庭", "family"),
    ("购买", "purchase"),
    ("地段", "location"),
    ("租金", "rental"),
    ("回报", "yield"),
    ("房产", "property"),
    ("顾问咨询会议", "consultation meeting advisor"),
    ("顾问客户文件", "advisor client documents"),
    ("顾问", "advisor consultation"),
    ("咨询", "consultation"),
    ("电话咨询", "phone consultation"),
    ("电话咨询办公室", "phone consultation office"),
    ("抵达新城市", "city arrival"),
    ("新城市", "city"),
    ("文件审核桌面", "document review desk"),
    ("文件审核", "document review"),
    ("不确定的决定", "uncertainty decision"),
    ("不确定", "uncertainty"),
    ("проверка документов", "document review"),
    ("на столе", "desk"),
    ("заявление на внж", "residency application residence permit"),
    # Cinematic Env Factory V6 — environmental cinema (not V5 abstract plates)
    ("premium business meeting background", "premium business meeting office cinematic background"),
    ("премиальный фон деловой встречи", "premium business meeting office cinematic background"),
    ("高端商务会议背景", "premium business meeting office cinematic background"),
    ("modern condominium interior", "premium condominium apartment interior cinematic background"),
    ("современный интерьер кондоминиума", "premium condominium apartment interior cinematic background"),
    ("现代公寓室内", "premium condominium apartment interior cinematic background"),
    ("financial district skyline", "premium financial district skyline city cinematic background"),
    ("скайлайн финансового района", "premium financial district skyline city cinematic background"),
    ("金融区天际线", "premium financial district skyline city cinematic background"),
    ("киноматографичный фон", "cinematic environment background"),
    ("电影环境背景", "cinematic environment background"),
    ("деловая встреча инвесторов", "business investment meeting investors"),
    ("投资者商务会议", "business investment meeting investors"),
    ("business investment meeting", "business investment meeting investors"),
    # Original4 spoken checks. Cues are vocabulary, not measured claims.
    ("毛收益还是净收益", "gross yield versus net yield"),
    ("毛收益還是淨收益", "gross yield versus net yield"),
    ("毛售益", "gross yield"),
    ("金售益", "net yield"),
    ("毛收益", "gross yield"),
    ("净收益", "net yield"),
    ("淨收益", "net yield"),
    ("租金回报率", "rental yield gross net"),
    ("租金回報率", "rental yield gross net"),
    ("租金回报", "rental yield"),
    ("租金回報", "rental yield"),
    ("市场价值", "market value resale"),
    ("市場價值", "market value resale"),
    ("转售", "resale"),
    ("轉售", "resale"),
    ("本地人", "local buyer"),
    ("下一位买家", "next buyer pool"),
    ("下一位買家", "next buyer pool"),
    ("物业", "operating cost"),
    ("物業", "operating cost"),
    ("管理费", "management cost"),
    ("管理費", "management cost"),
    ("税后", "after tax"),
    ("稅後", "after tax"),
    ("валовая доходность", "gross yield"),
    ("чистая доходность", "net yield"),
    ("перепродажа", "resale"),
    ("рыночная стоимость", "market value resale"),
    ("местный покупатель", "local buyer"),
)


def normalize_query(text):
    query = text or ""
    try:
        from concepts import PHRASES
    except ImportError:
        from media.library.concepts import PHRASES
    try:
        from concept_triggers import expand_query as _expand_concept
    except ImportError:
        from media.library.concept_triggers import expand_query as _expand_concept
    # Case-fold Latin/Cyrillic so «ВНЖ» still hits the «внж» phrase.
    folded = query.casefold()
    pairs = list(PHRASES) + list(_QUERY_ALIASES)
    pairs.sort(key=lambda item: len(item[0]), reverse=True)
    for source, english in pairs:
        needle = source.casefold()
        start = 0
        while True:
            at = folded.find(needle, start)
            if at < 0:
                break
            query = query[:at] + f" {english} " + query[at + len(source):]
            folded = query.casefold()
            start = at + len(english) + 2
    return _expand_concept(query)


_STOP = frozenset({
    "a", "an", "the", "in", "on", "of", "for", "to", "and", "or", "with",
    "before", "into", "from", "at", "by", "is", "are",
})

# A spoken form should still find the tag the library already uses.
_EXPAND = {
    "arriving": ("arrival",),
    "arrive": ("arrival",),
    "considering": ("planning", "decision"),
    "choosing": ("comparison", "decision"),
    "successful": ("approval", "success"),
    "preparation": ("documents", "application"),
    "abroad": ("international", "relocation"),
    "owner": ("business", "entrepreneur"),
    "uncertainty": ("uncertainty", "decision"),
}

_SCENE = frozenset({
    "family", "couple", "planning", "packing", "arrival", "apartment", "viewing",
    "consultation", "city", "travel", "luggage", "advisor", "buyer", "home",
    "suitcase", "departure", "uncertainty", "decision", "document", "documents",
    "property", "investment", "business", "approval", "passport", "route",
})


def _tokens(text):
    # Latin + digits + Cyrillic + CJK — do not drop RU/ZH tags from the haystack.
    blob = normalize_query(text).lower()
    return re.findall(r"[a-z0-9]+|[\u0400-\u04ff]+|[\u4e00-\u9fff]+", blob)


def _query_words(query):
    words = []
    for part in _tokens(query):
        if part in _STOP or len(part) < 2:
            continue
        words.append(part)
        words.extend(_EXPAND.get(part, ()))
    return list(dict.fromkeys(words))


def _overlay_path():
    return Path(__file__).resolve().parent / "localized_overlay.json"


def load(path=None):
    file = Path(path) if path else MANIFEST
    data = json.loads(file.read_text())
    assets = data["assets"] if isinstance(data, dict) else data
    overlay_file = _overlay_path()
    if not overlay_file.is_file():
        return assets
    overlay = json.loads(overlay_file.read_text())
    rows = overlay.get("assets") if isinstance(overlay, dict) else overlay
    by_id = {row.get("id"): row for row in rows or [] if row.get("id")}
    if not by_id:
        return assets
    merged = []
    for asset in assets:
        extra = by_id.get(asset.get("id"))
        if not extra:
            merged.append(asset)
            continue
        row = dict(asset)
        for key in ("tags_ru", "tags_zh", "localized", "conceptId"):
            if extra.get(key) and not row.get(key):
                row[key] = extra[key]
        merged.append(row)
    return _merge_visual_index(merged, file)


def _merge_visual_index(assets, manifest_path):
    index_file = Path(manifest_path).parent / "visual-index.json"
    if not index_file.is_file():
        return assets
    payload = json.loads(index_file.read_text(encoding="utf-8"))
    rows = payload.get("assets") if isinstance(payload, dict) else None
    if not isinstance(rows, dict):
        return assets
    merged = []
    for asset in assets:
        extra = rows.get(asset.get("id"))
        if not extra:
            merged.append(asset)
            continue
        row = dict(asset)
        if extra.get("frameReviewed") and extra.get("visible"):
            row["reviewedVisible"] = extra["visible"]
        if extra.get("admits"):
            row["visualAdmits"] = list(extra["admits"])
        retrieval = extra.get("retrieval")
        if retrieval:
            row["visualRetrieval"] = retrieval
        row["frameReviewed"] = bool(extra.get("frameReviewed"))
        row["visualReviewStatus"] = extra.get("reviewStatus")
        merged.append(row)
    return merged


def _joined(value):
    if isinstance(value, list):
        return " ".join(str(item) for item in value)
    return str(value or "")


def _localized(value):
    if isinstance(value, dict):
        return " ".join(str(item) for item in value.values())
    return _joined(value)


def _hay(asset):
    parts = [
        asset.get("id", ""),
        asset.get("conceptId", ""),
        _localized(asset.get("description")),
        _joined(asset.get("domain")),
        asset.get("visualFamily", ""),
        asset.get("action", ""),
        asset.get("environment", ""),
        asset.get("region", ""),
        asset.get("energy", ""),
        asset.get("motionPotential", ""),
        _localized(asset.get("tags")),
        _joined(asset.get("tags_ru")),
        _joined(asset.get("tags_zh")),
        " ".join(asset.get("subjects") or []),
        " ".join(asset.get("mood") or []),
        " ".join(asset.get("emotion") or []),
        " ".join(asset.get("sceneRoles") or []),
        " ".join(asset.get("recommendedTreatments") or []),
        " ".join(asset.get("propertyType") or []),
        " ".join(asset.get("textSafeAreas") or []),
        # Situations / actions / relationships (semantic coverage V1).
        " ".join(asset.get("situations") or []),
        " ".join(asset.get("actions") or []),
        " ".join(asset.get("relationships") or []),
        asset.get("matchMode") or "",
        asset.get("reviewedVisible") or "",
        _joined(asset.get("visualRetrieval")),
    ]
    blob = re.sub(r"\b(?:four|one|two|three|\d+)[\s-]seconds?\b", "duration", " ".join(parts), flags=re.I)
    return _tokens(blob)


# Query intent buckets for ranking (literal object vs lived situation vs abstract mark).
_LITERAL = frozenset({
    "passport", "document", "documents", "desk", "paperwork", "application", "stamp", "keys",
})
_SITUATION = frozenset({
    "family", "couple", "home", "door", "doorway", "arrival", "consultation", "meeting",
    "advisor", "packing", "travel", "apartment", "buyer", "phone",
})
_CONCEPTUAL = frozenset({
    "route", "path", "growth", "risk", "deadline", "comparison", "process", "steps",
})
_DECORATIVE_HINT = frozenset({"arrow", "mark", "overlay", "wipe", "icon"})


def _same_domain(asset, domain):
    value = asset.get("domain")
    if isinstance(value, list):
        return domain in value
    return value == domain


def _query_mode(words):
    """Classify the ask: situation > literal > conceptual > decorative."""
    w = set(words)
    if w & _DECORATIVE_HINT and not (w & _SITUATION) and not (w & _LITERAL):
        return "decorative"
    if w & _SITUATION:
        return "situational"
    if w & _LITERAL:
        return "literal"
    if w & _CONCEPTUAL:
        return "conceptual"
    return "contextual"


def _locale_blob(asset, locale):
    loc = asset.get("localized") or {}
    block = loc.get(locale) or {}
    parts = [
        block.get("title") or "",
        block.get("description") or "",
        " ".join(block.get("terms") or []),
    ]
    if str(locale).startswith("ru"):
        parts.append(_joined(asset.get("tags_ru")))
    elif str(locale).startswith("zh"):
        parts.append(_joined(asset.get("tags_zh")))
    return _tokens(" ".join(parts))


def _rank_score(asset, words, text_safe, preferred_scene_role, preferred_energy, preferred_composition=None, recent_ids=(), allow_empty=False, locale=None):
    hay = _hay(asset)
    overlap = sum(1 for word in words if word in hay)
    if overlap == 0 and not allow_empty:
        return None
    score = overlap * 2 + (asset.get("qualityScore") or 0)
    if locale:
        local = _locale_blob(asset, locale)
        score += 1.4 * sum(1 for word in words if word in local)
    family = asset.get("visualFamily") or ""
    category = asset.get("category") or ""
    mode = _query_mode(words)
    asset_mode = (asset.get("matchMode") or "").lower()
    if family == "premium_3d":
        # High-end 3D object plates — preferred for conceptual object queries.
        score += 2.1
    if asset.get("kind") == "3d_motion":
        score += 0.8
    elif family == "cinematic_environment":
        # V6 photoreal env stills/I2V — preferred for real-world background queries.
        score += 1.35
    elif family == "deterministic_motion":
        score += 0.45
    elif family == "generative_motion":
        score += 0.35
    elif family == "photography":
        score += 0.25
    elif category == "icons":
        score -= 0.25
    # V5 abstract Remotion plates must not win environmental / photographic BG asks.
    env_ask = bool(set(words) & {
        "background", "skyline", "office", "meeting", "condo", "condominium",
        "apartment", "city", "district", "cinematic", "environment", "boardroom",
        "lobby", "interior", "capital", "investment", "investor", "shareholder",
        "executive", "skyscraper", "фон", "背景", "капитал", "инвестиции",
        "акционер", "资本", "投资", "股东",
    })
    if env_ask and (asset.get("batch") or "") == "premium-media-factory-v5-batch1":
        if str(asset.get("id") or "").startswith("pmv5_bg_"):
            score -= 4.0
    if env_ask and family == "cinematic_environment":
        score += 2.0
        if (asset.get("type") or "") == "video":
            score += 0.8
    matched_scene = [word for word in words if word in _SCENE and word in hay]
    decorative = category == "decorative" or asset_mode == "decorative"
    asks_mark = any(word in words for word in ("arrow", "mark", "overlay", "transition", "wipe"))
    if matched_scene:
        if family == "photography":
            score += 2.4
        elif family == "cinematic_environment":
            score += 2.6
        elif family == "generative_motion":
            score += 2.1
        elif family == "editorial_object":
            score += 0.8
        elif family == "deterministic_motion":
            score += 1.2
        elif family == "premium_3d":
            score += 2.0
        elif decorative:
            score -= 3
        elif family in ("line", "") and category in ("icons", "immigration", "decorative"):
            score -= 0.6
    elif decorative and not asks_mark:
        score -= 1.5
    # Situation/action/relationship overlap beats loose tag soup.
    situ = set(_tokens(" ".join(asset.get("situations") or [])))
    acts = set(_tokens(" ".join(asset.get("actions") or [])))
    rels = set(_tokens(" ".join(asset.get("relationships") or [])))
    score += 1.6 * len(set(words) & situ)
    score += 1.2 * len(set(words) & acts)
    score += 1.1 * len(set(words) & rels)
    if mode == "situational" and family == "photography":
        score += 1.5
    if mode == "situational" and family == "cinematic_environment":
        score += 1.7
    if mode == "literal" and family == "editorial_object":
        score += 1.2
    if mode in ("literal", "conceptual") and family == "premium_3d":
        score += 1.4
    if preferred_scene_role in ("foreground_object", "semantic_object") and family == "premium_3d":
        score += 1.8
    if preferred_scene_role == "background" and family == "cinematic_environment":
        score += 1.6
    if mode == "situational" and decorative:
        score -= 2.5
    if mode == "literal" and decorative and not asks_mark:
        score -= 2.0
    if asset_mode and asset_mode == mode:
        score += 0.9
    roles = asset.get("sceneRoles") or []
    if preferred_scene_role and preferred_scene_role in roles:
        score += 1.8
    if preferred_energy and asset.get("energy") == preferred_energy:
        score += 0.8
    if text_safe and text_safe in (asset.get("textSafeAreas") or []):
        score += 1.5
    if preferred_composition and asset.get("composition") == preferred_composition:
        score += 1.6
    if asset.get("id") in set(recent_ids or ()):
        score -= 4.5
    # Curated editorial people plates beat anonymous RunPod stills when both match —
    # but not when the ask is a cinematic environment / skyline / office background.
    if (asset.get("id") or "").startswith("people_") and family == "photography" and not env_ask:
        score += 0.7
    # V6 cinematic env masters are intentional runpod photography/I2V — do not penalize.
    if asset.get("source") == "runpod" and mode == "situational" and family != "cinematic_environment":
        score -= 0.35
    if preferred_scene_role == "background" and family == "cinematic_environment" and (asset.get("type") or "") == "video":
        score += 1.2
    return score


# Manifest status values hidden from default search (cleanup V1). Ids preserved.
_HIDDEN_STATUS = frozenset({"quarantined", "rejected", "duplicate", "corrupt"})
# Not auto-retrieved until reviewed; ids stay in the manifest.
_HOLD_STATUS = frozenset({"needs_review", "unreviewed", "restricted", "planned"})
# Quality tiers that must not win auto ranking (cleanup classify).
_BLOCKED_QUALITY = frozenset({"LOW", "LEGACY", "UNCERTAIN", "CORRUPT"})
_MIN_QUALITY_SCORE = 0.35


def _eligible_for_auto(asset, *, include_hidden=False) -> bool:
    """Quality gate before ranking. Quarantine/reject never re-enter defaults."""
    status = asset.get("status") or "active"
    if not include_hidden and status in _HIDDEN_STATUS:
        return False
    if not include_hidden and status in _HOLD_STATUS:
        return False
    if (asset.get("qualityTier") or asset.get("quality") or "").upper() in _BLOCKED_QUALITY:
        return False
    score = asset.get("qualityScore")
    if score is not None and float(score) < _MIN_QUALITY_SCORE:
        return False
    # Missing Remotion stubs / broken paths must not be ranked as media.
    rel = asset.get("file") or ""
    if rel.startswith("motion/src/") or rel.endswith("scenes.tsx"):
        return False
    return True


# A named instrument is not admitted by a nearby theme. The asset must
# carry that ask in visualAdmits, which is set only after a frame review.
_SPECIFIC_ASKS = (
    ("property_sale_contract", ("房产买卖合同", "договор купли-продажи", "property sale contract")),
    ("equity_transfer_agreement", ("股权转让协议", "соглашение о передаче доли", "equity transfer agreement")),
    ("bank_ledger_document", ("银行完税流水", "банковская выписка", "bank ledger")),
    ("legal_agreement_document", ("证据协议", "правовое соглашение", "legal agreement")),
)


def specific_asks(query):
    folded = (query or "").casefold()
    return [ask for ask, needles in _SPECIFIC_ASKS if any(needle.casefold() in folded for needle in needles)]


def specific_block(query, asset):
    """Return a NO_MATCH reason when the picture was not reviewed for this ask."""
    asks = specific_asks(query)
    if not asks:
        return None
    admits = set(asset.get("visualAdmits") or [])
    missing = [ask for ask in asks if ask not in admits]
    if not missing:
        return None
    return "NO_MATCH:" + ",".join(missing)


def _unapproved_3d(asset) -> bool:
    if (asset.get("visualFamily") or "") == "premium_3d":
        return True
    if str(asset.get("id") or "").startswith("l3d_"):
        return True
    if asset.get("kind") == "3d_motion":
        return True
    return False


def _intelligence_on() -> bool:
    try:
        from backend.config import settings
    except Exception:
        return False
    return bool(getattr(settings, "visual_intelligence_enabled", False))


# Cosine below this does not admit an asset that has no keyword overlap.
_VECTOR_ONLY_MIN = 0.28


def _vector_bonuses(query: str) -> dict:
    """Asset id → cosine similarity. Empty when the flag is off or pgvector is unavailable."""
    if not _intelligence_on():
        return {}
    try:
        from backend.visual_intelligence import asset_similarities
        return asset_similarities(query)
    except Exception:
        return {}


def search_assets(
    query, type=None, category=None, aspect_ratio=None, composition=None, limit=5,
    path=None, text_safe=None, domain=None, exclude_ids=(), preferred_scene_role=None,
    preferred_energy=None, locale=None, preferred_composition=None, recent_ids=(),
    scene_role=None, text_position=None, excluded_asset_ids=(),
    include_hidden=False,
):
    """Rank assets by meaning, quality, role, and whether type can sit on them.

    text_safe prefers assets whose textSafeAreas include that side, without
    dropping a strong semantic match that has no composition note yet.
    exclude_ids drops files already used in the current video.
    include_hidden=True keeps quarantined/rejected rows (default: skip them).
    Quality eligibility runs before ranking — gaps fall through empty so Remotion
    can use typography / diagram / presenter instead of a placeholder.
    """
    words = _query_words(query)
    if (query or "").strip() and not words:
        return []
    intelligence = _intelligence_on()
    bonuses = _vector_bonuses(query) if intelligence and (query or "").strip() else {}
    skipped = set(exclude_ids or ()) | set(excluded_asset_ids or ())
    role = preferred_scene_role or scene_role
    safe = text_safe or text_position
    found = []
    stage = []
    for asset in load(path):
        if asset.get("id") in skipped:
            continue
        if not _eligible_for_auto(asset, include_hidden=include_hidden):
            continue
        if intelligence and _unapproved_3d(asset):
            continue
        if type and asset.get("type") != type:
            continue
        if category and asset.get("category") != category:
            continue
        if aspect_ratio and asset.get("aspectRatio") != aspect_ratio:
            continue
        if composition and asset.get("composition") != composition:
            continue
        if domain and not _same_domain(asset, domain):
            continue
        if specific_block(query, asset):
            continue
        bonus = float(bonuses.get(asset.get("id")) or 0)
        if intelligence:
            # Stage 1: keyword score, or a vector candidate when the keyword missed.
            # Cosine is not added here. Stage 2 reranks the pool.
            if not words:
                stage.append((asset.get("qualityScore") or 0, True, asset))
                continue
            score = _rank_score(
                asset, words, safe, role, preferred_energy,
                preferred_composition or composition, recent_ids, locale=locale,
            )
            if score is None:
                if bonus < 0.36:
                    continue
                stage.append((0.0, False, asset))
                continue
            if composition and asset.get("composition") == composition:
                score += 1.2
            stage.append((score, True, asset))
            continue
        if not words:
            score = (asset.get("qualityScore") or 0) + bonus * 3
        else:
            score = _rank_score(
                asset, words, safe, role, preferred_energy,
                preferred_composition or composition, recent_ids, locale=locale,
            )
            if score is None:
                if bonus < _VECTOR_ONLY_MIN:
                    continue
                score = _rank_score(
                    asset, words, safe, role, preferred_energy,
                    preferred_composition or composition, recent_ids,
                    allow_empty=True, locale=locale,
                )
                if score is None:
                    continue
                score += bonus * 4
            else:
                score += bonus * 3
            if composition and asset.get("composition") == composition:
                score += 1.2
        found.append((score, asset.get("qualityScore") or 0, asset))
    if intelligence:
        stage.sort(key=lambda item: item[0], reverse=True)
        lexical = [item for item in stage if item[1]][:24]
        vector_only = [item for item in stage if not item[1]]
        vector_only.sort(key=lambda item: float(bonuses.get(item[2].get("id")) or 0), reverse=True)
        pool = lexical + vector_only[: max(0, 28 - len(lexical))]
        penalties = {}
        try:
            from backend.experience_memory import asset_relevance_penalties
            penalties = asset_relevance_penalties()
        except Exception:
            penalties = {}
        try:
            from media.library.rerank import rerank_candidates
        except ImportError:
            from rerank import rerank_candidates
        return rerank_candidates(pool, words=words, bonuses=bonuses, limit=limit, penalties=penalties)
    found.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [asset for _, _, asset in found[:limit]]
