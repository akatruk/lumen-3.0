# Before and after

The production site at `https://lumen-fix.universalgravity.org/#studio` stops on the sign-in wall. The before and after below are the same local Studio account (`ux-proof@example.com`) on `http://127.0.0.1:5178/#studio`. Isolated sqlite: `/tmp/lumen-create-ux`. Production was not changed.

## Before

One screen, top to bottom:

- Headline “Learn the technique. Tell your story.”
- Douyin, Instagram Reels, YouTube Shorts badges
- Douyin search (keyword, sort, date) marked as step 1
- “Your references 0/5”, and the create button disabled until a reference existed
- Step 2: file, required project name, required script
- Button “Analyze & build my plan”
- No output-language control. Russian interface language still created an English project.

## After

Screenshot: `after-desktop.png`. Phone width 390: `after-mobile.png`.

- Headline “New project”
- Video file, output language (Русский / English / 中文), project name
- Advanced is closed. Inside it: the same Douyin search, the reference list, and an optional script
- Button “Create project”, enabled once a file is chosen
- Name fills from the filename. A 130-character stem is cut to 120. `咨询-Обзор.mp4` stayed `咨询-Обзор`

Primary visible controls: file, language, name, Advanced, Create. Mandatory empty decision: the file. Language starts as the interface language (English, 中文, or Русский), shown in the select, because source detection is not available during upload.

## What the server still does

Same upload, same project id, same checksum, same fast create, same background transcription. `language=ru` is stored as `ru` and as `context.video_language=ru-RU`, so Create video opens on Русский instead of falling through to English. A missing source language does not label the job as a dub; the voice line stays “Original speaker audio” until speech is actually identified.
