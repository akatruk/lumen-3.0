const NARROW = new Set(["i", "l", "j", "I", "'", ",", ".", ":", ";", "!", "|"]);
const MEDIUM_NARROW = new Set(["f", "t", "r"]);
const WIDE = new Set(["m", "w"]);
const EXTRA_WIDE = new Set(["M", "W", "%", "@"]);

function unit(char: string): number {
  if (char === " ") return 0.278;
  if (char === "?" || char === "&") return 0.58;
  if (NARROW.has(char)) return 0.24;
  if (MEDIUM_NARROW.has(char)) return 0.36;
  if (EXTRA_WIDE.has(char)) return 0.92;
  if (WIDE.has(char)) return 0.78;
  const code = char.codePointAt(0) ?? 0;
  if (code >= 65 && code <= 90) return 0.7;
  if (code >= 48 && code <= 57) return 0.62;
  if (code > 127) return 1;
  return 0.56;
}

function weightScale(weight: number): number {
  if (weight >= 700) return 1.08;
  if (weight >= 600) return 1.04;
  return 1;
}

/** Arial-like width used when a canvas is not available. Deterministic. */
export function estimateWidth(text: string, fontSize: number, fontWeight: number, trackingEm: number): number {
  const glyphs = [...text];
  if (glyphs.length === 0) return 0;
  const base = glyphs.reduce((sum, char) => sum + unit(char), 0) * fontSize * weightScale(fontWeight);
  const tracking = trackingEm * fontSize * Math.max(0, glyphs.length - 1);
  return Math.max(base * 0.4, base + tracking);
}

let canvas: HTMLCanvasElement | null = null;

/** Real glyph width in the browser. Falls back to the estimate in Node tests. */
export function measureForRender(
  text: string,
  fontSize: number,
  fontFamily: string,
  fontWeight: number,
  trackingEm: number,
): number {
  if (typeof document === "undefined") {
    return estimateWidth(text, fontSize, fontWeight, trackingEm);
  }
  if (!canvas) canvas = document.createElement("canvas");
  const context = canvas.getContext("2d");
  if (!context) return estimateWidth(text, fontSize, fontWeight, trackingEm);
  context.font = `${fontWeight} ${fontSize}px ${fontFamily}`;
  const measured = context.measureText(text).width;
  const tracking = trackingEm * fontSize * Math.max(0, [...text].length - 1);
  const width = measured + tracking;
  if (!Number.isFinite(width) || width <= 0) {
    return estimateWidth(text, fontSize, fontWeight, trackingEm);
  }
  return width;
}
