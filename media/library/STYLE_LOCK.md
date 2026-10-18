# Style lock

Three families share one palette and the same restraint. They are not the same technique.

## Families

- **A. Line / vector.** Icons, gold paths, and the house. `viewBox="0 0 24"`, stroke width 1.6, round caps and joins, gold `#E0B15A`, transparent background. Recognizable at about 80–120 px on a 1080×1920 frame.
- **B. Editorial objects.** Isolated still-life objects (shield, folder, calendar, seal, luggage). Often photographed on white and keyed. Type is added later.
- **C. Cinematic photography.** Premium editorial photographs. Realistic people, natural light, negative space, and a subject that stays important.

Accepted Remotion clips are deterministic motion. Clips grown from an approved still are generative motion. Both stay subtle.

## Color

Dark premium backgrounds, restrained mint, gold line, off-white type.

| Role | Hex |
| --- | --- |
| Navy | `#0E1A2B` |
| Blue | `#7EB6C9` |
| Mint | `#8FCBB4` |
| Gold line | `#E0B15A` |
| Paper | `#F4EFE6` |
| Check | `#3E8F62` |

## Photography

Premium editorial. Realistic people. Natural light, bright enough to see faces and clothes. The subject is the focal point, not a small figure in a dark room. Leave usable negative space. Frame 9:16, full bleed, no black bars. No readable signs, no text, no logos.

## Motion

Subtle and purposeful. Breathing, a small hand movement, a slight gesture, a slow push. No morphing, no orbit, no new people, no new objects, no face change, no clothing change.

## Composition

Photographs and generative clips are 9:16. Text sits in the open part of the frame (the side or the top away from the subject). Line marks are 1:1 and transparent so they can sit over a plate.

## Travel

Never frame a departure board, an arrival board, a gate display, signage, a ticket screen, a monitor, or an ad.

Prefer close luggage, a traveler walking, terminal architecture, a window with an aircraft, a moving walkway, hands on a suitcase, a silhouette against a window, a rear or side view, or seating with no signage.

Every travel prompt ends with: no readable signs, no departure board, no arrival board, no gate display, no information screen, no advertising text, no ticket text, no logos, no captions, no typography.

Do not put the word watermark in a prompt. The image model refuses it.

`people_airport_001` stays in `rejected/` only. It shows readable departure boards and is not in the production manifest.

## WebM alpha

Remotion's own VP8 encode dropped alpha. Production WebM is encoded with system ffmpeg:

`libvpx-vp9 -pix_fmt yuva420p -auto-alt-ref 0`

ffprobe may still report `yuv420p`. Decode with `-c:v libvpx-vp9` and check that alpha is present.
