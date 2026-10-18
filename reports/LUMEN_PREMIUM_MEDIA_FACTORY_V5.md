# Lumen Premium Media Factory V5

**Date:** 2026-10-13  
**Branch:** `feat/media-library-cleanup-v1`  
**Director baseline:** V11.2 (preserved; not redesigned)  
**Flags:** `PREMIUM_3D_MODE=off`, `quality_gate_v2.production_ready=[]`

## Audit (local manifest)

| Metric | Count |
| --- | ---: |
| Manifest assets (pre-index) | 669 |
| After batch1 index | **692** (+23) |
| Backgrounds | 47 → +8 recipe rows |
| Layers / parallax | 15 → +4 |
| Premium 3D family | 15 (+3 candidates `needs_review`) |
| Business category | sparse → +5 deterministic motion rows |
| Transitions | +3 Remotion types |

Gaps addressed without generative video: cinematic plates, parallax stacks, business connectors, transitions. True I2V/SDXL masters **blocked**.

## GPU (read-only)

See `reports/PREMIUM_GPU_SELECTION.md`.

| Pod | Status | GPU | $/hr |
| --- | --- | --- | ---: |
| `dznvwn90el5au4` (`lumen-hypit-4090`) | **EXITED** | RTX PRO 4500 | ~0.72 |
| `hufsgfs9f7gpga` (`lumen-web-gpu`) | **EXITED** | RTX PRO 4500 | ~0.72 |

Balance ~$7.90. **No resume.** Recommend ONE config when authorized: resume `dznvwn90el5au4` only.

**Status:** `BLOCKED_ON_GPU_APPROVAL` for generative video / RunPod stills.

## Contrast engine (critical fix)

| Item | Path |
| --- | --- |
| Resolver | `motion/src/utils/adaptiveLineStyle.ts` |
| Tests | `motion/src/utils/adaptiveLineStyle.test.ts` (6 pass) |
| Wiring | `ConnectorStroke.tsx`, `BusinessMotion.tsx`, `ConceptViz` growth arrow |
| Director stamp | `director_v11_2.stamp_face_safe_business_motion` → `sceneTheme` / `connectorBackground` |

Behavior: sample **full path** against background (solid/gradient/samples/regions). Gold `#E0B15A` on beige `#F4EFE6` → `outlined` or `recolored` (not `ok`). Dark ink plates keep gold.

**Frame evidence:** `output/premium-media-v5/frames/` — baseline t18 light-grey connectors on beige office; v12 dark adaptive strokes on same beat.

## First batch (23)

| Group | Count | Production status |
| --- | ---: | --- |
| Cinematic BG treatments | 8 | QA (Remotion plates) |
| Parallax stacks | 4 | QA |
| Premium 3D candidates | 3 | `needs_review` — not production_ready |
| Business motion presets | 5 | **approved_code** |
| Transitions | 3 | **approved_code** |

Recipe: `recipes/premium-media-factory-v5-batch1.json`  
Contact: `media/library/out/contact-sheets/premium-media-v5-batch1.html`  
Indexer: `scripts/index_premium_media_v5_batch1.py`

Rejected from production auto-mount: plastic/flicker/text-in-image/bad-alpha; all experimental 3D; GPU generative until approved.

## A/B render (origin1)

| File | SHA-256 |
| --- | --- |
| `output/premium-media-v5/baseline-v11-2.mp4` | `861ad01c34361dbf0456587735f03a0d1e6fb7bb1a425f96afd4708ea373ef88` |
| `output/premium-media-v5/premium-motion-v12-test.mp4` | `a1a1808341b2f2b5c662df4ac2d0639ab51af50885707d1ac4159419b626ef7f` |

- Duration ~60s; language en-US; seed 42; `LUMEN_BACKGROUND_PLATE=paper_grain`
- Passport/relocation FG on investment speech: **0 hits**
- Desktop: `~/Desktop/baseline-v11-2.mp4`, `~/Desktop/premium-motion-v12-test.mp4`
- Heuristic Director (`directorMode=heuristic`) — not claimed as live LLM editorial quality

## Storage paths

| Role | Path |
| --- | --- |
| DO volume (authoritative library) | `/mnt/volume_nyc1_1791446889637/app-library` |
| Repo manifest mirror | `media/library/out/manifest.json` |
| Masters (future GPU) | volume only; never overwrite `status=approved` |
| App | `/opt/lumen-rebuild` on `142.93.248.163` |

## Tests run

- `cd motion && npm test` — 58 pass (incl. adaptiveLineStyle)
- `pytest backend/tests/test_director_v11_1.py test_director_v11_2.py` — 10 pass

## Shipped vs blocked

| Shipped | Blocked |
| --- | --- |
| Adaptive contrast + tests | RunPod resume / paid SDXL/I2V |
| Remotion cinematic plates + parallax recipes | New generative video masters |
| Business motion `capital_flow` + connector wiring | Auto 3D production_ready |
| Transition types soft_pull / cross_blur / iris_soft | Expanding full ~145 asset catalog |
| Manifest +23 rows, docs/skills, origin1 A/B MP4s | |

## Deploy / git

| Item | Value |
| --- | --- |
| Git SHA | `bb1583d576848d8e7c7558cadc42757676d976d7` |
| Branch | `feat/media-library-cleanup-v1` (pushed) |
| Deploy host | `142.93.248.163` `/opt/lumen-rebuild` |
| Health | `http://127.0.0.1:8018/api/health` → **200** |
| Volume manifest | `/mnt/volume_nyc1_1791446889637/app-library/manifest.json` (692 assets, 23 pmv5) |
| RunPod after deploy | both pods still **EXITED** |
