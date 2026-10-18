# Rendering and audio

## CURRENT STATE

| Layer | Owner |
| --- | --- |
| Hypit picture | Prompt → external/GPU → FFmpeg assembly (`media.render`) |
| Director V3 | Remotion CLI → H.264+AAC MP4; speech from `speaker.mp4` + bed |
| Probe / accept | `media.probe` — 1080×1920, audio present, duration check |
| Music / SFX | Studio assets + `sound_effects` on Hypit path |

## TARGET STATE

Remotion produces the picture; FFmpeg remains for probe, loudness helpers, and legacy Hypit assembly.
Speech stays dominant; music ducks where already implemented.

## Acceptance

Finished downloaded media is the truth — not job success alone (`docs/RELEASE_CHECKS.md`).
