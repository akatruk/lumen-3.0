# Change voiceover

Approved scope: a project button offering Russian, English and Mandarin with stock AI voices, short voice samples, and a separately playable/downloadable dubbed version. The source and successful master remain intact.

First release explicitly replaces the entire mixed audio track: it does not isolate speech from source music, clone a person's voice, or synchronize lips. Existing burned-in text stays unchanged. The UI discloses these limitations before submission. Target-language timed subtitles are downloadable separately.

Dubbing is bound to an immutable rendered master ID. Map transcript sentences onto that master's output timeline; when a source phrase crosses a cut or overlaps, recognize speech again from the finished master before translating. Reject invalid new timestamps rather than inventing words. Translate original speech with bounded structured output, synthesize each timed sentence, fit moderate timing differences without cutting words, and mux a new audio track with copied video. Excessively long speech fails clearly. Silence stays silent. No fake speech is added to music-only footage.

Use existing OpenRouter credentials, per-project spending ledger, durable worker and ownership checks. No automatic retry of ambiguous paid calls. Voice samples are fixed short phrases, cached by project/voice. An interrupted job becomes failed without replacing the prior successful output. Report stages and keep completed versions downloadable after a new master exists.

Verification: ownership, stale masters, empty/clipped transcripts, voice/language pairing, cost limits and deduplication; real FFmpeg timing and video preservation; UI empty/loading/error/ready paths; real Russian sample and test11 output once deployed. Keep old master unchanged.
