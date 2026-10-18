# Lumen fast project creation

Date: 2026-10-12  
Branch: `feat/media-library-cleanup-v1`

## Old creation flow

```
UPLOAD → probe → status=queued → enqueue studio_analyze
  → OpenRouter reference DNA + director_plan
  → status=ready → Create video
```

Blocking: OpenRouter credit, Douyin reference fetch, wait before workspace.

## New creation flow

```
UPLOAD → probe (+ checksum, fps, orientation) → status=ready
  → workspace opens (no AI)
  → Create video → ensure_analysis (cache or local transcript + heuristic Director)
  → studio_render / director_v3 as before
```

Flag: `FAST_PROJECT_CREATION_ENABLED` (default **true**).  
Rollback: `FAST_PROJECT_CREATION_ENABLED=0` + `LLM_PROVIDER=openrouter` + funded key.

## OpenRouter

| Path | Before | After |
| --- | --- | --- |
| Project create | Always (via analyze job) | **Never** |
| Deferred analysis | n/a | Only if `LLM_PROVIDER=openrouter` and key set |
| Style pictures / stock discovery | Optional paid | Unchanged (user-triggered) |

Default `LLM_PROVIDER=none`. Abstraction: `backend/providers/` (`llm`, `transcript`, `director`).

## Provider replacements

| Capability | Replacement |
| --- | --- |
| Transcript | Local WhisperX / faster-whisper when installed; else placeholder segments |
| Director plan | Heuristic `Director` from duration + transcript (empty recommendations) |
| DNA / OpenRouter vision | Skipped unless OpenRouter explicitly enabled |

## Remaining blockers

- Heuristic plans do not produce rich Douyin-style recommendations without OpenRouter.
- Real ASR quality depends on `faster-whisper` availability on the DO host.
- Full generation E2E on DO (Hypit GPU / Remotion) not re-run in this change set — unit/API coverage only for create + deferral.
- Production deploy still needs CI push to `deploy/testing` / `deploy/production` with env defaults.

## Latency (local unit path)

| Metric | Before (conceptual) | After |
| --- | --- | --- |
| AI requests during create | ≥1 OpenRouter | **0** |
| AI cost during create | OpenRouter tokens | **$0** |
| Processing after upload bytes land | analyze job wait | ffprobe + checksum only |
| Project-ready | after analyze | immediately `ready` |

## Tests

```
.venv/bin/python -m pytest backend/tests/test_fast_project_creation.py backend/tests/test_studio.py -q
→ 15 passed
```

Critical no-AI: create with empty `openrouter_api_key` + `llm_provider=none` → ready, zero jobs, no `ai.json_call`.

## Deployment status

- Pushed: `origin/feat/media-library-cleanup-v1` (`f43163a`).
- Feature flags default-safe (`FAST_PROJECT_CREATION_ENABLED=true`, `LLM_PROVIDER=none`).
- **Blocker:** this `lumen-3.0` repo has no `deploy/testing` branch / CI path on the DO host (`ssh lumen` runs MorcaLabs `strom-v2`, not this app). No live lumen-3.0 uvicorn found; docker requires sudo password. Live upload verify deferred until the app’s deploy target is available.
- Do not touch RunPod for this change.

## Git

Commit SHA: `f43163a4f19a875a92026430a12d128e48aa31f3` (docs SHA note on `9c953fb`)
