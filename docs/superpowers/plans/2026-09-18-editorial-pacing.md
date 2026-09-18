# Improve AI editorial decisions

User selected AI editing quality as the next priority; broad customer-video acceptance is deferred. Scope: measure meaningful visual pacing, expose needless segmentation/repeated footage/continuous-source transitions, and give the existing planner concrete editorial context. No new paid model stage or automatic customer render.

- [x] Add deterministic diagnostics with tests for artificial splitting, genuine visual changes, repetitions and speech-safe long takes.
- [x] Feed diagnostics into creative planning and replace clip-count pacing claims with visual-run measurements while preserving existing response compatibility.
- [x] Show measured proposal diagnostics in review, distinguish warnings from quality scores, and explain that long complete speech can be intentional.
- [x] Run targeted tests, typecheck/build and locale checks; publish after validation using existing rollback procedure.

A visual run joins contiguous source ranges only when static framing and labels remain identical, there are no inserts/cards/SFX, and the join is a straight cut. Role labels do not count as visual changes. Animated shots are conservatively kept separate. Repeated-source duration is total selected duration minus interval-union duration. These measurements do not identify actual objects or prove story quality.
