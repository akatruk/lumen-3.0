# Track dynamics and output-aware soundtrack planning

Soundtrack proposals now receive measured two-second RMS levels across each selected track (up to 420 seconds), large rises/drops and quiet ranges. The listening reel samples opening/middle/ending plus loud, quiet and strong-change regions, bounded to six four-second excerpts per track. These measurements are not emotion, beat or musical-phrase classifiers.

The planner now receives the compiled approved output timeline, including remapped speech captions and reordered shots. It must use output timestamps for the gain curve, and source timestamps for music selection. Actual sampled ranges are saved with the immutable proposal snapshot for acceptance validation. Existing revision/lock checks remain in effect.

No extra AI request was added; the larger sample reel may increase input usage within the existing project budget. Selecting one track and manual acceptance remain required. This does not implement semantic musical phrase reconstruction or guarantee editorial fit.

Validation: 10 isolated server tests passed in 4.34 seconds, including real audio decode, soundtrack sample reel and music rendering. Later speech-remapping addition passed the local proposal/accept/lock regression. Frontend production build passed. No paid AI validation was run in this block; model choice quality remains to be assessed on representative footage.
