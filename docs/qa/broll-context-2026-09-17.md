# Candidate footage identity and saved speech boundaries

Library B-roll sample reels now carry an explicit CANDIDATE SAMPLE REEL transport label. They previously carried ORIGINAL SOURCE VIDEO while the prompt separately contradicted that label. Both bounded repair branches preserve the role label. Existing callers retain the original default and quality review continues comparing the original source with the finished render.

Single-clip proposals now protect speech boundaries from both the analyzed transcript and saved editor captions. A manually corrected or added speech span cannot be ignored when validating a changed source start/end. Existing boundary positions remain allowed; this does not retrospectively rewrite saved edits.

Validation: 37 local tests passed with the server-only ASS reel test excluded. No paid provider calls; payload/retry behavior was checked with mocked HTTP responses. Correct role labeling reduces ambiguity but does not prove semantic match quality for customer footage.

Server: 41 isolated PostgreSQL QA tests passed, including real sample-reel generation, review source routing and B-roll range/ownership validation.
