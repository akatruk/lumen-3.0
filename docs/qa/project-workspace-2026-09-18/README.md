# Shared project workspace — 18 September 2026

Implemented the approved workspace prototype as real React UI for every project route. Studio projects have Edit, Subtitles, Audio, Effects, Materials and Review. Legacy analysis projects share the player/version/download shell and retain supported analysis, rendering and deletion controls.

The common player displays original footage, the current rendered output or any available ready voiceover. Downloads follow the selected finished version. Version rows include creation time and a short identifier to distinguish identical voices. Manual editing keeps its existing APIs, validation, revision checks and session draft; preview/scenes/actions are placed in the shared workspace with React portals. Only one main video is visible. Scene changes clear approval. Rendering requires saved approved edits and an explicit review dialog that discloses optional AI review costs. Existing quality reports, AI plan controls and platform versions remain under Review.

The subtitle panel distinguishes baked-in source text, new caption settings and reading-only transcript. Baked-in text is never presented as removable by a subtitle switch. Audio includes the existing voice generation and reusable music library. No mock AI output, demo render or test11-specific identifiers are in production code.

## Validation

- TypeScript and Vite production build passed. Existing advisory: JavaScript bundle exceeds Vite's 500 kB warning threshold.
- Four locale tests passed.
- Browser tests passed on actual test11 API snapshots with all writes intercepted: five versions, selected downloads, effects/caption draft persistence, scene approval, save payload and render revision, one visible main video, all six mobile tasks without horizontal overflow.
- Committed synthetic browser suite passed: Studio, different project ID, legacy analysis, processing before preview readiness, failed task with retained output. Includes compare/restore, correct download target, review gate, voice language persistence, Escape modal close, mobile layout and absence of JavaScript errors.
- Screenshots inspected at desktop 1512×1050 and mobile 390×844. Desktop artifact captures the workspace only. Preview media in snapshot tests are reduced local proxies; production keeps original protected media endpoints.

Run the repeatable suite against Vite:

```sh
npm run dev --prefix frontend -- --port 5192
PLAYWRIGHT_MODULE=/absolute/path/to/playwright node frontend/tests/workspace.browser.cjs
npm run test:locale --prefix frontend
npm run build --prefix frontend
```

Optional WORKSPACE_MEDIA=/absolute/path/to/video.mp4 supplies playable media to the intercepted fixture. Without it, media requests return 204; these tests cover UI/API wiring rather than codec playback. WORKSPACE_URL overrides the Vite address.

Deployment: static frontend only; no database migration, no project edits, no AI generation and no service restart required. The previous six feature commits already deployed on this host are included in the main-branch merge, preserving voiceovers, locale selection, music and Douyin previews.
