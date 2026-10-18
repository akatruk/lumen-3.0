# Overnight director quality recovery

Branch `experiment/overnight-director-quality` from `216913e7ec29ba5ff9d19cc6bfa7ac7b2e344d5c`.
Implementation commit `289651b1fca6ece8cecb9b36a17f3f6362b76136`. Nothing was merged or deployed. lumen-fix stays on `216913e`.

## 1. Which confirmed defects were fixed?

On the isolated 60s project `fc451a1e44834e73a28f7e02157e28dd` (source checksum prefix `f7a6fc43`, seed `448815100`, generation `gen_448815100`):

- Stock cards 目标 / 家庭 / 预算 and 全程陪同 / 方案 are gone from the sampled frames (1.5s, 6s, 12s, 21s, 30s, 37s).
- `people_door_001` is gone at 6s and 21s. The consult couple is gone at 30s.
- The contrast the speaker actually says is on screen at 12s: card `选国家` over `身份规划的第一步不是选国家`.
- Captions are the ASR lines, not the legacy pack (`计划搬迁吗`, `家庭与预算`, `咨询与方案`).

On the original3 excerpt (`cd5c9ab8b6e944babe80e109038be8bb`, source `data/original3/source` cut 42s–76s, file not modified):

- Frames show `使用场景`, `家庭结构`, and `代价` with the matching spoken line on the first two.
- The stock wall (`目标` / `迁往哪里`, `家庭` / `同行家人`, `预算` / `项目费用`, `期限` / `何时可以启动`) is absent after `conceptTriggers` is off.

## 2. Which functions changed?

- `backend/director_evidence.py`: `apply_evidence_gate`, spoken contrast and ordinal stamping, unsupported-claim drop, `drop_repeated_assets`.
- `backend/director_v3.py` `run_job`: calls the gate after V14–V18, then writes a shadow JSON that is not applied to the plan.
- `backend/director_v11.py`: `_concepts_for_scene` keeps hits that overlap the beat plus 1.5s. A template query with no local concept is cleared and the plate is dropped.
- `backend/director_v14.py`: Chinese `第N层` / traditional `層`, and `而是` followed by more words. `apply_semantic_motion` still returns immediately when `SEMANTIC_MOTION_V14_ENABLED` is off. This file also contains the previously uncommitted extractor helpers the gate calls (`adjacent_contrasts`, `ordinal_timeline_payloads`). They are on this branch because a clean checkout of `216913e` does not have them.
- `backend/director_quality_shadow.py` `diagnose`: findings only. `altersPlan` is false.
- `motion/src/preview/DirectorV3.tsx`: `Beside` and `CleanSteps` have no stock-pack fallback. The steps branch no longer mounts the legacy `Steps` wall. Consult and split layouts require a staged plate.
- V11 still writes the immigration pack. The web path strips it in the gate. Moving the gate inside `apply_semantic_intelligence` would break the origin1 pack tests, so it stays in `run_job`.

## 3. Which tests passed?

`pytest` on `test_director_evidence`, `test_director_v14`, `test_director_v11`, `test_director_v8`, `test_director_v3`: **53 passed**.

Also passed: `test_director_v11_1`, `test_director_v11_2`, `test_director_v9`, `test_director_media_rules` (19 passed in that combined run before the three revision failures below).

Covered by the new tests: unsupported 目标/家庭/预算, future `搬家` not becoming a doorway on the opener, 不是/而是 cards, `三口之家` is not three steps, an expense list is not a timeline, three 第N层 labels land on three scenes, repeated consult identity dropped, shadow does not mutate the plan.

## 4. Which tests failed?

`backend/tests/test_director_revisions.py`: 3 failed (`409` on propose/plan). `backend/app.py` is dirty from earlier work and is **not** in this commit. These failures were not bisected. Treat them as pre-existing against that dirty tree, not as a result of the evidence gate.

`test_studio.py::test_revision_lock_and_render_snapshot` was already failing because Remotion enqueues `director_v3`. It was not re-run tonight.

## 5. What happened to repeated B-roll?

`drop_repeated_assets` keeps the first plate identity (`people_consult_001` and `i2v_consult_001` share `consult`) and clears later copies. Scene-local concepts stop the 38s `搬家` hit from searching the opener as a doorway.

Sampled enhanced frames no longer show the door or the consult couple. The hook plan can still select `people_review_001` for a passport query. At 1.5s the layout is fullscreen speaker, so that plate is not visible. Speaker-only is preferred when the beat has no local concept.

## 6. What happened to unsupported cards?

A card title is kept only when it is a substring of that scene's quote. A non-empty explanation must also be in the quote or it is blanked. Steps with fewer than two labels are cleared unless `spokenStructure.evidence` is set, so one real `第N层` label survives and a stock pair does not.

