# Platform hook and CTA presentation

Each platform variant now stores editable hook duration, closing CTA duration, clean/bold/panel typography and top/center placement. AI planning can propose these fields; manual edits produce an immutable package revision and retain the existing review/lock controls. Old packages default to three-second hook, CTA disabled.

The renderer burns the hook and CTA into the exported video, using output timestamps and aspect-aware font sizing. Hook has priority on short videos; overlapping CTA is shortened or omitted rather than stacked. Existing master captions are not removed or restyled. Both overlays can be disabled. No automatic publishing added.

Validation includes overlay timing, disabled/short-video behavior, ASS sanitization, existing package revision/lock tests and real platform exports. Technical tests do not establish platform-specific editorial quality.

Validation completed: 13 isolated server tests passed in 29.38 seconds; an additional five-platform render with panel styling, shortened hook and closing CTA passed in 28.05 seconds. Frontend TypeScript/Vite build passed. No paid AI calls were made.
