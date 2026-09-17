# Soundtrack proposals and volume automation

Editors choose 1–3 private licensed music assets. The worker builds labeled audible samples from beginning/middle/end and submits that reel with the source video, saved edit and creator context for a soundtrack proposal. The model can decline all candidates. Offsets must lie within a heard sample; output-time volume points are ordered, bounded and validated. Emotional-curve explanations are bilingual and remain subjective; unsampled audio is not represented as analyzed.

Application changes only music in the saved plan, is revision-checked, and respects music locks. Existing shot approvals/locks are untouched. The music editor exposes lock/unlock and editable gain points. The actual renderer interpolates gain, retains ducking/fades and preserves source video/speech timing. The timeline shows volume automation and existing estimated accents.

Validation includes ownership, no-apply-before-review, music lock enforcement, cached existing edit preservation, real audible candidate-reel creation and a rendered rising-gain test. AI choice is fixture-controlled in these tests; real editorial suitability across different genres is not guaranteed.

Release validation: 23 targeted server tests passed, then 161 full-suite tests passed / 1 opt-in generation test skipped. Deployed with backup `backups/music-style-20260916-143016`.
