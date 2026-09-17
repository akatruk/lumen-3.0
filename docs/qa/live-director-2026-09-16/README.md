# Real-provider Director flow

Synthetic packing footage (30 seconds) and a synthetic reference (12 seconds) were processed in an isolated `lumen_qa` schema using the production analysis model. No customer footage or production project records were used.

The completed run passed: real reference DNA → real source analysis → real executable creative plan → explicit acceptance → shot approval → saved plan → actual render → real AI quality review. The output was 12 seconds / 3 shots. The quality score was 57.2/100, so the application retained `needs_review` and queued a quality-revision proposal. The review recommended music for the silent synthetic footage. No automatic approval or further paid revision execution occurred.

Settled provider charges in the passing run totaled $0.1327305: DNA $0.00780525, source planning $0.02457825, timeline planning $0.0911235 and quality review $0.0092235. Its project budget was $1. No repair call was needed. The full test passed in 111.66 seconds.

The first run also reached rendered output but failed a test assertion requiring `complete`; `needs_review` is a valid outcome. That assertion was corrected, and the passing rerun additionally verifies that the quality review was available. The first run's settled cost was not retained. This is functional integration evidence, not a claim that a synthetic pattern is a polished customer video.

`report.json` contains the passing run's proposal, resulting quality assessment, events and spend, with no API credentials.
