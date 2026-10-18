# Semantic motion in the real Create Video path

Date: 2026-10-16. Branch `experiment/semantic-motion-webstudio`. Not merged. Not deployed. Production `142.93.248.163` / `/opt/lumen-rebuild` was not touched. Global flags stayed at their defaults (`SEMANTIC_MOTION_V14_ENABLED`, `V15`, and `SEMANTIC_NUMERIC_RANGE_ENABLED` were `0` in the isolated worker).

Production readiness: **not ready to deploy.** The profile is off unless a generation selects it. One existing classifier still turns a spoken noun list into `motion.process_timeline.v1` (see original1 at 21–27.6s). That is a remaining selector limit, not a reason to turn the profile on for every project.

## Call graph

```
CreateVideo.tsx create()
  POST /api/studio/projects/{id}/create-video
    body.semantic_motion_profile = "evidence_gated_v1" | null
studio.create_video
  ensure_analysis → heuristic plan (LLM_PROVIDER=none)
  enqueue director_v3
    payload.semantic_motion_profile, transcript, language, source_language, dubbed
worker kind=director_v3
  director_v3.run_job
    enrich → v8 expand → v9 → v11 → v11.1 → v11.2 → v10
    if profile != evidence_gated_v1:
        apply_semantic_motion()          # no-op while V14 flag is 0
    v15, scene_composer_v16, motion_design_v18   # no-op while their flags are 0
    if profile == evidence_gated_v1:
        semantic_motion_profile.apply_profile
          with_segment_ids
          apply_semantic_motion(..., force=True)
          apply_numeric_range(..., force=True)
          apply_evidence_gate
          bind_graphic_lifecycle
    else:
        apply_numeric_range()            # no-op while the range flag is 0
        apply_evidence_gate
    resolve_scene_plan → attach_transcript_captions → store_render_plan
    render_with_plan (DirectorV3Preview)
```

`force=True` does not set the process environment flags.

## Where the proofs diverged

The earlier proof script set `SEMANTIC_NUMERIC_RANGE_ENABLED=1` for original2 and called the gate directly. Create Video never sent a profile, so `apply_numeric_range` and `apply_semantic_motion` returned the plan unchanged. The evidence gate can still mount `motion.process_timeline.v1` for a 第N层 cluster without the V14 flag. That is why the list proof drew a timeline and a normal Create Video click did not draw a range.

A second gap: the heuristic `Caption` model has no id, and `as_ranged_rows` dropped the id stored in `source-transcript.json`. The lifecycle then rejected the timeline as `missing_source_segment_ids` after the audit had already accepted it. The first original3 job (`gen_257427650`, render `27b56890cc564e90b5edd3d509c9b9ef`) shows that: audit accepted `motion.process_timeline.v1`, `semanticMotionV14` on the scene was null, the MP4 has no list. The fix restores `segment_001…` in order (the same ids `save_verified` writes) and keeps a row id that is already present.

## What changed

| Function | Change |
|---|---|
| `semantic_motion_profile.apply_profile` | Per-job opt-in. Calls the existing classifiers with `force=True`, then the evidence gate, then the lifecycle. |
| `semantic_motion_profile.bind_graphic_lifecycle` | Drops a graphic with no source time, no segment ids, no display interval, a display that starts >0.35s before the evidence or ends >1.5s after it, an ungrounded range, a forged 泰铢, or a timeline left with fewer than two real labels. Clears unit `泰国` / `泰诸` and records `unitOmitted=asr_unit_unverified`. One rejection does not fail the plan. Reasons go to `semanticMotionRejections`. |
| `semantic_motion_profile.with_segment_ids` | Fills missing caption ids as `segment_001…`. |
| `source_transcript.as_ranged_rows` | Keeps the verified segment id. |
| `semantic_numeric_range.apply_numeric_range` | `force=False` by default. |
| `director_v14.contrast_sides` | `强调 X … 更看重(的是) Y` wins over the 中国/泰国 party pair. |
| `director_v3.run_job` | Profile branch. Result records `semanticMotionProfile`. |
| `studio.create_video` / editing-controls | Optional `semantic_motion_profile`. Any other name is 422. Stored on the project and copied onto the job. |
| `CreateVideo.tsx` | Checkbox “Visual intelligence: evidence-gated motion (experimental)”. Persists through editing-controls and is sent on Create Video. |
| `remotion_engine.resolve_scene_plan` | Copies `semanticMotionProfile`, `semanticMotionRejections`, and `semanticEventAudit`. Duration stays a float so a 36.4s source is not truncated to 36. |

