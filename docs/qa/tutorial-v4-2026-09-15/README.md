# Bilingual tutorial update — 2026-09-15

Scope: replace the short overview and add a detailed, chaptered instruction in English and Mandarin Chinese. Illustrations explain the existing workflow; they are not a screen recording or a claim about processing speed.

## Deliverables
- English and Chinese 10-second overviews, 1920×1080 H.264/AAC.
- English detailed guide: 95.27 seconds; Chinese detailed guide: 75.53 seconds.
- Seven chapters: Douyin references, owned footage, creator profile, plan review, alternatives, master review, platform exports.
- Authored captions burned into the image, optional VTT tracks, posters, downloadable MP4, and readable transcript.
- Dedicated Video guide / 视频指南 navigation item. Media and text follow the site language; changing language stops the prior video.

## Voice and validation
MiniMax speech-2.8-hd through the configured OpenRouter account. English_Graceful_Lady and Chinese (Mandarin)_Warm_Bestie. Natural speed, normalized scene audio, pauses between detailed steps. Four mixed tracks were transcribed with Whisper to check completeness. Proper-name/homophone transcription differences remain (Douyin in English, Chinese 剪法/减法); no native-speaker listening review is claimed. Captions retain the authored script and use phrase-based timings.

Local browser checks: sidebar route, both language choices, quick/full selection, chapter seeking before initial playback, no horizontal overflow at desktop viewport. Final media decoding and production checks recorded below.

Sources: onboarding-video/guide-script.json and src/guide-v2; reproduction helpers generate_guide_v2.py, prepare_guide_v2.py, verify_guide_speech.py. Existing v3 assets are retained for cached clients.

## Final verification
All four videos decoded end-to-end with FFmpeg without errors. Short videos are exactly 10.000 seconds; full videos are 95.266667 and 75.533333 seconds. Remotion TypeScript check and frontend production build passed. Live bundle: index-JYdChAfw.js. All 12 MP4/JPG/VTT assets return HTTP 200 with correct content types; all four MP4s support HTTP 206 byte ranges. Dedicated route and chapter playback verified in local QA; public login also offers both lengths and languages.

Deployed frontend only with backup /opt/lumen-rebuild/backups/tutorial-v4-20260915-100416. Existing web and worker remain active. No database changes.
