# Rebuild scope and source audit — 2026-09-14

## Source repositories found

1. `/Users/akatruk_macbook/Documents/github/lumen`, HEAD `967823e`.
   Original Strom/Lumen content pipeline: NestJS backend, Next.js frontend, Python `AI_editing` service.
   Examined README, frontend package manifest, editing documentation, editor decision logic and B-roll generator.
2. `/Users/akatruk_macbook/Documents/github/lumen2.1`, HEAD `5c211b5`.
   China/Douyin influencer marketplace with products, campaigns, discovery and collaboration surfaces.
   Examined README, package manifest, local agent instructions and configuration variable names.
3. Other copies exist: `Downloads/lumen-main`, `Documents/lumen-main.zip`, a Codex worktree of lumen2.1.

The user's English narration draft describes the broader Growth Operator (product intelligence, creator marketplace, authorized account connections, customer operations, leads and the growth loop). It is reference material, not authorization for outreach or account changes.

The old repositories have existing uncommitted work. Neither was edited. No SSH session successfully authenticated to the old VM; no old services were restarted or modified.

## Findings influencing the new implementation

- The original editor derives much of its decision process from transcript segments. It includes automatic repetition, silence and speech-gap cutting. The new core sends both native video and audio to its multimodal model and presents evidence per moment.
- The old B-roll generator contains topic-specific matching rules and a default Bangkok office fallback. The new core requires source-frame references and a per-video prompt; it has no generic stock fallback silently inserted into a result.
- Marketplace documentation explicitly describes demo fixtures and browser-local persistence for parts of the earlier UI. The new video studio uses server-side, account-scoped persistence and fails explicitly when a provider is unavailable.
- The new model adapter uses the existing Lumen OpenRouter credential only after explicit approval to transfer it to the new VM. The key is not bundled in client code or committed.

## Delivered first slice

Upload → source analysis → evidence-backed edit plan → selectable recommendations → automatic or requested render → technical checks → AI quality review → download. UI, recommendations and captions support English and Simplified Chinese.

This is a new video core, not a declaration that all earlier Lumen modules or production-readiness requirements are complete.

## Quality acceptance still required

1. Fund the AI provider and run 3–5 representative videos, including Mandarin and English speech, already-subtitled footage, music-only videos and product demonstrations.
2. Compare source and output with human review: product fidelity, coherent first seconds, speech continuity, subtitle accuracy and safe areas, sound, rendering artifacts.
3. Record actual model costs, latency, failure rates and number of user corrections per finished video. Editorial scores must not be presented as measured retention or guaranteed uplift.
4. Verify live generation API access and frame-conditioned output. A generated MP4 alone is not acceptance of visual quality.
5. Add shot-level regeneration / editable captions / richer timeline editing from observed failure cases rather than generic transformations.

## Next Lumen modules

- Editable product resume cards with brand truth and restricted claims, shared with the video core.
- Creator dossiers backed by analyzed videos; live Douyin discovery only via a verified authorized provider.
- Campaign briefs, submissions, approvals and measured outcomes.
- Authorized business account integrations, human escalation and lead workflows.

These modules are not dummy navigation links in the current video studio. Their code and data contracts should be added as working vertical slices.

## Infrastructure decision

Do not rent RunPod yet. The initial VM serves the application and runs FFmpeg; AI understanding and optional generated clips use APIs. Evaluate RunPod after establishing a reference-quality baseline and actual usage costs. A GPU instance does not by itself improve prompts, grounding, montage or validation.

The current storage is a bounded private directory on the new VM. Move large media into S3-compatible storage and add off-site backups before admitting valuable production media at scale. The current app has invitation-only registration and no public sample projects.
