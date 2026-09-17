"""Small, reviewable cut shifts around measured music accents; no speech cuts."""
def propose(edit,accents,track_duration,speech):
    result=edit.model_copy(deep=True);changes=[]
    if not edit.music or any(not c.approved for c in edit.clips):return result,changes
    offset=edit.music.source_start;loop=track_duration-offset
    if loop<.1:return result,changes
    duration=sum(c.end-c.start for c in edit.clips)
    beats=[];base=0
    while base<duration and len(beats)<5000:
        beats.extend(base+t-offset for t in accents if offset<=t<track_duration and base+t-offset<duration)
        base+=loop
    if not beats:return result,changes
    def has_layers(c):return c.card or c.cutaway or c.external_broll or c.sound_effects or c.text.strip()
    for i in range(len(result.clips)-1):
        left,right=result.clips[i:i+2]
        if left.locked or right.locked or has_layers(left) or has_layers(right):continue
        if abs(left.end-right.start)>.001 or right.transition!='cut':continue
        output=sum(c.end-c.start for c in result.clips[:i+1]);old=left.end
        candidates=sorted((b for b in beats if .025<abs(b-output)<=.35),key=lambda b:abs(b-output))
        for beat in candidates:
            new=old+beat-output
            if new-left.start<.5 or right.end-new<.5:continue
            lo,hi=sorted((old,new))
            # Reject even crossing a short spoken word, not just landing inside one.
            if any(c.start-.12<hi and c.end+.12>lo for c in speech):continue
            left.end=new;right.start=new;left.approved=False;right.approved=False
            changes.append({'left_id':left.id,'right_id':right.id,'from_output':round(output,3),'to_output':round(beat,3),'from_source':round(old,3),'to_source':round(new,3)})
            break
    return result,changes
