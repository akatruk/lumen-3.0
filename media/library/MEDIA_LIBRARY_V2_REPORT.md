# Media library expansion v2

The existing manifest, search, and contact-sheet folder were extended. They were not replaced.

## What changed

344 assets already in the library now carry `sceneRoles`, `energy`, `emotion`, `motionPotential`, and `recommendedTreatments`. Those fields are what the Director can use to ask for a hook, an insert, or a low-energy consultation instead of only a filename.

67 new vector assets were added for gaps that did not already have a strong equivalent:

- 20 conceptual metaphors (choice, two homes, approval, risk, investment path, family future, and the rest)
- 16 foreground shapes for parallax and wipes
- 10 transition strokes
- 21 separate layers in 6 packs: relocation city, apartment arrival, document desk, passport journey, property balcony, choice paths

No second generic house, globe, folder, or family icon was added. Passport, visa, relocation, and home icons that were already in the set stayed as they were.

Search now drops filler words such as "in", so a city query no longer opens on a decorative arrow whose description happens to contain that word. A duration phrase such as "four-second" no longer counts as the word "second". A photograph or clip is boosted only when that asset itself matches a scene word in the query. `search_assets` accepts `exclude_ids`, `preferred_scene_role`, and `preferred_energy`. The shot picker uses that ranking and then prefers a playable photo or clip over a line icon.

## Retrieval

Thirty-five meaning queries were run against the updated manifest, including Russian and Chinese. Representative results:

| Query | First result |
| --- | --- |
| family considering moving abroad | people_door_001 |
| семья планирует международный переезд | people_door_001 |
| 家庭计划国际搬迁 | people_door_001 |
| second passport / 第二护照 | doc_book_001 |
| arriving in new city | people_door_001, then still_city_001 |
| packing for international move | people_packing_001 |
| relocation uncertainty | people_couple_001 |
| immigration document preparation | people_review_001 |
| international property investment | re_inv_laptop |
| global route | global_route_001 |
| successful residency approval | document_approval_001 |
| condo exterior daylight | re_ext_condo_day |
| advisor consultation | people_consult_001 |

`exclude_ids` removes an asset already used in the current video, so the next scene can take the next photograph instead of the same doorway.

## Coverage that is still missing

These queries still have no photographic hero. The fallback is an existing icon, object, or route, and a new photo was not invented to paper over that:

- remote work abroad
- tax residency as a picture, rather than the tax icon
- a business owner who is clearly relocating, rather than a route plus an apartment still
- a dedicated residency-approval photograph (the approval motion clip is the current hero)
- cinematic detail inserts: wheels, a door handle, a pen, a key on a table, an elevator button
- human variants in wide, medium, and close for the same consultation
- Thailand or any other country as photography

The same person, couple, and doorway still have to cover planning, arrival, and a new home. That repetition is a coverage limit, not a search miss.

## Generation benchmark

The photographic target was 150–220 approved stills and 25–40 new micro-clips, in batches, after a three-concept benchmark (couple planning, document preparation, cinematic packing).

That benchmark was not run. The local image provider key is unset, so there is no model to compare and no batch was sent. Rejected generations were not added. The production manifest was not filled with unreviewed pictures.

No image-to-video clips were made. Existing approved clips stay the motion layer: consultation, couple, review, door, packing, apartment, phone, and the real-estate interiors and exteriors.

## Contact sheets

Labeled sheets are in `media/library/out/contact-sheets/`:

- hooks.jpg
- human-moments.jpg
- detail-inserts.jpg
- hero-visuals.jpg
- relocation.jpg
- immigration.jpg
- second-passport.jpg
- real-estate.jpg
- transitions.jpg
- micro-motion.jpg

## Observed renderer issues

Caption and label layout was not changed in this pass.

In the last full picture assembly, spoken captions sat too low in the frame: the box started near the bottom edge, so only the top of the glyphs remained visible. That is a caption-layout defect in the picture prompt, separate from which library file was chosen.
