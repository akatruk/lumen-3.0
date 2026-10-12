# Audio QA — director-v6-e-preview-20s.mp4

## Findings
- Container has AAC stereo audio (speech track from source speaker.mp4).
- Remotion composition mounts `bed.mp3` (`motion/public/director-v3/bed.mp3`, ~205s licensed bed) at ducked volume (`bedVolume` ≈ 0.26 with fades).
- Speech volume is prioritized (speaker Audio volume 1.6 vs bed ~0.26).
- No separate SFX stem in this composition.

## Verdict
- Background music: **present** via Remotion bed (not MUSIC_ASSET_REQUIRED).
- Subjective loudness of bed vs speech still needs ear-check on playback.
