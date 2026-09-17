# Platform duration controls — 2026-09-17

Per-platform editorial output limits are now exposed in English and Chinese. AI planning validates complete-scene selections against these limits before rendering. YouTube Shorts additionally requires square/portrait output and at most 180 seconds. Other ceilings are user editorial choices, not asserted platform policies.

Completed invalid platform-planning responses receive at most one budget-checked repair. Ambiguous HTTP/provider failures are not automatically replayed. Manual range edits can override the initial editorial target, while the hard Shorts restrictions remain enforced. Existing packages remain accessible.

Validation: 25 isolated server tests passed in 30.97 seconds across AI contracts, platform packaging and revisions, including real rendering. A subsequent local AI-contract run passed 16 tests, including an additional parametrized check that platform semantic validation runs on both attempts and cannot be bypassed.

Deployed backend ai.py/variants.py and frontend build index-DOs3eKl5.js. Deployment checks for active jobs before and after pausing web requests; retains a backup and existing assets.

Official Shorts reference: https://support.google.com/youtube/answer/15424877?hl=en

Limits: this does not establish policy eligibility for music rights or publishing, and does not guarantee editorial quality. An indivisible sentence/scene longer than the requested target may require a larger target or manual review.
