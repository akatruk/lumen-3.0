# Lumen V6 — Root Cause Analysis

**Reference:** `director-v5-e-preview-20s.mp4` / `output/director-v5/e-preview-20s.mp4`  
**Project:** `9a9c116d8e0d4f7f927e7f60cb926562` («e»)  
**Plan:** `data/…/remotion-plans/ordinary_9a9c116d_20s.json` (V5 stamp)

## Pipeline traced

```
source MP4
 → localization/source-transcript.json (real RU ASR on volume)
 → [V5 broke here] local source.transcript.json overwritten with EN placeholder
 → caption_phrases (locale=ru-RU but fields all English)
 → Remotion captions = English
 → criteriaCardsFor(ru-RU) = Russian cards
 → DirectorV3 MP4
```

## Defect → stage

| Observed defect | Root stage | Evidence |
| --- | --- | --- |
| EN captions + RU cards | **Transcript sidecar + caption field fallback** | V5 `source.transcript.json` had identical English in `en`/`ru`/`original`. `caption_phrases._row_text` previously fell back to `en` under `ru-RU`. Cards always from `criteriaCardsFor(locale)`. |
| Transcript fragments as “info” | **Caption grouping** | EN sentences sliced into crumbs (“and the”, “language of China”). RU long clauses similarly over-split. |
| Repetitive split / PIP | **visual_variation SCENES + SPEAKER pools** | Fixed 6-beat template; `broll` only `speaker_with_media`; weak consecutive-layout avoidance. |
| Weak hook | **Hook scene + empty execution.headline** | Hook was medium/fullscreen speaker only; no kinetic speech headline. |
| Similar dark media | **Library query diversity** | Queries not speech-driven; same consult/review plates recur. |
| Little meaningful motion | **Director treatments + concept stacking** | Treatments existed but enrichment did not force variety; concept overlays duplicated caption meaning. |
| Tiny PIP risk | Mitigated by V4 floor (360×480) — still used when framing=`pip` | V4 intact; V6 prefers split/fullscreen when consecutive PIP. |
| Audio “maybe no music” | **Remotion bed present but low** | `bed.mp3` mounted at ~0.26 volume; AAC stream exists — ear-check still required. |

## Authoritative source of truth (corrected)

| Concern | Authority |
| --- | --- |
| Speech text | Real transcript (`localization/source-transcript.json` / ASR) |
| Viewer locale | `project.language` / Create Video language |
| Captions | Transcript phrases matching locale script |
| Cards / headlines | Director semantics from speech (complete ideas), not caption crumbs |
| Composition | Remotion + V4 execution |

## V5 misdiagnosis note

Prior Hypit MP4 defects ≠ Remotion layout bugs. V5 Remotion path worked mechanically; editorial/locale quality failed at transcript + Director enrichment.
