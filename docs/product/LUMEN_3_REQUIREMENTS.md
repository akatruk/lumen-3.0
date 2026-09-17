# LUMEN 3.0 — product requirements

User-supplied scope, recorded 2026-09-17. This document defines intended behavior; it is not a claim that every requirement has passed acceptance testing.

## Central output

An editable **Director Timeline** containing second-by-second instructions for all editing decisions, with source ranges and output timing. The rendered video must reflect the approved timeline.

## Required editing capabilities

1. **Shot selection:** Presenter footage, close-ups, medium shots, B-roll, archival footage, news clips and documents.
2. **Cutting and pacing:** Trim footage, adjust shot duration and control the editing rhythm.
3. **Camera motion:** Zoom in/out, pan, push, pull and reframe footage.
4. **Transitions:** Standard cuts, zoom transitions, masks and other context-appropriate transitions.
5. **Visual inserts:** Maps, charts, timelines, rankings, number cards and data animations.
6. **B-roll selection:** Retrieve or generate visuals based on the meaning and narrative purpose of each script segment.
7. **Subtitle editing:** Regular captions, highlighted keywords, large numbers, dates, countries, comparisons and conclusions.
8. **Music editing:** Select background music based on the emotional curve; align edits with beats, rises, drops and pauses.
9. **Sound effects:** Add sound effects at emphasis points and transitions.
10. **Narrative restructuring:** Improve the hook, reorder sections and apply reusable storytelling structures.
11. **Creator styling:** Adjust pacing, presenter screen time, visual mix and editing style according to each creator's profile.
12. **Platform adaptation:** Change duration, aspect ratio, hook, captions, cover and CTA for TikTok, Reels, Shorts, Douyin, Xiaohongshu and other platforms.
13. **AI quality revision:** Score completed video and automatically recommend or generate another edit when quality is too low.
14. **Manual review:** Approve, Replace, Regenerate or Lock individual decisions before final rendering.

## Acceptance approach

The following verification criteria operationalize the scope above:

- Trace an AI recommendation from source/reference evidence to its timeline instruction and visible/audible rendered effect.
- Verify source and output timestamps after trimming, reordering and platform adaptation.
- Verify that approval governs final rendering and locked decisions survive applicable revisions.
- Exercise the controls in both English and Simplified Chinese, including mobile input.
- Validate the complete upload → reference DNA → source analysis → plan → review → render → quality review → export flow.
- Preserve the source and last successful output when a provider or rendering step fails.
- Assess editorial quality on representative real footage; synthetic tests alone establish technical behavior, not creative quality.

## Current coverage and evidence

See [implementation status and limitations](remaining-implementation.md) and [QA reports](../qa/).

Known areas needing deeper validation or richer implementation include transitions between moving shots, scene-level soundtrack selection beyond sampled audio, archive/news discovery beyond Commons, platform-specific visual restructuring beyond fitting a reviewed master, and editorial quality on real footage. These are not silently treated as fully complete because a corresponding UI control exists.
