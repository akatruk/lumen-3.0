# Keep selected audio across picture renders

Root cause: a new Master is published while final-output selection still references the preceding Master. The resolver correctly rejects that stale video, but falls back to source speech instead of rebuilding the selected audio over the new picture.

Implement source-timeline mapping of the selected generated voice (no new AI calls), remix current saved music and sound effects over the new picture, and atomically publish the new Master plus its carried voice/mix selection. Store clean carried voice separately to prevent cumulative music/SFX. Preserve translated caption timings. Reject missing voice coverage rather than silently using original speech. Preflight must describe retained voice accurately. Repair final2 after in-flight rendering completes, using the newest picture, without rerunning AI or changing its edits.

Verify consecutive renders, trim/reorder mapping, actual speech frequencies and frame identity, failure preservation, selection persistence and download after reload.
