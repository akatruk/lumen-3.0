# Canonical transcript

File: `data/<project>/localization/source-transcript.json`. Schema id remains `transcriptVersion=source-transcript-1` so existing readers keep working. An integer `version` counts edits.

| Requested field | Stored as |
| --- | --- |
| transcript id | `projectId` + `version` |
| project id | `projectId` |
| source checksum | `sourceChecksum` |
| source language | `sourceLanguage`, `languageStatus`, `detectedLanguage` |
| ASR model | `modelId`, `modelVersion` |
| alignment model | `alignment.model`, `alignmentModel` |
| model config | `configVersion`, `provenance` |
| raw recognition | `rawText`, `rawSegments` |
| corrected text | `segments` (current), `corrections` (history) |
| segment ids | `segment_001` … |
| word or character times | `segments[].words` from the aligner |
| validation | `status` / `validationStatus` (`verified` or `silence`) |
| review | `reviewStatus` (`unreviewed` or `corrected`) |
| version | `version` |
| times | `createdAt`, `updatedAt` |

`load_verified` rejects a missing checksum, a placeholder grid, a bad time order, an unverified status, and a model id that does not match `ASR_MODEL`. Corrections pin the file so a retry does not overwrite them.

`PUT /api/studio/projects/{id}/source-transcript` calls `apply_correction`. Raw segments stay. `version` increments. Project metadata `transcript_edit_version` changes, so `_cache_valid` refuses the old plan. The route does not touch `renders/`.

The Studio project page includes `TranscriptPanel`: list, seek, save, retry. That component was not exercised in a browser in this pass.

original1's placeholder file and English plan were not modified. original4's Whisper file was not modified. A future job with `ASR_MODEL=Qwen/Qwen3-ASR-1.7B` will not treat the Whisper file as a cache hit, because `cache_matches_model` compares model ids. That reprocess has not been run.
