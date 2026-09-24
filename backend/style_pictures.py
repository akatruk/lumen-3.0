"""Style match does not generate a picture for each element.

Diagrams stay owned words and tiles. A screenshot is an owned frame.
"""

def attach_art(pid, manual, enabled=False):
    """Drop a generated picture so it cannot enter the automatic cut."""
    del pid, enabled
    if not manual:
        return manual
    for clip in manual.get('clips') or []:
        if isinstance(clip, dict):
            clip['art'] = ''
    return manual
