# Final Hypit assembly prompt

Date: 2026-10-12

## What landed

`backend/assembly_prompt.txt` is now the user’s final editorial contract:

- Starts with `Create the finished video from the supplied original presenter footage…`
- `{{placeholders}}` for aspect, resolution, language, duration, graphics coverage/intensity, voice/caption/music, picture notes, source/speech refs, aligned transcript, staged asset manifest
- Face protection, phone captions, semantic beats, media-library use, graphics distribution across the full duration

Fill path: `prompt_modules.assemble.fill_assembly_template` → `assemble_hypit_prompt` → Studio create-video + `hypit_picture.render_picture` (`final_prompt.txt` + inject into `main.svml` `id="request"`).

## Supporting fixes

- Job `manual` now carries `width` / `height` / `aspect` / `duration` so re-assembly matches the stored prompt
- Aspect `original` resolves to a real ratio from frame size
- FFmpeg 9: `_picture_cut` uses `-filter_complex` (dropped `-filter_complex_script`)
- Render injects target `language` into prompt bindings when Edit omits it

## Verification

- Local + lumen-test: `44` tests in hypit_picture / presentation_graphics / language / prompt_modules — green
- lumen-test services restarted (`lumen-web`, `lumen-worker`)
- In-process smoke on droplet: `Graphics coverage: 40%`, `Graphics intensity: 55`, no leftover `{{…}}`, version `assembly:1b33b8bcc78e`

## Create Video proof (isolated)

| | |
|---|---|
| **Project** | `f1d2ee0a489245668cad19d7e7fa80e5` · title `original1-final-prompt-proof` (isolated copy of original1 source) |
| **Job** | `dcfc401664e5421bad9ec9e07f37f930` |
| **Render** | `0fe26d6eb0d94922a8aee09a2613e785` |
| **MP4** | `…/renders/0fe26d6…/result.mp4` · 1080×1920 · ~63.4s video + audio · sha256 `41979ae87eb032b18480793b25554cd93d9e5144cd431757ac8ebd1126f52a2f` |
| **Pod** | pinned `dznvwn90el5au4` resumed (no create) · SSH during run |

`final_prompt.txt` starts with **Create the finished video…**, fills `Graphics coverage: 60%`, voice/caption/music bindings, aligned EN transcript, and **STAGED LIBRARY FILES** with `./motion/N.mp4` (i2v_consult_001, re_inv_laptop, …). Empty gaps kept as host+speech.

Also stripped prompt-only keys (`duration`/`width`/`height`/`aspect`/`visual_energy`) before `Edit` validation in `worker.py` / `media.py` — Edit is Strict.

Prior `original1` DB row is gone; files under `32012faa…` unchanged. No silent overwrite of prior deliveries.
