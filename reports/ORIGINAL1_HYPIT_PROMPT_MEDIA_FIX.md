# original1 — Hypit prompt + media library fix

**Date:** 2026-10-12  
**Host:** lumen-test `142.93.248.163` (`/opt/lumen-rebuild`)  
**LLM_PROVIDER:** `none` (unchanged)

## Project / jobs

| | |
|---|---|
| **Project** | `32012faa46484303899bf28d06c5502f` · title **original1** · language **en** |
| **Failed (root cause)** | `9c3edd45…` · `hypit_unavailable` (stale SSH `:18388`) then bad picture from placeholder ASR |
| **Prior delivery (preserved)** | render `e9e6c0a4cf74421cabac35ba79876cf7` · sha256 `d181a8d5796443d0406c186a8c6a7db4ade6387f4d3514968ac21f000f833c5b` · copy under `/mnt/volume_nyc1_1791446889637/lumen/_preserve/original1_e9e6c0a4/` |
| **Fixed Create Video job** | `2bfc68bce36f4ca78da6a828415627b9` · **complete** |
| **New delivery** | render `5dd1527b7233416b92d4a95540cb22e5` · sha256 `c8c1fa956f87d4cf38a8a589b2214e3329a3194965f96d9d49f2314926ba80ff` · 1080×1920 · ~63.5s · AAC audio |

## Root cause (wrong prompt + no library)

1. **Placeholder transcript mislabeled as whisperx**  
   `faster_whisper` failed on PyAV (`metadata_errors` kwarg). Exception path fell back to `[segment 1]…[segment 8]` while metadata still said `transcript_provider=whisperx`.  
   Graphics and library search used those placeholders → black plates + literal `[segment N]` on screen; **zero** `library_id` / no `./motion/*.mp4` staged.

2. **`assembly_prompt.txt` was a Remotion E2E test brief**  
   Instructed Hypit to call `media/library/search.py` / Remotion — impossible on the RunPod workspace. Not a Hypit filming brief.

3. **Library paths in the prompt were host-absolute / catalog dumps**  
   Hypit can only resolve files staged into the job workspace (`./motion/N.mp4`).

4. **Historical final prompt was not persisted as an immutable artifact**  
   Only `localization/en-US/director-prompt.txt` existed. Reconstruction from code is not the historical send. New jobs write `hypit/final_prompt.txt` + `hypit/assets_manifest.json`.

## What we changed

| File | Change |
|---|---|
| `backend/assembly_prompt.txt` | Hypit-only brief: staged `./motion/*`, host PIP, language/Studio levels, no `search.py` |
| `backend/whisperx_local.py` | Load WAV via `wave`+numpy — bypass broken PyAV path |
| `backend/source_analysis.py` | Stamp **actual** transcript provider; detect placeholder; invalidate cache on placeholder |
| `backend/library_clips.py` | Prefer `/mnt/.../app-library`; skip placeholder queries; `staged_media_block` + `write_assets_manifest` |
| `backend/hypit_prompt.py` | Skip `[segment N]` captions in phrase rows |
| `backend/hypit_picture.py` | Persist `final_prompt.txt` + inject staged block into SVML `request` |
| `scripts/runpod_pod_control.py` | Allowed pod id → `sovtlhobiu7wvt` (current `lumen-hypit-4090`; old `nxi1rfwb94eufx` gone) |
| Tests | Placeholder detection; prompt markers; language/presentation module list |

## Actual final prompt (new job)

Saved on the render (not reconstructed):

`/mnt/volume_nyc1_1791446889637/lumen/32012faa46484303899bf28d06c5502f/renders/5dd1527b7233416b92d4a95540cb22e5/hypit/final_prompt.txt`

Starts with: `Film the host's original video. Hypit is the only renderer…`  
Includes Studio levels, localization module, **STAGED LIBRARY FILES** with `./motion/N.mp4` refs.  
`[segment` count in `main.svml`: **0**.

## Library assets used (confirmed in picture)

Manifest: `…/hypit/assets_manifest.json` · root `/mnt/volume_nyc1_1791446889637/app-library`

| Staged | Library id | Phrase (abbr.) | Role |
|---|---|---|---|
| `./motion/1.mp4` | `i2v_consult_001` | foreign investment companies / China | type |
| `./motion/2.mp4` | `re_inv_laptop` | first step of a Chinese investment company | number |
| `./motion/3.mp4` | `re_inv_meeting` | capital investment | flow |
| `./motion/4.mp4` | `re_ext_construction` | under the leadership of the government | object |
| `./motion/6.mp4` | `doc_calendar_001` | shareholder responsibility | timeline |
| `./motion/7.mp4` | `pm_bg_grid_001` | first thing in Thailand is not money | minimal |

**6 used / 13 planned shots.** Gaps kept host+speech (e.g. spoken `49%` as figure shot without a forced random plate).

Frame check (not just request presence):

- ~3s — consult I2V + host PIP + English caption (real speech, not `[segment N]`)
- ~12s — construction library still + host PIP + caption about capital investment

Audio: AAC stereo present for full ~63.5s (host/original path).

## RunPod

| | |
|---|---|
| Pod | `sovtlhobiu7wvt` · `lumen-hypit-4090` |
| During render | RUNNING · SSH `213.173.110.43:12221` (dynamic; not `:18388`) |
| After verify | **EXITED** (stopped) |
| `lumen-web-gpu` | EXITED · untouched |
| `LLM_PROVIDER` | **none** |

## Tests run

On lumen-test (`PYTHONPATH=/opt/lumen-rebuild`):

`test_placeholder_transcript` · `test_language` · `test_prompt_modules` · `test_editing_controls` · `test_presentation_graphics` → **31 passed**.

`test_hypit_picture::test_style_match_render_invokes_hypit_capture` still fails on local ffmpeg fixture env (`media_processing_failed`) — unrelated to prompt/library wiring; not used as acceptance.

## Lifecycle / blockers

| Check | Result |
|---|---|
| Real ASR → Create Video → finished MP4 | **Pass** (job `2bfc68bc…`, render `5dd1527b…`) |
| Prompt + assets artifacts on disk | **Pass** |
| Library visible in frames | **Pass** (consult / construction) |
| Previous delivery retained | **Pass** (`e9e6c0a4…` + `_preserve/`) |
| Player/download = selected delivery | New `result.render_id` is `5dd1527b…` |
| Second render + browser reload (`docs/RELEASE_CHECKS.md` full) | **Not re-run** in this pass (GPU cost); recommended smoke before prod-wide claim |
| Isolated copy of source/settings before prod create | Diagnose on live original1 with preserved prior MP4; no silent overwrite |

### Remaining blockers / follow-ups

1. Full `scripts/verify_release.py` + second Create Video on original1.
2. Some SVML motion refs still declare files for gap shots; Hypit/figures fill or skip — tighten so gap shots omit `src=` when stage fails.
3. Semantic pick quality: some plates are loosely related (e.g. construction for “government”); improve query/ranking later without inventing assets.
4. Keep `ALLOWED_POD` / discovery on **name** `lumen-hypit-4090` if RunPod recreates the id again.
