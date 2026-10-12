# V10.1 — 3D execution audit

**Baseline:** V9 (6–7/10)  
**Regressed:** V10 (4/10)  
**Delivery:** V10.1 = V9 editorial + quality gate (no production 3D)

## Root causes (V10)

| Class | Detail |
|-------|--------|
| RENDERING | `3d-library/alpha/*.webm` = `yuv420p` (opaque), not `yuva420p` |
| OBJECT_SCALE | areaShare 0.16 / max 340px → pocket icons |
| ASSET_QUALITY / MODEL_GEOMETRY | Primitive plastic boxes |
| MOTION_EXECUTION | slide_in / decorative holds |
| COMPOSITION | 3D on hook punch-in |
| SPATIAL_SAFETY | Hero passport trial covered mouth/chin |

## V10 bindings audited

| scene | asset | motion | loaded | alpha real? | recognizable | meaningful motion | vs V9 |
|-------|-------|--------|--------|-------------|--------------|-------------------|-------|
| hook | suitcase | slide_in | yes | no (yuv420p) | barely | no | worse |
| problem | passport | reveal | yes | no | weak | weak | worse |
| payoff | suitcase | reveal | yes | no | suitcase-ish | mild | worse |

## V10.1 trial (PNG seq + scale profiles) — REJECTED

PNG seq restored true RGBA. Scale/motion selection improved semantics. **Still worse than V9** as float-over-speaker:

1. Passport open → face collision  
2. Folder open → clutter on steps  
3. Suitcase reveal → plastic vs SVG  

Archived: `3d-comparison-clips/v101-trial-3d-REJECTED.mp4`

## Gate decision

- `production_ready`: none  
- `approved_trial_v101`: none (cleared after review)  
- Default pipeline: `PREMIUM_3D_MODE=v10.1` → bindCount 0  
- Rollback baseline remains V9  

Next experiment (not this release): **cutaway_hero** plate with improved materials — never float large 3D over the face.
