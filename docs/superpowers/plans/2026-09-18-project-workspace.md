# Shared project workspace implementation

Approved: user requested merging the reviewed interactive prototype for every project on 18 September 2026.

Goal: replace the project screen with the reviewed workspace while retaining real editing, approval, budget and ownership behavior.
Architecture: a shared React ProjectWorkspace owns the main player, version selection, scene navigation and inspector. Studio tools use existing ManualEditor/Dubbing APIs. Manual preview/scenes/actions use React portals into the workspace; no demo data enters production. Legacy analysis projects use the same shell with their supported analysis controls.

- [x] Add ProjectWorkspace and workspace translations/CSS. Ready videos and dubbed versions select the central player and have direct downloads. Handle loading, failed catalogue refresh, no result and active jobs.
- [x] Integrate DirectorProject and legacy ProjectView with shared player. Preserve original review/retry/delete/analysis controls. All projects receive the shell automatically.
- [x] Organize ManualEditor by task and selected scene; keep a single persistent edit state while changing tasks. Portal preview and scenes into the central area, review/save/render actions into the bottom bar. Preserve validation and explicit paid review selection.
- [x] Integrate voiceover panel without additional main video players. Keep generated samples, blocked reasons, costs and immutable versions.
- [x] Build/typecheck, locale tests and browser integration tests with intercepted representative API data: multiple project IDs, legacy, loading/failed states, draft retention, subtitles, real action payloads, version downloads, keyboard and mobile widths.
- [ ] Commit only implementation/design files, merge current feature ancestry to origin/main after checking remote state. Deploy tested static assets to the existing server with rollback backup. Verify public assets and authenticated project screens without paid generation.
