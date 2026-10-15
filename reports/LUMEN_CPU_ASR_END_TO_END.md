# CPU transcription and a new-upload video

## Root cause

A new upload had no verified transcript. The local `.venv` (Python 3.14.6, arm64) could not import NumPy, so `whisperx_local` failed and the product used to invent `[segment N]` captions. Those Latin placeholders were classified as English, the Chinese project was dubbed, and the worker reported `hypit_unavailable` because the GPU key was missing. The earlier original3 browser success used a restored transcript, not a fresh ASR run.

## What shipped

- `faster-whisper==1.2.1` and `ctranslate2==4.8.3` are pinned in `backend/requirements.txt`. NumPy stays `2.5.3`. CPU int8 only.
- Upload still returns `ready` immediately and queues one `transcribe` job on the existing worker. Same checksum + model + config does not start a second ASR.
- The transcript record stores project id, checksum, source language, model id, model version, config version, segments, timestamps, and status. Placeholder text is rejected. A different model archives the previous file instead of overwriting it.
- Create Video requires that transcript. Same language keeps `dubbed=false` and `voice=none`. A missing target voice is `MISSING_TARGET_LANGUAGE_VOICE`.
- Model files go to `ASR_MODEL_CACHE`, or `/mnt/volume_nyc1_1791446889637/lumen-asr` when that volume is mounted, otherwise `data/asr-models`.

Selected model: `Systran/faster-whisper-small`, device CPU, compute int8, beam 1, temperature 0, VAD on, config `cpu-int8-vad-1`. Package versions on the Mac run: faster-whisper 1.2.1, ctranslate2 4.8.3.

Medium on the same 20-second Chinese excerpt: load 21.244s, infer 8.124s, language `zh` probability 0.971. It wrote 药 where small wrote 要. Small infer on that excerpt was 3.777s. Small stays the default because the accepted original3 transcript is already small and the worker is shared with Remotion.

## Languages actually run

| Clip | Detection | Result |
| --- | --- | --- |
| original3, first 60s | `zh` 0.995 | 28 segments, first line 很多人第一次来咨询 先会问 |
| `onboarding-video/public/narration-en.wav` (10s repo narration) | `en` 0.990 | Upload your video. Let AI find the highlights. Choose your improvements. Preview and download your new cut. |
| `docs/ux/prototype/assets/russian.mp4`, first 20s | `ru` 0.960 | Сорваться и уехать не всегда легко, а вот нырнуть воду. |

`Hayek-Law-English.mp4` is Russian speech. It was not used as an English fixture.

## 60-second measurements (small, weights already on disk)

| Measure | Value |
| --- | --- |
| Model load | 0.753s |
| Infer | 6.217s |
| Transcription job wall | 7.53s |
| Peak RSS | 1014939648 bytes (`ru_maxrss` on macOS) |
| Second call, weights warm | load 0.613s, infer 6.339s |
| Upload HTTP to `ready` | 0.094s |
| Remotion job wall | 248.11s |

CPU percent during ASR was not sampled. Silence (4s) returned 0 segments and is rejected. A non-video file raises `TRANSCRIPTION_FAILED`.

## New-upload run

Isolated data dir `/tmp/lumen-asr-e2e-20261016`. No preloaded transcript. The file input cannot be driven from this browser, so the upload was `POST /api/studio/projects` (the form's endpoint) with `data/asr-models/tmp/zh-60.mp4`. The browser then opened the project, selected 中文, set 60.1s, and clicked Create video.

- Project `fc451a1e44834e73a28f7e02157e28dd`
- Upload status `ready`, `transcription_pending`, then `transcription_completed`, source language `zh-CN`
- Director job `89c29199445f4c5982c40de604b88ef3`: `dubbed=false`, `voice=null`, 28 real lines, no `[segment]`
- Render `94c1b71ac66247fbbc3c768f7e6d3351`
- File `/tmp/lumen-asr-e2e-20261016/fc451a1e44834e73a28f7e02157e28dd/renders/94c1b71ac66247fbbc3c768f7e6d3351/result.mp4`
- 1080×1920, H.264 + AAC, 60.160s, 26683851 bytes
- SHA256 `e21bf8dac04f4fa5ab1a07d044159ab9be389f2e77c22604e7dea6a335f3914b`
- Player: one video, `readyState` 4, duration 60.16, src `.../media/result?v=94c1b71ac66247fbbc3c768f7e6d3351`
- Download `GET /api/projects/fc451a1e44834e73a28f7e02157e28dd/media/result` returned the same SHA256. The in-page Download video link returned 200.

## Production

Host `lumen-fix` is `142.93.248.163`. App Python is 3.12.3. The venv already has faster-whisper 1.2.1, NumPy 2.5.3, and ctranslate2 4.8.2. Root disk has 4.8G free. The 100G volume has 79G free. `FAST_PROJECT_CREATION_ENABLED=1`, `LLM_PROVIDER=none`, `REMOTION_ENGINE_ENABLED=1`. Experience-memory and visual-intelligence flags are 0. Deployment of this commit is recorded below after the push.

## Limits

- One transcription at a time, on the same worker as Remotion.
- English coverage here is the repo narration clip, not a field recording.
- A live worker-kill and a forced timeout were not run. Restart requeues a transcription twice, then marks `transcription_failed` without failing the upload.
- Heuristic scene titles are still generic. Captions carry the speech.
