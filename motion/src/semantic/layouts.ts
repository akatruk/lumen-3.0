/**
 * Shared layout regions for semantic motion V14.
 * Five components reuse these three variants — no per-component geometry.
 * Face band, speaker column, PIP, and caption band are hard exclusions.
 */
import { CANVAS } from "../themes/tokens";
import { pipRect, PORTRAIT, splitMediaRect, splitSpeakerRect } from "../preview/portraitLayouts";

export type LayoutVariant = "full_frame" | "speaker_visual" | "overlay" | "editorial_focus";
export type MediaSide = "left" | "right";

export type Rect = { left: number; top: number; width: number; height: number };

export function rectsOverlap(a: Rect, b: Rect, gap = 0): boolean {
  return (
    a.left < b.left + b.width + gap &&
    a.left + a.width + gap > b.left &&
    a.top < b.top + b.height + gap &&
    a.top + a.height + gap > b.top
  );
}

/** Composer rects are used only when they clear the measured face and the caption plate. */
export function compositionClears(motion: Rect, face?: Rect | null, caption?: Rect | null): boolean {
  if (motion.width < 300 || motion.height < 200) return false;
  if (face && rectsOverlap(motion, face, 8)) return false;
  if (caption && rectsOverlap(motion, caption, 12)) return false;
  return true;
}

/** Caption plate is ~210px tall and sits on top of the bottom clearance. */
export function captionBand(): Rect {
  const plate = 210;
  const top = PORTRAIT.height - PORTRAIT.captionClearance - plate;
  return {
    left: 0,
    top,
    width: PORTRAIT.width,
    height: PORTRAIT.height - top,
  };
}

/** Full-bleed talking-head face band. Split layouts keep the face in the speaker column. */
export function faceBandRect(): Rect {
  const top = Math.round(PORTRAIT.height * PORTRAIT.faceBand.top);
  const bottom = Math.round(PORTRAIT.height * PORTRAIT.faceBand.bottom);
  return {
    left: Math.round(PORTRAIT.width * 0.18),
    top,
    width: Math.round(PORTRAIT.width * 0.64),
    height: bottom - top,
  };
}

export function pipSafeRect(): Rect {
  const p = pipRect();
  return {
    left: PORTRAIT.width - p.right - p.width,
    top: PORTRAIT.height - p.bottom - p.height,
    width: p.width,
    height: p.height,
  };
}

function overlayRect(): Rect {
  const face = faceBandRect();
  const cap = captionBand();
  // Sit under a typical talking-head mouth, not only the nominal face band.
  const top = Math.max(face.top + face.height + 36, Math.round(PORTRAIT.height * 0.55));
  const bottom = cap.top - 36;
  return {
    left: 72,
    top,
    width: CANVAS.width - 144,
    height: Math.max(240, bottom - top),
  };
}

function fullFrameRect(): Rect {
  const cap = captionBand();
  const pip = pipSafeRect();
  const left = 64;
  const right = pip.left - 28;
  return {
    left,
    top: 150,
    width: Math.max(420, right - left),
    height: Math.max(480, cap.top - 170),
  };
}

/**
 * Wide graphic over a 9:16 PIP that stops 20px above the caption band.
 * 360×640 matches a portrait source, so cover does not crop the head the way
 * the 360×420 full_frame PIP does. A 70% side column cannot hold a 324px PIP,
 * so the graphic uses the full inset row (952 / 1080).
 */
export function editorialFocusRects(): { graphic: Rect; speaker: Rect } {
  const cap = captionBand();
  const gap = 20;
  const pipW = 360;
  const pipH = 640;
  const margin = 64;
  const speaker: Rect = {
    left: CANVAS.width - margin - pipW,
    top: cap.top - gap - pipH,
    width: pipW,
    height: pipH,
  };
  const top = 128;
  const graphic: Rect = {
    left: margin,
    top,
    width: CANVAS.width - margin * 2,
    height: speaker.top - gap - top,
  };
  return { graphic, speaker };
}

function speakerVisualRect(side: MediaSide): Rect {
  const media = splitMediaRect(side);
  const cap = captionBand();
  const top = Math.max(media.top, 160);
  const bottom = Math.min(media.top + media.height, cap.top - 16);
  return {
    left: media.left,
    top,
    width: media.width,
    height: Math.max(320, bottom - top),
  };
}

export function regionFor(layout: LayoutVariant, mediaSide: MediaSide = "left"): Rect {
  if (layout === "editorial_focus") return editorialFocusRects().graphic;
  if (layout === "full_frame") return fullFrameRect();
  if (layout === "speaker_visual") return speakerVisualRect(mediaSide);
  return overlayRect();
}

export function layoutIsSafe(layout: LayoutVariant, mediaSide: MediaSide = "left"): boolean {
  const rect = regionFor(layout, mediaSide);
  const cap = captionBand();
  if (rectsOverlap(rect, cap)) return false;
  if (rect.left < 24 || rect.top < 80) return false;
  if (rect.left + rect.width > CANVAS.width - 24) return false;
  if (layout === "overlay" && rectsOverlap(rect, faceBandRect())) return false;
  if (layout === "full_frame" && rectsOverlap(rect, pipSafeRect())) return false;
  if (layout === "speaker_visual") {
    const speakerSide: MediaSide = mediaSide === "left" ? "right" : "left";
    const speaker = splitSpeakerRect(speakerSide);
    const speakerRect: Rect = {
      left: speaker.left,
      top: speaker.top,
      width: speaker.width,
      height: speaker.height,
    };
    if (rectsOverlap(rect, speakerRect)) return false;
  }
  if (layout === "editorial_focus") {
    const speaker = editorialFocusRects().speaker;
    if (rectsOverlap(rect, speaker, 12)) return false;
    if (rectsOverlap(speaker, cap, 12)) return false;
    if (speaker.width < 324 || speaker.height < 400) return false;
  }
  return rect.width >= 360 && rect.height >= 220;
}

/** Unsafe requests fall through to the next variant that clears face + captions. */
export function resolveLayout(
  requested: LayoutVariant,
  mediaSide: MediaSide = "left",
): { layout: LayoutVariant; rect: Rect; fallback: boolean } {
  const order: LayoutVariant[] =
    requested === "editorial_focus"
      ? ["editorial_focus", "speaker_visual", "overlay", "full_frame"]
      : requested === "full_frame"
        ? ["full_frame", "speaker_visual", "overlay"]
        : requested === "speaker_visual"
          ? ["speaker_visual", "overlay", "full_frame"]
          : ["overlay", "speaker_visual", "full_frame"];
  for (const layout of order) {
    if (layoutIsSafe(layout, mediaSide)) {
      return { layout, rect: regionFor(layout, mediaSide), fallback: layout !== requested };
    }
  }
  const rect = overlayRect();
  return { layout: "overlay", rect, fallback: requested !== "overlay" };
}
