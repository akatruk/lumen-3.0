# Media library cleanup V1

Date: 2026-10-10 (UTC). Host: `root@142.93.248.163` (lumen-fix).  
Library: `/mnt/volume_nyc1_1791446889637/app-library`.  
**No RunPod / GPU. No gen APIs. No permanent deletes. First pass = dry-run only.**

## Verdict: PASS

| Criterion | Result |
| --- | --- |
| Inventory count ~811 | **PASS** — **811** manifest rows |
| CPU quality classify PREMIUM…UNCERTAIN | **PASS** — Pillow + ffprobe |
| SHA256 + perceptual duplicate groups | **PASS** — 3 exact, 10 perceptual |
| Recommend best, do not delete | **PASS** — keep ids named; files untouched |
| Contact sheets under `contact-sheets/cleanup/` | **PASS** — 6 JPGs on volume |
| `reports/media-cleanup-review.json` | **PASS** |
| Quarantine/restore helpers (metadata status) | **PASS** — dry-run apply would touch 10 ids, wrote 0 |
| `search.py` skips quarantined/rejected | **PASS** — unit tested; no mass status apply yet so live search unchanged |
| Asset ids / history preserved | **PASS** |
| Unstable writes skipped | **PASS** — 0 files mtime &lt; 30m at apply time; stability gate in helpers |

## Inventory (authoritative)

| Metric | Count |
| --- | ---: |
| Manifest assets | **811** |
| Files present | 806 |
| Files missing | 5 (`re_motion_*` Remotion stubs → `motion/src/realestate/scenes.tsx`) |
| Disk files | 1094 |
| RunPod stills | 400 |
| Vector | 341 |
| Video rows | 17 |
| Motion rows (legacy) | 5 |

Manifest SHA256: `e9511b58dbb134226370bbaab9225fd0c5936816d338dfb1d851cefb7a90f13b`

## Quality (CPU)

| Tier | Count |
| --- | ---: |
| PREMIUM | 375 |
| GOOD | 431 |
| ACCEPTABLE | 0 |
| LOW | 0 |
| LEGACY | 5 |
| UNCERTAIN | 0 |

Photography / RunPod stills dominate PREMIUM. Vectors classify GOOD. Legacy = five missing Remotion motion placeholders.

## Duplicates

### Exact SHA256 (3 groups)

| Keep | Quarantine candidates |
| --- | --- |
| `v2_layer_relocation-city_background` | `v2_layer_passport-journey_background`, `v2_layer_property-balcony_background` |
| `imm_obj_home` | `icon_home` |
| `path_route` | `concept_path_001` |

### Perceptual (10 groups)

Still↔i2v pairs (`people_*` / `i2v_*`) and photo↔motion real-estate pairs are flagged for review but **not** auto-recommended for quarantine when quality tiers tie (intentional — motion is not a disposable still).

One near-dupe recommendation: `target_hit_001` vs keep `global_route_001` — **human review** (different concepts; phash on video frames can collide).

## Recommended quarantine (dry-run, n=10)

Not applied. Manifest still has **0** `status` fields.

1–5. `re_motion_price_*` / `comparison` / `purchase` — legacy missing  
6–7. duplicate v2 layer backgrounds  
8. `icon_home` (exact bytes of `imm_obj_home`) — confirm tags before apply  
9. `concept_path_001` (exact of `path_route`)  
10. `target_hit_001` — review before apply  

Apply later (status only, no file move):

```bash
python scripts/media_library_cleanup_v1.py apply-quarantine \
  --library /mnt/volume_nyc1_1791446889637/app-library \
  --manifest /mnt/volume_nyc1_1791446889637/app-library/manifest.json \
  --review reports/media-cleanup-review.json \
  --commit
```

Restore:

```bash
python scripts/media_library_cleanup_v1.py restore \
  --manifest …/manifest.json --ids <id> [--commit]
```

## Contact sheets (volume only — not in git)

`/mnt/volume_nyc1_1791446889637/app-library/contact-sheets/cleanup/`

| File | Bytes | SHA256 (prefix) |
| --- | ---: | --- |
| low-quality.jpg | 11109 | `7f2421f4538d28c6…` |
| duplicates.jpg | 213092 | `65c6c47631b826c0…` |
| legacy.jpg | 31355 | `4ade9df6cbae32d6…` |
| replacements.jpg | 182346 | `6de4b0f71e98d4a9…` |
| uncertain.jpg | 11859 | `c7e811b397b20b42…` |
| videos.jpg | 277410 | `332d26e8ad1933e2…` |

Full asset review JSON on volume: `contact-sheets/cleanup/media-cleanup-review.full.json`

## Tooling deployed

| Path | Role |
| --- | --- |
| `scripts/media_cleanup_v1/` | audit, classify, hashes, quarantine, contact sheets |
| `scripts/media_library_cleanup_v1.py` | CLI entry |
| `media/library/search.py` | skip `status ∈ {quarantined, rejected}` unless `include_hidden=True` |
| `backend/tests/test_media_cleanup_v1.py` | 9 tests |

On DO: `/opt/lumen-rebuild/scripts/…` + Pillow in `/opt/lumen-rebuild/venv`.

## Report SHAs

| File | SHA256 |
| --- | --- |
| `reports/media-cleanup-review.json` | `5de080fa19060d85c4f796f7662958d6fb6c9dbf60dbd9e1fa9857bb620890c9` |
| `reports/MEDIA_LIBRARY_INVENTORY.md` | `e7c3308818170834d808dd147cff3d7171024dce2cb15799a091d4aa7eade6a8` |

## Tests

```text
.venv/bin/python -m pytest backend/tests/test_media_cleanup_v1.py -q
# 9 passed
```

## Git

Branch: `feat/media-library-cleanup-v1`  
Commit: `5aa437e3571729637fa60d4594f623f17cd0347d`

## Explicit non-actions

- No `rm` / quarantine directory moves on production media  
- No status mass-apply (`--commit` not used)  
- No RunPod / Comfy / image-video gen  
- Motion V3 agent files left alone (additive `scripts/` + `reports/` only; minimal `search.py` filter)
