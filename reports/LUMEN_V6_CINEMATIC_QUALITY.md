# Lumen V6 — Cinematic Director Quality Recovery

**Date:** 2026-04-12  
**Branch:** `feat/media-library-cleanup-v1`  
**Tip SHA:** _(filled after commit)_  
**Preview:** `output/director-v6/director-v6-e-preview-20s.mp4`  
**Desktop:** `~/Desktop/director-v6-e-preview-20s.mp4`

## Root causes

See `reports/LUMEN_V6_ROOT_CAUSE.md`.

Primary blocker: V5 used an **English placeholder transcript** under `ru-RU`, while Remotion cards stayed Russian → EN+RU mix. Secondary: fixed beat template without speech enrichment / layout diversity.

## Actual code changes

| Area | Change |
| --- | --- |
| `backend/locale_consistency.py` | Script/locale gate; no silent cross-language field fallback |
| `backend/caption_phrases.py` | Locale-strict text; clause-aware grouping; merge dangling conjunction crumbs |
| `backend/director_semantics.py` | Speech→headline/cards/queries; layout diversification; semantic validate |
| `backend/remotion_engine.py` | `languageValidation`; pass cards/headline/steps into Remotion props |
| `backend/visual_variation.py` | Broader SPEAKER pools; always overwrite store_plan |
| `backend/director_v3.py` | Enrich plan from transcript before resolve |
| `motion/.../DirectorV3.tsx` | Kinetic hook headline; planned criteria cards; caption≠headline dedupe |
| `scripts/ordinary_director_render.py` | Load localization transcript; enrich before render |

## Tests

```
pytest backend/tests/test_locale_consistency.py \
       backend/tests/test_caption_phrases.py \
       backend/tests/test_director_execution.py \
       backend/tests/test_remotion_engine.py
→ 22+ passed (locale suite included)
```

## Language validation

`language-validation.json`: `ok: true`, `captionLocaleOk: true`, `cardLocaleOk: true`, locale `ru-RU`.

## Captions

Real RU source transcript (volume `localization/source-transcript.json`).  
Examples: «Планируете переезд», «с чего начать?», «Мы сопровождаем весь процесс».

## Motion / scene diversity

`motion-diversity-report.md`: uniqueLayouts=4, consecutiveLayoutRepeats=0, pass=true.

## Media

Speech-triggered queries (relocation/consult/docs). Assets include `people_couple_001`, `re_agent_docs` (see `asset-selection-report.json`).

## Audio

`audio-qa.md`: Remotion `bed.mp3` present + ducked; speech prioritized. Not MUSIC_ASSET_REQUIRED.

## V5 vs V6

`output/director-v6/V5_V6_COMPARISON.md` — language mix resolved; hook + diversity improved.

## directorMode

`heuristic` (RunPod not resumed; LLM_PROVIDER=none). Not claimed as LLM-directed.

## Deployment

| Item | Value |
| --- | --- |
| Host | `142.93.248.163` `/opt/lumen-rebuild` |
| Health | ok · `fast_project_creation: true` |
| Flags | `FAST_PROJECT_CREATION_ENABLED=1`, `REMOTION_ENGINE_ENABLED=1`, `LLM_PROVIDER=none` |
| Smoke | `v6_locale_gate_ok` on server venv |
| Volume | 100G preserved (17G used) |
| RunPod / strom-v2 | untouched |

## Remaining defects

- Caption windows can still split mid-clause («программу с»).
- Transitions are mostly `cut` (diversify later).
- Concept viz mid-cards can still compete with hook headline on some frames.
- Full Create Video smoke on lumen-test for non-preview path still recommended.
- EN/ZH full renders for this source need dubbed/target transcripts (locale gate will drop mismatched captions).

## Rollback

Restore previous backend/motion from `backups/`; or disable semantic enrichment by reverting `director_semantics` wiring. Remotion flag unchanged.
