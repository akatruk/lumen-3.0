# Render delivery investigation and fixes

## Production evidence (final2)

Project `9b3f7ca5bfe549bcadac78d63ba16757` has saved manual revision 8. The delivered picture comes from Master `3d9d91ac54284c80ba4a1186e3a59c30`, revision 2: one 0–162.1-second scene, static 1x framing, no inserts or added captions. The last three studio_render payloads contain that same unchanged picture configuration. The current saved scene has zoom_end=1.2, approved=false, no movement duration, normalization and Easy Lemon music. No later picture-render job exists.

The selected delivery is audio mix `423b1104966945e298e99f423ba7828d`, using the same Master picture and Russian voice `3242a5a016584394b79f3ad3c021358f`. Four full creative plans and two individual proposals remain ready at older revisions, never accepted. One music proposal is also ready (music was applied directly instead). Ready proposals are not executable saved edits.

## Changes

- Compare intended picture with the rendered Director Timeline, ignoring review flags, IDs and independent audio updates. Show pending edits and the audio/picture distinction beside the actual player, with direct preflight entry.
- Preset zoom now completes in four seconds (or the shorter scene duration), then holds. Its duration is editable and shared by browser preview, executable timeline and FFmpeg. Existing saved edits retain their timing until explicitly changed. Long camera moves get a warning in the inspector and summary.
- API rejects partial scene approval instead of silently omitting unapproved footage. Preflight summary includes all intended scenes and reports outstanding approval.
- Summary offers navigation to unapplied AI proposals. No implicit proposal acceptance or paid generation.

## Verification

- 33 Linux tests passed, including real FFmpeg manual/auto reorder/trim, captions, graphics, animated framing, B-roll, audio and final music tests. The new pixel test confirms short-duration movement reaches its target and holds while the video retains its full duration.
- 53 Linux tests passed in the second focused group, including AI-plan acceptance through real rendering, creative effects and timeline audio. A prior test expecting partial approval was updated to require all scenes, matching the safety fix.
- Final local non-render regression group: 42 passed, one ASS-dependent test excluded (covered on Linux). It includes effective movement signature comparisons.
- All 28 browser editor scenarios passed, plus five workspace scenarios, new delivery-status regression, preflight regression and four locale tests. Frontend production build passes.
- Read-only authenticated production browser: picture_pending=true, separate_audio=true, one unapproved scene, correct 162.1-second summary and slow-scene warning, no JavaScript errors, zero writes. Screenshots inspected. Final2 settings, approval, media selection and final file were not modified.
- Published frontend index SHA-256 `198c89f064c48c3dd4effbeb4f2da6d84a4e77384b8c25bbc19adedb71c6d559`; production services healthy.

## Limits

This does not automatically accept old AI proposals, remove subtitles burned into source pixels, or transfer separately generated dubbing to a newly edited Master. The preflight continues to state that a new picture render uses source audio plus saved music; current delivered Russian dubbing remains untouched by this investigation. No paid AI calls were made. A missing legacy Director Timeline is treated as unknown, not assumed current.
