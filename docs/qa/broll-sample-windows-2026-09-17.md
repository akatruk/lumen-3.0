# Coherent B-roll review windows

Visual library matching now uses up to five windows per candidate, up to four seconds each and never longer than the target scene. Short assets are divided into contiguous windows for complete coverage when they fit that bound; long assets are sampled evenly through the start, interior and ending. This removes the previous two-second ceiling on visually supported inserts. Music sampling retains its existing behavior.

The proposal stores its immutable sample ranges and exposes them in EN/ZH review UI. Validation still rejects ranges extending outside a single viewed window, unseen gaps and unrelated clip changes. Old proposals keep their original sampled bounds. No extra model call is introduced, but more input video can increase inference cost within the existing project budget.

Validation: frontend build and 12 local non-render tests passed. Coverage includes 0.1–420-second assets, short target scenes, complete short-asset coverage, bounded review duration, valid four-second inserts and unseen-gap rejection. Server additionally renders the labeled sample reel. No paid provider or customer-footage validation was performed; broader sampling does not guarantee editorial quality or exhaustive long-video inspection.
