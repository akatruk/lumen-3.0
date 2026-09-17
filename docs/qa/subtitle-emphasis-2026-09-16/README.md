# Subtitle emphasis

Caption schema now accepts optional emphasis_en/emphasis_zh lists (up to 8 phrases, 48 characters each). Defaults preserve existing subtitles. Manual editor exposes language-specific phrases. New Director analyses are prompted to propose up to three exact, meaningful words/phrases without changing qualifiers or negations.

ASS renderer applies constant color tags after sanitizing caption text. English matching uses case-insensitive word boundaries; Chinese matching uses literal substrings. Phrase matching supports a line break inside a subtitle chunk. A phrase split across separate timed caption chunks is not highlighted across chunks. Yellow accents on white captions; cyan accents on yellow captions. Timing and content stay unchanged. This is static emphasis within each caption, not word-by-word karaoke timing or automatic resizing of numbers.

Tests cover word boundaries, phrases over line breaks, language isolation, ASS-injection sanitation and colored pixels in actual EN/ZH renders. Live AI suggestion quality and browser interaction not tested; no paid AI calls made.

Chinese rendered frame visually inspected: date in yellow, adjacent text remains white. Initial full-suite SSH stream stopped producing output after partial progress and the remote pytest process had exited; repeated with server-side log capture to obtain a complete, auditable result.

Full isolated PostgreSQL suite: 112 passed in 65.27 seconds; frontend build index-BxEbPpm2.js passed. Deployed with no active jobs; backup /opt/lumen-rebuild/backups/emphasis-20260916-095935. Web and worker active; old VM and excluded pg hosts untouched. This does not claim live AI quality validation or full subtitle motion typography.
