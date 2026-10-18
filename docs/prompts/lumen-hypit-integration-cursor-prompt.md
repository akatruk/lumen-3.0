> **Note:** Current MAIN product prompt for editing/render QA is [`cinematic-director-v3-quality-recovery.md`](./cinematic-director-v3-quality-recovery.md). Hypit assembly remains `backend/assembly_prompt.txt`.

# Cursor prompt: integrate Hypit into Lumen's real-estate video studio

Use this prompt in Cursor with the Lumen 3.0 repository open.

**Working name:** Lumen next version ("Lumen 4.0" is only a working label; do not rename the product or repository without confirmation).

**Initial deployment assumption:** a private, single-organization tool for the user's own real-estate business and team. The product creates real-estate videos; it is not tied to a city or country. Mention a location only when the user chooses to include it in a particular video.

## Copy and paste into Cursor

```text
You are working in the existing Lumen 3.0 repository. Evolve it into the next Lumen version by integrating the open-source Hypit video workflow/rendering project as an internal engine behind Lumen's existing product experience.

The first real business workflow is the user's own real-estate sales team. The team already has a person who films properties. Lumen should help that team turn footage and supplied property information into polished, persuasive real-estate videos. Video creation is not tied to a city or country; location is optional content for an individual video, not required project setup. This is an internal tool for the user's own organization unless the user explicitly changes that scope.

Product boundary
- Lumen remains the application, brand, user workflow, project data owner, review surface, and source of truth.
- Hypit provides video workflow/composition and rendering capabilities behind an integration boundary. Do not make staff operate two unrelated applications or manually shuttle a project between them.
- Use Hypit's capabilities where they fit. Do not assume Hypit can already do every Lumen feature, and do not replace working Lumen capabilities until the equivalent end-to-end behavior is demonstrated.
- Keep the integration generic enough for Lumen's existing video use cases, while making property marketing the first complete, polished workflow.
- Treat “Lumen 4.0” as a working label only. Do not perform a broad rename, rebrand, production migration, or deployment as part of this work.

Mandatory first steps
1. Read `AGENTS.md`, `README.md`, `docs/RELEASE_CHECKS.md`, `docs/product/LUMEN_3_REQUIREMENTS.md`, `docs/product/remaining-implementation.md`, `docs/product/BUSINESS_PRD_IMPACT_2026-09-15.md`, and `docs/product/PILOT_SCOPE.md`. Reconcile the implementation with current behavior and the repo's release requirements; do not treat planned features as already implemented.
2. Inspect `git status` and the existing diff before changing anything. Treat every pre-existing edit and untracked file as user-owned. Do not reset, stash, overwrite, reformat, or revert unrelated work. Make focused changes and report any conflict before touching a file with pre-existing edits.
3. Inspect the current Hypit upstream at `https://github.com/hypit-ai/hypit`: its architecture, CLI/runtime, data formats, media pipeline, dependencies, and integrations. Do not infer technical fit from the README alone.
4. Keep the implementation for the user's own single organization and preserve Hypit's notices. If the scope later changes to a hosted service for other companies or commercial redistribution, get written authorization before implementing that scope.

Implementation approach
6. Before large changes, write a concise design and phased implementation plan in `docs/superpowers/specs/` using the repository's naming convention. Compare viable integration boundaries (for example: in-process package, isolated worker/CLI, or service) using evidence from both codebases. Recommend the smallest reliable option that fits Lumen's runtime, queue, storage, and deployment. Keep the Lumen API, auth, projects, media ownership, budgets, approvals, and immutable delivery history authoritative. Avoid duplicate project models and duplicate uploads.
7. If a user-owned Hypit fork remote is already configured, use it as the fork source. If it is not available, do not invent its URL, change Lumen's Git remote, create/push a GitHub fork, or publish code. Continue the read-only compatibility assessment and establish the narrow Lumen integration boundary; clearly identify anything that truly requires the user's fork URL.
8. Implement incrementally in the existing repository. Do not stop after writing the plan: continue through the phases that can be completed safely in this checkout. Keep every phase reviewable, preserve the current working application, and summarize the concrete work as you go.

User workflow to deliver
9. A staff member creates or opens a property-video project in Lumen and enters/chooses:
   - the property facts and their source/verification status;
   - the intended buyer audience and video language;
   - the available property footage, photos, logo/brand assets, approved music, and any rights-cleared supporting media;
   - an optional reference video for creative inspiration;
   - the target publishing destinations and a factual call to action/contact method.
