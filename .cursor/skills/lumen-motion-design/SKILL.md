---
name: lumen-motion-design
description: >-
  Professional motion principles for Lumen Remotion scenes: hierarchy, easing,
  stagger, depth, budgets, and premium editorial aesthetic.
---

# Motion design

## Do

- Clear visual hierarchy; one primary reveal per beat
- Controlled easing (`Easing.out(cubic)`); staggered entrances
- Layered depth (parallax / plates) with a motion budget
- Meaningful transitions; cuts are often best

## Avoid

- PowerPoint wipes, random bounce, continuous spin
- Animating every layer at once
- Excessive zoom; repetitive identical card loops

Choreography per scene: entrance → reveal → hold → emphasis → exit.

Director V3 portrait splits (`portraitLayouts.ts`): fill the canvas; animate speaker panel width/position from near-fullscreen into the split (no unexplained jump to a tiny float). Crossfades must not fade from empty black. Concept PIP is a rounded portrait card, not a 220px face circle.
