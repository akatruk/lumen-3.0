# Lumen · Chinese onboarding film

A 10-second, 1920×1080, 30 fps Mandarin product walkthrough. Four 75-frame scenes explain upload/brief, analysis, recommendation selection, and preview/download. Interface illustrations are demonstrative; there is no claim that real video processing completes in ten seconds.

Voiceover: MiniMax Speech 2.8 HD via OpenRouter, Chinese (Mandarin)_Warm_Bestie. One continuous synthesis of original instructional copy, divided only at measured sentence silences to align the four scenes. No speech speed adjustment. Master normalized to -16 LUFS / -1.5 dBTP before AAC encoding. The previous macOS system voice has been replaced. Automated comparative listening preferred this variant; this is not evidence of human indistinguishability. Chinese typography uses PingFang SC on macOS. Render on macOS for the same typography, or install an appropriate Simplified Chinese font and update the fallback for other environments.

Preview: `npm install`, then `npx remotion studio --no-open`.

Render: `npx remotion render LumenChineseGuide ../frontend/public/tutorial/lumen-guide-zh.mp4 --codec=h264 --crf=18 --pixel-format=yuv420p --concurrency=2`.

For exact MP4 container duration, remux with `ffmpeg -i input.mp4 -t 10 -c:v copy -c:a aac -b:a 160k -movflags +faststart output.mp4`.

Published assets: frontend/public/tutorial/lumen-guide-zh.{mp4,jpg,vtt}. Embedded on the sign-in screen and studio home using the TutorialVideo component, on-demand native controls, no autoplay, Simplified Chinese caption track.

Validation: 300 video frames; final container 10.000 seconds; H.264 1080p plus AAC; four-scene contact sheet reviewed; production frontend build passed; public video HTTP 200 and byte-range HTTP 206 confirmed.

## Current V5 presentation and complete walkthrough

`guide-v5-script.json` is the authored EN/Mandarin source. Four `LumenV5-{guide|walkthrough}-{en|zh}` compositions in `src/guide-v5` replace V4 media on the website. `guide` is the product presentation; `walkthrough` has 13 instructional chapters. These are illustrated workflow guides, not screen recordings or measurements of processing speed.

Generate speech with `generate_guide_v5.py` using server-side `LUMEN_VOICE_CONFIG` (never commit credentials). MP3 masters are cached by script hash. Run `prepare_guide_v5.py` to normalize speech, build timing/captions and regenerate the website chapter metadata. Render using Remotion at 1920×1080, 30 fps, H.264/AAC, CRF 24. Normalized WAVs are reproducible and ignored by Git. `verify_guide_v5.py` optionally checks narration completeness with transcription.

The guides cover access, references, upload, Script & intended message, brand constraints, language and budget, DNA, timeline review, B-roll, captions/music/graphics, alternatives, final quality review and five-platform exports. They describe current limits rather than claiming autonomous publication or guaranteed video quality.
