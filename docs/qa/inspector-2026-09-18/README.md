# Inspector UI verification - 2026-09-18

The shared project inspector now has scene navigation/status, visual effect presets, flat settings groups and secondary help/reorder controls. The draft player is larger, with its controls above the sticky action footer. All new text supports Russian, English and Chinese. No-motion also clears end-position panning.

## Verification

- TypeScript/Vite production build passed; existing bundle-size warning remains.
- Four localization checks passed.
- 26 editor browser scenarios passed, including the new scene navigation, preset and lock scenario. The new test initially used an exact label that included a numeric output; corrected to the accessible slider and reran successfully. The overlay test now opens its intentionally collapsed section.
- Five workspace scenarios passed (studio, other project, legacy, processing, failure).
- Render-summary browser scenario passed (error, stale revision, retry, mobile layout, no accidental render).
- Russian screenshots inspected at 1440x1000 and 390x844; no horizontal overflow or browser exceptions.
- Production test11: scene navigation, actual Inspect seek, first-scene transition disablement and desktop/mobile layout passed. Production checks blocked all non-GET API requests; no project writes occurred.
- Published HTML, JS and CSS bytes match the local production build.

## Release

JS: index-Bo0a7tfk.js. CSS: index-BvZ9mHUO.css.
Static-only deployment; services remained active.
Backup: /opt/lumen-rebuild/backups/project-workspace-20260918-112333.
AI submission and editing persistence tests use intercepted fixture APIs; production QA did not spend credits or render new videos.