V15–V18 are not called from `apply_profile` and their flags were not set.

## Profile

`evidence_gated_v1` only. Existing projects stay on the old path until the checkbox is on. The value is on the studio context (survived a reload of original3 before Create Video) and on the director job payload and the stored render plan.

## Browser acceptance

Isolated stack only: API `127.0.0.1:8018`, Vite `127.0.0.1:5178`, worker, sqlite `reports/semantic-motion-webstudio/isolated/lumen.db`. Account `motion-proof@example.com` created through the register form. Invite `motion-gate-16`.

The file dialog cannot be driven from this browser. Each excerpt was posted to `POST /api/studio/projects` with the session cookie (source and reference are the same excerpt). Language, the experimental checkbox, duration, and Create Video were clicked in the browser. Create Video then ran the normal queued `director_v3` job. No plan JSON was injected. No proof renderer.

Studio rejects a source shorter than 30s, so the excerpts are longer than the 15–30s preference. Timing is the source timing shifted by the cut, not a new edit.

Transcripts are the canonical ASR, clipped and shifted, written with `save_verified` (`faster-whisper-small`, checksum matched). faster-whisper on this machine still raises `metadata_errors`. There was no second listen. Uncertain tokens were not rewritten.

### TEST A — original3 layers

Project `bbfc523bb22c4c21b7075a6a3c76eade`. Excerpt `sources/original3-excerpt.mp4` from `data/original3/source` at 42.80s, container 34.033s. Language 中文, voice “Original speaker audio”, duration 34.033s, profile on.

Acceptance job: generation `gen_631280367`, render `1f206276c1cc44449f9d93b46dfa66bb`.

`motion.process_timeline.v1` steps: 使用场景, 家庭结构, 代价. Evidence 0–32.2s, display 0–33.432s (the existing 1.2s last-step hold). Segment ids `segment_001`–`segment_018`. No 步骤 labels.

Frames (`frames/original3/`):

- 4.0s caption 第一层叫使用场景, only 使用场景 is lit.
- 16.0s caption 真实居住的路线, still only 使用场景 (家庭结构 has not been said; that line is 16.52s).
- 17.6s caption 第二层叫家庭结构, 家庭结构 is lit.
- 31.0s caption 第三层叫代价, 代价 is lit, the earlier labels are dim.
- 33.6s caption 这里不只是申请费, the list is gone.

SHA256 player and download: `1fc9ad5b2c50b396b990f144c63e79c6af00310bb1936f4f56e18988e8e03f65`.

### TEST B — original2 range

Project `14dd4a24d3f043e595395cd7dc02f55a`. Excerpt from 15.46s, 33.0s. Generation `gen_856109875`, render `24c3a69d819c46e197deb2f5ceffed64`.

Selected through the job, flags still 0:

| Quote | Display | What is drawn | What is omitted |
|---|---|---|---|
| 月薪差不多在1.5-2.5万泰国左右吧 | 0–5.2 | 1.5万–2.5万, 月薪 | unit 泰国 (`asr_unit_unverified`). Not rewritten to 泰铢 |
| 折合人民币三四千 | 5.2–7.2 | 3千–4千 人民币 | — |
| 那月薪普通是2.5-3.5万泰诸 | 12.2–16.8 | 2.5万–3.5万, 月薪 | unit 泰诸 |
| 优秀的甚至能拿到4-5万泰诸 | 16.8–20.0 | 4万–5万 | unit 泰诸. Period not invented |
| 也就是8000-1万块的人民币 | 20.0–23.4 | 8000–1万 人民币 | — |
| 那大概在400-1200人民币每天 | 28.6–33.0 | 400–1200 人民币, 每天 | — |

Frames at 2s, 6s, and 30s match those rows. The caption still prints the ASR line, including 泰国, because the caption is the transcript. The graphic does not treat 泰国 as a currency.

