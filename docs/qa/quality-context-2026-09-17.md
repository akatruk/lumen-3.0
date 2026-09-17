# Final-render quality review context

The quality reviewer previously inherited the initial-analysis system prompt (including requests for source timestamps, transcripts and recommendations), and received manual edit source ranges without a compiled output mapping. This made the instruction contract ambiguous after scene reordering.

Changes:
- Dedicated final-render review system: output timestamps, original-source comparison, evidence-based defects, intentional inserts and music, locked-decision handling.
- Manual review context uses the same approved output timeline compiler as the editor, including music, inserts, caption mappings and cutaways. Unapproved clips are omitted.
- Legacy recommendation ranges are explicitly labelled source-time ranges.
- Evaluator rubric version advances to editorial-five-v2; historical v1 scores are not directly compared with v2.

Verification: 29 targeted local tests passed. 33 server tests passed against isolated schemas in lumen_qa, covering context contracts, provider contracts, score comparison, worker defaults and quality revision integration. No paid AI calls were made. Tests establish deterministic plumbing, not subjective review accuracy. Actual final video and original source remain supplied to the reviewer; metadata is not accepted as proof of rendering success.