10. Lumen helps turn that material into an editable video plan: opening hook, scene order, property highlights, captions, on-screen facts, music/sound choices, and CTA. Include location only if explicitly requested for that video. Recommendations should be tied to the supplied footage and verified facts. Staff can inspect and change the plan before rendering.
11. Hypit performs the supported composition/rendering work through Lumen's internal integration. Lumen shows job state, errors, costs where measurable, preview, review controls, and the final approved deliverable. Re-rendering after an edit must produce a new immutable delivery and must not silently replace the last successful version. Keep the selected preview and main download aligned to the same approved delivery.
12. Produce platform or audience variants only where the existing Lumen/Hypit pipeline can actually render and verify them. Reuse approved material and facts; allow relevant language, opening, duration, captions, cover, and CTA differences. Do not promise automatic publishing or analytics unless the current implementation and supported platform permissions prove them.

Property-marketing accuracy and rights
- Never invent or infer price, currency, floor area, bedrooms, floor, tenure/ownership terms, fees, availability, developer identity, amenities, travel times, investment returns, visa/citizenship benefits, or legal claims. Use only explicit user-provided or verified facts. Do not require city/country data or hard-code a geographic market; include location in a video only when the user supplies and wants that information shown. Keep a source or confirmation marker for important claims where the existing data model supports it.
- A reference video is for analyzing general creative techniques (such as pacing, hook structure, caption rhythm, or shot progression). Do not use its footage, voice, music, logos, or identifiable people in the output unless the user has supplied the necessary rights.
- Clearly distinguish actual property footage from AI-generated illustrative material. Never present generated visuals as the actual unit, view, building, amenity, neighborhood, or nearby destination.
- Make human review/approval mandatory before final delivery. Do not auto-publish.

Phases and acceptance
Phase A — audit and design:
- Record the current Lumen workflow and identify the Hypit capabilities and gaps from source code, not marketing claims.
- Document the integration boundary, data handoff, dependency/runtime implications, security/credential handling, failure recovery, likely external model costs, and a migration/rollback strategy.
- Identify one narrow first vertical slice and its acceptance path. Keep broader product expansion separate.

Phase B — integration foundation:
- Implement an isolated Hypit adapter/engine boundary appropriate to the verified architecture.
- Pass an explicit, versioned render package from Lumen to the engine and return job status, logs/manifest, preview, and final artifacts with stable identifiers. Validate paths, file sizes, media types, and ownership; do not expose shell execution or secrets to the browser.
- Reuse Lumen's existing queue, storage, project access checks, and budget mechanisms where appropriate. Make retries safe and prevent duplicate deliveries.

Phase C — complete property-video vertical slice:
- From one isolated test property project, provide supplied property facts, owned test footage, an optional rights-cleared style reference, a target audience/language, branding, and a CTA. Location is optional and must not be required to generate the video.
- Generate an editable plan, render a polished sales-presentation video with the integrated engine, review it in Lumen, make at least one edit, render again, reload the project, and download the selected final version.
- Validate the actual media output (duration, frames, audio, captions/overlays, CTA, and delivery identity), not just UI state or a successful job response.

Phase D — reliability and useful variants:
- Verify failed jobs preserve the prior successful output; retries and repeat renders do not corrupt project state; costs and limitations are visible; approvals and locked decisions survive unrelated edits.
- Add only the platform/audience variants justified by verified render capabilities and current product scope. Keep each variant independently reviewable and tied to the same approved source project and facts.

Acceptance criteria
1. The user completes the core workflow entirely from Lumen without manually operating a separate Hypit UI or copying files between apps.
2. One property project can go from supplied materials and verified facts through an editable plan, human approval, integrated render, preview, edit, second render, reload, and matching final download.
3. The final video uses approved property footage and exact supplied facts; it has intentional pacing, readable captions, suitable visual treatment, branding, and a working CTA. No unsupported facts or unlicensed reference media appear.
4. Errors, retries, cost limits, licensing/rights metadata, and the last good output are handled visibly and safely.
5. The code follows the existing Lumen patterns, localization requirements, auth boundaries, and `AGENTS.md` / `docs/RELEASE_CHECKS.md` release verification. Add focused coverage for new behavior and perform the required affected lifecycle checks. State clearly which checks use synthetic fixtures and which validate real providers/media.
6. Do not deploy, publish a release, push branches, publish a fork, alter production data, or send messages to third parties as part of this implementation. Prepare a reviewable local result and report any release steps separately.

Working style and final report
- Give progress updates and the final report in Russian. Keep code identifiers and technical documentation consistent with the repository's existing conventions.
- Make reasonable routine engineering decisions from the repository context. Ask the user only for a genuinely missing input, a decision that changes the intended deployment scope, or an external credential/approval needed to continue.
- Do not silently weaken an acceptance criterion when a check fails. Diagnose the cause, preserve the previous working output, and report any blocker with its user impact.
- At completion, report: (1) what changed, (2) the chosen integration boundary and why, (3) attribution handling, (4) the end-to-end workflow actually verified, (5) checks not run or gaps remaining, and (6) whether the code is ready for a separate deployment review. Do not claim Hypit integration is complete if only a plan, adapter stub, or mocked UI exists.
```
