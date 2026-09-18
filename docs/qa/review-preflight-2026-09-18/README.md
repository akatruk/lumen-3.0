# Review preflight fix

The footer disabled “Review and create version” for unapproved scenes and unsaved edits. Users could not reach the review that explained those blockers.

The review dialog now opens independently of render eligibility. It lists unapproved scenes with separate inspect and approve actions, exposes unsaved changes with an explicit save-and-refresh action, and displays validation/task/save errors in the dialog. Saved summary is hidden while changes are unsaved. Actual rendering still requires valid, approved, saved edits and a matching summary revision.

Verified with the mobile browser regression: unapproved scene → dialog → explicit approval → save → matching summary → explicit render request. No render before confirmation. Also covers summary failure/retry, stale revision, near-original warning, overflow. Workspace browser scenarios: studio, other project, legacy, processing, failure pass. Production rendering is not triggered by this verification.

Extended audit: 26/28 passed on first run. Save-failure assertion was updated to find the visible alert (the closed dialog also contains the error); retest passed. Playback timed out because WORKSPACE_MEDIA was omitted and the fixture serves HTTP 204; rerun with /tmp/lumen-qa-video.mp4 passed. Thus all 28 scenarios passed across initial run and targeted reruns.

Published frontend verified over public HTTPS: index SHA-256 e663f9df487bad1cf970be2495c3c52710ee801e096bd48db578457af405ec0d matches local build and server. Both production services active. No real project edits, approval changes, or renders performed.
