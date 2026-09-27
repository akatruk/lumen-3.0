/** Clip-relative windows already stored on a clip. This does not measure or round a new exit. */

export type LayerWindow = { start: number; end: number };
export type LayerId = "shot" | "blur" | "glow" | "shadow" | "speed" | "join" | "cutout" | "mask" | "split" | "reference" | "art" | "broll" | "callout" | "card" | "progress";
export type ClipLayer = { id: LayerId; windows: LayerWindow[] };

export type TimedClip = {
  start: number;
  end: number;
  text?: string;
  kinetic?: boolean;
  title_in?: number;
  title_out?: number;
  title_x?: number | null;
  kinetic_at?: number[];
  effect_at?: number;
  effect_end?: number;
  blur?: number;
  glow?: boolean;
  glow_amount?: number;
  shadow?: boolean;
  shade?: number;
  speed?: number | null;
  speed_end?: number | null;
  external_broll?: { start: number; end: number } | null;
  cutaway?: { start: number; end: number } | null;
  picture_insert?: { start: number; end: number; at?: number } | null;
  art?: string;
  cutout?: boolean;
  mask?: boolean;
  split?: boolean;
  transition?: string;
  transition_seconds?: number | null;
  progress?: number;
  progress_at?: number;
  progress_end?: number;
  card?: { start: number; end: number } | null;
};

