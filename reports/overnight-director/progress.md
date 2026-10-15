# Overnight director progress

Branch: `experiment/overnight-director-quality`
Base: `216913e7ec29ba5ff9d19cc6bfa7ac7b2e344d5c`
Host: local Mac, 10 CPU, 24 GB RAM. No production deploy. V14–V18 flags left at default off.

## Phase

Renders and visual QA done. Implementation commit `289651b`.

## Done

- `backend/director_evidence.py` drops labels the beat does not say, stamps 不是/而是 and 第N层 onto the overlapping scene, drops a repeated plate identity.
- `director_v11._concepts_for_scene` ignores concepts outside the beat. A template query with no local concept is cleared.
- `director_v3.run_job` calls the gate after V14–V18. Shadow JSON is written beside the plan and is not applied.
- Remotion `Beside` / `CleanSteps` no longer fall back to 目标/家庭/预算 or 全程陪同. Split and consult layouts require a staged plate.
- `backend/tests/test_director_evidence.py` plus `test_director_v11`, `test_director_v14`, `test_director_v8`, `test_director_v3`: 53 passed.
- Enhanced 60s: `output/overnight-director/fc451a1e-enhanced.mp4` SHA256 `7dd98a42d402512f5211f4d459d3808591c44232c0cc04f480bb0e41b5676b91`.
- original3 excerpt: `output/overnight-director/original3-short-proof.mp4` SHA256 `667f21a911472540213e4f22b8a3929c70895e0e9554ff04e6b548f405f5fa76`.
- Comparison sheet: `output/overnight-director/frames/comparison-sheet.jpg`.

## Remaining

- Layer labels stay for the whole beat, so a later line in the same beat can sit under an earlier label.
- Each single-label beat is painted as 步骤 1.
- The 60s picture is mostly the speaker. Selection is less wrong. Variety is lower.
- Do not deploy.
