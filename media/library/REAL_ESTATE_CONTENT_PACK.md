# Real estate content pack

Status after the first production pass and a partial second photograph batch. This pack lives inside the existing library at `media/library/` and on the volume at `/media/media-library`. It does not replace the general icons, the approved motion clips, or the search index.

## Counts

| Layer | Accepted | Target | Notes |
| --- | ---: | ---: | --- |
| Photographs | 29 | 100–140 | 19 from batch 1, 10 from batch 2 |
| Line objects | 21 | 60–80 | Gold stroke SVG, same family as the general icons |
| Deterministic motion presets | 5 | 20–25 | Parameterized Remotion components, not baked numbers |
| Generic mini-broll | 5 | 20–30 | Image-to-video from accepted stills |
| Backgrounds | 0 | 10–15 | Not started |
| Bangkok stills | 0 | 20–30 | Not started |
| Bangkok mini-broll | 0 | 5–8 | Not started |
| Scene recipes | 30 | ~30 | `media/library/real-estate-scene-recipes.json` |

Rejected photographs: 1 (`re_int_bath`, a public restroom with stalls). Kept in `rejected/`. A later home bathroom (`re_int_bath_home`) was accepted.

Batch 2 asked for 20 stills. Ten were written. The next ten returned HTTP 402 from the image provider and were not retried.

Accepted / generated for photographs: 29 / 30 finished files (the public bathroom is the only visual reject). The 402 responses produced no files.

## Photographs

Batch 1, accepted: couple and agent viewing, agent showing, balcony, empty-apartment walk, living room, kitchen, bedroom, empty interior, dining, agent with documents, key handover, agent with a blank tablet, investor at a laptop, investor meeting, daylight condo tower, golden-hour house, quiet street, park, couple planning.

Batch 2, accepted: private bathroom, home office, entrance hall, premium living room, small apartment, family living room, affordable living room, villa, townhouses, construction tower with a crane.

People stay large and in daylight. Interiors now cover affordable, mid-market, and premium. Construction has no site boards. The golden-hour “house” reads as a low pavilion by water; it is still a useful luxury exterior.

Contact sheet: `contact-sheets/real-estate-photography.jpg`.

## Objects

Twenty-one gold line drawings: condo, villa, floor plan, balcony, crane, door, keys, mortgage, yield, inspection, pool, gym, parking, elevator, tenant, agent, renovation, transit, shopping, tree, occupancy.

Crane and tenant were redrawn after the first sheet. The crane now reads as a tower crane. The tenant is a person beside a key.

Contact sheet: `contact-sheets/real-estate-objects.jpg`.

Existing general icons were left in place. These drawings only add real-estate shapes the general set did not already cover well.

## Motion presets

Source: `motion/src/realestate/scenes.tsx`, registered from `motion/src/realestate/index.tsx`.

- `RePriceCounter` — currency, value, label
- `RePriceChange` — previous and next
- `ReRentalYield` — monthly rent and yield
- `RePropertyComparison` — two sides
- `RePurchaseProcess` — stage labels

Demo figures exist only as Remotion `defaultProps` so a preview can render. A Director call replaces them. Canvas is 1080×1920 at 30 fps. The duplicate `index.ts` entry was removed so the bundler uses the `.tsx` root.

Stills of the price counter and the purchase process were checked: words stay whole.

## Mini-broll

Five clips, each 4.0 seconds, from accepted stills:

- `re_ext_condo_day_motion`
- `re_int_living_motion`
- `re_int_empty_motion`
- `re_view_balcony_motion`
- `re_buyer_plan_motion`

Start and end frames keep the same person, face, furniture, and building. Motion is a slow push.

Provider settings follow the existing video call: `google/veo-3.1-fast`, first frame from the still, 720×1280, 24 fps, about 4 seconds. That is short of the 1080×1920 / 30 fps target. The files are usable as portrait b-roll and can be scaled in the edit.

Contact sheet of middle frames: `contact-sheets/real-estate-motion.jpg`.

A keys handover clip was not generated in this pass. Search for “agent giving keys” as video therefore does not return a keys clip.

## Scene recipes

Thirty recipes in `real-estate-scene-recipes.json`, from `property_hook` through `final_property_cta`. Each names a motion component, an asset query, a layout, a duration band, and the values the Director supplies.

