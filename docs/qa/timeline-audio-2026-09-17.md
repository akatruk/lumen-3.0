# Director Timeline audio timing

Timeline sound-effect records now include actual end times and durations, mapped through approved output order. The UI uses click/chime/whoosh durations rather than drawing all accents as 0.6 seconds. Music displays actual repeat boundaries based on the selected excerpt, separate from estimated beat accents, plus edge-smoothing and effective fade durations. Tracks that do not repeat are no longer labeled looped. Drafts containing unapproved shots keep music timing in the approved-output view.

Validation: frontend build, Node boundary checks (offsets, exact endpoint, no repeat, invalid period and display cap), and backend output-order/approval regression passed. Display is capped at 80 repeat markers with an explicit label. This improves plan visibility; no audio synthesis or approved clip timing changed.
