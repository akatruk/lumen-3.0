# Russian interface QA — 2026-09-17

Scope: explicit English / 中文 / Русский selectors on login, desktop and mobile; persisted preference; Russian UI catalog across studio, editor, assets, music, variants, voiceover, settings, errors and written tutorial chapters.

Validation completed before deployment:
- TypeScript and Vite production build passed.
- Four locale tests passed: validated locale/content-language separation; complete main dictionary coverage; static editor/error-message coverage; Russian tutorial timing compatibility.
- Chrome verified all three languages at login, Russian authentication errors and persistence after reload.
- Chrome exercised test11 using read-only API data: Russian manual editor, voiceover actions and download labels.
- Russian create-project form retains a valid en/zh caption-language value; no project was submitted.
- Russian written guide points to existing English video files, not nonexistent ru media.
- At 390 px, document width is 390 px and closed sidebar ends at x=0; all three language options remain accessible.
- No JavaScript runtime errors in completed browser checks.

Browser fixture adjustments: exact heading assertions account for the reference-count suffix; JSON API fixtures use decoded JSON instead of replaying compression headers; browser contexts are closed before disposing API transport. These are QA-harness changes, not application changes.

Limits: existing AI-authored reports are displayed in English in Russian UI, with an explicit notice. This release translates the interface and written guide; it does not generate Russian tutorial audio or translate stored project content. Voiceover language is independent. Vite reports a non-blocking bundle-size warning (approximately 190 kB gzipped JS).

Production validation: deployed the frontend with an atomic index replacement and retained previous bundles. Live Chrome checks at 1440 px and 390 px passed for ru/en/zh switching, reload persistence, voiceover and download controls. No visible alert or JavaScript errors; no horizontal overflow. Backend services and project media were not changed. Backup: /opt/lumen-rebuild/backups/russian-ui-20260917/index.html.
