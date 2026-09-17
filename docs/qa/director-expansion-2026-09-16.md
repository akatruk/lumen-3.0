# Director expansion: transitions, quality, generated inserts and maps

## Implemented

- Cross dissolve, zoom, wipe-left and circle-mask incoming transitions, available in manual editor and creative planning. The outgoing frame is held over the first up-to-0.3 seconds of the incoming shot. Timing and incoming audio are preserved, rather than shortening shots for an overlap.
- Optional finished-render AI review from the manual editor (on by default in UI). Five editorial scores, a 75/100 review threshold and concrete revision suggestions. A low-scoring render queues one creative-plan draft with output-to-source timeline context and the current edit. Locked/changed plans skip automatic drafting. No automatic replacement of the finished video; no recursive render/review loop.
- Generated illustrative B-roll as a per-clip proposal. Uses source frame plus segment transcript/editor direction through the configured OpenRouter video model. Private generated asset, preview, explicit replacement, separate approval. Existing audio remains. It is not archival/news evidence or verified property footage.
- World-location map cards with Natural Earth public-domain land outlines, 1–5 supplied coordinate points, bilingual labels and staggered markers. Coordinates must be explicitly supplied. Equirectangular world overview, no political/property boundaries or automatic geocoding.

## Validation

Transition tests check decoded audio equality, duration and eventual incoming image. Quality tests check locks, preserved renders and one draft; full media flow covers both manual-only and AI-review paths using fixture reviews. Generated asset tests cover preview-before-apply and asset storage. A separate opt-in live provider test generated and previewed a four-second synthetic blue-wave clip successfully; no user footage was used. The initial live attempt lacked the key in the isolated test runtime and did not submit a provider request; the explicitly configured retry passed.

Map cards passed real FFmpeg rendering; map-preview.png was inspected visually. Targeted server runs passed 20 transition/quality/flow tests and 20 map/B-roll/graphics tests. Full regression run recorded separately after completion.

## Limits

Editorial scores are subjective judgments, not predicted engagement. Generated inserts are reviewed, not automatically judged accurate. This release does not provide archive/news retrieval, emotional music matching, automatic beat-based recutting, learned creator profiles, or autonomous multi-render comparison. Those remain separate work.

## Sources

- OpenRouter video API: https://openrouter.ai/docs/guides/overview/multimodal/video-generation
- Natural Earth data: https://github.com/nvkelso/natural-earth-vector
