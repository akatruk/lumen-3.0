"""Compare intended picture edits with the picture actually delivered by the Master.
Audio-only deliveries retain the Master's picture; revisions alone are not evidence.
"""
from .timeline import compile_timeline


def picture(timeline, style):
    tracks=(timeline or {}).get('tracks',{})
    def clean(value):
        if isinstance(value,list):return [clean(v) for v in value]
        if isinstance(value,dict):return {k:clean(v) for k,v in value.items() if k not in {'id','decision_id','locked','shot_type','audio_fade_ms'}}
        return value
    value={k:clean(tracks.get(k,[])) for k in ('video','titles','inserts','cutaways','captions')}
    # Older timelines omit a movement duration; that means the entire shot.
    for shot in value['video']:
        motion=shot.get('motion',{})
        if motion.get('from')==motion.get('to'):motion.pop('duration',None)
        else:motion.setdefault('duration',shot['end']-shot['start'])
    if value['captions']:value['caption_style']={k:style.get(k,v) for k,v in {'font_size':'medium','position':'bottom','color':'white'}.items()}
    return value


def delivery_state(edit, result, selected_audio=False):
    # Include unapproved scenes to compare the intended edit, not silently omit them.
    intended=edit.model_copy(update={'clips':[c.model_copy(update={'approved':True}) for c in edit.clips]})
    actual=(result or {}).get('director_timeline')
    known=actual is not None
    return {
        'render_id':(result or {}).get('render_id'),
        'picture_pending':picture(compile_timeline(intended),edit.model_dump())!=picture(actual,(result or {}).get('caption_style',{})) if known else None,
        'rendered_scenes':len(actual['tracks']['video']) if known else None,
        'unapproved_scenes':sum(not c.approved for c in edit.clips),
        'separate_audio':bool(selected_audio),
    }
