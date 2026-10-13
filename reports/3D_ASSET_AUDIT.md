# 3D Asset Audit — Lumen Premium Quality Recovery V2

**Date:** 2026-10-13  
**Auditor path:** local `3d-library/` + DO volume ` /mnt/volume_nyc1_1791446889637` (78 GB free)  
**RunPod:** not resumed (no auto-restart). Local Blender **5.2.2 LTS** used for redesign.

## Inventory summary

| Kind | Count | Path |
|------|------:|------|
| `.blend` | 15 | `3d-library/blender/` |
| `.glb` | 15 | `3d-library/models/` |
| PNG α sequences | 15 × 90f | `3d-library/alpha_png/<asset>/<motion>/` |
| `.webm` | 15 | `3d-library/alpha/` — **all `yuv420p` opaque** |
| Preview stills | 15+ | `3d-library/previews/` |
| Metadata JSON | 15 | `3d-library/metadata/` |
| Registry | 1 | `3d-library/3d-asset-registry.json` |

No unrelated second library found. DO `premium3d` publish path exists on volume; local masters are authoritative for V2.

## Per-asset classification (V1 factory)

| assetId | concept | motions | glb≈ | PNG α | WebM α | geometry | materials | status |
|---------|---------|---------|------|-------|--------|----------|-----------|--------|
| l3d_generic_passport | passport | reveal, open, rotate_subtle | ~96–113 KB | yes RGBA | **no** (yuv420p) | bevelled cubes + torus seal | flat Principled | **REJECTED** |
| l3d_premium_suitcase | relocation | reveal, slide_in, floating_hold | ~113–136 KB | yes | **no** | cube body + cylinders | flat teal plastic | **REJECTED** |
| l3d_document_folder | documents | reveal, open, scale_reveal | ~18 KB | yes | **no** | two planes + sheets | flat manila | **REJECTED** |
| l3d_global_mobility_globe | global_mobility | reveal, rotate_subtle, light_reveal | larger | yes | **no** | UV sphere + tori | toy look | **REJECTED** |
| l3d_apartment_building | property | reveal, camera_push, depth_entrance | — | yes | **no** | box tower + windows | procedural pilot | **EXPERIMENTAL** (hold) |

## Subject coverage (PNG mid-frame)

| asset/motion | subject bbox coverage | note |
|--------------|----------------------:|------|
| passport/open | ~63% | Source framing OK — Remotion downscales to icon |
| suitcase/reveal | ~65% | Handle clipped at top |
| folder/open | ~50% | Recognizable as folder but plastic |

## Root causes (evidence-backed)

| Code | Cause | Evidence |
|------|-------|----------|
| **A** Primitive geometry | cube/cylinder assemblies | `blender_factory.py` builders |
| **B** Low materials | solid Base Color only, no leather/grain maps | Principled nodes without noise |
| **C** Lighting OK-ish | three-point studio present | not primary failure |
| **D** Camera | three-quarter OK; suitcase handle crop | preview stills |
| **E** Scale in Remotion | `FloatingForeground` max 340px / areaShare 0.16 | V10 frames vs 63% source |
| **F** Bounding box | source OK; compositor shrinks | V10 t=1 suitcase |
| **G** Wrong motion | `slide_in` / decorative holds | V10 plan bindings |
| **H** SVG fallback | V10.1 gate → V9 SVG (correct) | plan `family != premium_3d` |
| **I** Alpha fail | WebM `yuv420p`; Remotion `transparent` cannot invent α | ffprobe |
| **J** Director auto-bind | V10 picked any `approved` registry row | `director_v10.py` legacy |
| **K** Composition | float-over-speaker + punch-in | face collision in V10.1 trial |
| **L** Assets did render | PNG/GLB present | not a missing-file issue |

## Ratings context

| Version | Rating | 3D |
|---------|--------|----|
| V9 | 6–7/10 | SVG/PNG floats only |
| V10 | 4/10 | Forced V1 3D WebM |
| V10.1 | 5/10 | Gate off → V9 baseline |

## V2 mandate

Rebuild **only** passport, suitcase, folder as `l3d_v2_*` with hinged geometry, PBR noise materials, contact shadows, tight framing, **PNG seq + ProRes 4444** alpha. Register as `PREMIUM_READY` only after moving showcase QA.
