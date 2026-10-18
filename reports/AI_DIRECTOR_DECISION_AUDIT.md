# AI Director decision audit

`lumen-fc451a1e.mp4` is the isolated upload render, not a lumen-fix job. SHA256 `e21bf8dac04f4fa5ab1a07d044159ab9be389f2e77c22604e7dea6a335f3914b` matches render `94c1b71ac66247fbbc3c768f7e6d3351`.

| Field | Value |
| --- | --- |
| Project | `fc451a1e44834e73a28f7e02157e28dd` |
| Generation | `gen_448815100` |
| Director job | `89c29199445f4c5982c40de604b88ef3` |
| Transcription job | `00feff4f06da43c9821e6293a5af9f7b` |
| Source checksum | `f7a6fc43c2631b053a34a59676aeef762e5ee1b33679d52765cf98dc43cdf234` |
| Plans | `visual-history/gen_448815100.json` (6-beat heuristic) and `remotion-plans/gen_448815100.json` (what Remotion received) |

Both files are under `/tmp/lumen-asr-e2e-20261016/`. The heuristic plan has no cards. The remotion plan is the one that was rendered. Scene JSON is `reports/director-decision-trace.json`.

## Transcript

Verified. `source-transcript.json` status `verified`, 28 segments, 0.00–60.36s, language `zh-CN`, model `Systran/faster-whisper-small`. Checksum matches the 60s source. Project language `zh-CN`. `dubbed=false`, `voice=none`. Caption source on the render plan is `source_transcript`. No `[segment]` text. The director job payload contains those 28 lines.

This source is the first 60.1s of original3. The full original3 checksum in `reports/original3/source-analysis.json` is `0a82755d83c2eba84647f70189c825a1a9eb5a81503cfca3f711bbb8f6c5d96c` (151.1s). Do not treat that file as this project's transcript.

## What the frames show

Times are the beat weights in the remotion plan (sum 1800, duration 60.1s).

| Scene | Time | Speech under it | Selected plate | What the frame shows |
| --- | --- | --- | --- | --- |
| hook | 0.00–3.00 | 很多人第一次来咨询 先会问 | `people_door_001` + suitcase | Speaker. Suitcase outline. Door hidden. |
| context | 3.00–9.02 | 哪本护照最好办 / 走进医院 | `people_door_001` | Doorway family, split. |
| problem | 9.02–16.03 | 第一步不是选国家 而是定义问题 | `people_consult_001` + passport | Speaker. Faint passport. Plate hidden. |
| residency | 16.03–26.04 | 出行受限 / 教育 / 退休居住 / 跨境经营 | `people_door_001` | Same doorway family again. |
| consult | 26.04–34.06 | 这些目标都叫移民 / 法律工具完全不同 | `i2v_consult_001` | Consult couple + PIP. |
| beside | 34.06–40.07 | 长期居留 / 工作权 / 入籍 / 不搬家 | card 目标·家庭·预算 | Card reads 家庭 / 同行家人与时间安排. |
| steps | 40.07–45.08 | 备用选项 / 三个筛选 starts | 咨询 → 方案 → 文件 | Overlay 全程陪同, 步骤 2, 方案. Phone clip hidden. |
| proof | 45.08–51.09 | 第一层叫使用场景 / 未来五年 | `people_consult_001` | Same consult couple again. |
| payoff | 51.09–56.09 | 住多久 / 工作 / 上学 | boardroom clip | Speaker only. Clip hidden. |
| return | 56.09–60.10 | 不要研究长期居住 / 第二层 | family consult clip | Speaker only. Clip hidden. |

Visible time: speaker 19.02s, B-roll 30.06s, text cards 11.02s. Semantic-motion components: 0s. `semanticMotion.display` is `omit` on every scene. `semanticMotionAudit.resolvedCount` is 0.

Visible repeats: `people_door_001` at 3–9s and 16–26s (16.03s). The consult couple at 26–34s and 45–51s (14.03s). Four more scenes selected a plate the fullscreen speaker layout never mounts.

## Where the decision breaks

