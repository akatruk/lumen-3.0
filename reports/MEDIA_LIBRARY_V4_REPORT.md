# Media library V4 report

## What changed

Search now expands Russian and Chinese phrases onto the shared English tags, and it refuses to dump the icon set when a phrase does not match. A recent asset is ranked down when another relevant hit exists. A new generation reads asset ids from stored visual plans and avoids them. The document and proof beats rotate among different queries (residence application, document review, consultation, phone consult) instead of one fixed sentence.

No new image or video file was added. The paid batch did not run.

## Counts

| | |
| --- | ---: |
| Starting approved rows | 411 |
| New approved assets | 0 |
| Final approved rows | 411 |
| Photographs | 40 |
| Motion video | 17 |
| SVG | 341 |
| Rejected this pass | 0 |
| New duplicates | 0 |

## Credits and models

Configured, not invented:

- Still image: `google/gemini-2.5-flash-image` through OpenRouter.
- Motion: `google/veo-3.1-fast`.
- Daily budget in config: 20 USD.

Production key check on 10 October 2026: `total_credits` 20, `total_usage` 20.327. The account is already past the credit balance. Batch 1 (30 photographs, 20 details, 15 hero objects, 10 motion clips, 10 layered assets) was not submitted. A retry would be another HTTP 402. Estimated cost was not spent. Actual cost this pass: 0.

Prompt templates for a later batch, when credits exist, are the four sentences in the task (photography, hero object, detail insert, image-to-video). They were not sent to a provider.

## Cross-generation picks

Previous three previews, six library slots, five unique ids, `document_approval_001` twice, and the consultation still/clip pair.

Same three seeds after the memory pass, each plan told about the assets already chosen:

| Seed | Document beat | Proof beat |
| --- | --- | --- |
| 839204 | `people_door_001` | `document_approval_001` |
| 120011 | `i2v_review_001` | `i2v_phone_001` |
| 103 | `people_review_001` | `i2v_consult_001` |

Overlap across those three plans: none. Meaning of the six beats is unchanged. Speaker scenes still do not swap the host for a random plate.

Previews rendered from these plans: `output/media-library-v4/variant-a.mp4`, `variant-b.mp4`, `variant-c.mp4`. Each is 1080×1920, 20.05 s, H.264 + AAC. At 8 s the proof beats differ (mean absolute difference 40–69). At 5 s, B and C are close (1.5): `i2v_review_001` is the moving version of the same review still as `people_review_001`. The ids differ; the photograph does not. A at that second is the doorway still (difference about 33).

## Tests

`media/library/search.test.py`: 11 tests, including the 60-query set.

`backend/tests/test_visual_variation.py` and `backend/tests/test_director_v3.py`: 10 tests. The same seed still rebuilds the same plan. A repeated asset id is left behind when another qualified file exists.

## Not done

- AI Engineering Memory is not in this repository. Decisions are in this report and in git, not in a second database.
- Contact sheets for a new batch were not made, because there is no new batch.
- `conceptId` was not written into all 411 manifest rows.
- English, Russian, and Chinese voice was not re-generated. The previews keep the existing Russian speaker track. A missing target-language voice is not replaced.
- Photographs for citizenship, a company move, and remote work are still missing. Search cannot invent them.

## Git

Code commit: `253c4887766eee422480f36c7154f04b2b329e2a` on `fix/seedance-import-prologue`.

## Disk

`media/library/out` is 82 MB. Server volume 83 GB free. Root 13 GB free. This pass did not copy new masters.
