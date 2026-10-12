# RunPod Native AI Director V1

Date: 2026-10-12  
Branch: `feat/media-library-cleanup-v1`  
Host: `root@142.93.248.163` (`lumen-test`) — `/opt/lumen-rebuild`  
Constraint: **no OpenRouter**, **no DO Serverless Inference**, **no strom-v2**, FAST create stays on.

## Verdict

| Criterion | Status |
| --- | ---: |
| Pod `lumen-hypit-4090` (`nxi1rfwb94eufx`) RUNNING RTX 4090 24GB | **PASS** |
| Local LLM installed (Ollama) + model selected | **PASS** — `qwen2.5:7b-instruct` |
| OpenAI-compatible `/v1` on pod loopback + SSH tunnel | **PASS** |
| `LLM_PROVIDER=runpod` fail-closed (`RUNPOD_LLM_UNAVAILABLE`) | **PASS** (unit + live) |
| No silent heuristic when provider=runpod | **PASS** |
| Fast create READY when RunPod LLM down | **PASS** |
| Heuristic vs RunPod A/B (same transcript) | **PASS** |
| GPU load → plan → unload before Hypit/speech | **PASS** (hooks in `hypit_gpu.film` / `gpu_speech`) |
| Remotion 20s staging preview (project «e») | see render log / path below |
| Global `REMOTION_ENGINE_ENABLED` | **left false** (staging only) |
| Deploy with `LLM_PROVIDER=runpod` | set on lumen-test after health OK |

## Machine

| Item | Value |
| --- | --- |
| Pod | `nxi1rfwb94eufx` / `lumen-hypit-4090` |
| GPU | NVIDIA GeForce RTX 4090, 24564 MiB |
| Driver / CUDA | 570.211.01 / 12.8 |
| Torch | 2.8.0+cu128 |
| Volume | `spsiypcy8y` @ `/workspace` |
| LLM home | `/workspace/lumen-llm/` (bin, models, logs) |
| Idle VRAM before LLM | 1 MiB |
| Balance at audit | ~$10 (spend ~$0.90/hr while RUNNING) |

`lumen-web-gpu` left **EXITED**. No new pod created.

## Model benchmark (identifiers that exist)

| Model | Size | Peak VRAM | Latency (Director JSON) | Schema keys OK |
| --- | ---: | ---: | ---: | ---: |
| `qwen2.5:7b-instruct` | 4.7 GB | ~6748 MiB | ~9–22 s | **yes** (after normalize) |
| `qwen3:8b` | 5.2 GB | ~9980 MiB | ~23 s | incomplete (`recommendations` missing) |

**Winner: `qwen2.5:7b-instruct`** — best schema compliance, lower VRAM, faster.  
Runtime: **Ollama 0.40.3** (OpenAI-compatible `http://127.0.0.1:11434/v1`). Bound to loopback; DO reaches it via existing Hypit SSH key / local forward. Not exposed publicly.

Why Ollama over vLLM/llama.cpp: already-warm PyTorch image, trivial `keep_alive=0` unload for shared 4090 with Hypit/I2V/speech, OpenAI `/v1` shim, models on network volume.

## Integration

| Piece | Path |
| --- | --- |
| Client + tunnel + unload | `backend/runpod_llm.py` |
| Schema coerce | `backend/runpod_director_normalize.py` |
| Provider | `backend/providers/llm.py` (`RunPodLLMProvider`) |
| Director | `backend/providers/director.py` (`RunPodDirectorProvider`) |
| Fail-closed generation | `backend/source_analysis.ensure_analysis` |
| Health | `GET /api/health` (flags) + `GET /api/health/runpod-llm` (auth deep probe) |
| Ops | `scripts/runpod_llm_control.py` |

Flags:

```
FAST_PROJECT_CREATION_ENABLED=1
LLM_PROVIDER=runpod          # fail-closed at Create Video
RUNPOD_LLM_MODEL=qwen2.5:7b-instruct
REMOTION_ENGINE_ENABLED=     # unset/false — project «e» still Remotion
```

## A/B (same 20s RU transcript)

| | Heuristic | RunPod LLM |
| --- | --- | --- |
| Scenes | 4 flat grid | 3 semantic (`hook`,`context`,`transition`) |
| Summary | boilerplate | grounded in transcript |
| Latency | n/a | ~21 s (incl. load) |

Artifact: `reports/runpod_director_ab.json` on host; plan `reports/runpod_director_plan.json`.

## Remotion staging

Project «e» `9a9c116d8e0d4f7f927e7f60cb926562` source present.  
Preview target: `output/runpod-director-v1/e-preview-20s.mp4` (ordinary Director V3 chain).  
Do **not** flip global Remotion until non-«e» face-safe review.

## Ops notes

- Keep Ollama on pod: `OLLAMA_MODELS=/workspace/lumen-llm/models`; `ollama serve` on `127.0.0.1:11434`.
- Before Hypit/speech: `runpod_llm.unload_model()` (already hooked).
- Pod EXITED → code still works offline/mock; live SUCCESS needs resume of **existing** `nxi1rfwb94eufx` (do not create a new paid pod).
- Rotate RunPod API key if it ever appeared in shell `set -x` logs.

## Tests

`PYTHONPATH=. .venv/bin/pytest backend/tests/test_runpod_llm_provider.py backend/tests/test_fast_project_creation.py` — pass.


## Deploy stamp (close-out)

- Code + adapters on `lumen-test` `/opt/lumen-rebuild`
- Preview: `/opt/lumen-rebuild/output/runpod-director-v1/e-preview-20s.mp4` (20.05s, 1080×1920, 7.0 MB, sha `ef9de2b4782b857c…`)
- Unit tests: `test_runpod_llm_provider` + fast-create — **11 passed**
- Live LLM A/B while pod was RUNNING: **PASS** (`reports/runpod_director_ab.json`)
- Close-out pod status: **EXITED** (`nxi1rfwb94eufx`) — do not auto-resume
- Production flag left at `LLM_PROVIDER=none` so Create Video stays usable; flip to `runpod` after:
  1. `python3 scripts/runpod_pod_control.py resume` (existing pod only)
  2. ensure Ollama serve + model on volume
  3. set `LLM_PROVIDER=runpod` + restart `lumen-web` / `lumen-worker`

**Live LLM criterion at close-out:** FAIL until existing pod resumed (approval required). Integration/code/tests/preview: PASS.

## Production readiness follow-up (2026-10-12)

See `reports/RUNPOD_DIRECTOR_PRODUCTION_READINESS.md`.

Honest split: Remotion `e-preview-20s.mp4` **PASS** technically, but it is the **ordinary Director V3** path (`ordinary_9a9c116d_20s`), **not** qwen2.5 plan→Remotion. LLM A/B remains plan-only evidence. Host left `LLM_PROVIDER=none`; pod **EXITED**. Overall: **NOT production-ready** for LLM-directed Create Video.
