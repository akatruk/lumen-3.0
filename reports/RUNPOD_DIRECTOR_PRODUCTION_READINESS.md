# RunPod Director V1 — production readiness

Date: 2026-10-12  
Branch: `feat/media-library-cleanup-v1`  
Host: `lumen-test` (`142.93.248.163`) `/opt/lumen-rebuild`  
Constraint for this pass: **no GPU resume**, **no `LLM_PROVIDER` flip**, **no OpenRouter**.

## Verdict

**NOT production-ready** for LLM-directed Create Video.

| Layer | Status | Notes |
| --- | ---: | --- |
| Remotion «e» 20s preview render | **PASS** (technical) | `e-preview-20s.mp4` plays; 1080×1920@30; AAC present |
| Visual QA of that preview | **CONDITIONAL PASS** | Speaker + captions generally face-safe; one caption bug (literal `C`) |
| Preview driven by qwen2.5:7b | **FAIL** | Preview is ordinary Director V3 `resolve_plan`, not RunPod LLM plan |
| RunPod LLM A/B (plan-only) | **PASS** (historical) | While pod was RUNNING; artifact `reports/runpod_director_ab.json` |
| Live LLM now | **FAIL** | Pod `nxi1rfwb94eufx` **EXITED**; host `LLM_PROVIDER=none` |
| Fast create AI-free | **PASS** | Upload still no LLM |
| Media volume / manifest | **PASS** | 829 assets; 18 `pm_*` premium motion on disk |
| Unit regressions | **PASS** | 11 tests (`test_runpod_llm_provider` + `test_fast_project_creation`) |

Do **not** treat “MP4 rendered OK” as LLM Director production readiness.

## 1. Preview location

| Item | Value |
| --- | --- |
| Host path | `/opt/lumen-rebuild/output/runpod-director-v1/e-preview-20s.mp4` |
| Local copy | `output/runpod-director-v1/e-preview-20s.mp4` |
| Report | `e-preview-20s.report.json` (host + `reports/e-preview-20s.report.json`) |
| SHA-256 prefix | `ef9de2b4782b857c…` (matches render.log) |
| Size / duration | 6.7 MB / 20.05 s |
| Video | H.264 1080×1920 30 fps (600 frames) |
| Audio | AAC 48 kHz stereo; mean ≈ −22.4 dB, max ≈ −1.2 dB |
| Encoder comment | `Made with Remotion 4.0.524` |

## 2–4. Frame / motion QA (sampled t≈1,5,10,15,19 s)

Frames: `output/runpod-director-v1/frames/f01.jpg` … `f05.jpg`.

| Check | Observation |
| --- | --- |
| Speaker visibility | Present full-frame, split, and PIP; face lit and sharp |
| Face-safe | Captions/cards stay on torso / lower third; face clear in sampled frames |
| Caption readability | Dark pill + white/gold RU text; generally strong contrast |
| Motion diversity | Hook cards → residency split → consult plate+PIP → criteria cards → return host |
| Semantic media | Doorway family / consult phone plate match relocation/consult beats |
| Source preservation | Host identity continuous; original speaker is protagonist |
| Audio sync | Speech present and loud; no silent track. Exact lip-sync not instrumented this pass |
| BGM | No separate music bed identified in this preview (speech-forward mix) |

**Bug (remaining):** at ~5 s split (residency), left caption pill shows a lone **`C`** instead of a full RU caption — typography/localization defect in that beat.

## 5. Heuristic vs RunPod LLM (plan A/B)

From `reports/runpod_director_ab.json` (live when pod RUNNING; latency ~21 s):

| | Heuristic | RunPod `qwen2.5:7b-instruct` |
| --- | --- | --- |
| Scenes | 4 flat grid | 3 semantic (`hook`,`context`,`transition`) |
| Summary | boilerplate “Local plan…” | grounded residency-via-property summary |
| Provenance | `director_mode=heuristic` | health `provider=runpod`, model listed |

**This A/B is plan-generation only.** It was **not** the input to `e-preview-20s.mp4`.

## 6. Was the preview from qwen2.5?

**No.**

`e-preview-20s.report.json`:

