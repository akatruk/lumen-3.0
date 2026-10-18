# AI Director V4 — production LLM + Remotion validation

Date: 2026-10-12  
Host inspected: `root@142.93.248.163` (`lumen-test`) — `/opt/lumen-rebuild`  
Branch: `feat/media-library-cleanup-v1`  
Constraint: **no OpenRouter**; **no strom-v2**; FAST create stays on; no RunPod restart.

## Verdict: BLOCKED (required LLM provider missing)

Production LLM Director V4 **cannot ship** on lumen-test without inventing credentials or violating the no-OpenRouter rule.

| Criterion | Status |
| --- | ---: |
| Fast upload AI-free | **PASS** (unchanged: `FAST_PROJECT_CREATION_ENABLED=1`) |
| Real LLM Director (non-OpenRouter) | **BLOCKED** |
| Validated semantic scene plans from LLM | **BLOCKED** |
| Media library + visual_variation | **PASS** (already wired; heuristic path) |
| Remotion real render path | **PARTIAL** — project «e» always Remotion; `REMOTION_ENGINE_ENABLED` still **false** |
| Heuristic vs LLM 20s compare | **BLOCKED** (no LLM) |
| Deploy with LLM mode | **NOT DONE** (would be a lie) |
| Commit + push of this report | see Git |

## 1. Model / credential discovery (names only)

### lumen-test `.env` key names present

`DATABASE_URL`, `DATA_DIR`, `FAST_PROJECT_CREATION_ENABLED`, `GOOGLE_*`, `LLM_PROVIDER`, `LUMEN_*`, `MAX_DURATION_SECONDS`, **`OPENROUTER_API_KEY`**, `PUBLIC_ORIGIN`, `RUNPOD_API_KEY`, `SECURE_COOKIES`, `TIKHUB_*`, `TRANSCRIPT_PROVIDER`

### Non-secret flag values

| Flag | Value |
| --- | --- |
| `FAST_PROJECT_CREATION_ENABLED` | `1` |
| `LLM_PROVIDER` | `none` |
| `REMOTION_ENGINE_ENABLED` | **absent** → settings default `false` |

### Missing for DigitalOcean Gradient / Serverless Inference

Per DO docs, serverless inference needs a Model Access Key and OpenAI-compatible base URL:

| Required | Expected | On lumen-test |
| --- | --- | ---: |
| Model Access Key | `MODEL_ACCESS_KEY` and/or `GRADIENT_MODEL_ACCESS_KEY` (`doo-v1-…`) | **ABSENT** |
| Endpoint | `https://inference.do-ai.run/v1` (`/chat/completions`, `/models`) | unreachable without key |
| Optional PAT | `DIGITALOCEAN_API_TOKEN` / `DIGITALOCEAN_ACCESS_TOKEN` | **ABSENT** |

Also absent: local Ollama on host (`:11434` refused), `doctl`, any `DO_*` / `GRADIENT_*` / `INFERENCE_*` env keys.

Vault (`secret/admins/*`): session **403** — could not read alternate secret stores from this agent.

Local Mac shell: `MODEL_ACCESS_KEY`, `GRADIENT_MODEL_ACCESS_KEY`, DO tokens — all **UNSET**.

Local Ollama (dev Mac only): `qwen2.5-coder:14b` — **not** on lumen-test; coding model only; not a production Director provider.

### Providers already in code

| Provider | Path | Notes |
| --- | --- | --- |
| `none` | `backend/providers/llm.py` | default |
| `openrouter` | same + `backend/ai.py` | **forbidden for this task** even though `OPENROUTER_API_KEY` exists on host |
| DigitalOcean / Gradient | **not implemented** | no adapter, no model catalog call |

**No inventable model ID.** Without `MODEL_ACCESS_KEY`, `/v1/models` cannot be queried, so GPT-6.1 Sol / any claimed DO catalog ID is unverified.

## 2. Why we STOP (do not invent)

Brief rules:

1. Do not use OpenRouter.
2. Do not invent model IDs.
3. Production LLM mode must not silently fall back to heuristic.
4. If required provider unavailable → report blocker with exact missing credential/endpoint.

Enabling `LLM_PROVIDER=openrouter` would violate (1).  
Implementing `LLM_PROVIDER=digitalocean` that calls a guessed model without a key would violate (2)/(4).  
Setting `LLM_PROVIDER=digitalocean` without a key and falling back to heuristic would violate (3).

## 3. Remotion audit (parallel workstream)

| Item | Finding |
| --- | --- |
| Why flag disabled | Intentional: non-«e» Hypit fallback until speaker staging generalized (`reports/REMOTION_ENGINE_V1.md`) |
| Project «e» | `9a9c116d…` **always** Remotion via `remotion_engine.should_use_remotion` / `studio.create-video` |
| Binary | `/opt/lumen-rebuild/motion/node_modules/.bin/remotion` **OK**; Node v22.20.0 |
| Public media | `/mnt/volume_nyc1_1791446889637/lumen-motion/public/director-v3/` has speaker/consult/passport |
| Library | `app-library` file count **1136** on volume (prior report cited 811 manifest assets) |
| Prior renders on «e» | **69** render dirs preserved |
| `REMOTION_ENGINE_ENABLED` | still **off** — do not flip globally until non-«e» path is face-safe |

