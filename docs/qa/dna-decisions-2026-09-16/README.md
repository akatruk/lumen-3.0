# DNA → executable decisions

Studio analysis now automatically queues the complete creative decision pass after saving source analysis and reference DNA. No extra prompt or Generate button is needed for new analyses. The existing project budget still controls provider calls; no automatic approval or rendering is introduced.

Each generated clip has a matching decision: title, owned-footage observation, executable change, rationale and optional timed reference technique. A DNA-backed plan must cite at least one actual reference. Clip-index coverage, known reference IDs and reference bounds are validated before publication and acceptance. Original source speech timings remain canonical.

Main UI presents decisions and their reference evidence first; regeneration is a refinement control and legacy trim/loudness tools are collapsed. Existing saved proposals remain readable. New proposal jobs do not replace approved edits.

Local targeted tests: 28 passed. Frontend build succeeded (index-BdDe9BvV.js). Isolated PostgreSQL/FFmpeg run: 128 tests passed; the old full-flow fixture needed the newly automatic decision step. Updated full-flow test passed through decision generation, reference evidence, approval and real render/download. Subsequent response-limit checks: 22 passed.

Deployment backup: /opt/lumen-rebuild/backups/dna-decisions-20260916-110145. Public entry serves index-BdDe9BvV.js; services and health verified.

During deployment, an active long-reference analysis failed at the prior 12,000-token reference output ceiling (11,961 completion tokens, finish_reason length). Reference DNA now has the same 32,000-token allowance as Director plans and is prompted to keep shot fields concise. Saved failed project acb461c2fb3844fd9264a4751912c11b queued once for recovery. Existing cached-DNA project 837141609a5c42d5aa70644fe515b3e9 has ready decision proposal 2342eb7b9a1640dab1e4300812f5d255: 10 scene decisions, 2 explicitly linked to validated reference ranges. Several decisions retain the source; these must not be described as ten improvements. Examples include retaining the source action hook with a sound accent based on reference 0–4.4 seconds. The proposal is unapproved. No timeline automatically accepted.
