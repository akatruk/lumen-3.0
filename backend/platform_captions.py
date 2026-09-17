"""Restyle Lumen captions from a clean companion, never overlay old burned captions."""
from . import media
from .schemas import Caption

def caption_source(source,master,variant):
    if not master.get('caption_master'):
        if variant.caption_mode!='inherit':raise ValueError('caption_master_required')
        return source
    path=source.with_name('caption-free.mp4') if master.get('captions_enabled') else source
    if not path.is_file():raise ValueError('caption_master_required')
    return path

def write(path,master,variant,language,w,h,timeline):
    if not master.get('caption_master') or variant.caption_mode=='off':return False
    if variant.caption_mode=='inherit' and not master.get('captions_enabled'):return False
    captions=[]
    for raw in master.get('caption_transcript',[]):
        original=Caption.model_validate(raw)
        for a,b in media.remap_span(original.start,original.end,master['timeline']):
            captions.append(original.model_copy(update={'start':a,'end':b}))
    style=master.get('caption_style',{}) if variant.caption_mode=='inherit' else {
        'font_size':variant.caption_size,'position':variant.caption_position,'color':variant.caption_color}
    media.write_subtitles(path,captions,timeline,language,w,h,style)
    return True


def protected_speech(master,analysis):
    """Map original and saved master speech to master time, even with captions off."""
    rows=[*analysis.get('transcript',[]),
          *master.get('caption_transcript',master.get('manual_transcript',[]))]
    return sorted({span for raw in rows
                   for span in media.remap_span(raw['start'],raw['end'],master['timeline'])})
