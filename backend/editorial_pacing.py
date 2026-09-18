"""Conservative timing diagnostics, not an engagement or semantic quality score."""
from .creator_style import Style


def _static_picture(clip):
    end = (clip.zoom_end if clip.zoom_end is not None else clip.zoom,
           clip.x_end if clip.x_end is not None else clip.x,
           clip.y_end if clip.y_end is not None else clip.y)
    if clip.card or clip.cutaway or clip.external_broll or clip.sound_effects:
        return None
    if (clip.zoom, clip.x, clip.y) != end:
        return None
    # Position has no effect at 1x. A role label is not a visual operation.
    return (clip.zoom, clip.x if clip.zoom > 1 else .5,
            clip.y if clip.zoom > 1 else .5, clip.text.strip())


def diagnose(edit, style=None, scenes=()):
    preference = Style.model_validate(style or {})
    target = {'calm': [6, 12], 'balanced': [3, 7], 'dynamic': [1.5, 4]}[preference.pacing]
    scene_edges = {float(edge) for scene in scenes for edge in (scene['start'], scene['end'])}
    runs = []
    artificial = []
    continuous_transitions = []
    cursor = 0.0
    for i, clip in enumerate(edit.clips):
        previous = edit.clips[i-1] if i else None
        same_picture = previous is not None and _static_picture(clip) is not None and _static_picture(previous) == _static_picture(clip)
        continuous = previous is not None and abs(previous.end-clip.start) < .001
        edges = [clip.start, *sorted(edge for edge in scene_edges if clip.start < edge < clip.end), clip.end]
        for part, (start, end) in enumerate(zip(edges, edges[1:])):
            natural_boundary = any(abs(start-edge) < .001 for edge in scene_edges)
            if part == 0 and continuous and same_picture and clip.transition == 'cut' and not natural_boundary:
                runs[-1]['end'] = round(cursor+end-start, 3)
                runs[-1]['clip_indices'].append(i)
                artificial.append(i)
            else:
                runs.append({'start': round(cursor, 3), 'end': round(cursor+end-start, 3), 'clip_indices': [i]})
            cursor += end-start
        if continuous and same_picture and clip.transition != 'cut' and not any(abs(clip.start-edge) < .001 for edge in scene_edges):
            continuous_transitions.append(i)
    union = 0.0
    covered_end = 0.0
    for start, end in sorted((c.start, c.end) for c in edit.clips):
        union += max(0, end-max(start, covered_end))
        covered_end = max(covered_end, end)
    return {
        'visual_runs': runs,
        'visual_run_count': len(runs),
        'average_visual_run_seconds': round(cursor/max(1, len(runs)), 2),
        'longest_visual_run_seconds': round(max((r['end']-r['start'] for r in runs), default=0), 2),
        'target_seconds': target,
        'long_runs': [r for r in runs if r['end']-r['start'] > target[1]+.001],
        'artificial_boundaries': artificial,
        'continuous_transition_indices': continuous_transitions,
        'repeated_source_seconds': round(max(0, cursor-union), 3),
        'opening_source': {'start': edit.clips[0].start, 'end': edit.clips[0].end} if edit.clips else None,
        'timing_only': True,
    }
