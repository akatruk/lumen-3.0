# Подтверждённый scope пилота

Уточнения пользователя после PRD, 15 сентября 2026.

Площадки: **Douyin, Instagram Reels (IG), YouTube Shorts**. Это закрывает вопрос о выборе трёх платформ в BUSINESS_PRD_IMPACT_2026-09-15.md. IG трактуется как Reels в контексте коротких вертикальных видео.

Тематики: **недвижимость, гражданство других стран, путешествия**.

Целевой сценарий: референсы + собственные материалы → согласованный master → три отдельные платформенные адаптации.

Интерфейс сохраняет English / 简体中文. Язык контента задаётся отдельно от площадки.

Поиск Douyin через TikHub остаётся источником референсов. Подключение поиска Instagram/YouTube этим уточнением не запрошено. Возможности публикации и доступные метрики нужно проверить отдельно для каждой площадки; автоматическая публикация пока не подтверждена.

Это фиксация требований, а не отчёт о реализации.

## Implementation checkpoint — 2026-09-15

The reference-to-owned workflow and approved master rendering are deployed. See [release validation](../qa/release-1-2026-09-15/REPORT.md). Platform-specific versions and publishing remain planned, not delivered. Current reference search is Douyin via TikHub; Instagram Reels and YouTube Shorts remain target destinations.

## Platform previews checkpoint — 2026-09-15

Three platform export previews are now implemented for new Studio projects: separately rendered MP4s, hook treatments, covers, copy, captions and a ZIP with the master. See [validation](../qa/platform-versions-2026-09-15/REPORT.md). All previews require human review; source content may use the same scene selection when no justified recut exists. Full native editing, per-fragment regeneration, publishing and analytics remain unfinished. This supersedes the earlier statement that only a single master can be exported.

## Variant revision checkpoint — 2026-09-15

Individual platform copy/range editing, approval/locking, immutable package history and restore are deployed. Only an edited platform is rerendered; other assets and approvals are preserved. See [validation](../qa/variant-revisions-2026-09-15/REPORT.md). This closes manual variant revision, not AI fragment regeneration, complete native adaptation, publishing or analytics.

## Scoped Director alternatives checkpoint — 2026-09-15

AI alternatives for a single existing unlocked decision can now be requested and explicitly accepted without changing other decisions or the old master. This regenerates an editing recommendation, not footage. See [validation](../qa/director-alternatives-2026-09-15/REPORT.md). Generated footage, multi-asset editing and real-video quality acceptance remain open.