- `generationId`: `ordinary_9a9c116d_20s`
- `path`: `plan_for_request≈resolve_plan → resolve_scene_plan → render_with_plan → DirectorV3Preview`
- Beats: fixed V3 set (`hook`,`residency`,`consult`,`beside`,`steps`,`return`)

That is the seeded Remotion Director V3 ordinary path, independent of `LLM_PROVIDER` / Ollama.

## 7. Pipeline map (what is / isn’t wired)

```
[Upload] ──AI-free──► READY          ✅ production today

[Create Video]
   ├─ LLM_PROVIDER=none  → heuristic plan stamp        ✅ safe default
   ├─ LLM_PROVIDER=runpod → Ollama on pod (fail-closed) ✅ code+tests; needs RUNNING pod
   └─ Project «e» Remotion
         └─ visual_variation.resolve_plan (ordinary)   ✅ preview proven
         └─ LLM studio plan → Remotion props            ❌ not proven / not wired for this MP4
```

Media retrieval for the preview used library plates (`people_door_001`, `i2v_phone_001`, `rp_detail_001`) via ordinary resolve — not the new `pm_*` premium pack.

## 8–9. DigitalOcean volume

| Check | Result |
| --- | --- |
| Volume | `/mnt/volume_nyc1_1791446889637/` ~79 GB free / ~15 GB used |
| Project source «e» | present (~22 MB) |
| Manifest assets | **829** |
| Premium motion | **18** files under `app-library/motion/premium/` (`pm_*`) |
| Sample codec | VP9 `yuv420p` (verify alpha claims separately; probe did not show `yuva`) |

## 10. Regression tests (local)

```
pytest backend/tests/test_runpod_llm_provider.py backend/tests/test_fast_project_creation.py
→ 11 passed
```

## 11. GPU cost / safe startup

| Item | Value |
| --- | --- |
| Pod | `nxi1rfwb94eufx` / `lumen-hypit-4090` |
| State now | **EXITED** (this validation did not resume) |
| Rough burn | ~$0.90/hr while RUNNING (prior ops notes) |
| Model VRAM | ~6.7 GB for `qwen2.5:7b-instruct` |

### Safe RunPod startup sequence (manual / authorized only)

1. Resume **existing** pod only: `scripts/runpod_pod_control.py resume` → `nxi1rfwb94eufx`  
   Do **not** create a new pod; do **not** start `lumen-web-gpu`.
2. SSH: ensure Ollama serve on `127.0.0.1:11434`, models under `/workspace/lumen-llm/models`, model `qwen2.5:7b-instruct` pulled.
3. On lumen-test: set `LLM_PROVIDER=runpod`, `RUNPOD_LLM_MODEL=qwen2.5:7b-instruct`, keep `FAST_PROJECT_CREATION_ENABLED=1`.
4. `systemctl restart lumen-web lumen-worker`.
5. Probe: `GET /api/health/runpod-llm` (auth) — must be ok; Create Video with provider=runpod must **fail closed** if Ollama down (no silent heuristic).
6. After jobs: unload LLM before Hypit/speech (hooks already in `hypit_gpu` / `gpu_speech`); stop pod when idle.

### Recommended production configuration (until LLM path is end-to-end proven)

```
FAST_PROJECT_CREATION_ENABLED=1
LLM_PROVIDER=none
REMOTION_ENGINE_ENABLED=false   # «e» still Remotion via project id
# RUNPOD_LLM_* kept in code defaults; do not enable until startup sequence verified
```

Flip to `LLM_PROVIDER=runpod` only after a Create Video that stamps `director_mode=runpod` **and** a Remotion/Hypit delivery that consumes that plan (not only ordinary `resolve_plan`).

## Remaining bugs / gaps

1. Preview ≠ LLM Director — missing end-to-end wiring proof.
2. Caption artifact `C` on residency split beat.
3. Premium `pm_*` not evidenced in this 20s preview selection.
4. Global Remotion still flag-off for non-«e».
5. Pod EXITED → live Create Video cannot use RunPod LLM today (by design with `LLM_PROVIDER=none`).
6. No instrumental A/V sync / BGM measurement beyond loudness + stream presence.

## Git

Readiness doc: this file.  
Related code already on branch (`0970226` RunPod provider, `2651286` / later deploy markers).  
Do not commit the 6.7 MB MP4.
