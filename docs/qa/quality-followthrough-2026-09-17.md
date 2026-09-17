# Quality review follow-through

Automatic low-quality revision drafts now snapshot structured feedback: render id, revisions, approved output timeline, legacy source ranges and score comparison. Every issue requires exactly one indexed bilingual planner response (`addressed` or `not_applied`). Missing, duplicate and out-of-range responses fail validation and participate in the existing bounded repair. Ordinary creative drafts require no quality responses; historical drafts remain readable.

The editor displays the original issue beside the proposed remedy or reason for leaving it unchanged, in EN/ZH. “Fix proposed” explicitly does not mean verified: the user still reviews and approves the edit, and a subsequent render/review is needed to judge improvement. Coverage validation cannot prove that an AI-authored fix is effective.

Validation: production frontend build passed; 31 isolated server tests passed including actual synthetic rendering, locked-shot preservation, feedback snapshots and coverage rejection cases. Local run passed 24 and failed the actual rendering case because local FFmpeg lacks the server's ASS capability; that same case passed on the server. No paid provider requests were run.

Headless Chrome fixture confirmed both EN and ZH issue text, response labels and reasons render from the API payload. This is not an authenticated production browser test. Deployed with backup `backups/quality-followthrough-20260917-115933`.
