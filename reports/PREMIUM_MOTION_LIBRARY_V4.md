# Premium Motion Library V4

Date: 2026-10-12. Branch: `feat/media-library-cleanup-v1`. Host: lumen-fix (`142.93.248.163`).

## Verdict

**Calibration PASS (18/18 approved).** Mass production toward ~90 **stopped** after calibration: Remotion deterministic path is proven; generative I2V is blocked (no Wan/LTX/SVD/SDXL weights on GPU volume; RunPod balance ≈ **$9.70**). Human contact-sheet review recommended before scaling.

## Audit

| Item | Value |
| --- | --- |
| Volume | `/mnt/volume_nyc1_1791446889637/` — 100 GB, **79 GB free** |
| Library root | `…/app-library` (= `/opt/lumen-rebuild/media/library/out`) |
| Manifest before | **811** assets |
| Manifest after | **829** (+18 premium motion) |
| Motion on disk (pre) | 17 files under `motion/{people,real-estate,conceptual,documents,global,backgrounds}` |
| GPU pod | `nxi1rfwb94eufx` / `lumen-hypit-4090` |
| GPU at audit | **RUNNING**, idle (0% util, 1 MiB) → **stopped** after audit (no busy jobs) |
| Balance | ≈ **$9.70**; hourly ≈ **$0.89** |
| `/workspace` | `lumen-llm` (Ollama) + `lumen-runtime.tar` only — **no** `*.safetensors`, no Wan/LTX/SVD |
| `lumen-web-gpu` | EXITED (untouched) |
| strom-v2 | not touched |

## Model chosen

**Remotion deterministic** (`motion/src/clips/premium/*`) → PNG sequence → **ffmpeg `libvpx-vp9` `yuva420p`** (true alpha). H.264 never claimed as alpha. BG plates are opaque navy (alpha not required).

I2V deferred: no video checkpoint on volume; budget too low to download models.

## Calibration batch (18)

| Role | Count | IDs |
| --- | ---: | --- |
| Hero | 5 | `pm_hero_{growth,risk,deadline,steps,compare}_001` |
| Concept | 4 | `pm_concept_{shield,folder,path,check}_001` |
| FG | 3 | `pm_fg_{wipe,ring,mask}_001` |
| BG | 3 | `pm_bg_{navy,grid,dust}_001` |
| Scene | 3 | `pm_scene_{approval,mobility,choice}_001` |

- **Approved:** 18  
- **Rejected:** 0  
- Contact sheets: `app-library/contact-sheets/premium-motion/` (`calibration-18.jpg`, role sheets)  
- Recipes: `media/library/recipes/premium-motion-v4-calibration.json`  
- Render/index: `media/library/render_premium_motion_v4.py`, `index_premium_motion_v4.py`

## Transfer

Path: `/mnt/volume_nyc1_1791446889637/app-library/motion/premium/`  
Method: rsync → SHA-256 verify vs calibration report → atomic `.partial` rename.  
Checksums: `app-library/reports/premium-motion-v4-calibration-report.json`.

## Search / Director

- `search.py` indexes `tags_ru` / `tags_zh`
- `concepts.py` phrases for growth/risk/deadline/steps/choice/shield/mobility (RU/ZH → EN tags)
- Smoke: `рост прибыли` / `利润增长` / `choice fork` → `pm_*` first
- Director dry-run (3×20s **retrieval** plans): 18/18 beats picked `pm_*`; files on disk  
  **Blocker:** `REMOTION_ENGINE_ENABLED=false` — no full Remotion MP4 variants rendered. LLM_PROVIDER=`runpod` (not DO Inference Director V4).

## Cost

| | USD |
| --- | ---: |
| Paid gen this batch | **$0** (CPU Remotion) |
| GPU idle before stop | ~minutes at $0.89/hr (stopped) |
| Remaining balance | ≈ $9.70 |

## Mass production (~90)

Stopped. Next batches only after human review of `contact-sheets/premium-motion/calibration-18.jpg` and explicit budget for any generative path (checkpoint download + GPU hours). Remotion-only expansion can continue without GPU when authorized.

## Deploy

- Code synced to `/opt/lumen-rebuild/media/library/{search,concepts,recipes,index_*}`.py  
- Manifest on volume: 829 rows  
- Health: `http://127.0.0.1:8018/api/health` → `{"status":"ok"}`  
- Deploy SHA recorded in report footer after push

## Success criteria (§§38)

| Criterion | Status |
| --- | --- |
| Audit real paths + GPU + disk + models | PASS |
| Recipes + STYLE_LOCK | PASS |
| 18 calibration + contact sheets | PASS |
| QA reject weak; transfer approved + checksums | PASS (0 reject) |
| Search + multilingual tags | PASS |
| Mass ~90 | STOPPED (calibration gate / budget / no I2V weights) |
| Director 3×20s with new assets | PARTIAL — retrieval OK; Remotion render blocked by flag |
| Deploy + health | PASS |
| Report + docs + skills | PASS (this file + arch docs) |
| Commit+push source only | pending push |
