#!/usr/bin/env python3
"""Keyword vs semantic rerank.

Tag overlap is reported as a legacy number. nDCG uses intents_v2 judgments only.
Unlabeled assets are not counted as misses.
"""
from __future__ import annotations

import importlib.util
import json
import math
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.config import settings
from media.library.search import search_assets

_v1_spec = importlib.util.spec_from_file_location(
    'benchmark_visual_intelligence_v1',
    ROOT / 'scripts' / 'benchmark_visual_intelligence.py',
)
_v1 = importlib.util.module_from_spec(_v1_spec)
_v1_spec.loader.exec_module(_v1)
CASES = _v1.CASES
_metrics = _v1._metrics

DATASET = ROOT / 'media' / 'library' / 'relevance' / 'intents_v2.json'
GRADES = {
    'highly_relevant': 3,
    'relevant': 2,
    'weakly_relevant': 1,
    'irrelevant': 0,
}
BINARY = {'highly_relevant': 1, 'relevant': 1, 'weakly_relevant': 0, 'irrelevant': 0}


def _ndcg(ids: list[str], judgments: dict[str, str]) -> float | None:
    if not judgments:
        return None
    gains = []
    labeled = 0
    for asset_id in ids[:5]:
        grade = judgments.get(asset_id)
        if grade is None:
            continue
        labeled += 1
        gains.append(GRADES[grade])
    if not labeled:
        return None
    dcg = sum((2 ** gain - 1) / math.log2(index + 2) for index, gain in enumerate(gains))
    ideal = sorted((GRADES[grade] for grade in judgments.values()), reverse=True)[:labeled]
    idcg = sum((2 ** gain - 1) / math.log2(index + 2) for index, gain in enumerate(ideal))
    return round(dcg / idcg, 4) if idcg else None


def _judged(ids: list[str], judgments: dict[str, str]) -> dict:
    known = [asset_id for asset_id in ids[:5] if asset_id in judgments]
    if not known:
        return {'precision_at_5': None, 'ndcg_at_5': None, 'labeled_in_top5': 0, 'unlabeled_in_top5': len(ids[:5])}
    hits = sum(BINARY[judgments[asset_id]] for asset_id in known)
    return {
        'precision_at_5': round(hits / len(known), 4),
        'ndcg_at_5': _ndcg(ids, judgments),
        'labeled_in_top5': len(known),
        'unlabeled_in_top5': len(ids[:5]) - len(known),
    }


def _mean(values):
    values = [value for value in values if value is not None]
    return round(statistics.mean(values), 4) if values else None


def _by_locale(rows, key):
    locales = ('en-US', 'ru-RU', 'zh-CN')
    return {locale: _mean(row[key] for row in rows if row['locale'] == locale) for locale in locales}


def _run_mode(path: Path, intelligence: bool) -> dict:
    settings.visual_intelligence_enabled = intelligence
    payload = json.loads(DATASET.read_text(encoding='utf-8'))
    rows = []
    started = time.perf_counter()
    for intent in payload['intents']:
        for locale, query in intent['queries'].items():
            t0 = time.perf_counter()
            hits = search_assets(query, limit=5, path=path)
            ids = [hit.get('id') for hit in hits]
            judged = _judged(ids, intent.get('judgments') or {})
            families = {hit.get('visualFamily') or 'unknown' for hit in hits}
            rows.append({
                'intent': intent['id'],
                'domain': intent['domain'],
                'locale': locale,
                'query': query,
                'seconds': round(time.perf_counter() - t0, 4),
                'ids': ids,
                'diversity': round(len(families) / len(hits), 4) if hits else 0,
                'duplicate_rate': round(1 - (len(set(ids)) / len(ids)), 4) if ids else 0,
                **judged,
            })
    legacy = []
    for locale, query, tokens in CASES:
        t0 = time.perf_counter()
        hits = search_assets(query, limit=5, path=path)
        row = _metrics(hits, tokens)
        row.update({'locale': locale, 'query': query, 'seconds': round(time.perf_counter() - t0, 4)})
        legacy.append(row)
    return {
        'mode': 'rerank' if intelligence else 'keyword',
        'seconds': round(time.perf_counter() - started, 3),
        'judged_precision_at_5': _mean(row['precision_at_5'] for row in rows),
        'judged_ndcg_at_5': _mean(row['ndcg_at_5'] for row in rows),
        'judged_by_locale': {
            'precision_at_5': _by_locale(rows, 'precision_at_5'),
            'ndcg_at_5': _by_locale(rows, 'ndcg_at_5'),
        },
        'labeled_hits': sum(row['labeled_in_top5'] for row in rows),
        'unlabeled_hits': sum(row['unlabeled_in_top5'] for row in rows),
        'diversity': _mean(row['diversity'] for row in rows),
        'duplicate_rate': _mean(row['duplicate_rate'] for row in rows),
        'latency_median': round(statistics.median(row['seconds'] for row in rows), 4),
        'legacy_tag_precision_at_5': _mean(row['precision_at_5'] for row in legacy),
        'legacy_tag_by_locale': _by_locale(legacy, 'precision_at_5'),
        'cases': rows,
        'legacy_cases': legacy,
    }


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'media' / 'library' / 'out' / 'manifest.json'
    keyword = _run_mode(path, False)
    rerank = _run_mode(path, True)
    report = {'manifest': str(path), 'keyword': keyword, 'rerank': rerank}
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if out:
        out.write_text(text + '\n', encoding='utf-8')
    else:
        slim = {key: {k: v for k, v in mode.items() if k not in ('cases', 'legacy_cases')} for key, mode in (('keyword', keyword), ('rerank', rerank))}
        print(json.dumps(slim, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
