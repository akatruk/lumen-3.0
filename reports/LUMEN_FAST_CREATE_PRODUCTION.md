# Fast create — production deploy report

Date: 2026-10-12

## Actual deployment target

| Item | Value |
| --- | --- |
| Host | `root@142.93.248.163` — hostname **`lumen-fix`** |
| Public | `https://lumen-fix.universalgravity.org` |
| App | `/opt/lumen-rebuild` |
| Services | `lumen-web`, `lumen-worker` |
| Volume | `/mnt/volume_nyc1_1791446889637/` (100 GB, 811 library assets) |
| **Not used** | SSH `Host lumen` / `188.166.244.242` (**strom-v2**) — untouched |

## Deployed commit / marker

- Feature code base: `d7bdbdd` + director-mode signaling (working tree → archive)
- Server marker: `/opt/lumen-rebuild/DEPLOY_SHA.txt`
- Backup: `/opt/lumen-rebuild/backups/fast-create-20261012-071106.tar.gz`
- Env: `FAST_PROJECT_CREATION_ENABLED=1`, `LLM_PROVIDER=none`, `TRANSCRIPT_PROVIDER=auto`
- RunPod: **not touched** (worker paused only during create-video enqueue test)

## Application health

- `http://127.0.0.1:8018/api/health` → `{"status":"ok"}`
- `lumen-web` / `lumen-worker` → **active**
- Imports: `fast=True`, `llm_provider=none`, `llm_available=False`, default Director provider **`heuristic`**

## Upload test (production)

**PASS**

- Create → `201`, `status=ready`, `stage=ready`
- Jobs after create: **[]**
- OpenRouter hooks patched to explode if called → **0 calls**
- Source saved + `source_checksum` + portrait metadata
- Language API `PUT .../language` for `ru-RU` / `en-US` / `zh-CN` → **200**

## Generation test

**PASS (trigger + deferred analysis only — GPU render intentionally cancelled)**

- `POST create-video` → `200`
- Response: `director_mode=heuristic`, `director_provider=heuristic`, `analysis_quality=local_baseline`
- Enqueued `studio_render` then **failed before worker** to avoid RunPod
- **Active Director: heuristic local baseline — NOT LLM / not AI-directed production quality**

Full Hypit/Remotion MP4 path not re-run in this verify (would resume GPU). Remotion module still importable; `remotion_engine.enabled()` remains **false** (flag unset).

## Provider architecture

| Setting | Effect |
| --- | --- |
| `LLM_PROVIDER=none` | Create never calls OpenRouter; generation uses heuristic Director with explicit mode stamp |
| `LLM_PROVIDER=openrouter` + key | Create still AI-free; **Create video** may run full `studio.analyze` LLM Director |
| Remaining OpenRouter uses | Optional: style pictures, stock discovery, quality review, legacy DNA — user-triggered / optional paths |

No other LLM endpoints are configured on this host (no local Ollama / DO inference for Director).

## Multilingual / regression

| Check | Result |
| --- | --- |
| Locales in config | ru-RU / en-US / zh-CN |
| Voice resolve | original vs dubbed modes resolve without silent wrong-language swap |
| Media library | 811 assets on volume |
| Existing projects with result | **8 preserved** (count unchanged during E2E) |
| Cards / Remotion code | present; Remotion flag still off |

## Git

Pushed on `feat/media-library-cleanup-v1` after this report commit.

## Rollback

1. Restore `backups/fast-create-20261012-071106.tar.gz`
2. Or set `FAST_PROJECT_CREATION_ENABLED=0` + `LLM_PROVIDER=openrouter` (funded)
3. `systemctl restart lumen-web lumen-worker`
