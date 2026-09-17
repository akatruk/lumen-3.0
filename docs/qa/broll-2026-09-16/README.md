# Source B-roll cutaways

Implemented per-clip cutaway decisions: clip-local insertion start/end plus owned-source start. FFmpeg overlays that source interval while mapping only base clip audio. Titles/cards are applied after the cutaway; captions remain global. The compiled Director Timeline contains a separate cutaways track. Approval and lock protections apply to the enclosing clip. AI single-clip proposals may suggest cutaways grounded in the same owned source; all proposals remain unapproved until manually accepted and approved.

Frontend adds bilingual source selection and muted preview, with range validation and a separate track. Preview shows selected source footage; final render is authoritative for compositing. No external assets or synthetic B-roll generation are claimed for this feature.

Validation: production frontend build; local real-FFmpeg pixel and audio test; full isolated server suite 80 passed/2 skipped; PostgreSQL QA 16 passed. Synthetic red/blue source and 440/880 Hz audio prove picture replacement preserves 440 Hz base audio. Browser automation tools were unavailable for this turn; no interactive-browser QA claim. No paid provider requests.
