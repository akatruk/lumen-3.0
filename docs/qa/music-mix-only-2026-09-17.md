# Improve the current soundtrack mix

Adds a mix-only music proposal mode. The server selects the currently saved track, preserves its asset id and source offset, and allows gain, output-time volume points, ducking and fades to change. Track/offset changes are rejected during generation and acceptance. Locked music, stale revisions, foreign assets and concurrent jobs retain existing protections. The chosen offset is added to the listening samples when not already covered. Applying a proposal changes only music and preserves footage edits.

EN/ZH UI offers soundtrack selection or improving the current mix. The latter requires saved music, and the proposal still needs explicit application. No extra model call is introduced.

Validation: production frontend build and local API/validation tests passed. Tests cover saved-track selection, hearing the current offset, no mutation before acceptance, acceptance preserving clips and track alignment, and rejection of changed asset/offset. Provider responses are mocked; this is not a new paid listening-quality evaluation.
