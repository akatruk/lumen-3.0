# Voiceover validation — 2026-09-17

Implemented and deployed a project-level Change voiceover panel with Russian, English and Mandarin stock voices, reusable samples, separate video/subtitle downloads, durable jobs and immutable master snapshots.

## Automated checks

- 14 focused API/worker/audio tests passed locally and on the Linux deployment host.
- 30 selected tests passed on Linux: dubbing, dubbing_audio, studio, director_revisions, music_plans, worker_defaults.
- Frontend production build passed. Chrome fixture checks covered prerequisites, voice/language submission, ready downloads, retry and mobile layout.
- Real FFmpeg tests verify preserved video packets, output duration, placement of speech/silence, and rejection of excessively long speech.
- Local music-plan media testing is limited by Homebrew FFmpeg lacking the ASS filter; the Linux suite passed.

## Live test11

Project: c4ee827c897a4960a6eb9131207f5a6e.
Master retained: ead7d660b8dd4c3eb9f6432f8a3b4081.
Russian male sample: d9e8609e076a44008c610dc923eebc79, decoded duration 7.056 seconds.
Russian video: 16993aa9bea3489294faa5663e86b7c8, ready, 26 translated phrases.

Chrome decoded and played the completed 480×848 video, duration 160.838 seconds. Owned MP4 download returned HTTP 200 with attachment disposition; unauthenticated access returned 401. No visible errors remained in the voiceover panel.

The video packet SHA-256 matches the Master exactly. New audio measured -17.5 dB mean and -1.5 dB peak. Russian VTT timestamps and text were checked. Project spending ledger increased from $0.45048525 to $0.69464365, including samples, transcription attempts, translation and conservative TTS reservations; this is not a claim of final provider-invoiced cost.

The old source transcript crossed the final cut boundary. The pipeline now recognizes the final Master when source mapping is unsafe, validates its timing and caches valid recognition per immutable Master. One completed invalid recognition may be repaired within the displayed budget; transport failures are never automatically replayed. The initial live full request failed safely on invalid recognition; a subsequent real provider response was validated and reused in the successful retry. Original Master and project status were preserved.

Temporary owner QA session was revoked and local browser credentials deleted after checks. Production authentication remained enabled.

## First-release limits

The dubbed version replaces the entire original mixed audio, including music and ambient sound. It uses stock AI voices, does not clone speakers or synchronize lips, and leaves burned-in screen text unchanged. Translated subtitles are a separate VTT file. Russian generation was tested live; English/Mandarin generation is covered by request validation but was not separately purchased during this check. Pronunciation and translation still need human review before publishing.
