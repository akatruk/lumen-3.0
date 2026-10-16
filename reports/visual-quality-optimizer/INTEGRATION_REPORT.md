# Visual Quality Optimizer V1

Branch: `experiment/visual-quality-optimizer`
Base: `1c2c33f1fc0c2dc54e6b6f5560e5c29075d0b64a` (`experiment/semantic-motion-webstudio`)
Not merged. Not pushed. Not deployed.

## Architecture

The optimizer is a check on a finished Director plan. It does not classify beats, pick components, or call a model.

```
verified transcript
  -> existing Director (unchanged)
  -> scene plan
  -> visual_quality_optimizer.apply
  -> existing staging / resolve_scene_plan / Remotion
```

Hook: `director_v3.run_job`, after the evidence-gated profile block and before background staging.

| mode | behavior |
|---|---|
| `off` (default) | returns the same plan object. No findings, no database call. |
| `shadow` | attaches `visualQualityReport`. Same `scenes` list. |
| `apply_safe` | drops an unsupported optional graphic, shortens a stale display past the 1.5s hold, or replaces a repeated plate only when the finding already names an approved overlapping alternative. |

The job field is `visual_optimizer_mode`. There is no environment switch and no UI default. An exception in analysis leaves the Director plan renderable. The evidence gate still runs before this hook.

`resolve_scene_plan` copies `visualOptimizerMode` and `visualQualityReport` onto the stored render plan. Those keys are not scene props.

## Timeline classification

`director_v14._steps_from_quote` no longer treats a noun list as a process.

A timeline still requires either a complete ordinal run (`第1…第N`, no gaps) or an order cue (`first` / `then` / `next` / `step N` / `сначала` / `затем` / `шаг N` / `第N`). A comma-and list without that cue returns no steps. The old hardcoded triple `银行开户 / 工作证 / 签证申请` is gone, and the same rule rejects the English and Russian translations of that sentence.

Ordered layers still extract. `第一层叫使用场景 第二层叫家庭结构 第三层叫代价` stays `motion.process_timeline.v1`.

V15 `document_workflow` was built from those same steps. On the original1 transcript it no longer fires. `test_director_v15.py` now expects that. This is the classification change, not a silenced assertion.

## Experience memory

No migration. No new table. No embedding job.

Existing tables, all `vector(512)`, from `backend/experience_memory.py`:

- `generation_history`
- `generation_reviews` (`review_source` is `user` or `automated`; a user row has a rating and a null QA score, and the reverse)
- `scene_feedback`
- `asset_feedback` (migration 002)
- `asset_embeddings`
- `scene_embeddings`

`recall_experience` does not embed text. It returns immediately when there is no query vector, the vector is not length 512, the memory flags are off, or the database is not Postgres. A live query, when all of those pass, reads at most 8 `scene_feedback` rows with `review_source='user'` and `vector_dimension=512`, with `statement_timeout` 1500ms. Cosine is stored as `similarity` and marked `similarityIsNotQuality`. Automated QA scores are not read.

This checkout's isolated acceptance database is SQLite. Retrieval reason on that store: `postgres_unavailable` or `experience_memory_disabled`. The optimizer still emits evidence findings. Production Postgres on lumen-fix was not queried.

No human ratings were written.

## Shadow findings

Persisted render plans from the semantic-motion acceptance (isolated SQLite). Labels below are the ones in the task, not new rater scores.

| plan | findings | NO_CHANGE | note |
|---|---|---|---|
| original1 `gen_289082071` | 1 | 7 | `UNJUSTIFIED_PROCESS_TIMELINE` on `steps__evt_0d6cde0b468a`. Quote `银行开户工作证签证申请都会盯着资金到位情况…`. Suggested `SAFE_FALLBACK`. |
| original2 `gen_856109875` | 0 | 8 | Ranges whose unit was omitted (`asr_unit_unverified`) are not `UNSUPPORTED_VISIBLE_CLAIM`. `400–1200 人民币/每天` stays. |
| original3 `gen_631280367` | 0 | 2 | `使用场景 / 家庭结构 / 代价` stays. Display slack 1.23s is inside the 1.5s hold. |

`evaluate` time: 0.065ms, 0.019ms, 0.333ms. Database queries: 0.

Icon reuse (`foreground.assetId=goal`, file `static/icons/goal.svg`) was a false positive in the first cut and is excluded. SVG icons are not B-roll. After that filter the original1 shadow report has only the timeline finding.

Repeated photographic plates are not dropped for diversity. Shared subject tokens produce `justified_reuse` / `NO_CHANGE`. No approved alternative produces `NO_SAFE_ALTERNATIVE` and the plate stays.

## A/B

Same stored original1 plan, same speaker file, same Remotion `render_assembly`. The only plan edit on B is the optimizer drop of that one timeline. This is not a second Create Video pass; a fresh director run would also skip the timeline because the extractor no longer emits it.

| | file | sha256 | duration | audio md5 |
|---|---|---|---|---|
| A control | `reports/visual-quality-optimizer/ab/a-control.mp4` | `ab89b049678fb597ac4b89ac4f3e732f897fa1845e431c03eed4cf24fd00e84c` | 36.459s | `dc5f019966998cc8614b0bfd0d7108cf` |
| B apply_safe | `reports/visual-quality-optimizer/ab/b-apply-safe.mp4` | `5ea02b51a0002f51a2aa3a6f68dde75cf5779bb9f6b287bfc5a9a6d97aa08985` | 36.459s | `dc5f019966998cc8614b0bfd0d7108cf` |

1080×1920, h264 + aac. Audio streams match. Contact sheets: `contact-4s.png`, `contact-18s.png`, `contact-24s.png`, `contact-32s.png` (A left, B right).

- 4s: both show `≥3` / `公司` over `普通泰国有限公司通常需要至少三名股东`.
- 18s: both show `中国 ≠ 泰国` over the 出资节奏 line.
- 24s: A shows `银行开户 / 工作证 / 签证申请`. B is the speaker full frame. The caption is the same line on both.
- 32s: both show `法人代表 ≠ 董事权限`.

Render time was about 105s and 111s. That cost is Remotion, and only when `apply_safe` is asked to render. Shadow does not add a render.

MP4s and frames are local evidence. They are not in the commit.

## Tests

`73 passed`: `test_visual_quality_optimizer.py`, `test_director_v14.py`, `test_director_v15.py`, `test_semantic_motion_profile.py`, `test_director_evidence.py`, `test_scene_composer_v16.py`.

Covered: finding detection, provenance fields, ranking, shadow identity, invalid timeline, justified and unjustified reuse, missing feedback, sqlite store, dimension mismatch, language/audio keys left in place, malformed plan, no safe alternative, stale display shortened to evidence end + 1.2s.

## Production

Default remains `off`. Existing projects do not run the optimizer. Flags, production Postgres, RunPod, and strom-v2 were not touched.

Not production-ready to turn on. `apply_safe` is justified for this one timeline class and was checked on one 36s plan. It has not been run through a live Create Video click on a new upload, and there is no verified user-feedback corpus in the isolated database to rank treatments.

## Limitations

- Retrieval is unused until a caller supplies a 512-d vector and the existing memory flags are on. This task did not embed transcripts.
- `apply_safe` will not invent a plate, a step label, or a layout.
- Layout repetition is reported and not applied.
- A noun list that also contains an order cue can still become a timeline. `首先` is not a cue. `第N`, `first`, `then`, `next`, `step N`, and `шаг N` are.
