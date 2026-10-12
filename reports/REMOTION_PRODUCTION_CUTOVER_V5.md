# Remotion Production Cutover V5

**Date:** 2026-04-12  
**Branch:** `feat/media-library-cleanup-v1`  
**Host:** lumen-test `142.93.248.163` `/opt/lumen-rebuild`  
**Baseline Git (Director V4):** `dfb34b0`

## Verdict

Director V4 + Remotion is the **default** Create Video path for supported projects (`REMOTION_ENGINE_ENABLED` defaults **true**). Captions come from real transcript phrase groups. Hypit remains an **explicit** legacy path only — no silent fallback. Three real 20s previews passed gates.

## Render routing

### Before (V4)

| Condition | Renderer |
| --- | --- |
| Project «e» (`9a9c116d…`) | Remotion (`should_use_remotion` hard-pin) |
| Other projects + `REMOTION_ENGINE_ENABLED=0` (common) | Hypit |
| Flag on | Remotion |

### After (V5)

| Condition | Renderer |
| --- | --- |
| `REMOTION_ENGINE_ENABLED=1` (default) | **Remotion** |
| Project «e» | Always Remotion |
| `REMOTION_ENGINE_ENABLED=0` | Hypit (explicit legacy) |
| Remotion job failure | **Fail visible** — do not switch to Hypit |

Selection: `backend/remotion_engine.should_use_remotion(project_id)`  
Create Video: `backend/studio.py` → `director_v3` job when Remotion; else Hypit illustration path.

## Caption source

| Piece | Role |
| --- | --- |
| `backend/caption_phrases.py` | Group transcript rows → EN 2–6 / RU 2–5 / ZH CJK; min duration; drop crumbs |
| `remotion_engine.attach_transcript_captions` | Prefer source words; else target alignment; set `captionSource` |
| `visual_variation` / Director props | Pass `captions` into Remotion |
| Remotion `DirectorV3` | Prefer `visualPlan.captions` over caption-pack |

**Never** use arbitrary LLM caption fragments for Remotion captions.

## Transparency fields

On Remotion deliveries / plans:

- `renderer`: `remotion` | `hypit`
- `directorMode`: `runpod_llm` | `heuristic` | …
- `executionValidation`: `passed` | `repaired` | `failed`
- `captionSource`: `source_transcript` | `target_alignment` | `unavailable`

## Director V4 (preserved)

`backend/director_execution.enforce_plan` still runs inside `resolve_scene_plan`:

- PIP / speaker ≥ 324px (Remotion PIP 360×480)
- Incomplete heading rejection
- Transcript-fragment card rejection
- Duplicate statistic removal
- Face-safe / typography checks as implemented

## Tests

```text
pytest backend/tests/test_director_execution.py \
       backend/tests/test_caption_phrases.py \
       backend/tests/test_remotion_engine_v5.py
→ 18 passed
```

## Real previews (20s)

| Project | Alias | Lang | Renderer | captionSource | caps | executionValidation | Desktop |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `9a9c116d8e0d4f7f927e7f60cb926562` | e | ru-RU | remotion | source_transcript | 11 | passed | `~/Desktop/director-v5-e-preview-20s.mp4` |
| `090c9f0d5c3a40eab225191adfa70586` | b | en-US | remotion | source_transcript | 12 | passed | `~/Desktop/director-v5-b-preview-20s.mp4` |
| `director_v5_original1` (Desktop `original1.mp4`) | c | en-US | remotion | source_transcript | 12 | passed | `~/Desktop/director-v5-c-preview-20s.mp4` |

Repo copies: `output/director-v5/{e,b,c}-preview-20s.mp4` + `.report.json`.

Gates: remotion · captions>0 · executionValidation ≠ failed · no silent Hypit.

**Note:** Prior defective MP4 (`lumen-32012faa (3).mp4`) was **Hypit**, not Remotion layout.

## Multilingual

Contract preserved: `ru-RU` / `en-US` / `zh-CN`. Phrase grouping is locale-aware. Dubbed path uses target alignment when source words absent. No language mixing in caption builder.

## Rollout

1. **Done locally:** flag default on + transcript captions + three previews  
2. **Staging (lumen-test):** deploy with `REMOTION_ENGINE_ENABLED=1`, `FAST_PROJECT_CREATION_ENABLED=1`  
3. **Production default:** same flag semantics once staging smoke OK  
4. **Rollback:** `REMOTION_ENGINE_ENABLED=0` → Hypit for non-«e»; «e» stays Remotion  

## Deployment

Target: `142.93.248.163:/opt/lumen-rebuild`  
Preserve media volume · do not touch strom-v2 · do not restart RunPod · verify web+worker.

*(Filled after deploy.)*

## Docs / skills updated

- `docs/architecture/VIDEO_PIPELINE.md`
- `docs/architecture/REMOTION_ENGINE.md`
- `docs/architecture/AI_DIRECTOR.md`
- `docs/architecture/MULTILINGUAL_PIPELINE.md`
- Cursor skills: remotion / director / multilingual (routing + caption contract)

## Git

SHA: _(filled after commit)_  
Push: `feat/media-library-cleanup-v1` (no force)

## Remaining issues

- Full-length production Create Video on lumen-test still needs post-deploy smoke (beyond 20s preview helper).
- Target-language dubbed caption path needs a live dub render for `target_alignment` proof (unit-covered).
- Hypit assembly path retained for unsupported / flag-off projects — not deleted.
