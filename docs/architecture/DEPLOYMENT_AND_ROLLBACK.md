# Deployment and rollback

The historical mixed-file deployment at 9116f15 is superseded by the semantic release described in docs/testing/SEMANTIC_RELEASE_2026-10-18.md. Do not infer a deployed runtime from DEPLOY_SHA.txt alone: compare the file hashes in DEPLOY_MANIFEST.json and verify that services started after those files and configuration were installed.

## Deploy

1. Build the frontend and run the current affected backend/motion/localization checks.
2. Use an isolated database and complete the current browser → job → Remotion → repeated render → reload → download lifecycle. Record where AI/ASR responses are fixtures.
3. Confirm no production job is queued or running. Back up code, environment and PostgreSQL before stopping services.
4. Deploy a Git revision, replacing the backend and renderer sources together. Preserve the existing mounted media library, project directories, model cache and service memory limits.
5. SEMANTIC_PLANNER_REQUIRED=1 selects the existing hosted OpenRouter semantic planner and fails closed. It does not start a local text model. Keep unrelated provider/feature flags unchanged.
6. Restart lumen-web, lumen-worker and lumen-asr only. Never restart ASR during recognition/alignment.
7. Verify health, service state, configuration, deployed hashes and the authenticated browser. Existing project rows and delivery files must remain unchanged.

## Rollback

Stop the three Lumen services, restore the previous backend, motion source/config, frontend build, auxiliary sources and environment from the pre-deployment backup, then restart the services. Restore deployment stamps together with the code. Database restore is not automatic: do not overwrite user data created after deployment. Keep media and model directories intact.

Never describe fixture acceptance as proof of live provider behavior or universal creative quality.
