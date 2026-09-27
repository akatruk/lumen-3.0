"""Live analysis steps stored on the project so the page can show what is happening."""
import time

from .db import event, project, update

STAGE = {
    'prepare': 'preparing',
    'reference_fetch': 'reference_analysis',
    'reference_model': 'reference_analysis',
    'reference_cuts': 'measuring_reference',
    'reference_shots': 'measuring_reference',
    'reference_grade': 'measuring_reference',
    'owned_color': 'measuring_owned',
    'owned_sound': 'measuring_owned',
    'owned_motion': 'measuring_owned',
    'owned_model': 'understanding',
    'director': 'director_planning',
    'style_cut': 'style_match',
}


def _progress(step, done, total):
    anchor = {
        'prepare': 8,
        'reference_fetch': 14,
        'reference_model': 20,
        'reference_cuts': 24,
        'reference_shots': 28,
        'reference_grade': 60,
        'owned_color': 64,
        'owned_sound': 68,
        'owned_motion': 74,
        'owned_model': 74,
        'director': 84,
        'style_cut': 93,
    }.get(step, 8)
    if step == 'reference_shots' and total:
        try:
            fraction = max(0.0, min(1.0, float(done or 0) / float(total)))
        except (TypeError, ValueError, ZeroDivisionError):
            fraction = 0.0
        anchor = 28 + int(30 * fraction)
    return max(1, min(99, int(anchor)))


def note(pid, step, part=None, done=None, total=None, progress=None, plan=None):
    """Record the current analysis step without dropping the probed video metadata."""
    try:
        _write(pid, step, part, done, total, progress, plan)
    except Exception:
        return

def _write(pid, step, part, done, total, progress, plan):
    current = project(pid)
    if not current:
        return
    meta = dict(current.get('metadata') or {})
    previous = meta.get('activity') if isinstance(meta.get('activity'), dict) else {}
    log = [row for row in (previous.get('log') or []) if isinstance(row, dict) and row.get('step')]
    if previous.get('step') and previous.get('step') != step:
        log.append({'step': previous['step']})
        log = log[-12:]
    chosen = plan if isinstance(plan, list) and plan else previous.get('plan')
    if not isinstance(chosen, list) or not chosen:
        chosen = [step]
    same = previous.get('step') == step and previous.get('at')
    meta['activity'] = {
        'step': step,
        'part': part,
        'done': done,
        'total': total,
        'at': previous.get('at') if same else time.time(),
        'log': log,
        'plan': chosen,
    }
    value = _progress(step, done, total) if progress is None else int(progress)
    if current.get('status') == 'analyzing':
        try:
            value = max(int(current.get('progress') or 0), value)
        except (TypeError, ValueError):
            pass
    value = max(1, min(99, value))
    update(pid, status='analyzing', stage=STAGE.get(step, 'preparing'), progress=value, metadata=meta)
    if not same:
        event(pid, 'stage', step)
