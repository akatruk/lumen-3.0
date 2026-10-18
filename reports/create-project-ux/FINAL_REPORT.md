# Create Project form

The studio create screen is now the video, the output language, and the name. References and the script sit in Advanced. Production was not deployed.

## Changed files

- `frontend/src/Studio.tsx` — the form
- `frontend/src/studioCreate.ts` — a file alone is enough; title comes from the filename
- `frontend/src/studio.css` — spacing and a full-width button under 600px
- `frontend/src/ru.ts` — the new sentences
- `frontend/src/CreateVideo.tsx` — output language falls back to `project.language`; an unknown source language is not shown as a dub
- `backend/studio.py` — `ru` accepted, empty script accepted, references optional, `video_language` stored as `ru-RU` / `en-US` / `zh-CN`
- `backend/tests/test_studio.py`
- `frontend/tests/studio-create.test.cjs`

No new endpoint. No schema change. Existing rows are not rewritten. Hidden defaults still go out: topic travel, audience “General audience”, tone “Calm, factual”, budget 5, rights confirmed, style match off.

## Tests

- `pytest backend/tests/test_studio.py`: 8 passed, 1 failed. `test_revision_lock_and_render_snapshot` looks for a queued `studio_render` and finds none. Create video returns 200 and waits while the transcription job is pending. That deferral is the fast-create path; this change did not add it.
- `node --test frontend/tests/studio-create.test.cjs`: 2 passed
- `tsc -b` in `frontend`: clean
- Browser results: `BROWSER_TEST_RESULTS.md`

## Limits

- Source language still arrives only after the worker transcribes. The form does not guess it. The shown default is the interface language, and it is visible.
- The local worker was not running, so the transcript stayed `transcription_pending`. Upload was not marked failed.
- Semantic motion, the optimizer, and layout ranking are not on this form.
- This branch sits on the experimental motion history. Do not deploy the branch. Production stays on `c717f86`. A later deploy, if you want it, is a cherry-pick of this commit onto that SHA, after you approve it.

## Git

Commit `16d965b010a50041134e179a0c07da20c3c14906` on `experiment/create-project-ux`. Not merged. Not pushed. Not deployed.