The heuristic plan (`visual_variation` / `plan_for_request`, `director_provider=heuristic`, `LLM_PROVIDER=none`) is a 6-beat template: hook, residency, consult, beside, steps, return. Headlines and cards are empty. Queries are stock English (`family home doorway relocation`, `advisor client meeting trust`).

`director_v3.run_job` then runs, in order: `director_semantics.enrich_plan_from_transcript`, `director_v8.expand_plan_for_duration`, `director_v8.fill_media_for_scenes`, V9, V11, V11.1, V11.2, fill again, V9 again, V10, then V14–V18 which return immediately.

`enrich_plan_from_transcript` joins the whole minute and, because `detect_topic_domain` sees 咨询 and 护照, stamps the immigration pack onto the `beside` and `steps` beats:

- `director_semantics._CRITERIA_ZH` / `director_v11._CRITERIA_PACKS['immigration']['zh']`: 目标, 家庭, 预算, with explanations 迁往哪里以及为何出发, 同行家人与时间安排, 项目费用是否可承受.
- `_STEPS_ZH`: 全程陪同 / 咨询, 方案, 文件.

None of those six strings is in the 60s transcript. `director_v9.simplify_scene_composition` keeps them (`Never strip factual card/step content`) and sets `suppressHeadline`. `motion/src/preview/DirectorV3.tsx` `Beside` still paints `criteriaCards` when `sceneId === "beside"`. `CleanSteps` paints the step title. That is the 目标 card. It was chosen by the pack, not by the quote at 34s.

`director_v8.LONG_BEATS` then replaces the timeline with ten fixed beats. `context` is hardcoded to `family home doorway relocation`. `hook.query` starts null. `director_v11._concepts_for_scene` does not look at the beat window. It walks `_BEAT_CONCEPT_PREF`. Hook's first hit is `relocation_move`, evidence `也有人根本不准备搬家` at 38.24s, so the opener is searched as a doorway. The same concept is attached to `context`. `residency` keeps `document review desk paperwork` and still receives `people_door_001`. Eight scenes carry the concept `consultation` from 0.00–2.64s (`很多人第一次来咨询`), so their query becomes `consultation meeting advisor`.

`fill_media_for_scenes` keeps an `assetId` once set. The second pass does not re-rank. Fullscreen layouts in `DirectorV3` then drop the plate: hook, problem, payoff, and return selected media that the frame does not show.

V14–V18 were not considered. `director_v14.enabled()` reads `SEMANTIC_MOTION_V14_ENABLED`, default `0`, and `apply_semantic_motion` returns before `classify_quote`. V15, V16, V17, and V18 do the same with their own env flags. The render plan has no `semanticMotionV14` on any scene. `reports/original3/semantic-coverage.json` already measured the matchers with the flag forced: 0 of 78 ASR lines and 0 of 11 grouped quotes select a component. Enabling the flags on this build would not draw 不是选国家 or 第一层叫使用场景.

## 9 versus 11

Same analysis version `original3-source-audit-1`, same full-source checksum.

- `source-analysis.json`: 11 segments, 11 `visualOpportunities` (s08 holds two).
- `semantic-coverage.json`: 11 `groupedQuotes` (s01–s11, s08 merged, s11 is the closing fragment) and `metrics.motionComponentCoverage.justifiedScenes` = 9.

11 is the quote grouping. 9 is the subset that audit treated as worth a diagram. `scene_07` is in both the partial list and the unsupported list on purpose. `selectedByClassifiers` is 0 in both senses. This MP4 only contains s01–s04 and the start of s05 (42.8s onward). s06–s11 are past 60s and are not in the file.

## Root causes

