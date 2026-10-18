/**
 * Shared data + layout for the three numeric-range presentations.
 * Endpoints and units stay spoken strings. Presentation does not rewrite them.
 */
import type { SupportedLocale } from "../localization/language-config";
import { segmentForLineBreak } from "../localization/segment";
import { CANVAS } from "../themes/tokens";
import type { NumericRangeValue, SemanticMotionPayload } from "./types";
import { captionBand, rectsOverlap, type Rect } from "./layouts";
import { rangeKindLabel } from "./numericRange";

export const RANGE_PRESENTATIONS = ["finance", "editorial", "split"] as const;
export type RangePresentation = (typeof RANGE_PRESENTATIONS)[number];

/** Stroke is the light core. The dark outline sits outside it. Never a 3px hairline. */
export const CONNECTOR_STROKE: Record<RangePresentation, number> = {
  finance: 10,
  editorial: 16,
  split: 12,
};

/** Measured on original2 15.2–23.2s, scaled 720×1280 → 1080×1920. */
export const RANGE_FACE: Rect = { left: 270, top: 470, width: 380, height: 520 };
export const RANGE_CHEST: Rect = { left: 160, top: 1080, width: 700, height: 300 };

const SPLIT_END = { scale: 1.12, translateX: -64.8, translateY: -12 };

export type RangeModel = {
  lowText: string;
  highText: string;
  lowDisplay: string;
  highDisplay: string;
  unit: string;
  heading: string;
  kind: string;
  locale: SupportedLocale;
};

export type RangePhase = {
  frames: number;
  enter: number;
  lowAt: number;
  highAt: number;
  connectAt: number;
  connectEnd: number;
  emphasisAt: number;
  exitAt: number;
};

export type SplitFrame = { scale: number; translateX: number; translateY: number };

function localeOf(locale: string): SupportedLocale {
  if (locale.startsWith("zh")) return "zh-CN";
  if (locale.startsWith("ru")) return "ru-RU";
  return "en-US";
}

/** Group the numeric body. The spoken suffix (万 / 千) stays attached. */
export function formatEndpoint(text: string, locale: string): string {
  const raw = String(text || "").trim();
  const match = raw.match(/^(\d+(?:[.,]\d+)?)(.*)$/);
  if (!match) return raw;
  const numeric = match[1].replace(",", ".");
  const suffix = match[2];
  const value = Number(numeric);
  if (!Number.isFinite(value)) return raw;
  const decimals = numeric.includes(".") ? numeric.split(".")[1].length : 0;
  const loc = localeOf(locale);
  const body = new Intl.NumberFormat(loc, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
    useGrouping: false,
  }).format(value);
  return `${body}${suffix}`;
}

/**
 * EN/RU break on spaces and never split a word.
 * ZH breaks on characters; a digit run stays whole; a line does not start with closing punctuation.
 */
export function wrapRangeLabel(text: string, locale: string, maxChars: number): string[] {
  const clean = String(text || "").trim();
  if (!clean) return [];
  const limit = Math.max(1, Math.round(maxChars));
  if (localeOf(locale) === "zh-CN") {
    const tokens = segmentForLineBreak(clean);
    const lines: string[] = [];
    let line = "";
    for (const token of tokens) {
      const nextLen = [...line].length + [...token].length;
      if (line && nextLen > limit) {
        lines.push(line);
        line = token;
      } else {
        line += token;
      }
    }
    if (line) lines.push(line);
    return lines;
  }
  const words = clean.split(/\s+/).filter(Boolean);
  const lines: string[] = [];
  let line = "";
  for (const word of words) {
    const next = line ? `${line} ${word}` : word;
    if (line && next.length > limit) {
      lines.push(line);
      line = word;
    } else {
      line = next;
    }
  }
  if (line) lines.push(line);
  return lines;
}

export function buildRangeModel(
  payload: Pick<SemanticMotionPayload, "range" | "labels"> & { range?: NumericRangeValue },
  locale: string,
): RangeModel | null {
  const range = payload.range;
  const lowText = String(range?.lowText || "").trim();
  const highText = String(range?.highText || "").trim();
  if (!lowText || !highText) return null;
  const loc = localeOf(locale);
  const stamped = payload.labels || {};
  const heading =
    (loc === "zh-CN" ? stamped["zh-CN"] : loc === "ru-RU" ? stamped["ru-RU"] : stamped["en-US"]) ||
    rangeKindLabel(range?.kind, loc);
  return {
    lowText,
    highText,
    lowDisplay: formatEndpoint(lowText, loc),
    highDisplay: formatEndpoint(highText, loc),
    unit: String(range?.unit || "").trim(),
    heading,
    kind: String(range?.kind || "money"),
    locale: loc,
  };
}

