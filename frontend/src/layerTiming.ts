/** Clip-relative windows already stored on a clip. This does not measure or round a new exit. */

export type LayerWindow = { start: number; end: number };
export type LayerId = "shot" | "callout" | "card" | "progress";
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

export function clipLayers(clip: TimedClip): ClipLayer[] {
  const span = clipSpan(clip);
  if (!span) return [];
  const layers: ClipLayer[] = [{ id: "shot", windows: [{ start: 0, end: span }] }];
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
