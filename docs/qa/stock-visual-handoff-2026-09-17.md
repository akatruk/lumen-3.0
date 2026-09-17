# Search-to-visual-review handoff

Imported search candidates now have a direct action to prepare visual B-roll matching for the selected saved scene. A second action compares up to three imported candidates in search-result order. The existing AI review panel opens with assets and scene-specific instructions preselected. The producer starts the request, previews the proposed sampled interval, applies it and approves separately. The existing server continues to enforce ownership, revision, locks and sampled-time bounds.

Changing scenes clears candidate selections and instructions; an already-consumed handoff does not replay on returning to a scene. Locked/dirty/busy scenes cannot initiate this handoff.

Validation: production TypeScript/Vite build passed. Headless Chrome fixture verified the review panel opens, selects the imported asset and submits library_broll with the correct scene/revision. Requests were mocked; no paid calls, customer data or authenticated production E2E run. This connects the existing bounded sample-review capability; it does not inspect every frame or add autonomous importing/approval.
