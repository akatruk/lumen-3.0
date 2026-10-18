# Repository cleanup — 2026-10-18

All local branch tips were already included in main at 94a5870. Dirty older working copies were not evidence of additional unmerged branches.

Recovery snapshots: `/Users/akatruk_macbook/Documents/github/.lumen-recovery/20261018-194716`. They include each checkout HEAD, status, binary diff and source archive before alignment. Existing media, model data and generated outputs remain on disk.

53 untracked source files in the primary checkout matched main byte for byte. The older Qwen service omitted the memory guard already present in main; the older EditorialProof had an unused variable. Main versions take precedence.

Remaining source scripts, recipes, metadata and documentation are added by this cleanup. Generated caches, library outputs, render outputs and local acceptance reports are excluded from new Git additions. No generator, provider, production deployment or service restart is run. This cleanup does not resolve the 97 full-suite failures recorded in MAIN_CONSOLIDATION_2026-10-18.md.

## Retained source additions

- `3d-library-v2/metadata/l3d_v2_folder_folder_open.json`
- `3d-library-v2/metadata/l3d_v2_passport_passport_open.json`
- `3d-library-v2/metadata/l3d_v2_suitcase_suitcase_roll.json`
- `3d-library/metadata/l3d_apartment_building_camera_push.json`
- `3d-library/metadata/l3d_apartment_building_depth_entrance.json`
- `3d-library/metadata/l3d_apartment_building_reveal.json`
- `3d-library/metadata/l3d_document_folder_open.json`
- `3d-library/metadata/l3d_document_folder_reveal.json`
- `3d-library/metadata/l3d_document_folder_scale_reveal.json`
- `3d-library/metadata/l3d_generic_passport_open.json`
- `3d-library/metadata/l3d_generic_passport_reveal.json`
- `3d-library/metadata/l3d_generic_passport_rotate_subtle.json`
- `3d-library/metadata/l3d_global_mobility_globe_light_reveal.json`
- `3d-library/metadata/l3d_global_mobility_globe_reveal.json`
- `3d-library/metadata/l3d_global_mobility_globe_rotate_subtle.json`
- `3d-library/metadata/l3d_premium_suitcase_floating_hold.json`
- `3d-library/metadata/l3d_premium_suitcase_reveal.json`
- `3d-library/metadata/l3d_premium_suitcase_slide_in.json`
- `3d-library/metadata/registry.json`
- `docs/audits/LUMEN_DEEP_PRODUCTION_AUDIT.md`
- `docs/motion/GOLD_STANDARD_DESIGN_SPEC.md`
- `docs/multilingual-card-audit.md`
- `docs/prompts/lumen-hypit-integration-cursor-prompt.md`
- `media/asset-generation-plan.json`
- `media/asset-taxonomy.md`
- `media/library/MEDIA_LIBRARY_V2_REPORT.md`
- `media/library/REAL_ESTATE_CONTENT_PACK.md`
- `media/library/STYLE_LOCK.md`
- `media/library/build_vector.py`
- `media/library/contact_v2.py`
- `media/library/immigration-scene-recipes.json`
- `media/library/immigration_pack.py`
- `media/library/library_v2.py`
- `media/library/package-lock.json`
- `media/library/package.json`
- `media/library/plans/cinematic-env-v6-batch1.jsonl`
- `media/library/plans/cinematic-env-v6-i2v-batch1.jsonl`
- `media/library/plans/pmv5-generative-stills.jsonl`
- `media/library/plans/v3-i2v-batch1.jsonl`
- `media/library/publish_batch.py`
- `media/library/real-estate-scene-recipes.json`
- `media/library/real_estate_vectors.py`
- `media/library/render_svg.js`
- `media/style-test-review.md`
- `recipes/cinematic-env-factory-v6-batch1.json`
- `scripts/check_runpod_gen_status.sh`
- `scripts/run_cinematic_env_v6_on_pod.sh`