Several recipes point at components that are not built yet and currently reuse `RePurchaseProcess`, `RePriceChange`, or `RePropertyComparison` as a stand-in: amenities, features, mortgage breakdown, market chart, inspection, portfolio. Those need their own presets before they match the recipe name.

## Search

`search.py` was extended, not replaced. The haystack includes domain, visual family, action, region, subjects, mood, property type, and text-safe areas. `text_safe` adds a bonus when that side is listed.

Checked queries:

- “couple viewing condo” returns `re_view_couple_right`, the balcony, and the empty-apartment walk.
- “property investment rental yield” returns the yield icon, the yield motion preset, occupancy, and the investor laptop.
- “buying apartment legal documents” returns the inspection icon and the agent-with-documents photo, then the general contract and legal icons.
- “property price growth investment” returns the price-change preset, growth, and yield.
- “property viewing with text space on left” prefers assets whose `textSafeAreas` include `left`, including the balcony and the brighter property-viewing repair.
- “Bangkok condo lifestyle” has no regional photographs yet, so it falls through to generic condo, pool, and balcony icons.
- “agent giving keys to buyer” as video does not return a keys clip. The still `re_agent_keys` is in the library as an image.

## Models and settings

- Stills: `google/gemini-2.5-flash-image` through the OpenRouter chat-completions image call, aspect ratio 9:16. Prompts forbid letters, digits, logos, captions, and readable signs. The word that makes the model refuse a frame was left out of the prompt.
- Objects: authored SVG, viewBox 24, stroke `#E0B15A`, stroke width 1.6, round caps. Rasterized for the contact sheet with `@resvg/resvg-js`.
- Motion: Remotion, theme tokens, `AutoFitText`.
- Mini-broll: `google/veo-3.1-fast`, image-to-video from the approved still, audio off.

## Storage

On the volume, `/media/media-library` is about 113 MB after this pack. The real-estate photographs on disk are about 24 MB for the first 19 plus the second 10. The five clips are about 7 MB together. The volume is the 100 GB disk; this pack does not crowd it.

Server manifest after the id merge: 241 assets, 60 of them with the `re_` prefix (21 objects, 29 photographs, 5 motion presets, 5 clips). Non-`re_` assets were kept.

## Bangkok

No Bangkok or Southeast Asia assets yet. Do not treat generic city frames as Bangkok. When that subpack exists it must carry `region` values `bangkok`, `thailand`, and `southeast_asia`.

`contact-sheets/real-estate-bangkok.jpg` is not created, because that set does not exist.

## Known gaps

- Photograph inventory is 29, not 100–140. Missing clusters: evening tower, residential skyline, family viewing, kitchen inspection, wide key handover, seller preparing a home, cafe street, dusk street, empty balcony, waterfront housing. Those ten were the 402 stop.
- Affordable and luxury interiors exist as single frames, not as a range.
- Hero objects are line icons, not a 60–80 object set. Still missing as their own drawings: house (distinct from villa), window, map pin, contract stack, signature, folder, calendar, deposit, cash flow, down payment, expenses, tax, insurance, portfolio of buildings, risk, title, identity.
- Backgrounds: architectural grid, floor-plan pattern, map wash, blueprint, skyline wash.
- Twenty motion presets are still only recipes: cash flow, mortgage breakdown, buy versus rent as its own layout, location map, distance rings, amenities, floor-plan reveal, features, price per square meter, investment growth, rental income, occupancy, document check, inspection, key handover, before/after, portfolio, market trend, neighborhood score.
- Mini-broll list is five of about thirty. No Bangkok clips.
- Clips are 720×1280 at 24 fps.
- `re_ext_house_gold` is a pavilion by water more than a two-storey house.

## Next categories, in order

1. Retry the ten photographs that returned 402, then keep going through viewing, documents, and location until the photograph pool is past 100.
2. Cash-flow, mortgage, location-map, and floor-plan motion presets.
3. Mini-broll only from stills that already passed, including a keys handover once a wide, bright frame exists.
4. Bangkok subpack, tagged, with no readable transit signs or building names.
5. Subtle backgrounds, type still dominant.
