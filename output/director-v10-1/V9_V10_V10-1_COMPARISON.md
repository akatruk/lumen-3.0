# V9 vs V10 vs V10.1

| Version | User / review | 3D policy | Delivery |
|---------|---------------|-----------|----------|
| V9 | 6–7/10 preferred | SVG/PNG floats only | `output/director-v9/director-v9-e-preview-60s.mp4` |
| V10 | 4/10 | Auto-bind opaque WebM 3D | `output/director-v10/director-v10-e-preview-60s.mp4` |
| V10.1 | restore V9 quality | Hard gate; **0** production 3D | `output/director-v10-1/director-v10-1-e-preview-60s.mp4` |

## Why V10 lost

1. **RENDERING** — WebM claimed alpha, actually `yuv420p`.
2. **OBJECT_SCALE** — 340px icons on speaker.
3. **ASSET_QUALITY** — procedural plastic geometry.
4. **COMPOSITION** — 3D on hook punch-in.
5. **MOTION** — `slide_in` / weak reveal over semantic open.

## Trial repairs (rejected)

Rendered once with passport open / folder open / suitcase reveal at hero|supporting scale + PNG seq alpha.

| Moment | Trial result vs V9 | Decision |
|--------|--------------------|----------|
| problem + passport open | Face collision; unrecognizable slabs | **REJECT** |
| steps + folder open | Plastic clutter vs CleanSteps | **REJECT** |
| payoff + suitcase reveal | Toy suitcase vs V9 pin SVG | **REJECT** |

Evidence:

- `3d-comparison-clips/v101-trial-3d-REJECTED.mp4`
- `3d-comparison-clips/passport_v9_vs_trial3d.mp4`
- `3d-comparison-clips/folder_v9_vs_trial3d.mp4`
- `3d-comparison-clips/suitcase_v9_vs_trial3d.mp4`
- `3d-comparison-clips/rejected-stills/`

## V10.1 delivery

- Editorial = V9 clean composition (SVG floats, no premium_3d family).
- Gate: `media/library/3d_factory/quality_gate_v101.json`
- `production_ready: []` — nothing auto-activates globally.
- Remotion keeps `png_seq` + scale profiles for a future **cutaway_hero** path (not float-over-face).
- Hook recovered vs V10: `3d-comparison-clips/hook_v10_vs_v101.mp4`

## Status taxonomy

| Status | Assets |
|--------|--------|
| production_ready | — |
| experimental | apartment building variants (cutaway-only later) |
| rejected | passport, folder, suitcase, globe (all motions) |
