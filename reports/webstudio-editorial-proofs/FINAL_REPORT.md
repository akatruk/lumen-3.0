# Web Studio editorial proofs

Two short MP4s. No deploy. No production flag change. No new component.

## What went through the studio chain

`resolve_plan` → `scripts/overnight_director_render.gate` (enrich, v8, v9, v11, v11.1, v11.2, v10, v14–v18 with their flags off, numeric range, evidence gate) → `resolve_scene_plan` → transcript captions → `render_assembly` (`DirectorV3Preview`).

The browser was not clicked. The excerpt was cut with ffmpeg from the canonical source. The source files were not modified.

| Proof | File | SHA256 | Duration | Wall | Parent max RSS |
| --- | --- | --- | --- | --- | --- |
| original3 list | `output/webstudio-editorial-proofs/original3-list-proof.mp4` | `4c7cd62aa93e2a8902f023cc5b147b20ca7116f3be84a40f5230d646794b8a55` | 33.920s | 83.41s | 886636544 |
| original2 range | `output/webstudio-editorial-proofs/original2-range-proof.mp4` | `703a28d4adc542f3ae8452e722f3dcb4de77ec2fa3d9d8635eab2ec6764abc2d` | 20.053s | 65.73s | 1035403264 |

## Automatic vs manual

Automatic, from the cached transcript:

- original3: `ordinal_timeline_payloads` found 使用场景 / 家庭结构 / 代价 and stamped `motion.process_timeline.v1` with `at` / `until`. V14's global flag stayed off. The evidence gate mounts that one payload.
- original2: `classify_numeric_range` found each band. The proof process set `SEMANTIC_NUMERIC_RANGE_ENABLED=1`. The default remains `0`. A normal Create Video click does not draw the range until that existing flag is on.

Manual, and labeled as the experiment, not as a Director decision:

- The time window. original3 is 42.80–76.68s so the cut starts on 我建议先做三个筛选 and ends on 这里不只是申请费. original2 is 15.46–35.46s, the first salary sentence through the end of 4–5万泰诸.
- Seed `448815100`. Language `zh-CN`. No dub.

Scene ids were not branched on.

## What is in the picture

- List: `motion.process_timeline.v1` in the left `speaker_visual` column. Speaker on the right. Frames: `output/webstudio-editorial-proofs/frames/o3-*.jpg`.
- Range: `motion.numeric_range.v1` in the same split. Frames: `o2-*.jpg`.
- Neither file shows a doorway, a consult couple, an equity chart, or `步骤 1`.

## Sync

Sampled frames match the segment windows. A waveform aligner was not run, so the 300ms tolerance is UNCERTAIN. Word order inside one salary sentence is UNCERTAIN: both ends are on screen together because they share one ASR segment.

original3 sampled result is PASS, including 26.0s: caption 今天适合三口之家的方案, 代价 is not on screen, earlier rows are dim.

original2: the first and second salary bands are UNCERTAIN at word level and correct at segment level. The gap at 10s has no range. `泰诸` and `泰国` are the transcript tokens. They were not rewritten to 泰铢. A second listen failed (`faster_whisper` `metadata_errors` on this venv).

## Known short defects

Both are fixed in the list proof. `步骤` is not drawn. `代价` is hidden until 30.44s of the export and is not the active row during 三口之家.

## Reference B

Opened. Comparison is in `reference-comparison.md`. The list column measures 51.1% of the frame width. Reference B's page was previously measured at 77.5% of its width. The proofs are the split column, not that page.

## Tests

58 passed across evidence, v14, numeric range, v11, v3. 3 failed in `test_director_revisions.py` (409). `backend/app.py` was not edited and is still dirty. Details in `test-results.txt`.

## Blocker

The salary graphic does not appear on a default Web Studio click. `SEMANTIC_NUMERIC_RANGE_ENABLED` defaults to 0. The list does appear without that flag, because the evidence gate mounts the existing timeline.

The unit on screen is the ASR string. If the speaker said 泰铢 and the transcript says 泰国, the graphic repeats the transcript. That was not re-heard.

## Next step

Turn the numeric-range apply on in the experimental job without changing the production default, then one more 20s original2 export. Do not render 151s.
