# Lumen semantic motion V15

**Date:** 2026-10-14  
**Flags:** `SEMANTIC_MOTION_V14_ENABLED=0` and `SEMANTIC_MOTION_V15_ENABLED=0` by default. Production picture stays V11.2 until a flag is turned on for a controlled test.  
**Dependency:** V14 (`reports/LUMEN_SEMANTIC_MOTION_V14.md`). Same Remotion mount, same catalog, same three layouts.

## V14 gate

Checked before any V15 code. Five components, 15 layout shots, RU/EN/ZH gallery props, registry keyword match, CPU A/B files, and the default-off flag are in the tree.

| check | result |
| --- | --- |
| components | `motion.capital_flow.v1` … `motion.process_timeline.v1` |
| variants | `galleryShots()` = 15, layouts safe against face, PIP, captions |
| locales | gallery en/ru/zh, 37.5s, 1080×1920 |
| A/B | `output/semantic-motion-v14/origin1-motion-baseline.mp4` 60.05s H.264+AAC; `origin1-motion-v14.mp4` 60.05s |
| tests | `motion` semantic tests pass; `test_director_v14.py` pass |
| flag | `semantic_motion_v14_enabled` default false; env unset reads off |
| residual | overlay scrim still meets the caption plate; face stays clear |

Not a blocker. V14 was not enabled globally.

## New components

`motion/src/semantic/componentsV15.tsx` on the V14 layout resolver. Not a second renderer.

| componentId | visualIntent | Draws |
| --- | --- | --- |
| `motion.risk_matrix.v1` | `risk_matrix` | Only the cells in the payload |
| `motion.capital_allocation.v1` | `capital_allocation` | Bar widths from given values |
| `motion.company_ecosystem.v1` | `company_ecosystem` | Named nodes and given links |
| `motion.document_workflow.v1` | `document_workflow` | Document icon plus named steps |
| `motion.financial_metrics.v1` | `financial_metrics` | Counter; unit only if provided |
| `motion.business_decision.v1` | `business_decision` | Root plus spoken branches |
| `motion.geographic_expansion.v1` | `geographic_expansion` | Place nodes, no country outlines |
| `motion.investment_milestones.v1` | `investment_milestones` | Ordered milestones from the payload |
| `motion.contract_relationship.v1` | `contract_relationship` | Named parties and a document node |
| `motion.before_after.v1` | `before_after` | Two states, no benefit badge |

10 × 3 layouts = 30 variants. With V14, the library is 15 components and 45 variants. Locales stay `ru-RU`, `en-US`, `zh-CN` on one component. `formatMetric` groups 120000 as `120,000 USD` / `120 000 USD` / `120,000 USD`.

Catalog rows were appended to `media/library/catalogs/semantic_motion_v14.json`. Lookup is still `search_motion_components`. No CLIP embeddings. Recipes: `recipes/semantic-motion-v15.json`.

## Director

`backend/director_v15.py` runs after V14 when `SEMANTIC_MOTION_V15_ENABLED=1`. It forces the V14 selector for that render only. It does not set the V14 env flag.

Origin1, en-US, seed 42, 60s, same footage and transcript:

| scene | intent | why |
| --- | --- | --- |
| problem | capital_flow | capital is named, no amount |
| residency | shareholder_network | ≥3 is spoken |
| consult | ownership_split | ≤49% only |
| beside | business_comparison | China ≠ Thailand |
| steps | document_workflow | bank accounts, work permits, visa applications |

Risk, allocation, ecosystem, metrics, decision, geography, milestones, contract, and before/after do not fire. China versus Thailand is not drawn as an expansion route. An unspoken 51% `localRatio` on a leftover V11.1 equity panel is removed while V15 is on.

## Previews

Composition `SemanticMotionV15Gallery`, 30 shots × 75 frames, 75.0s, 1080×1920, 30fps:

- `output/semantic-motion-v15/gallery-en.mp4` (815,929 bytes)
- `output/semantic-motion-v15/gallery-ru.mp4` (836,257 bytes)
- `output/semantic-motion-v15/gallery-zh.mp4` (718,590 bytes)

Frames checked: risk entrance and settled pair, RU allocation 40/35/25, ZH `申请、审核`, `120,000 USD`, Thailand → Singapore nodes, before/after on the beige overlay. These files are not in git.

## Origin1 A/B

| | V14 | V15 |
| --- | --- | --- |
| file | `output/semantic-motion-v14/origin1-motion-v14.mp4` | `output/semantic-motion-v15/origin1-motion-v15.mp4` |
| flags | V14=1, V15=0 | V14=1, V15=1 |
| duration | 60.05s | 60.05s |
| size | 26,395,157 | 26,419,824 |
| picture | 1080×1920 H.264 + AAC | 1080×1920 H.264 + AAC |
| sha256 prefix | `77d8180799f3485f` | `0fafae83d3140b8c` |
| wall | 261s | 246s |
| peak RSS | 0.98 GB | 1,030,111,232 bytes (~0.96 GB) |
| CPU | concurrency 1 | concurrency 1; 617s user / 246s real |
| failures | none | none |

The visible origin1 change is the document workflow in place of the generic timeline. No RunPod. No GPU packages.

## Visual QA

- ≤49% ring, face in the PIP, caption readable, no 51.
- Document steps sit on the chest. Eyes and mouth stay clear. The scrim still meets the caption plate. A hand can pass under the scrim.
- Full-frame gallery shots keep the PIP column empty, so diagrams sit on the left.
- The long RU label `Операционная деятельность компании` wraps small inside that column. It is not mid-word clipped. Shorter labels stay at body size.
- Metric card is a compact plate, not a full-height empty column.

## Tests

- `cd motion && npx tsc --noEmit` and `node --import tsx --test src/semantic/*.test.ts` — pass (layout, V14 gallery, V15 gallery, `formatMetric`)
- `pytest backend/tests/test_director_v14.py backend/tests/test_director_v15.py` — 17 pass

## Git

Implementation commit: `41e901749c8b376911ba73a08e3f49f702c569bf` on `feat/media-library-cleanup-v1`.

## Deployment

Host `lumen-fix` (`142.93.248.163`, `/opt/lumen-rebuild`) checked before sync. `DEPLOY_SHA.txt` is `41e901749c8b376911ba73a08e3f49f702c569bf`. `lumen-web` and `lumen-worker` are active. Health: `status=ok`, `fast_project_creation=true`, visual intelligence off, pgvector `0.6.0`.

`director_v15.enabled()` is `False`. `SEMANTIC_MOTION_V14_ENABLED` and `SEMANTIC_MOTION_V15_ENABLED` are unset. `FAST_PROJECT_CREATION_ENABLED=1`. `VISUAL_INTELLIGENCE_ENABLED=0`. `VISUAL_EXPERIENCE_MEMORY_ENABLED=0`. strom-v2, RunPod, Postgres storage, source videos, and approved media binaries were not touched.
