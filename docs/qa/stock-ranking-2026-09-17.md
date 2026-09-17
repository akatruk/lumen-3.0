# Scene-grounded external B-roll ranking

Discovery now collects up to 24 eligible Commons candidates across up to three searches, then asks a second AI stage to assess each against the saved scene, transcript and purpose. Exact candidate-id coverage is validated. Rejected or below-60 relevance matches are excluded; up to 12 remaining candidates are ordered by score, each with bilingual reasoning and illustration/specific-subject classification. This score is metadata relevance, not visual verification, authenticity or production quality.

If ranking fails (including insufficient budget), retrieved candidates remain available with an explicit unranked warning. No search silently modifies the saved edit. Existing ownership, revision, lock, licensed-import and manual-placement controls remain.

Validation: frontend build and 12 local tests passed. Isolated server regression covers discovery, ranking and imports. Tests exercise exact ids, duplicate/unknown/missing ids, rejection, sorting, reasons, budget failure fallback, all-rejected results and preservation of the current edit. AI outputs and Commons responses are fixtures; this change has not had a new paid editorial-quality evaluation. The optional live test now requires ranking completion and has a $2 project ceiling.

Two AI stages, each with at most one repair; each request reserves $0.50 under the existing project budget mechanism. User-visible copy explains this. Full candidate video inspection and automatic placement remain separate review steps.
