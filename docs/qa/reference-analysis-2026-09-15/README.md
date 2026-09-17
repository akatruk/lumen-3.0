# Reference analysis recovery

Two historical failures reported provider_invalid_analysis during reference_dna. Historical payloads were not retained, so their exact schema violation cannot be reconstructed.

One user-approved diagnostic call succeeded: finish_reason=stop, 13 valid DNA shots, 6901 completion tokens, $0.03766425. No truncation or schema violation in this call. Its validated result was cached for the existing project after checking source duration, reference identity and absence of active jobs. No extra API call was used to cache it. The project still awaits Retry analysis for owned-footage planning; end-to-end planning has not been verified in this recovery.

Removed conflicting inherited editing-system instructions from the reference-only phase. Reference requests now receive a dedicated observation/DNA system prompt; strict schema and range validation remain. Earlier safe diagnostics distinguish truncation from invalid schema without storing source content in event logs.

Validation: 12 AI-contract/studio tests passed, including reference system isolation and safe schema/truncation diagnostics. Only backend ai.py and studio.py deployed in this release, with rollback backup and idle worker restart.
