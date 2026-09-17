# Executable change disclosure

Creative plan listing derives an audit from the actual edit fields, including existing proposals. The audit reports source coverage removed (union of intervals, so overlaps cannot hide omissions), source order changes, captions/audio normalization and per-shot operations. Splitting contiguous source or relabeling shot_type does not count as a change. Position changes at 1x zoom do not count as visible reframing.

EN/ZH UI separates retained shots from executable operations and warns when the entire plan has no changes. Planning instructions now explicitly require claims to match executed operations and prefer a few justified changes over preservation labels. This is not a semantic quality score or a guarantee of better AI edits; there is no added AI call or forced decorative effect.

Validation: nine targeted audit/creative-plan tests passed, including API listing and ownership/approval flows. TypeScript/Vite build passed. Real render test excluded because rendering code was unchanged; no authenticated browser walkthrough or paid generation performed this turn.

Deployed to the new Lumen VM after checking zero queued/running jobs. Backup: backups/edit-audit-20260916-115019. Web and worker active; public health returned ok and production HTML references index-YV_a2Xfw.js.
