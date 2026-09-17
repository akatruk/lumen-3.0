# LUMEN 3.0 implementation status — 2026-09-17

Deployed to lumen-fix.universalgravity.org. The original VM is out of scope.

| Requirement | Executable coverage | Practical limit |
|---|---|---|
| Shot selection | Source ranges, presenter/close-up/medium/B-roll/document/archive/news roles, owned media library inserts | Commons footage search/import is available; commercial news/archive catalogues are not integrated |
| Cutting/pacing | Trim, duration, reorder, speech-safe AI plans; creator pacing preferences | Targets cannot override complete speech or missing footage |
| Camera motion | Zoom, push/pull, pan/reframe with start/end coordinates | No subject tracking |
| Transitions | Cuts, fade, cross dissolve, zoom, wipe, circle mask | Moving tail/head blend across the cut; brief visual retiming (at most 133 ms displacement), unchanged clip durations and audio |
| Visual inserts | Numbers, comparisons, animated charts, rankings, timelines, world-location maps | Exact facts and map coordinates must be supplied; no invented data |
| B-roll | Commons discovery/import with source credits, semantic matching of private library samples, generated illustrative inserts, preview and replacement | Generation is illustration, not authentic archive/news footage |
| Subtitles | EN/ZH transcript, word-aware Chinese line/card wrapping, phrase emphasis, layout/style controls and overlays | No claim of perfect transcription or automatic fact verification |
| Music | Licensed uploads, AI selection using track-wide acoustic dynamics, adaptive listening samples and approved output timeline, volume curve, fades, ducking, rhythm estimates, track alignment and reviewable multi-cut beat alignment | Cut shifts are bounded and skip speech, locks, overlays and discontinuous source cuts |
| Sound effects | Timed chime/click/whoosh accents in real render | Limited built-in palette |
| Narrative | Hook/reorder plus reusable chronology, hook/proof/takeaway, problem/solution, comparison templates | Editorial quality needs real-video review |
| Creator styling | Structured pacing, presenter share, visual mix, tone/audience/rules; measurements on proposals | Preferences, not learned personal style; shot-role metrics are not face recognition |
| Platform adaptation | Five platforms, per-platform narrative instructions and duration ceilings, manually reorderable scenes, editable segments/title/copy/CTA, 4 aspect ratios, editable hook/closing CTA overlays (style, position, timing), cover timestamp, video/captions/package export | Shorts capped at 180 seconds and square/portrait; full-frame fit/padding; no automatic publishing or comprehensive platform-policy guarantees |
| Quality revision | Five AI scores, actionable fixes and one automatic low-score revision proposal | No unattended rerender/compare loop; application and final approval remain explicit |
| Manual review | Approve, replace, regenerate and lock; revisions, private assets and prior outputs preserved | Whole-plan replacement requires unlocking affected decisions |
| Director Timeline | Ordered source-time clips, output-time layers, motion, inserts, captions, sound and music automation | Proposed and approved views with pending-clip review; form/SVG editor, not a full drag-and-drop NLE |

Verification: full isolated server regression 161 passed / 1 skipped; later legacy-music schema compatibility test passed locally. Four output ratios rendered with audio. Headless Chrome validated the new editable controls. The skipped paid live-generation test had passed separately earlier. Synthetic/fixture coverage does not prove editorial quality across all customer footage.

Further work is quality depth, broader media catalogues and richer editing automation, not more cosmetic decision labels. Do not describe every PRD item as production-perfect based only on schema/UI presence.

A subsequent real-provider integration run passed DNA → analysis → editable plan → approval → render → quality assessment, creating a 12-second/3-shot edit from synthetic 30-second footage. Its 57.2/100 result correctly remained needs-review and queued a revision draft. Settled cost for that passing run: $0.1327305. See `docs/qa/live-director-2026-09-16/`.
