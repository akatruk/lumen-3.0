# Source audio edge smoothing

Added per-clip audio_fade_ms (0–100, default off), bilingual manual control and executable Director Timeline metadata. FFmpeg fades the original mixed audio at both clip edges, bounded to a quarter of clip length, before later soundtrack/SFX mixing. It does not change video timing, overlap/remove speech or claim to reconstruct interrupted music. It can soften speech on the edges; the UI explicitly states this. Locked clip protection includes this field.

AI planning guidance permits conservative 10–30 ms smoothing only at non-speech edges. Existing plans retain the default off.

New real-render tests measure reduced edge RMS while mid-clip RMS is preserved, unchanged duration/source timeline, silent input behavior and exported setting. Local tests: 22 passed; one existing ASS-render test requires server libass. Frontend TypeScript/Vite build passed.

Server PostgreSQL/libass validation: 23 passed in 16.64 seconds (audio edges, manual review and creative plans), including actual renders. No paid AI calls.