The 60s file has one supported card (`选国家`). It does not have 目标, 家庭, 预算, 全程陪同, or 方案.

## 7. Did Chinese semantic coverage improve?

Yes, on the structures this speech actually uses.

- `不是 A 而是 B` across two segments becomes two cards on the scene that contains both sides. The 60s line `而是定义问题 你究竟想解决什么` now matches.
- `第一层叫 X` / `第二层叫 Y` / `第三层叫 Z` (simplified or traditional 層) lands on the scene whose window contains that line.
- `三口之家` is not a step. An expense list is not a timeline. The labels are not hardcoded to 使用场景 / 家庭结构 / 代价. Those three strings appear because the original3 transcript says them.

The 60s upload transcript only has a bare `第二层` and the third name is past the cut, so that file cannot draw a three-step timeline. That is the source, not a miss.

## 8. Which motion components rendered?

No V14–V18 component. Flags stayed off. `semanticMotion` was not enabled for either experimental render.

What did render:

- 60s: fullscreen speaker, plus one contrast card from `Beside`.
- original3 short: `CleanSteps` with the spoken layer name. Each beat has one label, so the chrome says `步骤 1` on every layer.

## 9. Did pgvector contribute anything useful?

No. It was not queried. There are no new verified ratings, and none were invented.

## 10. Is the new MP4 visibly better?

Selection is less wrong. The picture is not a richer edit.

Enhanced 60s is the same speaker, same audio, same 60s, with the stock cards and the repeated doorway/consult plates removed at the sampled times, and one card that the sentence supports. Most of the minute is a talking head. Variety went down because unsupported plates were removed and nothing true was put in their place.

The original3 short shows the three spoken layer names and the speaker. It is a proof of the labels, not a finished editorial treatment.

No subjective score.

## 11. What remains broken?

- A layer label stays for the whole beat. At 26s the short still says `代价` while the caption is `今天适合三口之家的方案`. The caption is spoken. The label is from earlier in that beat.
- `步骤 1` on a one-label beat is chrome, not a spoken step index.
- `long60` is still a fixed 10-beat template when duration is at least 45s. The gate only strips claims and foreign concepts.
- Fullscreen speaker still hides a plate the plan selected. That plate must not be counted as a visible use.
- V14–V18 remain off. Turning them on was out of scope.
- `test_director_revisions.py` still fails on the dirty tree.

## 12. Should these changes be deployed?

No. The 60s result is a talking head plus one supported card. The short proof is label-correct and still a single-step chrome on each beat. Ship only after a review of the two MP4s.

Rollback: do not deploy this branch. Production remains `216913e` with V14–V18 off, `FAST_PROJECT_CREATION_ENABLED=1`, `LLM_PROVIDER=none`.

## Outputs

| File | SHA256 | Duration | Bytes |
| --- | --- | --- | --- |
| `~/Downloads/lumen-fc451a1e.mp4` (baseline, not modified) | `e21bf8dac04f4fa5ab1a07d044159ab9be389f2e77c22604e7dea6a335f3914b` | 60s class | 26683851 |
| `output/overnight-director/fc451a1e-enhanced.mp4` | `7dd98a42d402512f5211f4d459d3808591c44232c0cc04f480bb0e41b5676b91` | 60.160s | 31737579 |
| `output/overnight-director/original3-short-proof.mp4` | `667f21a911472540213e4f22b8a3929c70895e0e9554ff04e6b548f405f5fa76` | 34.048s | 17709735 |
| `output/overnight-director/frames/comparison-sheet.jpg` | baseline left, enhanced right, at 6, 12, 21, 30, 37s | | |

Enhanced encode: wall 237.23s, parent max RSS 939278336 bytes. The short keeper encode finished in about 137s including the four frame extracts. Peak RSS was not captured for that process. An earlier short (about 898 MB RSS) still painted the stock wall and was overwritten.

Render budget used: 2 full encodes that produced a file (the relative-path encode was discarded; the absolute-path file is the keeper) and 3 shorts (stock wall, CleanSteps with concept overlay, final). Caps were 2 full and 6 short.

MP4s and frames are not in git.

## Quantitative notes

Baseline visible time, from `reports/AI_DIRECTOR_DECISION_AUDIT.md`: speaker 19.02s, B-roll 30.06s, text cards 11.02s, semantic motion 0s. Doorway repeat 16.03s, consult couple repeat 14.03s.

Enhanced durations were not re-measured as a timeline. Sampled frames are speaker except the `选国家` card around 12s. Do not read the loss of B-roll as a quality score. The removed plates were the unsupported ones.

Unsupported visible claims in the sampled enhanced frames: 0. Cross-scene doorway from the 38s `搬家` line: absent at 6s and 21s. Repeated door and consult couple: absent at those samples.
