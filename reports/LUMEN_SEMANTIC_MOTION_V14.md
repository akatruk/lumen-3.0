# Lumen semantic motion V14

**Date:** 2026-10-14  
**Flag:** `SEMANTIC_MOTION_V14_ENABLED=0` (default). Production picture stays V11.2 until this flag is turned on for a controlled test.  
**Source:** `director_v5_original1`, en-US, seed 42, 60s. Same footage, transcript, and caption timestamps as the baseline render.

## Components

One Remotion renderer, `motion/src/semantic/SemanticMotion.tsx`. Five intents, three layouts (`full_frame`, `speaker_visual`, `overlay`) from `layouts.ts`. Not fifteen separate implementations.

| componentId | visualIntent | What it draws |
| --- | --- | --- |
| `motion.capital_flow.v1` | `capital_flow` | Named entities and a drawn connector. No amount unless the payload carries one. |
| `motion.shareholder_network.v1` | `shareholder_network` | Network into the company. Count and `≥` only when speech states them. |
| `motion.business_comparison.v1` | `business_comparison` | Two sides and an operator. `≠` only when the quote contrasts both sides. |
| `motion.ownership_split.v1` | `ownership_split` | Ring of spoken percentages. A single 49% does not become 51%. |
| `motion.process_timeline.v1` | `process_timeline` | Ordered steps named in the quote. |

Locales: `ru-RU`, `en-US`, `zh-CN` via label props and `AutoFitText`. One component. No text in PNG assets.

Connectors use `adaptiveLineStyle`. Overlay beats paint a dark scrim so type stays readable on a light shirt. Frame-driven `interpolate` only.

## Registry and Director

Catalog: `media/library/catalogs/semantic_motion_v14.json`. Lookup: `media/library/semantic_motion_registry.search_motion_components` (en / ru / zh tags). These rows are not written into CLIP `asset_embeddings`. `VISUAL_INTELLIGENCE_ENABLED` and `VISUAL_EXPERIENCE_MEMORY_ENABLED` stay 0. Selection still works with pgvector off.

`backend/director_v14.py` runs after V10 when the flag is on. Each graphic stores `segmentId`, `sourceTimestamp`, `sourceQuote`, `factClass=source_stated`. Scenes without a supported quote stay talking-head. On a selected scene, text cards and `businessMotion` panels are removed.

Recipes: `recipes/semantic-motion-v14.json`.

Origin1 with the flag on selected five beats, not a stack of all five at once:

| scene | intent | layout | segment |
| --- | --- | --- | --- |
| problem | capital_flow | overlay | seg_002 Capital → Company |
| residency | shareholder_network | speaker_visual | seg_006 ≥3 |
| consult | ownership_split | full_frame | seg_007 ≤49% |
| beside | business_comparison | speaker_visual | seg_009 China ≠ Thailand |
| steps | process_timeline | overlay | seg_010 Bank accounts, Work permits, Visa applications |

## Gallery

Composition `SemanticMotionV14Gallery` (15 shots × 75 frames, 37.5s, 1080×1920, 30fps):

- `output/semantic-motion-v14/gallery-en.mp4`
- `output/semantic-motion-v14/gallery-ru.mp4`
- `output/semantic-motion-v14/gallery-zh.mp4`

Frames checked at mid-shot for capital flow, shareholder network, comparison, ≤49% ring, and timeline in EN, plus RU capital labels and ZH 公司 / 咨询 / 文件 / 注册. Light plates use dark type. Narrow comparison stacks vertically so the labels are not clipped.

## Origin1 A/B

| | A baseline | B V14 |
| --- | --- | --- |
| file | `output/semantic-motion-v14/origin1-motion-baseline.mp4` | `output/semantic-motion-v14/origin1-motion-v14.mp4` |
| flag | `SEMANTIC_MOTION_V14_ENABLED=0` | `SEMANTIC_MOTION_V14_ENABLED=1` |
| duration | 60.05s | 60.05s |
| size | 30,349,990 bytes | 26,395,157 bytes |
| picture | 1080×1920 H.264 + AAC | 1080×1920 H.264 + AAC |
| sha256 prefix | `4d173f43f20916c0` | `77d8180799f3485f` |
| wall time | 307s | 261s |
| peak RSS | 1.06 GB | 0.98 GB |
| Remotion | `--concurrency=1` | `--concurrency=1` |
| failures | none | none |

CPU render on this Mac. No RunPod. No GPU packages.

## Visual QA

Inspected gallery frames and origin1 frames at 12s, 21s, 30s, 38s, 44s.

- Eyes and mouth stay clear on the fullscreen overlay beats. The overlay scrim sits on the chest, under the mouth.
- Split and full-frame beats keep the face in the speaker column or PIP. The ≤49% ring does not invent 51%.
- Captions stay in the lower plate. On fullscreen overlay beats the scrim still meets the top of that plate. Words are readable and not mid-split. Residual, not a face cover.
- Shareholder lines are light on the dark column. Comparison is China ≠ Thailand, stacked in the narrow column.
- Gallery 0% frame is the entrance (almost empty). 100% frame is the settled timeline. Motion is the in-between frames, not a still mock.

## Tests

- `cd motion && npm test && npm run typecheck` — pass, including `src/semantic/layouts.test.ts`
- `pytest backend/tests/test_director_v14.py` — 8 pass (flag off is a no-op, 49≠51, count only when spoken, comparison needs both sides, timeline steps, ru/en/zh registry)

## Deployment

Code deploys to lumen-fix with the flag left at 0. See the SHA below after the git commit. `FAST_PROJECT_CREATION_ENABLED` stays 1. Visual intelligence flags stay 0. strom-v2, RunPod, Postgres data, and approved media binaries are not part of this change.
