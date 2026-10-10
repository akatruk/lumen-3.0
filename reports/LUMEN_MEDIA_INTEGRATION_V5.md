# Lumen Media Integration V5

Date: 2026-10-11. Web node: `root@142.93.248.163` (`lumen-fix`).  
No RunPod resume. No new media generation. Library left on the volume.

## Storage (verified)

| Item | Value |
| --- | --- |
| Real mount | `/dev/sda` → `/mnt/volume_nyc1_1791446889637` (ext4, 100G, ~80G free) |
| Library path | `/mnt/volume_nyc1_1791446889637/app-library` |
| App symlink | `/opt/lumen-rebuild/media/library/out` → app-library |
| Manifest | **811** assets, **400** `source=runpod` |
| On-disk runpod files | **400** (225 `rp_` + 75 `hypit_` + 100 `v2_`) under `static/runpod/{photographs,details,objects,foreground}` |
| Integrity | 400/400 PNG magic OK; sizes ~0.79–2.27 MB; 0 missing runpod files; rejected/ separate (5 files, not in manifest) |
| Motion decode | library motion H.264 OK; Director `speaker.mp4` 1080×1920 H.264 |
| Thumbnails | 199 files under `thumbnails/` |
| Permissions | `lumen:lumen` tree; runpod PNGs readable |

**Hypothesis A (runpod included in 811):** **PASS** — 400 runpod rows + 400 files, 1:1 basename match.

## Search (RU / EN / ZH)

`media/library/search.py` + `media/library/concepts.py` deployed to DO.

| Metric | Result |
| --- | --- |
| Intents | **54** (18 concepts × en/ru/zh) |
| Hits (post V5 aliases + casefold) | **54 / 54** |
| Earlier stale snapshot | 46/54 (8 empty) — fixed without new media |

Previously empty (now resolved):

| Locale | Query |
| --- | --- |
| zh | 顾问咨询会议, 抵达新城市, 文件审核桌面, 不确定的决定, 顾问客户文件, 电话咨询办公室 |
| ru | заявление на ВНЖ, проверка документов на столе |

Also: `海外移居` → overseas immigration relocation. Cyrillic casefold so `ВНЖ` matches `внж`.

Evidence: `output/library-validation/multilingual-intents.json` (`empty: 0`).

## Director selection (root cause → fix)

**Why repeats / unused runpod:** `_candidates` only allowed `photography` / motion families. **240 / 400** runpod stills are `editorial_object` (details/objects/foreground) and were dropped. Foreground was hardcoded to `passport.png`. Intra-plan exclude only looked at the last asset.

**Fixes in `backend/visual_variation.py` + `DirectorV3.tsx`:**

- Plate families include `editorial_object`
- Full-plan exclude + concept/prefix usage weights + stronger `recent_ids` (12 gens, bg+fg)
- Library foreground pick + `stage_backgrounds` stages fg; Remotion uses `foreground.staged \|\| passport.png`
- Search import path no longer follows a monkeypatched `LIBRARY`

Tests: `backend/tests/test_visual_variation.py` — 7 passed (incl. runpod prefix + cross-seed diversity).

## Three variants (same speaker, different seeds)

Source: Director V3 `speaker.mp4`, 20.053 s, 1080×1920, H.264+AAC. No new assets.

| Variant | Seed | Art direction | Assets | SHA256 | Local path |
| --- | --- | --- | --- | --- | --- |
| a | 510011 | luxury_minimal | rp_photo_065, rp_photo_067, re_inv_meeting | `166ba7c7…0a30ce75` | `output/library-validation/variant-a.mp4` |
| b | 520022 | cinematic_editorial | rp_photo_033, v2_photo_007, v2_photo_011 | `bb3462e1…16c23c86` | `output/library-validation/variant-b.mp4` |
| c | 530033 | luxury_minimal | rp_object_003, v2_detai_007, re_agent_docs | `4bc9468d…fc94bb8a` | `output/library-validation/variant-c.mp4` |

DO paths: `/opt/lumen-rebuild/output/library-validation/variant-{a,b,c}.mp4`

### Unused / repeat

| Metric | Value |
| --- | --- |
| Picked total / unique | 9 / 9 |
| Repeat count | **0** |
| Cross-variant overlap | **[]** (ab/ac/bc all empty) |
| Prefix mix | rp_ 4, v2_ 3, re_ 2 |
| Runpod used in this trio | 7 |
| Runpod unused (pool) | 393 / 400 (expected — only 3 media beats × 3 seeds) |

Plans: `output/library-validation/variant-{a,b,c}.json`, `v5-render-summary.json`.

### QC checklist

| Check | Result |
| --- | --- |
| Speaker central / present | PASS (Director V3 host cuts) |
| Relevance | PASS (document / consult / object plates match residency brief) |
| Motion / treatments | PASS (distinct layouts, bg treatments, transitions per seed) |
| Diversity | PASS (overlap 0; rp_ + v2_ + editorial_object) |
| Captions / language | PASS (RU captions in composition) |
| Audio | PASS (AAC track present) |
| Music | bed.mp3 in public dir (composition default) |

## Deploy

| Item | Status |
| --- | --- |
| Code rsynced | `visual_variation.py`, `search.py`, `concepts.py`, `DirectorV3.tsx`, tests |
| Media storage | untouched (symlink intact) |
| `lumen-web` / `lumen-worker` | **active**, `/api/health` → `{"status":"ok"}` |
| Host | lumen-fix.universalgravity.org → 127.0.0.1:8018 |

## PASS / FAIL vs success criteria

| # | Criterion | Status |
| --- | --- | --- |
| 1 | Storage verified on real mount; 811/400 | **PASS** |
| 2 | Search RU/EN/ZH; intents ≥30 | **PASS** (54/54) |
| 3 | Director can use hypit_/v2_/rp_ (no hardcode-only pool) | **PASS** |
| 4 | Cross-seed diversity / usage memory | **PASS** (overlap 0) |
| 5 | Three 15–20s previews, no new media | **PASS** |
| 6 | QC | **PASS** |
| 7 | Deploy to DO web node without moving library | **PASS** |
| 8 | Docs committed; mp4s not in git | **PASS** (this commit) |

## SHA

V5 commit: `90f1b21bf2773e3ab22a5813e8e952aa8fc23fc4`. Prior HEAD: `f9913b4`.
