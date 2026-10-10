# Style lock V2 — premium cinematic editorial

Date: 2026-10-11. Source: approved Lumen library on `lumen-test` (`711` assets, `300` `source=runpod` after hypit-v5).

## Visual north star

Premium **cinematic editorial photography** for immigration, second-passport planning, relocation, and international real estate. Frames feel like a magazine feature or high-end agency campaign — not stock-catalog clutter, not illustration, not UI mockups.

## What approved RunPod / library stills already do well

- Soft natural daylight or gentle golden-hour; cool office glass as secondary mood
- Vertical 9:16 composition with clear subject hierarchy
- People: calm advisory moments, couples/families planning, arrivals — faces readable, hands mostly clean
- Interiors: empty or lightly staged condos, wide windows, muted neutrals
- Objects/details: closed blank booklets, keys, leather folders, luggage — **no readable marks**
- Foreground/layered: negative space for cards (usually right / upper-right)

## Locked look (must match)

| Axis | Lock |
| --- | --- |
| Medium | Photoreal editorial (not cartoon, not 3D render, not flat vector) |
| Light | Soft daylight / window light; mild contrast; no neon cyberpunk |
| Color | Natural skin; muted interiors; restrained accent (navy, burgundy, warm wood) |
| Lens feel | 35–50 mm equivalent; shallow DOF on details/heroes; architecture stays sharp |
| Grade | Clean, slightly cinematic; avoid heavy teal-orange or Instagram filters |
| Text | **None** — no letters, numbers, logos, watermarks, passport MRZ, signage |
| Hands/faces | Reject plastic skin, melted fingers, identity mush |
| Architecture | Straight verticals; no melting towers |

## Domains

immigration · second passport (blank covers only) · residency · family/couple relocation · remote work abroad · property viewing · condo interiors · investor calm · city arrival · packing

## Reject

Bad anatomy · plastic skin · readable text · passport/visa writing · logos · watermarks · duplicate near-identical framing vs existing `rp_*` / `hypit_*` · busy collage · gore · caricature

## Generation presets (V2)

| Preset | Use | Notes |
| --- | --- | --- |
| `cinematic_editorial` | photographs | soft daylight, photoreal, magazine |
| `detail_macro` | cinematic details | shallow DOF, tactile materials |
| `hero_object` | hero objects | centered product-hero, clean backdrop |
| `layered_foreground` | layered/FG | subject left/bottom, open right for type |

Negative (shared): `text, letters, numbers, logo, watermark, signature, passport MRZ, visa stamps, signage, label, barcode, QR, malformed hands, extra fingers, plastic skin, cartoon, anime, 3d render, collage`

## Motion (I2V) — deferred until lumen-owned weights exist

Profiles A–G (gentle push / pan / gesture / ambience) documented for later. Do not pull foreign ComfyUI LTX. Target 4s, subtle, face/architecture stable.
