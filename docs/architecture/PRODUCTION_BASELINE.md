# Production baseline

Checked 2026-10-18 06:28 UTC on `lumen-fix` (`142.93.248.163`), read-only. This checkout was not deployed and the host was not restarted.

## Versions

| | Value |
| --- | --- |
| Host | `lumen-fix`, 4 vCPU, 7941 MiB RAM, no GPU, no swap |
| `DEPLOY_SHA.txt` | `9116f15df1d0f68db6f299a402cb40557b74dd94` |
| Git on the host | No `.git` directory |
| This checkout | `a4985b604072efdad9cf4d38f58a881134fd0072` on `experiment/create-project-ux` |
| Ancestor | `9116f15` is not an ancestor of this checkout |

`DEPLOY_SHA.txt` is not a description of every file on the host. After that SHA was written, `/opt/lumen-rebuild` gained Qwen ASR modules that are not in `9116f15`, and `.env` `ASR_MODEL` is `Qwen/Qwen3-ASR-1.7B`. Those host edits are not in this git commit either.

## Services at check time

| Unit | State | Limit |
| --- | --- | --- |
| `lumen-web` | active | MemoryMax 800 MiB |
| `lumen-worker` | active | MemoryMax 2800 MiB, CPUQuota 180% |
| `lumen-asr` | active | MemoryMax 6200 MiB, CPUQuota 300%, `MemorySwapMax=0` |
| PostgreSQL | active | |
| Redis | inactive | |

Health: `llm_provider=none`, `fast_project_creation=true`, visual intelligence off, pgvector `0.6.0`.

Flags read from `/opt/lumen-rebuild/.env` names only: `FAST_PROJECT_CREATION_ENABLED=1`, `REMOTION_ENGINE_ENABLED=1`, `LLM_PROVIDER=none`, `TRANSCRIPT_PROVIDER=auto`, `ASR_MODEL=Qwen/Qwen3-ASR-1.7B`, `ASR_MODEL_CACHE=/mnt/volume_nyc1_1791446889637/lumen-asr`, `VISUAL_INTELLIGENCE_ENABLED=0`, `VISUAL_EXPERIENCE_MEMORY_ENABLED=0`. V14–V18 flags are unset. `RUNPOD_LLM_MODEL=qwen2.5:7b-instruct` is configured and not running on this host (no Ollama).

One job was `running`: `transcribe` `3c3a87baf59e4a859ce3b085fc64e3c2` for project `9ad7b6ce128e4587a7ebe2cbccedc77e`, model `Qwen/Qwen3-ASR-1.7B`. It was not cancelled.

## What the host actually runs

- Web upload still enqueues `jobs.kind=transcribe` on `lumen-worker`.
- When `ASR_MODEL` starts with `Qwen/Qwen3-ASR`, `get_transcript_provider()` returns `Qwen3TranscriptProvider`. That client talks to a Unix socket. It does not import `qwen_asr` inside the app venv (`qwen_asr` is absent there).
- `lumen-asr.service` runs `python -m backend.qwen3_asr_service` as user `lumen`. Recognition and alignment are child processes of `/mnt/volume_nyc1_1791446889637/qwen3-asr/venv/bin/python`.
- Weights on the volume: `Qwen/Qwen3-ASR-1.7B` snapshot `7278e1e70fe206f11671096ffdd38061171dd6e5`, `Qwen/Qwen3-ForcedAligner-0.6B` snapshot `c7cbf2048c462b0d63a45797104fc9db3ad62b7`. Tree size 14 GB. Whisper small (464 MB) is still in the ASR cache.
- Planner on the host is still `HeuristicDirectorProvider` plus a deterministic `source_brief.py` (`kind=deterministic_baseline`). `LLM_PROVIDER=none`.
- Create Video still enters `director_v3.run_job` and Remotion.

## Memory

| Observation | Measurement |
| --- | --- |
| Manual Qwen3-ASR-1.7B bf16 CPU probe | VmHWM 6,051,720 kB, inference 190.2 s, language Chinese, 329 characters. Process was finished by the 06:28 check. |
| `asr_qwen/recognize.py` during the live upload job | RSS 5,187,284 kB at 47 s elapsed. Not the aligner. |
| Host RAM | 7941 MiB, available about 7248 MiB after that child exited |
| Worker + ASR unit caps | 2800 + 6200 MiB, which is more than the host |

Qwen ASR and a Remotion render must not be assumed to fit at the same time. The ASR child is outside the 2800 MiB worker. The unit cap of 6200 MiB can still push the host into reclaim with no swap.

## Local tree vs host

This checkout has uncommitted work on Studio, Director, captions, and audio that the host SHA does not have. The host has `backend/qwen3_asr.py`, `qwen3_asr_service.py`, `qwen3_segments.py`, `asr_qwen/`, and a newer `source_transcript.py` that this commit did not contain at the start of the session.

Do not reset either tree to the other. The safe direction is: keep host projects and MP4s, land reviewed code in git, deploy only after the checks in `DEPLOYMENT_AND_ROLLBACK.md`.

## Migration

1. Leave `9116f15` recorded. Do not rewrite `DEPLOY_SHA.txt` until a real deploy.
2. New transcript fields are additive on `localization/source-transcript.json`. Old `source-transcript-1` files still load when the checksum and model match.
3. A corrected transcript sets `transcript_edit_version`. The next plan rebuilds. `renders/<id>/` is not rewritten.
4. `SEMANTIC_PLANNER_REQUIRED` defaults off. Heuristic planning stays labeled `local_baseline`. Turning the flag on without a planner command fails the job (`PLANNER_UNAVAILABLE`). It does not substitute a heuristic and report AI success.
5. original1 and original4 were not written during this pass.

## Rollback

On the host, without deleting media:

1. Stop `lumen-asr` only after confirming no transcribe job is running.
2. Set `ASR_MODEL=small` and restart `lumen-worker` so the provider returns faster-whisper. Do not delete `/mnt/volume_nyc1_1791446889637/qwen3-asr`.
3. Leave `REMOTION_ENGINE_ENABLED=1` and `LLM_PROVIDER=none`.
4. V14–V18 stay unset.

That rollback is not authorized by this document. It is the procedure.

## Tests run here

`PYTHONPATH=. .venv/bin/pytest` on `test_pipeline_repair.py`, `test_source_transcript.py` (19 passed) and `test_fast_project_creation.py`. `test_source_language.py::test_worker_does_not_force_the_output_language` failed once because a fake transcribe function rejected `on_phase`, then passed after the call became signature-aware.

No production upload, no Create Video, no new Qwen process. The host already had one.
