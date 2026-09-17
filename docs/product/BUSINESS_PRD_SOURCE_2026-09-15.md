# Business PRD — extracted source

Source: LUMEN_Viral_Video_Optimization_PRD.pages; Draft 0.1. Read-only local export, 2026-09-15. Original requirements, not implementation status.

LUMEN Viral Video Optimization and Cross Platform Publishing PRD
Brief product requirements for an assisted AI video workflow
Status | Draft | Version | 0.1

Product Summary
LUMEN will help a content team identify a top-performing reference video, understand the creative decisions behind its performance, and apply those reusable methods to the team's own footage. The system will then create platform-native versions, route them through review, publish through approved connectors, and collect performance data for future recommendations.
Core principle  Learn the method behind a viral video without copying its exact script, footage, or distinctive visual packaging.
Problem and Goal
Current limitation | Product response
Trend research is separated from editing, so editors must manually interpret why a reference works. | Convert the reference into structured Video DNA and reusable editing guidance.
Automated edits often rely on generic B-roll, fixed music, and template transitions. | Generate a Director Timeline based on the script meaning, creator style, and reference logic.
The same master file is often posted everywhere. | Produce platform-native cuts, metadata, covers, and publishing instructions from one Master Content Package.


Primary User Story
As a content producer, I want to select a high-performing reference video and upload our own footage so LUMEN can recommend and apply the strongest hook, pacing, visual, subtitle, and music techniques. I can review the result, generate versions for each target platform, and publish without rebuilding the edit manually.
End to End Workflow
Discover and select. Rank or import candidate videos using recency, views, engagement, creator relevance, and topic fit. The user confirms the reference set.
Analyze the reference. Segment each reference by shot and create Video DNA covering the hook, narrative, pacing, visual mix, captions, music, emotion, and purpose of each edit.
Prepare owned content. Ingest the team's footage, script, brand rules, creator profile, target audience, and usage rights.
Generate the Director Timeline. Transfer reusable editing logic to the owned content and produce second-by-second instructions for cuts, B-roll, charts, motion, subtitles, music, and sound effects.
Create and review. Render a preview and let the editor approve, replace, regenerate, or lock each major decision before the final render.
Adapt for each platform. Create native cuts and metadata for each target platform, including duration, aspect ratio, hook, caption density, cover, title, description, hashtags, and call to action.
Publish and learn. Send approved versions through official direct-publish or draft-upload APIs where available; otherwise provide assisted publishing or export. Collect post-publish performance data.
Functional Requirements
ID | Capability | Requirement
FR1 | Reference discovery | Accept video URLs or uploads; optionally surface top candidates from supported sources; capture source, date, engagement, topic, and rights status.
FR2 | Video DNA | Produce shot-level analysis with timecode, transcript, visual type, semantic role, motion, transition, subtitle emphasis, music state, emotion, information density, and why the edit supports retention.
FR3 | Creator and brand fit | Store creator tone, expertise, pacing, preferred visuals, prohibited styles, brand rules, and target audience. Use these constraints in every recommendation.
FR4 | Director Timeline | Map the owned script and footage to reusable narrative and editing patterns. Output an editable, executable timeline before rendering.
FR5 | Assisted editing | Apply cuts, reframing, B-roll, charts, maps, captions, motion, music, and sound effects. Support approve, replace, regenerate, and lock controls.
FR6 | Editorial review | Score the preview for hook, clarity, information density, visual quality, rhythm, credibility, creator fit, and platform fit. Require human review below the configured auto-publish threshold.
FR7 | Platform adaptation | Generate a Master Content Package and rebuild native variants rather than uploading the same MP4 to every platform.
FR8 | Publishing and analytics | Support API Direct Publish, API Draft Upload, Assisted Publish, or Export Only by platform. Store publish status and collect retention, watch time, completion, engagement, and conversion data when available.


Platform Output
Output type | Example platforms | Required adaptation
Vertical short form | TikTok, Douyin, Instagram Reels, Facebook Reels, YouTube Shorts, Xiaohongshu, WeChat Channels | 9:16 cut, stronger opening, safe zones, platform caption style, cover and post copy
Long form | YouTube and Bilibili | Longer narrative, chapter structure, 16:9 option, thumbnail, title and description


MVP Scope
Included | Not included
One to five user-selected reference videos per project / Owned vertical videos from 30 seconds to 3 minutes / Video DNA, Director Timeline, preview, and manual controls / At least three platform variants per approved master / Official publishing connector or assisted/export fallback | Exact cloning of another creator's video or protected assets / Unofficial login automation, CAPTCHA bypass, or policy workarounds / Fully autonomous publishing without configurable approval / Universal support for every platform metric or API / Model self-training before sufficient labeled review data exists


Pilot Success Metrics
Measure | Pilot target
Editor efficiency | At least 50 percent less editing time than the current manual baseline
First preview quality | At least 70 percent of previews approved with no more than one revision
Cross-platform readiness | At least three valid platform variants generated from each approved master
Publishing reliability | At least 95 percent successful handoff for supported publish and draft-upload flows, excluding platform policy rejections
Audience performance | At least 10 percent relative improvement in either early retention or completion rate against the creator's recent baseline during the pilot
Compliance | Zero confirmed use of unlicensed reference footage or unauthorized publishing methods


Acceptance Criteria
A producer can create a project from reference videos, owned footage, a script, and creator rules.
The system explains which reference techniques it is applying and links each recommendation to a point on the owned timeline.
The producer can replace, regenerate, or lock a recommendation without losing approved work.
The final project contains a Master Content Package and at least three platform-specific outputs; publishing remains blocked until rights, editorial, and human approval checks pass.
Key Risks and Controls
Risk | Control
Copyright or style copying | Extract general directing and editing methods only. Block reuse of exact scripts, footage, music, and distinctive packaging unless rights are documented.
Weak transfer from reference to owned content | Require semantic alignment with the new script and creator profile; expose recommendations for human review.
Platform or quality failure | Use approved APIs only, keep the first release human-in-the-loop, and use editor decisions plus performance data to raise automation gradually.


Recommended Delivery Sequence
Release | Scope
Release 1 | Reference import, Video DNA, Creator DNA, and an editable Director Timeline.
Release 2 | Preview rendering, assisted edit controls, editorial scoring, and Master Content Package.
Release 3 | Platform-native variants, publishing connectors, analytics, and recommendation feedback.
