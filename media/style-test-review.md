# Style test review

Eight assets, one contact sheet. The library is not scaled yet.

## Keep

- Document stack. Blank rules, one check, no readable type, clean edge after the checkerboard was removed.
- Globe with one route. This is the diagram language to repeat.
- Both photographs. Faces and hands hold up, and each leaves an open side for type. The family frame is three people, not four.

## Redo before any larger batch

- Target illustration. It came back as glossy 3D with a grunge halo. It does not belong with the line icon. Draw it flat, same stroke as the goal icon.
- Goal icon and family icon. Usable, but the goal has two arrowheads and the child overlaps the adults. These should be SVG, not another image-model pass. One stroke weight, then the rest of the icon set can match.
- Approved document. Same idea as the stack, and the paper edge is torn where the checkerboard was cut away. One sheet, straight edges.

## Process

The still model is `google/gemini-2.5-flash-image` through the existing OpenRouter call. It will not return a transparent PNG. Ask for a flat white field, then key it. Do not write the word watermark in the prompt.
