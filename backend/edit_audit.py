"""Describe executable changes, independently of AI editorial claims."""

def audit_edit(edit, duration):
    clips = edit.clips
    ordered = sorted((c.start, c.end) for c in clips)
    covered = 0.0
    end = 0.0
    for a, b in ordered:
        covered += max(0, b - max(a, end))
        end = max(end, b)
    removed = max(0, duration - covered)
    reordered = any(b.start < a.start for a, b in zip(clips, clips[1:]))
    rows = []
    for index, c in enumerate(clips):
        operations = []
        z1 = c.zoom_end if c.zoom_end is not None else c.zoom
        x1 = c.x_end if c.x_end is not None else c.x
        y1 = c.y_end if c.y_end is not None else c.y
        if max(c.zoom, z1) > 1:
            operations.append('motion' if (c.zoom, c.x, c.y) != (z1, x1, y1) else 'reframe')
        if c.transition == 'fade': operations.append('fade')
        if index>0 and c.transition in ('crossfade','zoom','wipe','circle'):operations.append(c.transition)
        if c.text.strip(): operations.append('title')
        if c.card: operations.append('graphic')
        if c.cutaway or c.external_broll: operations.append('broll')
        if c.sound_effects: operations.append('sound_effects')
        rows.append({'clip_index': index, 'operations': operations})
    global_operations = []
    if removed > .01: global_operations.append('trim')
    if reordered: global_operations.append('reorder')
    if edit.subtitles and edit.captions: global_operations.append('captions')
    if edit.music: global_operations.append('music')
    if edit.normalize: global_operations.append('normalize')
    return {
        'clips': rows, 'global_operations': global_operations,
        'removed_seconds': round(removed, 3),
        'has_changes': bool(global_operations or any(r['operations'] for r in rows)),
    }
