# Media library V4 audit

Counted from the live lumen-test library at `/opt/lumen-rebuild/media/library/out` → `/mnt/volume_nyc1_1791446889637/app-library` on 10 October 2026.

Starting inventory (after RunPod SDXL V1, before V4 batches). Final after V4: **636** rows, **225** RunPod stills — see `MEDIA_LIBRARY_V4_REPORT.md`.

## Inventory (server, start of V4 expansion)

| | Count |
| --- | ---: |
| Approved manifest rows | 486 |
| Images | 464 |
| Video files | 17 |
| Remotion motion presets (`.tsx`) | 5 |
| SVG | 341 |
| PNG | 123 |
| MP4 | 12 |
| WebM | 5 |
| Photography (`visualFamily`) | 70 |
| Editorial objects | 50 |
| Line drawings | 168 |
| Backgrounds (family) | 26 |
| Rows with no visual family | 150 |
| RunPod SDXL stills (`source=runpod`) | 75 |
| Rows with `conceptId` | 75 (the RunPod set) |
| Files missing on disk | 5 (Remotion presets point at `scenes.tsx`) |

RunPod breakdown at start: `rp_photo_` 30, `rp_detail_` 20, `rp_object_` 15, `rp_fg_` 10.

Volume free: ~80 GB on `/mnt/volume_nyc1_1791446889637`. Root free: ~13 GB.

## Provider status

- OpenRouter image/video: account already past credit balance (HTTP 402). Do not use.
- RunPod `lumen-web-gpu` (`wk5d9kjveiqn6l`): existing pod, resume-only. SDXL at `/workspace/lumen-media-v1`.
- ComfyUI / hgpoint checkpoints on the same volume: do not start or load.
- `lumen-picture` (`h2v7b8z2szwlv6`): leave EXITED / untouched.
- I2V: no lumen-owned video checkpoint under `/workspace/lumen-media-v1`. LTX on the volume belongs to another project. Motion deferred unless a lumen-native path appears after stills.

## Why the same pictures kept winning

Last three comparable edits (visual-randomization previews, seeds 839204 / 120011 / 103) each used two library picks:

| | Document beat | Proof beat |
| --- | --- | --- |
| A `gen_839204` | `document_approval_001` | `i2v_consult_001` |
| B `gen_120011` | `document_approval_001` | `people_consult_001` |
| C `gen_103` | `re_agent_docs` | `people_phone_001` |

Five unique assets across six slots. Causes: fixed English queries, quality-weight sticky top hits, no recent-id memory (fixed in code), and weak multilingual alias coverage for some phrases.

## Coverage gaps (addressed by V4 batches)

RunPod V1 heavily covered family planning, packing, new apartment, arrival, key handover. V4 batches target:

- `immigration.citizenship_planning`, `immigration.second_passport`
- `immigration.residency_application`, `immigration.approval`
- `immigration.country_comparison`
- `relocation.remote_work`, `relocation.couple`, `relocation.family_home`
- `travel.city_arrival`
- `real_estate.investor_meeting`
- more `property_investment` / `property_viewing` / `business` relocation

Batch plan: 2 × (30 photos + 20 details + 15 objects + 10 layered) = 150 stills. Estimated GPU cost well under $2; hard cap $20.

## Jobs / safety

At audit time: `jobs` table empty (`queued`/`running`/`processing` = 0). `lumen-web` and `lumen-worker` active. Do not restart worker while a job runs. Do not overwrite published player `d3fbb40fe25a4bb2adf74a32635df28b`. Project «е» is Director V3 Remotion, not Hypit.