/** Entry, low, high, connector, emphasis, exit. Scales with the segment length. */
export function rangeChoreography(frames: number): RangePhase {
  const safe = Math.max(24, Math.round(frames));
  const enter = Math.max(6, Math.min(14, Math.round(safe * 0.1)));
  const exitSpan = Math.max(6, Math.min(12, Math.round(safe * 0.12)));
  const exitAt = safe - exitSpan;
  const usable = Math.max(8, exitAt - enter);
  const lowAt = enter;
  const highAt = lowAt + Math.max(4, Math.round(usable * 0.18));
  const connectAt = highAt + Math.max(4, Math.round(usable * 0.16));
  const connectEnd = Math.min(exitAt - 4, connectAt + Math.max(6, Math.round(usable * 0.28)));
  const emphasisAt = connectEnd;
  return { frames: safe, enter, lowAt, highAt, connectAt, connectEnd, emphasisAt, exitAt };
}

export function splitFrame(progress: number): SplitFrame {
  const p = Math.min(1, Math.max(0, progress));
  return {
    scale: 1 + (SPLIT_END.scale - 1) * p,
    translateX: SPLIT_END.translateX * p,
    translateY: SPLIT_END.translateY * p,
  };
}

export function mapRangePoint(x: number, y: number, frame: SplitFrame): { x: number; y: number } {
  const cx = CANVAS.width / 2;
  const cy = CANVAS.height / 2;
  return {
    x: (x - cx) * frame.scale + cx + frame.translateX,
    y: (y - cy) * frame.scale + cy + frame.translateY,
  };
}

export function mapRangeRect(rect: Rect, frame: SplitFrame): Rect {
  const corners = [
    mapRangePoint(rect.left, rect.top, frame),
    mapRangePoint(rect.left + rect.width, rect.top, frame),
    mapRangePoint(rect.left, rect.top + rect.height, frame),
    mapRangePoint(rect.left + rect.width, rect.top + rect.height, frame),
  ];
  const xs = corners.map((point) => point.x);
  const ys = corners.map((point) => point.y);
  const left = Math.min(...xs);
  const top = Math.min(...ys);
  return { left, top, width: Math.max(...xs) - left, height: Math.max(...ys) - top };
}

/**
 * Right-column graphics. A/B sit on the clear poster, past the hair.
 * C is wider once the speaker has eased left; the face stays inside the left share.
 */
export function graphicRect(presentation: RangePresentation): Rect {
  if (presentation === "split") return { left: 624, top: 200, width: 416, height: 840 };
  if (presentation === "editorial") return { left: 736, top: 200, width: 308, height: 760 };
  return { left: 728, top: 188, width: 316, height: 800 };
}

export function rangeLayoutSafety(presentation: RangePresentation): {
  faceClear: boolean;
  chestClear: boolean;
  captionClear: boolean;
  faceInsideFrame: boolean;
  speakerShare: number;
  graphicShare: number;
  connector: number;
} {
  const graphic = graphicRect(presentation);
  const face = presentation === "split" ? mapRangeRect(RANGE_FACE, splitFrame(1)) : RANGE_FACE;
  const chest = presentation === "split" ? mapRangeRect(RANGE_CHEST, splitFrame(1)) : RANGE_CHEST;
  const faceInsideFrame =
    presentation !== "split" ||
    (face.left >= 0 &&
      face.top >= 0 &&
      face.left + face.width <= CANVAS.width &&
      face.top + face.height <= CANVAS.height);
  return {
    faceClear: !rectsOverlap(graphic, face, 8),
    chestClear: !rectsOverlap(graphic, chest, 8),
    captionClear: !rectsOverlap(graphic, captionBand(), 12),
    faceInsideFrame,
    speakerShare: presentation === "split" ? graphic.left / CANVAS.width : 1,
    graphicShare: graphic.width / CANVAS.width,
    connector: CONNECTOR_STROKE[presentation],
  };
}