SHA256 player and download: `9dd6acb83edc44372226faef6f58a035d5acad00aa78d3b3c4352d5ff87d3f14`.

### TEST C — original1 contrast

Project `aa292ac6830c49afa4cf7c2f4f72f6da`. Excerpt from 19.46s, 36.4s. Generation `gen_289082071`, render `a4b55b5983b244eeb0d245c6e73ced6d`.

| Window | Component | Labels |
|---|---|---|
| 0–3.2 | business_comparison | 钱 ≠ 股东结构 |
| 3.2–6.6 | shareholder_network | 至少三名股东. Not a numeric range |
| 6.6–9.4 | ownership_split | 不超过49% |
| 9.8–15.0 | business_comparison | 控制权 ≠ 金额 |
| 15.0–21.0 | business_comparison | 中国 ≠ 泰国 (出资节奏 sentence) |
| 21.0–27.6 | process_timeline | 银行开户, 工作证, 签证申请 |
| 27.6–36.0 | business_comparison | 法人代表 ≠ 董事权限 |

Frame at 18s: 中国 ≠ 泰国, caption is the 出资节奏 line. Frame at 32s: 法人代表 ≠ 董事权限, caption is the 董事 sentence. 中国 ≠ 泰国 is not on that frame. Display end of the country graphic is 21.0s, which is the evidence end.

The 21–27.6s timeline is words cut out of one sentence. They are in the quote. They are not 第N层 and they are not numbered 步骤. The existing step extractor still promotes that list. It does not carry the previous contrast.

SHA256 player and download: `853d834fe596872a0df1cb19004e231f71d84e0aa33f5da4c6c5a41513b08906`.

## Counts

| | A original3 | B original2 | C original1 |
|---|---|---|---|
| Selected components that rendered | 1 timeline | 6 ranges | 4 comparisons, 1 network, 1 split, 1 timeline |
| Unsupported currency substitutions | 0 | 0 (泰国/泰诸 omitted) | 0 |
| Cross-scene leakage of a finished contrast | 0 (list gone by 33.6s) | 0 (each range ends with its line) | 0 (中国 ≠ 泰国 gone before 法人代表) |
| Graphic past evidence by more than the 1.2s hold | 0 | 0 | 0 |
| Invented 步骤 labels | 0 | 0 | 0 |

The original1 noun-list timeline is a selector miss, counted separately from leakage.

## Audio

Same language, so `dubbed` is false and the job did not call a GPU voice. Output audio is AAC 48 kHz stereo. The source excerpts are AAC 44.1 kHz. On original3, mono 16 kHz correlation against the source over 20s is 0.632 after a 43ms alignment. That is the same speech after resample and re-encode, not a replacement dub. It is not a waveform measurement of 300ms caption accuracy.

## 409

`backend/tests/test_director_revisions.py`: `test_propose_accept_and_preserve`, `test_failure_and_locked`, `test_preserves_other_approved_decisions_and_rejects_stale` fail. The first assertion is line 20, `409 == 202`, on `POST /api/studio/projects/{id}/alternatives`. The body is `{"detail":"studio_surface_disabled"}` from `_RETIRED_SURFACE` in `backend/app.py` (the middleware returns 409 before the handler). That middleware is in HEAD and in production base `216913e`. These failures are pre-existing. Assertions were not changed. `backend/app.py` was not edited.

## Tests

`pytest` on `test_semantic_motion_profile.py`, `test_director_v14.py`, `test_semantic_numeric_range.py`, `test_director_evidence.py`, `test_source_transcript.py`, `test_remotion_engine.py`: 64 passed. Coverage includes profile on/off, studio captions without ids, 至少三名股东 not a range, 第一层 labels kept, forged 泰铢 rejected, contrast ending at its sentence, and the editing-controls round trip.

## Limits

- The noun-list timeline on original1 is still selected by the existing step extractor.
- Captions print the raw ASR line, so 泰国 remains in the caption while the graphic omits it.
- No waveform-locked 300ms claim.
- No Russian or English speech fixture was rendered. Unit tests cover a Russian `от…до` sentence and an English non-layer sentence only as “do not become a process timeline.”
- Upload used the studio endpoint, not the file dialog.
- The first original3 render is the failed id-less plan. It is not the acceptance file.
