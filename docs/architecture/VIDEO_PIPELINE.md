# Video pipeline

## CURRENT STATE (V5 cutover)

| Path | When | Engine |
| --- | --- | --- |
| **Director V4 + Remotion** | Default when `REMOTION_ENGINE_ENABLED=1` (default) · always for project «e» | `motion/` `DirectorV3Preview` via `director_v3` job |
| **Hypit legacy** | Explicit only when `REMOTION_ENGINE_ENABLED=0` (non-«e») | `assembly_prompt.txt` → GPU Hypit |
| Studio edit plan | All | `studio.state` + worker jobs |

```
upload → ffprobe metadata → status=ready (no LLM)
  → Create video
       → deferred transcript / Director plan
       → if should_use_remotion(pid):
            director_v3 job → resolve_scene_plan + enforce + transcript captions
            → Remotion MP4 (renderer=remotion)
         else:
            studio_render illustration → Hypit (renderer=hypit, explicit)
```

**No silent Hypit fallback** after a Remotion failure.

Invariant: **PROJECT CREATION MUST NOT REQUIRE AI INFERENCE** (`FAST_PROJECT_CREATION_ENABLED=1`).

## Delivery transparency

Every Remotion result records:

| Field | Values |
| --- | --- |
| `renderer` | `remotion` \| `hypit` |
| `directorMode` | `runpod_llm` \| `heuristic` \| … |
| `executionValidation` | `passed` \| `repaired` \| `failed` |
| `captionSource` | `source_transcript` \| `target_alignment` \| `unavailable` |

## Captions

`backend/caption_phrases.py` groups real transcript rows (EN 2–6 / RU 2–5 / ZH CJK spans).
Remotion prefers `visualPlan.captions`; caption-pack strings are legacy fallback only.

## Rollback

Set `REMOTION_ENGINE_ENABLED=0` on lumen-test → non-«e» Create Video returns to Hypit.
Project «e» stays Remotion.
