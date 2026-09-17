# External footage and timeline review

## Deployed behavior

Wikimedia Commons video search is available inside the manual editor, in English and Chinese UI. The first provider integration admits source metadata stating CC BY, CC0 or public-domain terms; explicit restrictions and pending license-review categories are excluded. The source page, creator and stated license are shown before import. Metadata is refreshed before downloading; a changed license/artist is rejected for renewed review.

Imports run as isolated durable jobs and retain the current edit on failure. Downloads accept only HTTPS upload.wikimedia.org Commons paths, disallow redirects, enforce a 50 MB transfer ceiling and bounded duration, and transcode validated media into private MP4 assets. Imports are revision-independent library operations; they do not approve or insert footage. Imported candidates are available to the existing semantic matching and manual placement controls. Repeated imports of an already stored Commons page reuse that private asset.

Used asset credits are attached to master results and included in new platform ZIPs as credits.json, with a separate download link. Credits cover actually rendered approved clips and the music bed. Source declarations are not an authenticity guarantee or a license for unrelated third-party material.

The Director Timeline now defaults to the entire proposed edit. Pending clips remain clickable and are visually marked with an amber dashed border. A separate Approved output view shows only clips that will render. Music output timing is shown only for the approved timeline while approvals remain incomplete. Short timelines scale to available minimum width. Silent source videos no longer show a nonexistent audio lane clip. Basic cleanup controls are grouped under an expandable section below the full creative plan.

## Evidence

- Twelve isolated server tests passed, including a live Commons search/import/private preview of the public-domain DSCOVR EPIC Earth Rotation clip (4.533 seconds), full render flow, platform exports and credit downloads.
- Three local stock regression tests passed after duplicate-reuse and import-status improvements.
- Headless Chrome assertions confirmed that pending clips appear, remain selectable for editing, and disappear only in Approved output mode. Screenshot inspected.
- Frontend TypeScript/Vite production builds passed.
- Stock deployment backup: backups/stock-library-20260917-074520.

## Source documentation

- https://www.mediawiki.org/wiki/Extension:TimedMediaHandler/API
- https://commons.wikimedia.org/wiki/Help:Machine-readable_data

## Limits

This searches Commons descriptions rather than commercial stock/news catalogues. Availability and relevance depend on that collection. Import alone does not demonstrate semantic suitability: preview, existing AI matching and editorial approval remain necessary. Synthetic generated footage remains separately labeled as illustration.