Staging path for «e» remains: `visual_variation.plan_for_request` → `director_v3` job → `resolve_scene_plan` → Remotion CLI. Typography Remotion-only; face-safe gates already in Director V3 MAIN prompt.

**Not done this pass:** enable flag for all projects; new 20s LLM vs heuristic compare (no LLM).

## 4. Existing source for future A/B (when key arrives)

Use project «e» only — real source, not synthetic demo:

- Path: `/mnt/volume_nyc1_1791446889637/lumen/9a9c116d8e0d4f7f927e7f60cb926562/source`
- Director V3 composition: `DirectorV3Preview`
- Compare once DO inference works: same seed inputs, heuristic `director_mode=heuristic` vs `director_mode=digitalocean` (or whatever provider name), objective metrics only (asset diversity, treatment changes, caption geometry, face-collision flags).

## 5. Unblock checklist (ops)

1. Create DO Model Access Key (Control Panel → Serverless Inference → Model Access Keys).
2. On lumen-test `.env` only (never commit):
   - `MODEL_ACCESS_KEY=doo-v1-…` (and/or `GRADIENT_MODEL_ACCESS_KEY`)
   - Do **not** set `LLM_PROVIDER=openrouter`
3. From the host, list models (no secrets in logs):
   - `GET https://inference.do-ai.run/v1/models` with Bearer key
4. Pick best **returned** chat model for structured JSON Director plans.
5. Implement `LLM_PROVIDER=digitalocean` adapter: structured plans, validation, retries, timeouts, usage logging; **fail closed** if key/model missing (no heuristic silent swap).
6. Keep `FAST_PROJECT_CREATION_ENABLED=1` — Director only on Create Video.
7. Wire Director V4 inputs → validated semantic plan → existing `visual_variation` + media search.
8. Optional: set `REMOTION_ENGINE_ENABLED=true` only after non-«e» face-safe staging review.
9. 20s preview A/B on project «e»; deploy; report SHA.

## 6. Runtime stamp (discovery time)

```
fast=True llm=none remotion=False remotion_fn=False
llm_avail=False director=heuristic
DEPLOY_SHA.txt = d7bdbdd+director-mode 2026-10-12T07:11:09Z
health http://127.0.0.1:8018/api/health → ok
lumen-web / lumen-worker → active
```

strom-v2 (`188.166.244.242`) **not touched**. RunPod **not restarted**.

## 7. Git

This report + architecture/skill notes documenting the blocker. No LLM adapter claiming success. No secrets.

## 8. Follow-up credential hunt (2026-10-12, agent after 66796999)

**Result: NOT FOUND.** No partial `LLM_PROVIDER=digitalocean` implementation.

| Source | Result |
| --- | ---: |
| lumen-test `/opt/lumen-rebuild/.env` | `MODEL_ACCESS_KEY` / `GRADIENT_MODEL_ACCESS_KEY` / `DIGITALOCEAN_*` / `DO_*` / `GRADIENT_API_KEY` / `INFERENCE_API_KEY` → **ABSENT** (length check) |
| Vault `secret/admins/*` | **403** (no admins token; `root_token` file absent on this Mac; `VAULT_TOKEN` unset) |
| macOS Keychain | no items for `MODEL_ACCESS_KEY`, `GRADIENT_MODEL_ACCESS_KEY`, `DIGITALOCEAN_*`, `doctl`, `inference.do-ai.run`, DigitalOcean/Gradient labels |
| Local env | no repo `.env`; shell env unset for DO inference keys; no `doctl` |
| `.env.example` (lumen-3.0) | names only — **no** `MODEL_ACCESS_KEY` / `GRADIENT_*` documented |
| Related repos (`lumen`, `lumen2.1`) | OpenRouter / TikHub / etc. only — **no** DO Inference key names |
| GitHub Actions secrets (this repo) | **empty** (`total_count=0`) |
| Notion MCP + memory | no pages/memories holding Model Access / `inference.do-ai.run` credentials |
| Workspace rg for `doo-v1-` / key names | report/docs only — no live secret files |

Still present on host (forbidden for this track): `OPENROUTER_API_KEY`. Endpoint remains `https://inference.do-ai.run/v1` (do not invent alternatives).

### Unblock — user must provide

Paste **one** of these into a secure channel (chat/Vault), then ask agent to install on lumen-test only:

1. **Preferred:** DigitalOcean Serverless Inference **Model Access Key** (`doo-v1-…`)
   - Env name: `MODEL_ACCESS_KEY` (alias OK: `GRADIENT_MODEL_ACCESS_KEY`)
   - Where to create: DO Control Panel → **Gradient / Serverless Inference → Model Access Keys**
2. **Or:** store the same key under Vault `secret/admins/digitalocean/inference` (field `model_access_key`) and grant this agent an admins-capable Vault token.

**Do not** send OpenRouter keys. **Do not** ask for a fake/stub provider.

After key arrives, next agent steps (unchanged from §5): write key to `/opt/lumen-rebuild/.env` → `GET /v1/models` → pick returned chat model → implement fail-closed `LLM_PROVIDER=digitalocean` → keep `FAST_PROJECT_CREATION_ENABLED=1` → Remotion staging + 20s preview on project «e».
