"""Compare keyword search with hybrid pgvector search on a reviewed tag set.

Relevance is the library's own tags, not a fabricated quality score.
"""
from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.config import settings
from backend.database import connect
from media.library.search import load, search_assets

# Tokens are labels already used by the manifest (tags / tags_ru / tags_zh / situations).
CASES = [
    ('en-US', 'family planning relocation', ('family', 'relocation', 'planning', 'moving')),
    ('ru-RU', 'семья планирует переезд', ('family', 'relocation', 'planning', 'семья', 'переезд')),
    ('zh-CN', '家庭计划移居国外', ('family', 'relocation', 'planning', '家庭', '移居')),
    ('en-US', 'second passport citizenship', ('passport', 'citizenship')),
    ('ru-RU', 'второй паспорт', ('passport', 'паспорт', 'citizenship')),
    ('zh-CN', '第二护照', ('passport', '护照', 'citizenship')),
    ('en-US', 'family buying an apartment', ('apartment', 'family', 'buyer', 'property')),
    ('ru-RU', 'семья покупает квартиру', ('apartment', 'квартир', 'family', 'семья')),
    ('zh-CN', '家庭购买公寓', ('apartment', '公寓', 'family', '家庭')),
    ('en-US', 'advisor consultation meeting', ('consultation', 'advisor', 'meeting')),
    ('ru-RU', 'консультация с советником', ('consultation', 'консультац', 'advisor')),
    ('zh-CN', '顾问咨询会议', ('consultation', '顾问', '咨询')),
    ('en-US', 'residence visa application', ('visa', 'residence', 'permit')),
    ('ru-RU', 'виза и внж', ('visa', 'виз', 'внж', 'residence')),
    ('zh-CN', '签证居留', ('visa', '签证', '居留', 'residence')),
    ('en-US', 'document review on a desk', ('document', 'documents', 'desk', 'review')),
    ('ru-RU', 'проверка документов на столе', ('document', 'documents', 'документ', 'столе')),
    ('zh-CN', '文件审核桌面', ('document', '文件', '审核', 'desk')),
    ('en-US', 'arrival in a new city', ('city', 'arrival')),
    ('ru-RU', 'прибытие в новый город', ('city', 'город', 'arrival')),
    ('zh-CN', '抵达新城市', ('city', '城市', 'arrival')),
    ('en-US', 'packing a suitcase before departure', ('suitcase', 'packing', 'luggage')),
    ('ru-RU', 'собирает чемодан', ('suitcase', 'чемодан', 'packing')),
    ('zh-CN', '收拾行李箱', ('suitcase', 'packing', 'luggage')),
    ('en-US', 'investment growth arrow', ('investment', 'growth', 'arrow', 'profit')),
    ('ru-RU', 'рост инвестиций', ('investment', 'инвест', 'growth', 'рост')),
    ('zh-CN', '投资增长', ('investment', '投资', 'growth', '增长')),
    ('en-US', 'tax residency abroad', ('tax', 'residency', 'residence')),
    ('ru-RU', 'налоговое резидентство', ('tax', 'налогов', 'residency')),
    ('zh-CN', '税务居民', ('tax', '税务', 'residency')),
]


def _hay(asset: dict) -> str:
    parts = [
        asset.get('id') or '',
        asset.get('category') or '',
        ' '.join(asset.get('tags') or []),
        ' '.join(asset.get('tags_ru') or []),
        ' '.join(asset.get('tags_zh') or []),
        ' '.join(asset.get('situations') or []),
        ' '.join(asset.get('actions') or []),
    ]
    return ' '.join(parts).casefold()


def _relevant(asset: dict, tokens: tuple[str, ...]) -> bool:
    hay = _hay(asset)
    return any(token.casefold() in hay for token in tokens)


def _metrics(hits: list[dict], tokens: tuple[str, ...]) -> dict:
    top = hits[:5]
    relevant = sum(1 for asset in top if _relevant(asset, tokens))
    families = {asset.get('visualFamily') or 'unknown' for asset in top}
    ids = [asset.get('id') for asset in top]
    files = [asset.get('file') for asset in top]
    return {
        'precision_at_5': relevant / 5,
        'relevant_in_top5': relevant,
        'returned': len(top),
        'diversity': (len(families) / len(top)) if top else 0,
        'duplicate_rate': (1 - (len(set(ids)) / len(ids))) if ids else 0,
        'duplicate_file_rate': (1 - (len(set(files)) / len(files))) if files else 0,
        'ids': ids,
    }


def _run(path: Path, intelligence: bool) -> list[dict]:
    settings.visual_intelligence_enabled = intelligence
    rows = []
    for locale, query, tokens in CASES:
        started = time.perf_counter()
        hits = search_assets(query, limit=5, path=path)
        elapsed = time.perf_counter() - started
        row = _metrics(hits, tokens)
        row.update({'locale': locale, 'query': query, 'seconds': round(elapsed, 4), 'mode': 'hybrid' if intelligence else 'keyword'})
        rows.append(row)
    return rows


def _summary(rows: list[dict]) -> dict:
    warm = rows[1:] if len(rows) > 1 else rows
    return {
        'queries': len(rows),
        'precision_at_5': round(statistics.mean(row['precision_at_5'] for row in rows), 4),
        'diversity': round(statistics.mean(row['diversity'] for row in rows), 4),
        'duplicate_rate': round(statistics.mean(row['duplicate_rate'] for row in rows), 4),
        'latency_cold_seconds': rows[0]['seconds'] if rows else None,
        'latency_warm_median_seconds': round(statistics.median(row['seconds'] for row in warm), 4) if warm else None,
        'by_locale': {
            locale: round(statistics.mean(row['precision_at_5'] for row in rows if row['locale'] == locale), 4)
            for locale in ('en-US', 'ru-RU', 'zh-CN')
        },
    }


def main():
    path = ROOT / 'media' / 'library' / 'out' / 'manifest.json'
    assets = load(path)
    keyword = _run(path, False)
    hybrid = _run(path, True)
    db = {}
    with connect() as conn:
        if conn.postgres:
            db['pgvector'] = conn.execute("SELECT extversion FROM pg_extension WHERE extname='vector'").fetchone()['extversion']
            db['database_bytes'] = conn.execute('SELECT pg_database_size(current_database()) AS n').fetchone()['n']
            db['asset_embeddings'] = conn.execute('SELECT COUNT(*) AS n FROM asset_embeddings').fetchone()['n']
            db['by_modality'] = {
                row['modality']: row['n']
                for row in conn.execute('SELECT modality, COUNT(*) AS n FROM asset_embeddings GROUP BY modality')
            }
            started = time.perf_counter()
            conn.execute(
                '''SELECT asset_id FROM asset_embeddings
                   WHERE scope='library' AND embedding IS NOT NULL
                   ORDER BY embedding <=> (SELECT embedding FROM asset_embeddings WHERE scope='library' LIMIT 1)
                   LIMIT 5'''
            ).fetchall()
            db['vector_query_seconds'] = round(time.perf_counter() - started, 4)
            from backend.experience_memory import bounded_context
            started = time.perf_counter()
            context = bounded_context('director_v5_original1', 'family planning relocation', domain='')
            db['director_context_seconds'] = round(time.perf_counter() - started, 4)
            db['director_context_chars'] = len(json.dumps(context, ensure_ascii=False))
            db['director_context_items'] = len(context.get('items') or [])
    payload = {
        'assets_in_manifest': len(assets),
        'keyword': _summary(keyword),
        'hybrid': _summary(hybrid),
        'database': db,
        'cases': {'keyword': keyword, 'hybrid': hybrid},
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
