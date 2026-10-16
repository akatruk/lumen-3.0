# Create Project field inventory

Surface: `#studio`, `StudioCreate` in `frontend/src/Studio.tsx`. Endpoint stays `POST /api/studio/projects` (multipart `config` + `file`). Production was signed out, so the inventory is the local form that matches that component, not a guess from an older modal. The library `UploadModal` in `main.tsx` is not opened by any button.

## Before

| Field | Type | Default | Required | Backend | Later? |
| --- | --- | --- | --- | --- | --- |
| Douyin search | text + two selects | Most liked, any time | A reference was required to enable Create | `references[]` of result ids | Yes, analysis can run with none |
| Selected references | list, max 5 | empty | At least one, or the button stayed disabled | same | Yes |
| Video | file, mp4/mov/webm | none | Yes | `file` | No |
| Project name | text, 120 | trend handoff title, else empty | HTML required | `title` min 1 | Yes |
| Script | textarea, 6000 | trend handoff script, else empty | HTML required | `script` min 1 | Yes |
| Output language | not shown | UI language via `contentLanguage`: zh if the UI is Chinese, otherwise English. Russian UI still sent `en` | Hidden | `language` was only `en` or `zh` | Yes, on Create video |
| Creator topic, audience, tone, rules | not shown | travel, General audience, Calm factual, empty rules | Sent anyway | `creator` | Not on this form |
| Budget | not shown | 5 | Sent | `budget` | Not on this form |
| Rights | not shown | true | Sent | `owned_rights_confirmed` | Not on this form |
| Style match | not shown | false | Sent | `style_match` | Not on this form |
| Platform badges | decoration | Douyin, Reels, Shorts | No | Server always stores the five platform ids | No |

Validation that stayed on the server: vertical video, 30s–7min, 250MB, real media via ffprobe, checksum, fast create (`status=ready`) plus a background `transcribe` job. No synchronous ASR in the upload.

## Classification

| Field | Class | Why |
| --- | --- | --- |
| Video | KEEP_VISIBLE | The only thing the user came to do. Formats and the 250MB check stay. |
| Output language | KEEP_VISIBLE | It chooses captions, cards, and whether speech is dubbed. It was hidden and could not be Russian. Users can understand Русский / English / 中文. |
| Project name | KEEP_VISIBLE | People look for the file later. The filename is a safe default, so the field is not required when that default exists. |
| Script | MOVE_TO_ADVANCED | Useful for facts that must survive, not required to store a project. Empty script is now allowed. |
| Douyin references | MOVE_TO_ADVANCED | They teach pacing. Fast create does not need them. The search still works inside Advanced. |
| Creator, budget, rights, style match | REMOVE_FROM_UI | They were already invisible. The same stored defaults are still sent. No new controls. |
| Platform badges | REMOVE_FROM_UI | They were not settings. The server still records the platforms. |
| AI Director version, semantic motion, optimizer, ranking, ASR provider, CPU/GPU, media library | not on this form | Not invented here. Semantic motion stays on Create video, where it already was, and stays opt-in. |

Source language is not a field. It is written later to `metadata.source_language` by the transcription job. That write does not change `projects.language` or `context.video_language`.
