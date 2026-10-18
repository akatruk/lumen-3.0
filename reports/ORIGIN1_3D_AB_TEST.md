# ORIGIN1 / original1 — Director V9 vs experimental 3D A/B

**Date:** 2026-10-13  
**Project ID:** `director_v5_original1`  
**Aliases:** origin1, original1 (Desktop `original1.mp4`; data path `data/director_v5_original1/`)  
**NOT used:** project e / `9a9c116d…`

## Source

| Field | Value |
| --- | --- |
| Source file | `data/director_v5_original1/source` (= Desktop `original1.mp4`, 13 339 701 bytes) |
| Source duration | **63.47s** (H.264 + AAC) |
| Language | **en-US** |
| Transcript (project) | `data/director_v5_original1/source.transcript.json` — 6 segments, 0–20s coverage |
| Fuller speech text | `~/Desktop/original1.mp4.transcript.json` (12 phrases; timestamps compressed — semantic only) |
| Env | `FAST_PROJECT_CREATION=1` `LLM_PROVIDER=none` — no RunPod, no paid providers |
| Seed | **42** · duration **60s** |

## Actual speech (do not assume immigration)

Spoken themes from transcript (project + Desktop fuller text):

1. Foreign investment companies “only change the language of China” — misconception  
2. Chinese investment company first step is different  
3. Core = **capital investment**  
4. Government leadership → no immediate pay / company credit framing  
5. Shareholder responsibility + capital judgment  
6. **Thailand:** first thing is **shareholder structure**, not money  
7. Ordinary Thai companies ≥3 shareholders; foreign capital ratio usually **&lt;49%**  
8. Control locked at investment; money return / initial rhythm  

**Not spoken:** passport, visa, suitcase, relocation luggage, immigration paperwork.

## Semantic beats → 3D opportunity

| Beat / concept | l3d_v2 candidate | Match? |
| --- | --- | --- |
| Investment / China / capital | — | no asset |
| Shareholder structure / Thailand / 49% | — | no asset |
| Passport / residency | `l3d_v2_passport` | **no** |
| Suitcase / relocation | `l3d_v2_suitcase` | **no** |
| Documents / folder | `l3d_v2_folder` | **no** (corporate “structure” ≠ folder) |

**3D opportunities for this project:** none with current V2 library. Future finance assets (equity split, capital arrow, Thailand map) would be required — out of scope here.

## Pipeline

1. **Version A:** `PREMIUM_3D_MODE=v9` → `output/cross-project-origin1/baseline-v9.mp4`  
2. **Version B:** `PREMIUM_3D_MODE=experimental` (test-only speech match; does **not** mutate `production_ready`) → `experimental-3d.mp4`  
3. Script: `scripts/ordinary_director_render.py --project-id director_v5_original1 --source data/director_v5_original1/source --language en-US --duration 60 --seed 42`

## Results

| | A baseline V9 | B experimental 3D |
| --- | --- | --- |
| MP4 | `output/cross-project-origin1/baseline-v9.mp4` | `output/cross-project-origin1/experimental-3d.mp4` |
| Duration | 60.05s | 60.05s |
| 3D bindings | 0 (policy off) | **0 — `NO_RELEVANT_3D_ASSET`** |
| Contact sheet | `baseline-contact-sheet.jpg` | `experimental-contact-sheet.jpg` |

Artifacts: `scene-plan.json`, `3d-usage-report.json`, `asset-selection-report.json`, `quality-comparison.md`, `speech-semantics.json`.

## A/B findings

- Experimental path ran; speech matcher returned empty; B is V9-equivalent for 3D.  
- Face-safe; no black boxes; no forced 3D.  
- Contact sheets: no passport/suitcase/folder PNG floats on either cut.  
- Minor B-roll plate drift between sequential renders (visual-history recent pool) — unrelated to 3D.  
- Pre-existing Director defaults still inject immigration criteria cards / relocation queries onto investment speech (separate V9 semantics debt).

## Did experimental 3D improve quality vs V9?

**No.** Honest verdict: **no improvement** because **no relevant 3D asset was bound**. Fail-closed was correct. Shipping forced immigration 3D on this speech would have **hurt** relevance.

Production gate unchanged: `media/library/3d_factory/quality_gate_v2.json` → `production_ready: []`.

## Code added (test-only)

- `PREMIUM_3D_MODE=experimental` in `backend/director_v10.py` → `apply_premium_3d_experimental` in `backend/director_v10_2.py`  
- Speech-pattern match only (ignores immigration keyword defaults)  
- Tests: `backend/tests/test_director_v10_experimental.py`
