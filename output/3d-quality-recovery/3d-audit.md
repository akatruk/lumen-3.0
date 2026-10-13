# 3D Quality Recovery V2 — Audit

See also: `reports/3D_ASSET_AUDIT.md`

## Ratings

| Version | Rating | Notes |
|---------|--------|-------|
| V9 | 6–7/10 | Preferred editorial baseline |
| V10 | 4/10 | Forced V1 plastic 3D + opaque WebM |
| V10.1 | 5/10 | Gate off → V9 |
| V10.2 | =V9 editorial | V2 assets built; **not** production-bound |

## Root causes (confirmed)

1. **Primitive geometry** (V1 cubes) — still the core look problem after V2 (improved but not commercial).
2. **Opaque WebM** (`yuv420p`) — fixed via PNG seq + ProRes 4444 `yuva444p12le`.
3. **Remotion icon scale** — fixed via scale profiles + face-safe clamp.
4. **Ground plane in alpha** — fixed (removed from V2b renders).
5. **Director auto-bind** — fixed via `production_ready` gate (empty).

## V2 hero delivery (NEEDS_REWORK)

| Asset | Motion | Coverage | Alpha | ProRes |
|-------|--------|----------|-------|--------|
| l3d_v2_passport | passport_open | ~77% | RGBA PNG | yuva444p12le |
| l3d_v2_suitcase | suitcase_roll | ~60% | RGBA PNG | yuva444p12le |
| l3d_v2_folder | folder_open | ~68% | RGBA PNG | yuva444p12le |

A/B vs V9: V9 still cleaner. Trial archived under `scene-ab-comparison/`. Gate stays closed.
