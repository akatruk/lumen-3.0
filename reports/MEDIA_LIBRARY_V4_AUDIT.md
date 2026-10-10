# Media library V4 audit

Counted from `media/library/out/manifest.json` on 10 October 2026. The old figure of 248 is out of date.

## Inventory

| | Count |
| --- | ---: |
| Approved manifest rows | 411 |
| Images | 389 |
| Video files | 17 |
| Remotion motion presets (`.tsx`, file not a media master) | 5 |
| SVG | 341 |
| PNG | 48 |
| MP4 | 12 |
| WebM | 5 |
| Photography | 40 |
| Line drawings | 168 |
| Rows with no visual family | 150 |
| Backgrounds (family or category) | 26 family / 44 category |
| Hero-role rows | 70 |
| Layered ids | 21 |
| Motion clips that are real video | 17 |
| Files missing on disk | 5 (the real-estate Remotion presets point at `scenes.tsx`, not a video file) |

Domain field: immigration 116, real estate 60, relocation 47, unset 188.

Photographs: 29 real estate, 10 people, 1 city still.

No asset has `conceptId`. No description or tag field is a per-language object. Search has been matching English tags, with a short alias list for some Russian and Chinese words.

Library size on this machine: `media/library/out` is 82 MB. Server volume `/mnt/volume_nyc1_1791446889637` has 83 GB free. Root disk has 13 GB free.

## Why the same pictures kept winning

The last three comparable edits are the visual-randomization previews, seeds 839204, 120011, and 103. Each one only had two library picks (the document beat and the proof beat). The other beats stay on the speaker.

| | Document beat | Proof beat |
| --- | --- | --- |
| A `gen_839204` | `document_approval_001` | `i2v_consult_001` |
| B `gen_120011` | `document_approval_001` | `people_consult_001` |
| C `gen_103` | `re_agent_docs` | `people_phone_001` |

Five unique assets across six slots. `document_approval_001` was used twice. `people_consult_001` and `i2v_consult_001` are the same meeting, one still and one clip.

Causes, from the code and the queries, not from filenames:

1. Both scenes used one fixed English query (`passport document`, `consultation meeting`).
2. Search returned a short list and quality weight kept the top still.
3. Nothing remembered the previous generation.
4. A Russian or Chinese phrase that did not hit an alias became an empty token list. Search then returned the highest `qualityScore` rows, which are decorative arrows. That is a retrieval bug, not a missing photograph.

There is no separate AI Engineering Memory database in this repo.

## Coverage gaps

Photographs are the scarce layer: 40 against a long-term aim near 350. Motion video is 17 against an aim near 150. Useful human scenes exist for consultation, a couple, document review, a doorway, a phone call, two property viewings, packing, an apartment, and travel. They do not cover investor immigration, an interview, a family with children, affordable versus luxury as separate people scenes, or a true citizenship still.

Hero objects are mostly one gold-line SVG family. More globes would not add a new idea.

Remote-work and citizenship-planning queries still land on a route graphic or a buyer-at-a-desk still. Those concepts need a photograph before search can do better.
