# Deployment and rollback

Do not deploy this checkout yet.

## Why

- Host SHA file `9116f15` and this branch `a4985b6` are different histories, both dirty relative to each other.
- The host already has an uncommitted Qwen service and `ASR_MODEL=Qwen/Qwen3-ASR-1.7B`. Copying this tree over `/opt/lumen-rebuild` would mix two unsynced edits.
- ASR peak measured on that host is about 5.9 GiB. Worker cap is 2800 MiB. ASR unit cap is 6200 MiB. Together they exceed 7.8 GiB with no swap. A deploy that restarts `lumen-asr` during a running transcribe job would kill that job.
- End-to-end playback, captions, and retrieval were not verified. See `docs/testing/END_TO_END_RESULTS.md`.
- `SEMANTIC_PLANNER_REQUIRED` must stay unset or `0` until a text model is measured in its own process with ASR unloaded.

## When a deploy is approved

1. Confirm no `transcribe` or `director_v3` job is queued or running.
2. Confirm `MemAvailable` before any ASR restart. Do not start recognize while another recognize or align child exists.
3. Deploy the git revision, not a hand copy that drops the host-only fixes or this checkout's uncommitted Studio work, whichever is reviewed.
4. Leave model snapshots in `/mnt/volume_nyc1_1791446889637/qwen3-asr/hf`. Do not re-download over them.
5. Do not change `renders/` or original1 / original4 files.
6. Restart `lumen-web`, `lumen-worker`, and `lumen-asr` only. Do not raise MemoryMax in the same change.
7. Watch one new test project that is not original1 or original4 through transcript `verified`, then stop before Create Video unless a render is explicitly in scope.

## Rollback

1. Set `ASR_MODEL=small` if Qwen jobs are failing closed and Whisper is the accepted temporary path. Restart only the worker.
2. Stop `lumen-asr` if it is wedged and no job needs it.
3. Set `SEMANTIC_PLANNER_REQUIRED=0`.
4. Leave `REMOTION_ENGINE_ENABLED=1`.
5. Do not delete the volume model directory or project MP4s.

This document is the procedure. It was not executed.
