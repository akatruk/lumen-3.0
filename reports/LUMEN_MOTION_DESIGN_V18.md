# Lumen motion design V18

**Date:** 2026-10-14
**Flag:** `MOTION_DESIGN_V18_ENABLED=0` by default.
**Code:** `backend/motion_design_v18.py`, after the V16 composer. Same 15 components. No second renderer.

V14, V15, and V16 stay off unless the render process turns them on with V18. V17, visual intelligence, and experience memory stay off.

## What changed

`泰国` was matching `thailand_company_structure`, and V11.1 then painted `company_ownership` (`股权结构`) plus the formation-step stack on beats that never mention shareholders. V18 drops that graphic unless the scene's own quote supports ownership, equity, or capital. The beat stays a full-frame talking head. A Bangkok-skyline query on that beat is replaced from the words in the quote.

Diagrams that do match the quote are the existing semantic components, version `v18`: stroke nodes, no dark column plate, entry / hold / exit. A diagram is pushed to the chest band under a short face box. Digit runs stay one caption token (`8000-1`). A Chinese sentence is a caption, not an incomplete English heading, and adjacent Chinese lines are not glued into one plate. The caption paints the whole phrase at once.

## Frames

| file | sha256 | duration | wall | peak RSS |
| --- | --- | --- | --- | --- |
| `output/motion-design-v18/original2-v18.mp4` | `d605ad692615c2694a90dd7181545aa0461fdf82ab04bd81adacdaffcd4474c9` | 65.05s, 1080×1920, audio | 287s | 1.03 GiB |
| `output/motion-design-v18/original1-v18.mp4` | `0535ef0e435f0a1d475dd889fdc66465ac146744ac12ffcbbac7844b9b5bd8c6` | 60.05s, 1080×1920, audio | 243s | 0.89 GiB |
| `output/motion-design-v18/gallery-en.mp4` | `524ca0a09a3749c3f72f34b3ea5d4df65302b08c6236ec582ab56cba189fc3e7` | 112.5s, 45 shots | 195s | 0.83 GiB |

V11.2 baseline left in place: `861ad01c34361dbf0456587735f03a0d1e6fb7bb1a425f96afd4708ea373ef88`.
V17 original2 left in place: `3fb565311b1d7c7ef47ced161c48d28a9e2ff4e3ad37df28676134046b4993f6`.

original2, zh-CN, seed 42, same source. Sampled 8s, 36s, 46s, 58s. No `股权结构`, no `设立路径`, no tiny window, no skyline plate. Speaker is full frame. `8000-1万块的人民币` is intact. `泰国` and `泰诸` are unchanged. 26 caption phrases.

origin1, en-US, seed 42. Capital flow, `≤49%` with no complement, and a China / Thailand comparison are on screen. The face is not covered by an equity tree. `≤49%` sits on the shoulder.

Gallery stills: `preview-en.png`, `preview-zh.png` (投资人 / 资本 / 公司), `preview-ru.png` (Инвестор / Капитал / Компания).

Final renders completed. Earlier Chrome passes in this session were replaced by these files. No retry loop.

## Remaining defects

- CJK captions wrap on characters, so `特别` and `人民币` can break across the two lines. The full phrase is on the plate.
- On origin1 the lower capital-flow node meets the caption plate. The nodes are on the chest, not on the mouth.
- original2 does not draw the salary bands. None of the 15 components match that speech, so the picture stays the talking head.
- The China / Thailand comparison can sit on a beat whose caption is about capital timing.

## Tests

`pytest` `test_motion_design_v18.py` `test_director_execution.py` `test_caption_phrases.py` `test_director_v14.py` `test_scene_composer_v16.py`: pass.
`motion` `npm test` and `tsc --noEmit`: pass. Fixture tests, not a live editorial grade.

## Deploy

Host `lumen-fix` (`142.93.248.163`, `/opt/lumen-rebuild`). `DEPLOY_SHA.txt` is `bafc450670b00c89f5bbedbd7365648ef3f36a45`. Health: `status=ok`, `fast_project_creation=true`, visual intelligence off, pgvector `0.6.0`.

`MOTION_DESIGN_V18_ENABLED`, `SEMANTIC_MOTION_V14_ENABLED`, `SEMANTIC_MOTION_V15_ENABLED`, `SCENE_COMPOSER_V16_ENABLED`, and `MOTION_QUALITY_V17_ENABLED` are absent from `.env`. Imported `enabled()` is false for V18 and V14. `FAST_PROJECT_CREATION_ENABLED=1`. No reviews inserted. strom-v2 and RunPod were not touched.
