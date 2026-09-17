# Lumen V5 product presentation and full tutorial

Four new English/Mandarin videos replace V4 selections. Presentation: 69.9 seconds EN, 56.2 seconds ZH. Instruction: approximately 396 seconds EN / 286.4 seconds ZH, thirteen chapters. Final exact durations are in media-validation.json.

The old guide incorrectly described three-minute uploads and three platforms. V5 covers seven minutes/250 MB, five platforms, separate interface/output languages, practical Script/Brand examples, the Director Timeline, manual reapproval, media library and B-roll matching, licensed music, captions/cards, alternatives, quality review, re-rendering, and manual publication.

Visuals are deliberately illustrated workflow diagrams, labelled as such; they are not recorded live product footage. Examples are fictional, with no claim of actual processing speed or verified property identity. No customer content or credentials are shown.

Voices: MiniMax speech-2.8-hd, English_Graceful_Lady and Chinese (Mandarin)_Warm_Bestie, natural speed. Scene audio is normalized to -16 LUFS with pauses. Burned captions and optional VTT contain the authored script; timings are phrase estimates rather than word-aligned transcription.

Speech QA: Whisper transcribed all four assembled narration tracks. Normalized text agreement: EN presentation 1.000, EN tutorial .981, ZH presentation .973, ZH tutorial .949. Chinese differences include simplified/traditional characters and homophones. The full EN ASR omitted the final two sentences; separate transcription of the last scene confirmed both are present in audio. No native-speaker listening review or claim of human-indistinguishable speech is made.

Visual QA: inspected English brief and Chinese timeline stills at 1920×1080. Production frontend build and Remotion TypeScript compilation passed. A Chrome fixture verified thirteen chapters, language-specific video switching and the independent product presentation selector. Final decode and live media checks recorded after rendering/deployment.

Final visual check covered one frame from every chapter of all four completed videos. A grid-wrapper defect in reference/B-roll/export illustration scenes was corrected before publishing; replacement frames preserve original counts and the original AAC narration. Full-file decode passed for all four H.264/AAC exports.
