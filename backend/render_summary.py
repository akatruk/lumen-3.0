"""Facts about the saved executable edit, never AI descriptions."""
from .edit_audit import audit_edit
from .timeline import compile_timeline


def summarize(edit, duration):
    edit = edit.model_copy(update={'clips': [c for c in edit.clips if c.approved]})
    timeline = compile_timeline(edit)
    audit = audit_edit(edit, duration)
    removed = []
    cursor = 0.0
    for clip in sorted(edit.clips, key=lambda c: c.start):
        if clip.start > cursor:
            removed.append([round(cursor,3), round(clip.start,3)])
        cursor = max(cursor, clip.end)
    if cursor < duration:
        removed.append([round(cursor,3), round(duration,3)])
    visual = any(set(row['operations']) - {'sound_effects'} for row in audit['clips'])
    # A small tail trim, normalization, or fake split is not a visible new edit.
    near_original = not (visual or timeline['tracks']['captions'] or 'reorder' in audit['global_operations'] or audit['removed_seconds'] > max(2, duration * .02))
    return {
        'source_duration': duration, 'output_duration': timeline['duration'],
        'removed_ranges': removed, 'removed_seconds': audit['removed_seconds'],
        'global_operations': audit['global_operations'], 'near_original': near_original,
        'captions': len(timeline['tracks']['captions']), 'music': bool(edit.music),
        'normalize': edit.normalize,
        'clips': [shot | {'operations': row['operations']} for shot, row in zip(timeline['tracks']['video'], audit['clips'])],
    }
