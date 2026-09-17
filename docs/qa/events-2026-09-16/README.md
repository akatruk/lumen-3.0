# Event timelines

Added timeline visual cards with 2–5 bilingual milestones (date/stage and event), editable order, source attribution and clip-local display interval. Milestones are equally spaced, not a proportional date axis. Dates are editor-provided text, not parsed or independently verified. AI visual-card proposal prompt supports milestones and requires supplied factual evidence; approval is still required.

Existing number, comparison, bar-chart and ranking cards remain supported. Editor exposes timeline type, row addition/removal and move-up ordering. Card proposal preview displays each milestone. Dates/sources require human verification; no paid AI quality evaluation performed.

Validation: full isolated PostgreSQL suite initially 105 passed and one failed pixel test (thin line blurred by compression). Increased line width; both milestone tests then passed including real FFmpeg render. Final preview inspected visually. Frontend build index-ChSTqLLD.js passed. Live paid AI quality and interactive browser UI not tested.

Deployed with no active jobs; backup /opt/lumen-rebuild/backups/events-20260916-093413. Web and worker active after deployment. Old VM and excluded pg servers untouched.
