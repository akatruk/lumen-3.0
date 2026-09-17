# Individual variant editing, approval and immutable history

Implemented for Studio platform exports, 2026-09-15.

## Delivered

- Edit one platform's on-screen title, description, hashtags, CTA and retained scene ranges.
- Validate ranges on the approved master (including recognized speech boundaries and target language).
- Rerender only the selected platform. Copy other MP4/JPG/VTT assets byte-for-byte and preserve their approval/lock state.
- Approve, lock, unlock and reopen review independently per platform. Locked versions must first be unlocked; editing always resets that version's approval.
- Every edit/review creates a new package ID, new manifest and ZIP; previous complete packages remain downloadable.
- History selector, package-specific download URLs and restoration of a previous package for the current master. Older-master packages are readable but cannot be restored over a new master.
- Server rejects stale package IDs, concurrent jobs and cross-user access. Changes/restoration are recorded as events. Disk-space check runs before revision creation.
- A failed revision leaves previous complete packages available for restoration.
- Manual changes and review actions make no AI planning call. Re-rendering still uses CPU/storage.
- A package shows 3/3 approved only when all versions have been individually approved. This does not publish anything.

## Tests

Full PostgreSQL suite: 55 passed. Real QA test used existing synthetic travel content, without provider credentials or new AI requests:

1. Approve + lock Douyin; every video hash remains identical.
2. Reject an attempt to edit the locked version.
3. Edit only Instagram Reels: retain master range 10–26 seconds and update title.
4. Render a 16-second IG output. Douyin and YouTube files remain byte-identical and Douyin remains approved/locked.
5. The edited IG version requires review again.
6. Download previous package files; restore the original package and verify original file hashes.
7. Restore the edited package and approve/lock the remaining versions; manifest reports all three approved.
8. Confirm AI spending is unchanged.

See [live-report.json](live-report.json). The test checks mechanics, not professional editorial quality or real niche performance.

## Remaining scope

This provides manual per-platform editing and version history, not AI regeneration/replacement of arbitrary source footage, multi-asset editing, a full timeline editor, music/SFX generation, or publication/analytics connectors. Onboarding still needs updating. Human quality evaluation on real business footage remains outstanding.

## Browser and deployment verification

The isolated QA browser verified approved/locked controls, read-only historic packages, restoring the original package, opening the edit form, changing a draft title and cancelling, then restoring the fully approved package. The first QA restore was rejected by the origin guard; correcting only the QA server origin resolved it. No production authentication was bypassed.

Final focused regression: 6 passed. Deployed to the new VM 142.93.248.163 with backup `/opt/lumen-rebuild/backups/variant-revisions-20260915-072443`. Both web and worker are active. Public page and health return 200; unauthenticated history returns 401. Two existing production projects are preserved, no active jobs were interrupted, and the additive history table exists. Public assets: `index-KA18MUCA.js`, `index-C2eHEYaA.css`. Old Lumen VM was not modified.