| Code | When | Defect | Evidence | Function | Config | Smallest correction |
| --- | --- | --- | --- | --- | --- | --- |
| GENERIC_FALLBACK | 34.06–45.08 | Stock cards 目标/家庭/预算 and 咨询/方案/文件 over speech about 入籍 and 备用选项 | Frames at 37s and 42.5s. Strings are absent from the transcript. | `director_semantics.enrich_plan_from_transcript`, packs in `director_v11._CRITERIA_PACKS`, painted by `Beside` and `CleanSteps` | Heuristic, flags off | Stamp a card only from words inside that beat. Otherwise leave the speaker. |
| MEDIA_SELECTION_FAILURE | 3.00–9.02 and 16.03–26.04 | Same doorway behind 护照最好办 and behind 退休居住 | `people_door_001` on hook, context, residency | `director_v8.LONG_BEATS` context query; `director_v11._concepts_for_scene` attaches a 38s 搬家 hit to the opener; `fill_media_for_scenes` keeps the first asset | Library search, no pgvector on this path | Search with the quote whose midpoint is inside the beat. Do not reuse an asset whose query came from another beat. |
| MEDIA_SELECTION_FAILURE | 26.04–34.06 and 45.08–51.09 | Same consult couple behind 法律工具完全不同 and behind 未来五年 | `i2v_consult_001`, `people_consult_001` | `_concepts_for_scene` fallback copies the 0–2.64s 咨询 concept onto later beats | Same | One consult plate for the consult sentence. Later beats need their own quote or no plate. |
| FEATURE_FLAG_DISABLED | whole minute | No V14–V18 component was eligible at runtime | `apply_semantic_motion` returns when the env is off. Render plan has no v14 payload. | `director_v14.enabled`, `director_v15.enabled`, `scene_composer_v16.enabled`, `motion_quality_v17`, `motion_design_v18.enabled` | All default 0. Isolated env did not set them. Production `.env` from the ASR deploy also leaves them unset. | Do not flip the flags first. The matchers return empty on this speech. |
| SEMANTIC_CLASSIFICATION_FAILURE | 9.76–14.24 and 42.8–60.1 | 不是选国家 而是定义问题 and 第一层叫使用场景 match nothing | `semantic-coverage.json`: `classify_quote` and `classify_v15` return `[]`. `_party_pair` wants 中国+泰国. `_steps_from_quote` wants the English list or 银行开户/工作证/签证申请. | `director_v14.classify_quote`, `_steps_from_quote` | Flag off, so this code did not run on the render | Accept 不是 A 而是 B and 第N层叫X, using those strings as labels. |
| DIRECTOR_PLANNING_FAILURE | 0–60 | Ten fixed beats, not the spoken argument | Heuristic plan is 6 purposes. `expand_plan_for_duration` writes `form=long60` from `LONG_BEATS` whenever duration ≥ 45s. | `director_v8.expand_plan_for_duration` | `duration_seconds` 60.1 | Cut beats on transcript boundaries. Drop a beat that has no quote of its own. |
| REMOTION_RENDER_FAILURE | hook, problem, payoff, return | Selected plates are not in the picture | Plan lists door, consult, boardroom, family-consult. Frames are the speaker. | Fullscreen branch in `motion/src/preview/DirectorV3.tsx` after V9 sets `primaryVisualRole=speaker` | V9 `containerPolicy=minimal` | If the layout cannot show the plate, do not count it as used, and do not spend the next beat on the same plate. |

Transcript failure does not apply. Scene composer did not run. Component parameters were never filled because V14 returned first.

## Three fixes, not built

1. **Evidence gate on the stock packs.** `enrich_plan_from_transcript` and the V11 beside/steps rewrite. Expected: the 目标 card and the 咨询/方案/文件 overlay disappear on every video whose speech does not say those words, including this one. Effort: small. Regression: low if an empty card falls back to the speaker. The highest leverage, and it does not depend on a flag.

2. **Search inside the beat window.** `LONG_BEATS` default queries plus `_concepts_for_scene` plus `fill_media_for_scenes` asset retention. Expected: the doorway stops covering the hospital line and the five goals, and the consult room stops repeating under 未来五年. Applies to every long render, not only original3. Effort: medium. Regression: medium, because layout tests assume the ten-beat template.

3. **Matchers for 不是/而是 and 第N层, then call them from the default path.** `classify_quote` and `_steps_from_quote` are the reason a future flag-on run still draws nothing. Turning the flags on today changes nothing (`selectedByClassifiers` is 0). Effort: medium. Regression: medium once the default path can mount `business_comparison` and `process_timeline`. Do not enable V14–V18 until those matchers return the spoken labels.

No render, no flag change, no deploy.