function finite(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

export function clipSpan(clip: TimedClip): number {
  const span = clip.end - clip.start;
  return Number.isFinite(span) && span > 0 ? span : 0;
}

/** A missing or full-clip exit stays at the clip end. The stored fraction is not rounded. */
function exitAt(fraction: number | null, span: number, opened: number): number {
  if (fraction === null || fraction >= 0.999 || fraction * span <= opened) return span;
  return Math.max(opened, Math.min(span, fraction * span));
}

function marksOf(clip: TimedClip): number[] {
  return (clip.kinetic_at || [])
    .filter((item) => typeof item === "number" && Number.isFinite(item) && item >= 0 && item <= 1)
    .slice(0, 8);
}

function markWindows(marks: number[], span: number): LayerWindow[] {
  return marks
    .map((frac, index) => {
      const start = Math.max(0, Math.min(span, frac * span));
      const end =
        index + 1 < marks.length ? Math.max(start, Math.min(span, marks[index + 1] * span)) : span;
      return { start, end };
    })
    .filter((window) => window.end > window.start);
}

export function calloutBars(clip: TimedClip): LayerWindow[] {
  const span = clipSpan(clip);
  if (!span || !(clip.text || "").trim()) return [];
  const marks = marksOf(clip);
  if (clip.kinetic && marks.length >= 2) {
    const windows = markWindows(marks, span);
    if (windows.length) return windows;
  }
  if (clip.kinetic && finite(clip.title_x) !== null) {
    const opened = Math.max(0, Math.min(1, finite(clip.title_in) ?? 0)) * span;
    return [{ start: opened, end: exitAt(finite(clip.title_out) ?? 1, span, opened) }];
  }
  if (clip.kinetic && marks.length) {
    const windows = markWindows(marks, span);
    if (windows.length) return windows;
  }
  const opened = Math.max(0, Math.min(0.98, finite(clip.effect_at) ?? 0)) * span;
  return [{ start: opened, end: exitAt(finite(clip.effect_end) ?? 1, span, opened) }];
}

export function cardBar(clip: TimedClip): LayerWindow | null {
  const span = clipSpan(clip);
  const card = clip.card;
  if (!span || !card) return null;
  const start = finite(card.start);
  const end = finite(card.end);
  if (start === null || end === null || end <= start) return null;
  return { start, end };
}

export function progressBar(clip: TimedClip): LayerWindow | null {
  const span = clipSpan(clip);
  const amount = finite(clip.progress);
  if (!span || amount === null || amount <= 0) return null;
  const opened = Math.max(0, Math.min(1, finite(clip.progress_at) ?? 0)) * span;
  return { start: opened, end: exitAt(finite(clip.progress_end) ?? 1, span, opened) };
}

/** Blur, glow, and vignette. A measured effect_end below the clip stops the bar. An unmeasured exit runs to the clip end. */
function effectHold(clip: TimedClip): LayerWindow | null {
  const span = clipSpan(clip);
  if (!span) return null;
  const at = finite(clip.effect_at) ?? 0;
  const opened = at >= 0.2 ? Math.max(0, Math.min(0.98, at)) * span : 0;
  if (opened >= span) return null;
  return { start: opened, end: exitAt(finite(clip.effect_end) ?? 1, span, opened) };
}

/** Blur uses the same window as the gblur gate. */
export function blurBar(clip: TimedClip): LayerWindow | null {
  const amount = finite(clip.blur);
  if (amount === null || amount < 0.4) return null;
  return effectHold(clip);
}

function amountOn(flag: boolean | undefined, amount: number | null, floor: number): boolean {
  return flag === true || (amount !== null && amount >= floor);
}

/** Glow uses the same window as the unsharp gate. Off means no row. */
export function glowBar(clip: TimedClip): LayerWindow | null {
  if (!amountOn(clip.glow, finite(clip.glow_amount), 0.2)) return null;
  return effectHold(clip);
}

/** Shadow uses the same window as the vignette gate. Off means no row. */
export function shadowBar(clip: TimedClip): LayerWindow | null {
  if (!amountOn(clip.shadow, finite(clip.shade), 0.2)) return null;
  return effectHold(clip);
}

/** A flag that covers the clip. These filters store no separate window. */
function clipCover(on: boolean | undefined, span: number): LayerWindow | null {
  if (on !== true || !span) return null;
  return { start: 0, end: span };
}

export function cutoutBar(clip: TimedClip): LayerWindow | null {
  return clipCover(clip.cutout, clipSpan(clip));
}

export function maskBar(clip: TimedClip): LayerWindow | null {
  return clipCover(clip.mask, clipSpan(clip));
}

export function splitBar(clip: TimedClip): LayerWindow | null {
  return clipCover(clip.split, clipSpan(clip));
}

const STYLE_ART = /^style-art-[0-9]{1,2}\.png$/;

/** Generated art from the measured-graphic image path. The overlay covers the clip. */
export function artBar(clip: TimedClip): LayerWindow | null {
  const span = clipSpan(clip);
  if (!span || !STYLE_ART.test(clip.art || "")) return null;
  return { start: 0, end: span };
}

/** Insert start and end are clip-relative seconds, the same clock as a card window. */
function insertInside(insert: { start: number; end: number } | null | undefined, span: number): LayerWindow | null {
  if (!insert) return null;
  const start = finite(insert.start);
  const end = finite(insert.end);
  if (start === null || end === null || start < 0 || end > span || end <= start) return null;
  return { start, end };
}

export function brollBar(clip: TimedClip): LayerWindow | null {
  const span = clipSpan(clip);
  if (!span) return null;
  return insertInside(clip.external_broll, span) || insertInside(clip.cutaway, span);
}

/** Reference-frame copy. The bar is the picture_insert window in clip-relative seconds. */
export function referenceBar(clip: TimedClip): LayerWindow | null {
  const span = clipSpan(clip);
  if (!span) return null;
  return insertInside(clip.picture_insert, span);
}

/** A hold other than 1×, or a ramp, spans the clip. Speed 1 with no end has no row. */
export function speedBar(clip: TimedClip): LayerWindow | null {
  const span = clipSpan(clip);
  const speed = finite(clip.speed);
  if (!span || speed === null) return null;
  const closing = finite(clip.speed_end);
  const ramp = closing !== null && Math.abs(closing - speed) > 0.08;
  const hold = Math.abs(speed - 1) > 0.04 && (closing === null || Math.abs(closing - speed) <= 0.08);
  if (!ramp && !hold) return null;
  return { start: 0, end: span };
}

export function speedText(clip: TimedClip): string {
  const speed = finite(clip.speed) ?? 1;
  const closing = finite(clip.speed_end);
  const mark = (value: number) => `${Number(value.toFixed(2))}×`;
  if (closing !== null && Math.abs(closing - speed) > 0.08) return `${mark(speed)}–${mark(closing)}`;
  return mark(speed);
}

const JOINS = new Set(["crossfade", "zoom", "wipe", "wipe-up", "wipe-down", "circle", "diagtl", "diagtr", "diagbl", "diagbr"]);

/** Incoming half of a measured join, or both ends of a fade through black. A cut has no row. */
export function joinBars(clip: TimedClip): LayerWindow[] {
  const span = clipSpan(clip);
  const kind = clip.transition || "cut";
  if (!span || kind === "cut") return [];
  if (kind === "fade") {
    const fade = Math.min(0.25, span / 4);
    if (fade <= 0) return [];
    return [
      { start: 0, end: fade },
      { start: span - fade, end: span },
    ];
  }
  if (!JOINS.has(kind)) return [];
  let side = 0.4;
  const measured = finite(clip.transition_seconds);
  if (measured !== null && measured > 0.8) side = Math.max(0.4, measured / 2);
  const length = Math.min(side, span / 4, span);
  if (length <= 0) return [];
  return [{ start: 0, end: length }];
}

export function clipLayers(clip: TimedClip): ClipLayer[] {
  const span = clipSpan(clip);
  if (!span) return [];
  const layers: ClipLayer[] = [{ id: "shot", windows: [{ start: 0, end: span }] }];
  const blur = blurBar(clip);
  if (blur) layers.push({ id: "blur", windows: [blur] });
  const glow = glowBar(clip);
  if (glow) layers.push({ id: "glow", windows: [glow] });
  const shadow = shadowBar(clip);
  if (shadow) layers.push({ id: "shadow", windows: [shadow] });
  const speed = speedBar(clip);
  if (speed) layers.push({ id: "speed", windows: [speed] });
  const join = joinBars(clip);
  if (join.length) layers.push({ id: "join", windows: join });
  const cutout = cutoutBar(clip);
  if (cutout) layers.push({ id: "cutout", windows: [cutout] });
  const mask = maskBar(clip);
  if (mask) layers.push({ id: "mask", windows: [mask] });
  const split = splitBar(clip);
  if (split) layers.push({ id: "split", windows: [split] });
  const reference = referenceBar(clip);
  if (reference) layers.push({ id: "reference", windows: [reference] });
  const art = artBar(clip);
  if (art) layers.push({ id: "art", windows: [art] });
  const broll = brollBar(clip);
  if (broll) layers.push({ id: "broll", windows: [broll] });
  const callout = calloutBars(clip);
  if (callout.length) layers.push({ id: "callout", windows: callout });
  const card = cardBar(clip);
  if (card) layers.push({ id: "card", windows: [card] });
  const progress = progressBar(clip);
  if (progress) layers.push({ id: "progress", windows: [progress] });
  return layers;
}

export function formatSeconds(value: number): string {
  return `${value.toFixed(6).replace(/\.?0+$/, "")}s`;
}
