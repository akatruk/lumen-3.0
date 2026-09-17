# Moment preview and master/source clarity

View moment previously only moved currentTime; a paused video remained paused (especially invisible for a 0s seek). It now stores the complete range, switches to source, waits for metadata, seeks, scrolls/focuses and plays; it pauses at the end and explains autoplay denial. Preview-tab changes cancel the range. Existing results open in Master preview by default with an explicit original/result explanation.

Real Chrome playback against a local six-second MP4, mocked project metadata: default master, playback at zero, natural pause at 1.5s, switching from master to source, and rejected play feedback all passed. Used real elapsed time, not virtual-time media simulation. TypeScript/Vite build passed. No production projects or render jobs changed.

Read-only inspection of the latest final project: source 162.1s; rendered output 154.665s; two trims and audio normalization; no generated clips; needs_review, model score 54. Latest creative plan is ready but not accepted, with no saved manual timeline. AI QA observations have not been independently verified by watching the full render.
