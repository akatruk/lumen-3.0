# V8 vs V9 comparison

| | V8 | V9 |
| --- | --- | --- |
| Duration | 60.05s | **60.05s** |
| Opaque webm motion boxes | ~10 | **0** |
| Transparent float objects | 0 | **3** (passport, pin, suitcase) |
| Concept overlays | yes | **no** |
| Hero globe | yes | **no** |
| Steps | dark card stack | **speaker + progressive type** |
| Caption loops | restart ~40s | **deduped (12)** |
| compositionAudit.pass | n/a | **True** |

Same source «e», same 60s speech. Quality gain = composition, not length.
