# Project creation refactor

Date: 2026-10-12.

## Invariant

**PROJECT CREATION MUST NOT REQUIRE AI INFERENCE.**

Creating a project only establishes identity, source storage, basic media metadata, and `ready` state. Creative AI runs when the user presses **Create video**.

## Current pipeline (before)

```
UPLOAD → probe → INSERT status=queued → enqueue studio_analyze
  → OpenRouter (reference_dna + director_plan)
  → status=ready
  → Create video (requires plan)
```

Blocking costs: OpenRouter LLM calls, Douyin reference fetch, optional style-match, wait time before the workspace opens.

## New pipeline

```
UPLOAD → probe (+ checksum) → INSERT status=ready, stage=ready
  → workspace opens immediately
  → user sets language / voice / style
  → Create video
       → reuse cached source analysis if checksum+version match
       → else deferred analysis (local transcript + heuristic Director,
          or optional LLM provider if explicitly configured)
       → Hypit / Remotion render as today
```

Feature flag: `FAST_PROJECT_CREATION_ENABLED` (default **true**).

## OpenRouter

| Use | Role | After refactor |
| --- | --- | --- |
| `ai.json_call` director / DNA | LLM vision+JSON | **Not on create.** Optional at generation via `LLM_PROVIDER=openrouter` |
| `style_pictures` | image gen | Unchanged optional path; not required for create |
| Stock discovery | LLM queries | Unchanged; user-triggered |

Active production default: `LLM_PROVIDER=none` — no OpenRouter HTTP on create or deferred analysis.

Replacement for deferred transcript: local WhisperX CPU on the DO volume when available; otherwise silence-based placeholder captions (generation may be weak until ASR works).

Replacement for Director JSON: heuristic plan from transcript + duration (empty recommendations when no references). Full LLM Director remains behind the optional provider.

## Cache boundaries

**Source cache** (keyed by `source_checksum` + `analysis_version`): metadata, transcript, source-language hint, semantic segments / Director plan.

**Generation cache**: visual plan, voice, captions locale, Remotion/Hypit outputs — invalidated by language/style/voice changes, not by re-opening the project.

## Rollback

Set `FAST_PROJECT_CREATION_ENABLED=0` and `LLM_PROVIDER=openrouter` with a funded key to restore enqueue-on-create + OpenRouter analyze.

## Migration

Existing projects keep rows and plans. No destructive delete of historical analysis.
