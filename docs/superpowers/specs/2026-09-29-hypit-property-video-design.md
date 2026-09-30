# Property video on the Hypit capture boundary

Date: 2026-09-29. Working label only: this is not a product rename.

## Locked product rule

Lumen-fix only assembles the prompt for Hypit
(`https://github.com/hypit-ai/hypit`). Lumen stays the app, the project, the
sliders, and the review surface. Hypit generates the video from that prompt.

Sliders and every control in «Эффекты» change that prompt. Hypit renders it.
Card pixel size is not a Lumen effect. Duration share (10% of a 1-minute video
= 6 seconds of animation) and intensity (5–100, step 5) are prompt inputs, not
CSS. Do not invent a parallel composition engine: no plate CSS, zoom, font
size, seek-script geometry, timeline cuts inside `index.html`, or a second
renderer.

Lumen stays the application, the project record, and the delivery history. Hypit
(`https://github.com/hypit-ai/hypit`, inspected commit `b00532e`, package version
0.2.16) stays an engine behind that boundary. No user-owned Hypit fork remote is
configured on this repository. This design does not create one.

## What Lumen already does

A studio project already separates reference media (`role: reference_only`) from
owned footage, stores a creator profile (`topic` may be `real_estate`), and
requires human approval before `studio_render`. Platform export previews exist
for Douyin, Instagram Reels, YouTube Shorts, TikTok and Xiaohongshu. Publishing
and analytics are not implemented. Automatic approval is already off.

Style-match pictures already call Hypit without vendoring it. `backend/hypit_render.mjs`
imports `packages/provider-hyperframes-local` from `HYPIT_ROOT` (default
`/opt/hypit`) and `captureStagedVisual` writes `visual.mp4`. Lumen then muxes
owned audio. The browser never receives a shell or a provider credential.
`hypit_unavailable` fails the job and does not clear `projects.result`.

That path is an ad-hoc `job.json` (`directory`, `width`, `height`, `fpsNum`,
`fpsDen`, `frameCount`). It is not yet a versioned handoff, and it does not know
which property claims are allowed on screen.

## What Hypit actually provides

Evidence is the upstream tree, not the marketing README.

- Distribution CLI (`bin/hypit.mjs` → `packages/video-cli`): `studio`, `capture`,
  `media`, `transcribe`, `measure`, `snapshot`, `vocabulary`, plus the runtime
  `run`/`compile` flow. The CLI prints Hypit's name and run reports. Lumen must
  not surface that CLI.
- Authoring format is SVML plus a composition schema (`packages/composition`):
  timed visual nodes, media blob refs, font artifacts, and a manifest. A full
  Hypit project has its own workspace, runtime profile and resource store.
- Local picture rendering is `provider-hyperframes-local`: Chrome captures a
  HyperFrames HTML document and ffmpeg encodes it. Generation providers
  (Seedance, GPT Image, ElevenLabs, and others) are optional plugins with their
  own credentials and prices. This slice calls none of them.
- Hypit does not know Lumen projects, Google SSO, budgets, or immutable
  deliveries. Its studio UI is a second application. Staff must not be sent there.

License: Apache 2.0 plus conditions. Use for this organization's own work,
including a rendering backend it operates for itself, is permitted. Multi-tenant
hosting for other companies and commercial redistribution are not. The logo
clause does not apply while the CLI and its run reports are not shown. Output
belongs to the operator. Do not vendor the Hypit tree into this repo.

## Boundary chosen

Isolated worker process, the smallest option that matches the code already in
production:

| Option | Why it loses |
|---|---|
| In-process Python package | Hypit is a pnpm/TypeScript distribution. Importing it into uvicorn would mix Chrome, ffmpeg and model credentials into the API process. |
| Separate Hypit service | Adds a second deployable, a second project store, and a file shuttle. Nothing in the current queue needs that. |
| Hypit CLI as the product UI | Two applications. Also surfaces the CLI name and reports, which the logo clause then restricts. |

Lumen keeps auth, the studio project row, asset ownership, the job queue, spend,
and `projects.result`. The engine receives one versioned package and returns
files under that project's render directory.

`lumen.hypit.package.v1` records the schema, package id, project id, plan
revision, canvas, frame count, input paths, byte sizes, media types and
sha256, the notices above, and a cost block. Local capture meters no model
spend. Paths must resolve inside the project directory. Reference files
(`references/` and `reference_source`) are rejected. The JSON is scanned so
secrets are not copied into the package.

The capture command stays `node` + Hypit's `tsx` CLI + `backend/hypit_render.mjs`.
Failure deletes the incomplete render directory and leaves the selected
`result` row and its MP4 in place.

## First vertical slice

Property marketing on the existing studio project. No second project table.

Staff save a brief: audience, video language (`en` / `zh` / `ru`), optional
location that is shown only when they ask, facts with a source note and
`supplied` or `verified`, the fact keys to feature, a hook, a brand line, a
call to action and contact, and destinations chosen from the platforms Lumen
already names. Owned music may be attached by asset id. Illustrative assets are
listed and held out of the picture.

The plan is deterministic. It does not call a model. On-screen highlight text
must contain the supplied fact value. A number that is not in the supplied
facts, the call to action, or a location the user chose to show is rejected
(`unverified_claim`). Missing price, area, tenure, fees, developer, amenities
and similar claims are simply omitted. City and country are not required.

Approval is explicit and tied to the plan revision. Render writes a new
directory `renders/{id}/result.mp4` and a pending id. The selected delivery
changes only when staff approve that file. Preview of a pending file uses the
existing `?render=` media URL. The main result URL and that approval select the
same id.

Platform variant renders are not started here. Destinations are stored intent.
The existing variant pipeline remains the place that can render a reviewed
master, and publishing stays unimplemented.

## Out of this slice

- Installing or pinning Hypit on the production host (`HYPIT_ROOT`).
- Replacing the style-match picture path.
- AI-written property copy, translated facts, or generated views of the unit.
- A Hypit fork URL. None is configured.
- Deployment, a release, or a product rename.
