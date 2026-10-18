# Capital & business cinematic factory V7

Commit: `af80abcb68a5b83785bd98b9e919da0c721c17a7` on `feat/media-library-cleanup-v1`.

Date: 2026-10-14. Host: `lumen-fix` `142.93.248.163` `/opt/lumen-rebuild`. Volume: `/mnt/volume_nyc1_1791446889637/app-library` (~80G free before the batch). Pinned pod only: `dznvwn90el5au4` / `lumen-hypit-4090` / RTX PRO 4500. `hufsgfs9f7gpga` left EXITED. strom-v2 not touched. No OpenRouter.

## Result

| | |
| --- | --- |
| Clips generated | 10 / 10 (real SVD-XT files, not fabricated) |
| Clips approved | **7** |
| Clips rejected | **3** |
| Stills approved | 9 |
| Stills rejected | 1 (`cev7_cap_shareholders_004`) |
| Measured duration | **3.571429 s**, 25 frames, `7/1` fps, **1080x1920** H.264 |
| Not claimed | 5–6 s cinematic motion, 30 fps, setpts stretch |
| pgvector `asset_embeddings` where `asset_id LIKE 'cev7_%'` | **46** (16 text + 9 image + 21 keyframes). Second run added 0. Table total 1117. Rejected shareholder ids: 0 rows |
| `VISUAL_INTELLIGENCE_ENABLED` | **false** (left off) |
| Pod final | **EXITED**. Balance **$6.5755795892**. Idle spend **$0.008/hr**. Start balance ~$6.780. Spend this run ~$0.20 |
| origin1 | Retrieval only. Tops were not forced to all 10. No new mp4. No caption/voice/fact edit |

SVD-XT emits 25 frames. Playback at 7 fps is the reviewed export (~3.6 s). A 24 fps encode of the same frames would be ~1 s. Neither is a 6 s shot. `setpts` was not used.

## Approved clips

Paths under `/mnt/volume_nyc1_1791446889637/app-library/motion/cinematic-env-v7/clips/`.

| id | duration | grounding (from frames, not the prompt) |
| --- | --- | --- |
| `cev7_i2v_cap_office_seniors_001` | 3.571 s | 2 older men at a wood table, glass office, blurred pages |
| `cev7_i2v_cap_documents_003` | 3.571 s | 0 people. Two pens on an illegible page. No cash pile |
| `cev7_i2v_cap_district_005` | 3.571 s | 0 people. Glass towers. `syntheticCity`, city not verified |
| `cev7_i2v_cap_ceo_advisor_006` | 3.571 s | 2 men at a round window table. Motion is a small shift, not an orbit |
| `cev7_i2v_cap_exec_docs_007` | 3.571 s | 2 men, large page, no readable numbers |
| `cev7_i2v_cap_property_008` | 3.571 s | 3 men outside a glass commercial building (intent said investors; count on screen is 3) |
| `cev7_i2v_cap_global_skyline_010` | 3.571 s | 0 people. Skyline through a window wall. `syntheticCity` |

Desktop copies: `~/Desktop/cinematic-env-v7/cev7_i2v_cap_ceo_advisor_006.mp4`, `cev7_i2v_cap_global_skyline_010.mp4`.

## Rejected

| id | why |
| --- | --- |
| `cev7_i2v_cap_exec_negotiate_002` | Still shows 3 people. Mid frame adds a fourth. Person-count morph |
| `cev7_cap_shareholders_004` + `cev7_i2v_cap_shareholders_004` | Two men standing. Brief was three shareholders. Not published |
| `cev7_i2v_cap_founders_glass_009` | Mid frame smears the seated people. Still kept: 4 seated + 1 standing at the glass, city beyond, city not verified |

Rejected rows are in the manifest with `status=rejected` and are absent from default search and from `asset_embeddings`.

## Keyword smoke (`VISUAL_INTELLIGENCE_ENABLED=0`)

| query | locale | ids in the top hits |
| --- | --- | --- |
| `capital investment office` | en-US | `cev7_i2v_cap_office_seniors_001` first |
| `капитал офис инвестиции` | ru-RU | `cev7_i2v_cap_office_seniors_001` (with a V6 glass clip ahead of it) |
| `资本 投资 办公室` | zh-CN | `cev7_i2v_cap_office_seniors_001` |
| `financial district skyline` | en-US | `cev7_i2v_cap_district_005` |
| `финансовый район скайлайн` | ru-RU | `cev7_i2v_cap_district_005` |
| `金融 天际线 资本` | zh-CN | `cev7_i2v_cap_district_005` first |
| `акционер` | ru-RU | empty (rejected shareholder plate stays hidden) |

## origin1 `director_v5_original1`

`_candidates` on the live library, nothing written back to the project. Immigration was not added to queries. One existing V6 family clip (`cev6_i2v_fam_consult_003`) still sits in the shareholder-query pool; it was not the top and this batch did not promote it.

Tops actually chosen when each query keeps the previous top out:

- `business meeting corporate office asia` → `cev6_i2v_biz_boardroom_001`
- `capital investment finance chart` → `cev7_i2v_cap_office_seniors_001`
- `corporate boardroom shareholders meeting` → `cev6_i2v_biz_meeting_002`
- `financial analysis spreadsheet desk` → `cev6_i2v_city_skyline_001`
- `bangkok business district skyline daytime` → `cev7_i2v_cap_district_005`
- `corporate control handshake boardroom` → `cev6_i2v_biz_corridor_003`

Two of six tops are V7. The other four stay V6. The rejected two-person shareholder plate is not in that pool.

No Remotion preview. A render would call `store_plan` on the live origin1 project. GPU was already stopped. Facts, voice, and captions were not edited.

## Ingest

Approved rows went through `media/library/ingest.register_approved` with `en-US` / `ru-RU` / `zh-CN` and `qualityStatus=production_ready`. `visualGrounding` is separate from `intent`. Human `tagsAuthority=human` is preserved on reindex. ADR-010 rule 13 and the media-library skill say later cinematic batches use this same path.

## Not done

- Native 5–6 s / 30 fps motion. The model does not support it. Clips were not stretched.
- Four-executive lateral clip (morph). Three-shareholder plate (only two people on screen).
- origin1 mp4.
- `VISUAL_INTELLIGENCE_ENABLED` was not turned on.
- V6 files were not overwritten. Storage-audit dry-run deletions were not executed. No workflow file.
