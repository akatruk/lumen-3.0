# V5 vs V6 comparison — project «e» 20s

| Dimension | V5 `director-v5-e-preview-20s.mp4` | V6 `director-v6-e-preview-20s.mp4` |
| --- | --- | --- |
| Locale stamp | `ru-RU` | `ru-RU` |
| Caption language | **English** (wrong) | **Russian** (matches speech) |
| Cards | Russian criteria | Russian criteria (aligned) |
| `captionSource` | `source_transcript` (but EN placeholder) | `source_transcript` (real RU) |
| `languageValidation` | absent / would fail | `ok: true` |
| Hook | speaker only | close-up + kinetic «Планируете переезд» |
| Layout diversity | weak / repeated splits | 4 unique layouts, 0 consecutive repeats |
| Background treatments | limited | 5 unique |
| Captions count | 11 EN crumbs | 12 RU phrases (clause-merged) |
| Audio | AAC present; bed ducked | same Remotion bed path |
| SHA256 prefix | `81924f4f…` (V5 report) | `106bfcc6…` |

## Evidence-based observations

1. **Language mix fixed** — frame QA shows RU captions + RU cards; no EN speech lines.
2. **Hook improved** — kinetic headline from first speech segment; bottom caption deduped when identical.
3. **Motion variety improved** — consecutive layout repeats = 0 (motion-diversity-report).
4. **Remaining** — some captions still end mid-clause (“программу с”); concept viz can still add mid-frame cards; transitions all `cut`; return beat sometimes forced to split by diversifier.

## Files

- V5: `output/director-v5/e-preview-20s.mp4` · Desktop `director-v5-e-preview-20s.mp4`
- V6: `output/director-v6/director-v6-e-preview-20s.mp4` · Desktop `director-v6-e-preview-20s.mp4`
- Contact: `output/director-v6/v6-contact-sheet.jpg`
