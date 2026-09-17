# Music loop edge smoothing

Adds an optional 0–250 ms loop-edge fade to the music configuration and EN/ZH editor. It acts only if the chosen track excerpt must repeat. Fade length is bounded to one quarter of the excerpt for short tracks. Sample count and loop period stay unchanged; no video edits or beat timestamps move. Default 0 preserves existing projects. Music planning can propose 10–30 ms for a repeating excerpt, including mix-only proposals.

This is a brief fade-out/fade-in at repeated edges, not an overlapping crossfade, beat matching, stem separation or musical-phrase repair. Longer settings may produce audible dips; preview the final mix.

Validation: production frontend build passed. Synthetic PCM test verifies a large endpoint discontinuity falls below 100 sample units while interior samples and sample count remain unchanged. Disabled/non-repeating paths are byte-for-byte unchanged. Actual audio/video render tests exercise original-audio and silent-source cases with smoothing on and off, retaining duration and audible music.
