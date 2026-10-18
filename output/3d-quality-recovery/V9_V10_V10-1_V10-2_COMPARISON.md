# V9 → V10 → V10.1 → V10.2

| Version | Delivery | 3D | Verdict |
|---------|----------|----|---------|
| V9 | `director-v9-e-preview-60s.mp4` | SVG floats | Preferred (6–7/10) |
| V10 | `director-v10-e-preview-60s.mp4` | V1 forced | Regressed (4/10) |
| V10.1 | `director-v10-1-e-preview-60s.mp4` | gated off | Recovered toward V9 (5/10) |
| V10.2 | `output/3d-quality-recovery/director-v10-2-e-preview-60s.mp4` | V2 built, **boundCount=0** | V9 baseline preserved |

## What V2 fixed

- True alpha (PNG + ProRes 4444)
- Tight subject framing (~60–77% coverage)
- Hinged passport / rolling suitcase / opening folder motions
- Quality gate requiring `production_ready`
- Face-safe Remotion size clamp

## What V2 did **not** yet achieve

- Commercial leather/paper materials
- Non-toy suitcase proportions/details
- Folder hinge readability matching editorial stills
- Clear win vs V9 in moving A/B

## A/B evidence

- `scene-ab-comparison/passport_v9_vs_v102.mp4`
- `scene-ab-comparison/folder_v9_vs_v102.mp4`
- `scene-ab-comparison/suitcase_v9_vs_v102.mp4`
- Trial (not production): `scene-ab-comparison/v102-trial-3d.mp4`

**Decision:** keep V9 treatment in production until geometry/materials pass human PREMIUM_READY review.
