# Lumen Premium 3D Asset Factory V1

**Branch:** `feat/media-library-cleanup-v1`  
**Git SHA:** _(filled after commit)_  
**Preview:** `output/director-v10/director-v10-e-preview-60s.mp4`  
**Showcase:** `output/director-v10/3d-showcase.mp4`  
**Desktop:** `~/Desktop/director-v10-e-preview-60s.mp4`

## GPU / infrastructure

| Item | Status |
| --- | --- |
| RunPod pod `lumen-hypit-4090` (`dznvwn90el5au4`) | **EXITED** — not resumed (no authorization) |
| RunPod `lumen-web-gpu` | EXITED |
| Balance (at check) | ~$8.07 · spend/hr idle ~$0.008 |
| Local render host | Apple M5 · Blender **5.2.2 LTS** · EEVEE |
| nvidia-smi on RunPod | **Unavailable** while EXITED — activation required to verify RTX PRO 4500 / VRAM |
| Activation step | Authorize `python scripts/runpod_pod_control.py resume` on lumen-test, then `nvidia-smi` |

Pilot renders completed **locally**. Scale production should move to RunPod after resume authorization.

## Factory output (quality gate)

| Metric | Value |
| --- | --- |
| Objects | **5** |
| Motion variants | **15** (3 each) |
| Alpha masters | VP9 WebM (decoded RGBA alpha verified) |
| GLB | 15 valid |
| BLEND sources | 15 preserved |
| Alpha QA pass | **15 / 15** |
| Render time (full batch) | ~25 min local EEVEE |

### Objects

1. `l3d_generic_passport` — reveal / open / rotate_subtle  
2. `l3d_premium_suitcase` — reveal / slide_in / floating_hold  
3. `l3d_global_mobility_globe` — reveal / rotate_subtle / light_reveal  
4. `l3d_document_folder` — reveal / open / scale_reveal  
5. `l3d_apartment_building` — reveal / camera_push / depth_entrance  

## Storage

- Local: `3d-library/` + published `media/library/out/motion/premium3d/`
- DO volume: `/mnt/volume_nyc1_1791446889637/app-library/motion/premium3d/` (+ models/thumbnails/3d-library)
- Registry: `3d-library/3d-asset-registry.json` · `media/library/out/premium-3d-v1-rows.json`

## Integration

- Director V10: `backend/director_v10.py` — binds concepts → 3D alpha floats under V9 clean composition
- Remotion: `FloatingForeground` + `OffthreadVideo transparent`
- Search: RU/ZH tokenization fixed; `premium_3d` ranking boost
- Multilingual top hits: passport / второй паспорт / 第二本护照 / suitcase / чемодан → `l3d_*`

## V10 video

- Duration **60.05s** · same source «e» · ru-RU  
- Premium 3D on hook / problem / payoff (suitcase + passport)  
- Composition policy remains `v9_clean` (no black boxes)

## Remaining limitations

- Procedural EEVEE materials are **pilot-grade**, not scanned photogrammetry — improve textures before scaling to 30 objects
- RunPod GPU not verified live (pod EXITED)
- DO SSH intermittently timed out during final code deploy (assets ALPHA/GLB/manifest reached volume earlier: 15 webm). Re-run rsync + `systemctl restart lumen-web lumen-worker` when host is reachable.
- Procedural geometry is pilot-grade (clear silhouettes; still stylized vs photoreal). Improve materials before scaling to 30 objects.
- Do not mass-produce until style sign-off on contact sheet `3d-library/previews/3d-contact-sheet.png`
