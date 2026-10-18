# Semantic planner

`HeuristicDirectorProvider` is still the Create Video planner when `LLM_PROVIDER=none`. It slices the timeline and copies transcript lines into caption fields. `source_brief.py` writes `localization/source-brief.json` with `kind=deterministic_baseline` and `notASemanticModel=true`. Questions and numerals are listed from the transcript text. That file is not an LLM plan and is not labeled `analysis_quality=llm`.

`backend/semantic_planner.py` validates a plan whose passages cite real segment ids. It rejects unknown ids, a `heuristic` planner tag, and a question intent whose quote is not a question. `require_model()` raises `PLANNER_UNAVAILABLE` when `SEMANTIC_PLANNER_COMMAND` is empty.

`SEMANTIC_PLANNER_REQUIRED` defaults off. If it is on and `localization/semantic-plan.json` is missing or invalid, `director_v3.run_job` raises `PLANNER_UNAVAILABLE` or `PLANNER_INVALID`. It does not call `HeuristicDirectorProvider` and report success.

No local instruct model was loaded. The host has no Ollama. `qwen2.5:7b-instruct` is the RunPod setting. A 7B weight was not measured here and is not placed in the 2800 MiB worker.

Measured constraint: Qwen3-ASR-1.7B bf16 already peaked near 5.9 GiB on this 7.8 GiB host. A text model has to be a different process, and only while ASR is not resident. No model size is approved until that measurement exists.

Status: schema and fail-closed gate are implemented and unit-tested. A real semantic plan was not produced. Not deployed. Not verified on a video.
