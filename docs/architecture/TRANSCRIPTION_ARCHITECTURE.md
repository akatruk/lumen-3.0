# Transcription architecture

Upload still calls `enqueue_transcription` in `backend/transcription.py`. The worker runs `persist_source_transcript`. The browser can close. The job is on `lumen-worker`, which only holds the socket client.

## When `ASR_MODEL` is `Qwen/Qwen3-ASR-1.7B`

```
source file
  -> lumen-asr Unix socket
  -> ffmpeg 16 kHz mono WAV
  -> child: asr_qwen/recognize.py (pinned snapshot 7278e1e70fe2, bf16 CPU)
  -> child: asr_qwen/align.py (pinned snapshot c7cbf2048c46, bf16 CPU)
  -> qwen3_segments.group_tokens
  -> localization/source-transcript.json
```

Language is detected by Qwen unless `explicit_user_source_language` is set. `projects.language` is the output language and is not passed as the ASR language.

Empty or near-silent audio (`peak < 200`) is stored with `status=silence`. It is not `verified`. Placeholder grids still raise `SOURCE_TRANSCRIPT_UNAVAILABLE`.

`get_transcript_provider()` does not call Whisper when the model id starts with `Qwen/Qwen3-ASR`. A dead socket raises `TRANSCRIPTION_PROVIDER_UNAVAILABLE`.

Before each child, `asr_memory.assert_can_load` refuses when `MemAvailable` is below 6200 MiB. A second `recognize.py` or `align.py` raises `TRANSCRIPTION_BUSY`. Those checks are in this checkout. The host service that was already running does not include the memory gate until this code is deployed.

## When `ASR_MODEL` is `small`

The previous faster-whisper int8 path remains. Tests and machines without the Qwen venv use it. It is not a fallback behind a Qwen configuration.

## Failure

The worker marks `metadata.transcription=transcription_failed` and stores `transcription_error`. Studio already renders that state. No segment text is invented.

`POST /api/studio/projects/{id}/transcription/retry` queues a new job only when there is no verified transcript. A verified file, including one with corrections, is kept.

## Not verified on a new project

The live host job `3c3a87ba…` was already running. This pass did not start another model process and did not read that project's transcript.
