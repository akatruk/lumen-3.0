# Final music delivery and audio UX

## Root cause

The AI checkboxes selected comparison candidates only. Accepting an AI proposal updated studio_manual but did not update the delivery video. Dubbing replaced the entire original audio mix, including added music. These were separate workflows with no reliable final-output composition step.

## Change

The Audio panel leads with one soundtrack selector, track-only preview, volume and Add music to final video. Advanced timing/rhythm settings, voiceover controls, the music library and optional AI comparison are separate disclosures. The AI checkboxes explicitly do not change the video. Applying an AI proposal uses the same final-mix workflow.

A durable, free audio-only job uses the current immutable Master picture and selected voice. It replaces added music from an unmixed base rather than stacking mixes. Removal restores the selected voice. Selecting or generating a new voice reuses the current final soundtrack. The final selection is bound to the current Master and rejects stale delivery changes. Failures retain the previous final; interrupted jobs become retryable failures. Added music is saved with the manual plan for future picture renders.

Future manual renders retain a music-free base. Older Masters with baked-in added music and no clean base explicitly require a new render; the system does not pretend it can remove inseparable music. Original embedded background audio is not source-separated.

## Verification

- 40 Linux tests passed: final music, dubbing, real audio assembly, music controls, AI proposals, full rendering and caption-free render compatibility.
- 28 editor browser scenarios passed. Updated music, AI-to-final and applied-status assertions passed separately after UI refinement.
- Five workspace scenarios and render-summary flow passed after fixtures were updated for the new endpoint and intentional voiceover disclosure.
- Four locale tests, TypeScript/Vite build and diff checks passed; existing large-bundle warning remains.
- A real synthetic final download contains both 440 Hz voice and 220 Hz music, with unchanged encoded video packets.
- Real final2: selected Easy Lemon using the new UI, retained Russian male voice, verified final download bytes/ETag match the mix and reload persistence. No AI call or picture render was requested.
- Actual final2 mix has identical video packets to its voiceover base. A 15-second audio sample has voice correlation 0.997511 and added-audio RMS 0.010822, confirming the preserved voice plus new audio.
- Russian desktop/mobile screenshots have no horizontal overflow.

Backend/static deployment backup: /opt/lumen-rebuild/backups/final-music-20260918-115028.
Final static bundle: index-CbnUiuCn.js / index-BHzqZPlB.css.
Production mix: 423b1104966945e298e99f423ba7828d.

Final production browser verification: mixed video plays, time advances with audio, no media errors; applied-state control prevents duplicate mixing. HTML/JS/CSS SHA-256 values match the local build.

During the final static-only update, an SSH upload timed out and the reused deployment script briefly selected an older static archive. A new uniquely named archive was uploaded with fail-fast handling, then published and verified by hashes and browser playback. Corrected static backup: /opt/lumen-rebuild/backups/project-workspace-20260918-115454. The completed audio mix and saved final selection were unaffected.
