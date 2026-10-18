# AI video pipeline

Rendering entry remains `director_v3.run_job` and Remotion `DirectorV3Preview`. No Director V19 and no second composition engine.

```
upload
  -> transcribe job (worker client, Qwen children when ASR_MODEL is Qwen3-ASR)
  -> source-transcript.json
  -> optional semantic-plan.json (required only if SEMANTIC_PLANNER_REQUIRED=1)
  -> Director V3 expands scenes
  -> passage media gate (no-op without a valid semantic plan)
  -> later V11 passes can still rewrite queries; that gap is open
  -> evidence gate, then Remotion
```

`analysis_quality` for the default path stays `local_baseline`. A failed planner does not flip that to `llm`.

Finished MP4s stay under `renders/<render id>/`. Transcript edits invalidate the cached plan via `transcript_edit_version` and do not delete those files.

Caption language and dubbing are still one "Video language" control in `CreateVideo.tsx`. `resolve_voice` sets `dubbed` when the source locale and the target locale differ. Splitting those controls is not done.

## Component status

| Component | Implemented | Tested | Deployed | Verified |
| --- | --- | --- | --- | --- |
| Qwen client + isolated children in this repo | yes | unit only | host has an older copy, this diff is not deployed | no new job watched to completion |
| Canonical transcript + correction API | yes | unit | no | no browser pass |
| Fail-closed semantic planner | yes | unit | no | no model ran |
| NO_MATCH retrieval gate | yes | unit | no | no library search on a real project |
| Director V3 hook | yes | not an end-to-end render | no | no |
| Quality report | yes, plan JSON only | unit | no | no frames |
| Studio transcript panel | yes | not in a browser | no | no |
