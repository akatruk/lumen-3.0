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


## Independent revalidation — 2026-10-12 (Asia/Bangkok)

This section supersedes conflicting assertions above. No application code, deployment,
provider configuration, GPU services or pod lifecycle were changed during this pass.

### Verified evidence

- Checkout: `/Users/akatruk_macbook/Documents/github/lumen-3.0`, initial HEAD
  `722b51e`; remote branch `feat/media-library-cleanup-v1` matched that HEAD.
  Existing modified and untracked user files were preserved.
- Read-only SSH to `root@142.93.248.163` succeeded; hostname is `lumen-fix`.
  `/opt/lumen-rebuild` is not a Git checkout, so its deployed SHA could not be
  independently established with Git.
- Local and server MP4 SHA-256 both equal
  `ef9de2b4782b857c1e512f88d3f9d1f78dfca4029e9e6083809bad3a9842a95d`.
  Full FFmpeg decode succeeded without errors. Probe confirms 20.053333 seconds,
  H.264 1080x1920 at 30 fps and AAC stereo at 48 kHz. This proves decodability;
  it does not certify playback in every browser.
- A fresh 20-frame contact sheet (one frame per second across the entire clip)
  shows full host, split, consultation PIP, criteria and steps treatments.
  Full-size existing frames at approximately 5 and 10 seconds were inspected.
  The source speaker remains identifiable; the consult plate is related to the
  consultation theme, but source-transcript semantic fidelity is not established.
- **Visual gate FAIL:** at about 10 seconds the dark caption backing overlaps and
  dims the presenter PIP face. Opening cards also occupy the lower-face area in
  the contact sheet. Therefore the previous blanket face-safe assessment is too
  strong. The lone `C` at about 5 seconds becomes a complete phrase in later
  samples: it may be a caption entrance/reveal, not a persistent localization bug.
  Frame-by-frame timing is needed before calling it a broken caption.
- Measured audio mean -22.4 dB and peak -1.2 dB. Lip synchronization and the
  audible music mix were not perceptually verified. The current composition
  contains `Audio` for `bed.mp3`; a combined AAC stream cannot establish whether
  a separate music bed is audible. The earlier assertion of absent music is
  therefore unproven.
- Server `.env` still contains `LLM_PROVIDER=none`.

### Director provenance and comparison limits

`reports/runpod_director_ab.json` records a historical 21.42-second successful
request and health metadata for `qwen2.5:7b-instruct` through Ollama's forwarded
OpenAI-compatible endpoint. The saved plan differs from the heuristic summary
(3 semantic scenes versus 4). These are historical artifacts, not independently
replayed live inference. Raw request/response logs, model digest and a durable
request-to-render identifier were not available in the inspected evidence.
Model-generated scores in the plan are not human quality measurements.

The preview report and `scripts/ordinary_director_render.py` establish the ordinary
seeded `resolve_plan` → `resolve_scene_plan` → `render_with_plan` →
`DirectorV3Preview` path. Its selected assets are `people_door_001`,
`rp_detail_001` and `i2v_phone_001`. The RunPod provider returns a different Studio
Director schema. No artifact links its output to this preview's visual plan.
Thus this MP4 is evidence for the ordinary/heuristic renderer, not the Qwen renderer.
No paired, same-input Qwen-rendered preview was found; a visual A/B verdict is blocked.
Do not infer that all production routes are unwired solely from this one preview.

### Volume and manifest

The mounted volume reports 100 GB total, 16 GB used, 79 GB available. The
server manifest has 829 entries and no duplicate IDs. All 400 entries with
`source=runpod` resolve to existing files, including nested
`static/runpod/photographs/`. All 18 `pm_*` entries have files available.

Five entries (`re_motion_price_counter`, `re_motion_price_change`,
`re_motion_rental_yield`, `re_motion_comparison`, `re_motion_purchase`) reference
`motion/src/realestate/scenes.tsx`, which is not a file under the media volume.
That source exists in the local application checkout. These are procedural
references, not demonstrated lost recovery files; their server renderer mapping
and availability remain unverified. Manifest integrity is therefore conditional,
not an unconditional all-assets-on-volume PASS. Existing-file checks do not
constitute checksums or full decoding of all recovered assets.

### Fresh regressions

`PYTHONPATH=. .venv/bin/pytest backend/tests/test_runpod_llm_provider.py
backend/tests/test_fast_project_creation.py backend/tests/test_director_media_rules.py -q`
completed: **14 passed**, two dependency deprecation warnings. These tests cover
provider behavior, AI-free creation and media layer rules. They do not prove
live Qwen inference, a full browser/worker delivery lifecycle or creative quality.

### Operational recommendation and blockers

Keep the existing `LLM_PROVIDER=none` configuration. No RunPod API call was made,
so EXITED is historical reported state rather than a freshly verified pod status.
The prior ~$0.90/hour figure is historical and has not been verified as the
current price. Do not use it as a billing quote. Startup steps above are a
proposed authorized procedure, not a procedure executed in this pass.

Remaining acceptance work: obtain a same-source Qwen-rendered counterpart and
raw provider provenance; verify the scene-plan adapter and asset mappings;
resolve presenter-face obstruction; inspect motion continuously and listen to
speech/music against source; validate procedural assets on the host; and perform
an isolated complete Create Video/download lifecycle. Live inference cannot be
retested within the no-resume constraint when the pod is stopped.

**Verdict remains NOT production-ready / acceptance blocked.** Only technical
preview decoding, saved ordinary render provenance, scoped regressions and the
specified file-existence checks passed. No code fix or deployment is claimed.
