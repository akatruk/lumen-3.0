/**
 * Adaptive connector contrast — analyze the full path against the background,
 * not just endpoints. Fixes gold (#E0B15A) on beige paper plates.
 */

export type Rgb = { r: number; g: number; b: number; a?: number };

export type PathPoint = { x: number; y: number };

export type BackgroundProbe =
  | string
  | { kind: "solid"; color: string }
  | { kind: "gradient"; stops: Array<{ offset: number; color: string }> }
  | { kind: "samples"; colors: string[] }
  | { kind: "regions"; regions: Array<{ x0: number; y0: number; x1: number; y1: number; color: string }> };

export type SceneTheme = "ink" | "paper" | "photo" | "navy" | "gold_veil" | "auto";

export type AdaptiveLineInput = {
  background: BackgroundProbe;
  path: PathPoint[];
  preferredColor: string;
  strokeWidth?: number;
  sceneTheme?: SceneTheme;
  /** Minimum WCAG contrast ratio along the path (default 3.0 for graphics). */
  minContrast?: number;
};

export type AdaptiveLineStyle = {
  strokeColor: string;
  outlineColor: string | null;
  outlineWidth: number;
  shadow: string | null;
  contrastStatus: "ok" | "outlined" | "recolored" | "failed";
  /** Worst contrast ratio observed along the path for the chosen stroke. */
  minRatio: number;
};

const FALLBACK_DARK = "#1A1714";
const FALLBACK_LIGHT = "#F6F1E8";
const OUTLINE_DARK = "rgba(18,17,15,0.92)";
const OUTLINE_LIGHT = "rgba(246,241,232,0.92)";

export function parseColor(input: string): Rgb | null {
  const s = String(input || "").trim();
  if (!s) return null;
  if (s.startsWith("#")) {
    const hex = s.slice(1);
    if (hex.length === 3) {
      const r = parseInt(hex[0] + hex[0], 16);
      const g = parseInt(hex[1] + hex[1], 16);
      const b = parseInt(hex[2] + hex[2], 16);
      return Number.isFinite(r + g + b) ? { r, g, b, a: 1 } : null;
    }
    if (hex.length === 6 || hex.length === 8) {
      const r = parseInt(hex.slice(0, 2), 16);
      const g = parseInt(hex.slice(2, 4), 16);
      const b = parseInt(hex.slice(4, 6), 16);
      const a = hex.length === 8 ? parseInt(hex.slice(6, 8), 16) / 255 : 1;
      return Number.isFinite(r + g + b) ? { r, g, b, a } : null;
    }
    return null;
  }
  const m = s.match(
    /^rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)(?:\s*,\s*([\d.]+))?\s*\)$/i,
  );
  if (!m) return null;
  return {
    r: Math.max(0, Math.min(255, Number(m[1]))),
    g: Math.max(0, Math.min(255, Number(m[2]))),
    b: Math.max(0, Math.min(255, Number(m[3]))),
    a: m[4] != null ? Math.max(0, Math.min(1, Number(m[4]))) : 1,
  };
}

function srgbToLinear(c: number): number {
  const v = c / 255;
  return v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
}

export function relativeLuminance(rgb: Rgb): number {
  const r = srgbToLinear(rgb.r);
  const g = srgbToLinear(rgb.g);
  const b = srgbToLinear(rgb.b);
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

export function contrastRatio(a: Rgb, b: Rgb): number {
  const la = relativeLuminance(a);
  const lb = relativeLuminance(b);
  const lighter = Math.max(la, lb);
  const darker = Math.min(la, lb);
  return (lighter + 0.05) / (darker + 0.05);
}

function blendOver(fg: Rgb, bg: Rgb): Rgb {
  const a = fg.a == null ? 1 : fg.a;
  if (a >= 0.999) return { r: fg.r, g: fg.g, b: fg.b, a: 1 };
  const inv = 1 - a;
  return {
    r: fg.r * a + bg.r * inv,
    g: fg.g * a + bg.g * inv,
    b: fg.b * a + bg.b * inv,
    a: 1,
  };
}

function themeFallbackBg(sceneTheme: SceneTheme | undefined): string {
  switch (sceneTheme) {
    case "paper":
      return "#F4EFE6";
    case "navy":
      return "#0F1720";
    case "gold_veil":
      return "#2A2520";
    case "photo":
      return "#3A332C";
    case "ink":
    case "auto":
    default:
      return "#12110F";
  }
}

/** Sample background colors along the full connector path (not endpoints only). */
export function sampleBackgroundAlongPath(
  background: BackgroundProbe,
  path: PathPoint[],
  sceneTheme?: SceneTheme,
): Rgb[] {
  const fallback = parseColor(themeFallbackBg(sceneTheme))!;
  const pts = path.length >= 2 ? path : [{ x: 0, y: 0 }, { x: 1, y: 0 }];

  if (typeof background === "string") {
    const c = parseColor(background) || fallback;
    return pts.map(() => c);
  }
  if (background.kind === "solid") {
    const c = parseColor(background.color) || fallback;
    return pts.map(() => c);
  }
  if (background.kind === "samples") {
    const colors = background.colors
      .map((c) => parseColor(c))
      .filter((c): c is Rgb => Boolean(c));
    if (!colors.length) return pts.map(() => fallback);
    if (colors.length === 1) return pts.map(() => colors[0]);
    // Resample evenly onto path length.
    return pts.map((_, i) => {
      const t = pts.length <= 1 ? 0 : i / (pts.length - 1);
      const idx = Math.min(colors.length - 1, Math.round(t * (colors.length - 1)));
      return colors[idx];
    });
  }
  if (background.kind === "gradient") {
    const stops = [...background.stops]
      .map((s) => ({ offset: s.offset, rgb: parseColor(s.color) }))
      .filter((s): s is { offset: number; rgb: Rgb } => Boolean(s.rgb))
      .sort((a, b) => a.offset - b.offset);
    if (!stops.length) return pts.map(() => fallback);
    return pts.map((_, i) => {
      const t = pts.length <= 1 ? 0 : i / (pts.length - 1);
      if (t <= stops[0].offset) return stops[0].rgb;
      if (t >= stops[stops.length - 1].offset) return stops[stops.length - 1].rgb;
      for (let k = 0; k < stops.length - 1; k++) {
        const a = stops[k];
        const b = stops[k + 1];
        if (t >= a.offset && t <= b.offset) {
          const u = (t - a.offset) / Math.max(1e-6, b.offset - a.offset);
          return {
            r: a.rgb.r + (b.rgb.r - a.rgb.r) * u,
            g: a.rgb.g + (b.rgb.g - a.rgb.g) * u,
            b: a.rgb.b + (b.rgb.b - a.rgb.b) * u,
            a: 1,
          };
        }
      }
      return stops[stops.length - 1].rgb;
    });
  }
  if (background.kind === "regions") {
    return pts.map((p) => {
      for (const r of background.regions) {
        if (p.x >= r.x0 && p.x <= r.x1 && p.y >= r.y0 && p.y <= r.y1) {
          return parseColor(r.color) || fallback;
        }
      }
      return fallback;
    });
  }
  return pts.map(() => fallback);
}

function minContrastAlong(stroke: Rgb, backgrounds: Rgb[]): number {
  let worst = Infinity;
  for (const bg of backgrounds) {
    const blended = blendOver(stroke, bg);
    worst = Math.min(worst, contrastRatio(blended, bg));
  }
  return worst === Infinity ? 1 : worst;
}

function densifyPath(path: PathPoint[], samples = 12): PathPoint[] {
  if (path.length < 2) return path.length ? path : [{ x: 0, y: 0 }, { x: 1, y: 0 }];
  const out: PathPoint[] = [];
  for (let i = 0; i < path.length - 1; i++) {
    const a = path[i];
    const b = path[i + 1];
    const segSamples = Math.max(2, Math.ceil(samples / (path.length - 1)));
    for (let s = 0; s < segSamples; s++) {
      const t = s / segSamples;
      out.push({ x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t });
    }
  }
  out.push(path[path.length - 1]);
  return out;
}

function meanLuminance(colors: Rgb[]): number {
  if (!colors.length) return 0.2;
  return colors.reduce((acc, c) => acc + relativeLuminance(c), 0) / colors.length;
}

/**
 * Resolve stroke + outline so the full connector remains readable on mixed plates.
 */
export function adaptiveLineStyle(input: AdaptiveLineInput): AdaptiveLineStyle {
  const strokeWidth = input.strokeWidth ?? 3;
  const minContrast = input.minContrast ?? 3.0;
  const path = densifyPath(input.path, 16);
  const backgrounds = sampleBackgroundAlongPath(input.background, path, input.sceneTheme);
  const preferred = parseColor(input.preferredColor) || parseColor("#E0B15A")!;
  const preferredRatio = minContrastAlong(preferred, backgrounds);
  const avgLum = meanLuminance(backgrounds);
  const ink = parseColor(FALLBACK_DARK)!;
  const paper = parseColor(FALLBACK_LIGHT)!;

  if (preferredRatio >= minContrast) {
    return {
      strokeColor: input.preferredColor,
      outlineColor: null,
      outlineWidth: 0,
      shadow: null,
      contrastStatus: "ok",
      minRatio: preferredRatio,
    };
  }

  // Soft backgrounds (paper/beige): dark ink outline under gold; hard-fail → recolor ink.
  const outlineCandidate = avgLum > 0.45 ? OUTLINE_DARK : OUTLINE_LIGHT;
  const outlineRgb = parseColor(outlineCandidate)!;
  // Approximate outlined stroke as preferred composited over a thick outline halo on bg.
  const haloBg = backgrounds.map((bg) => blendOver({ ...outlineRgb, a: 0.85 }, bg));
  const outlinedRatio = minContrastAlong(preferred, haloBg);

  if (outlinedRatio >= minContrast * 0.85) {
    return {
      strokeColor: input.preferredColor,
      outlineColor: outlineCandidate,
      outlineWidth: Math.max(2, strokeWidth * 0.85),
      shadow:
        avgLum > 0.45
          ? `0 0 ${Math.round(strokeWidth * 1.5)}px rgba(18,17,15,0.55)`
          : `0 0 ${Math.round(strokeWidth * 1.5)}px rgba(246,241,232,0.35)`,
      contrastStatus: "outlined",
      minRatio: outlinedRatio,
    };
  }

  const inkRatio = minContrastAlong(ink, backgrounds);
  const paperRatio = minContrastAlong(paper, backgrounds);
  if (inkRatio >= paperRatio && inkRatio >= minContrast * 0.9) {
    return {
      strokeColor: FALLBACK_DARK,
      outlineColor: OUTLINE_LIGHT,
      outlineWidth: Math.max(1.5, strokeWidth * 0.55),
      shadow: "0 1px 3px rgba(246,241,232,0.35)",
      contrastStatus: "recolored",
      minRatio: inkRatio,
    };
  }
  if (paperRatio >= minContrast * 0.9) {
    return {
      strokeColor: FALLBACK_LIGHT,
      outlineColor: OUTLINE_DARK,
      outlineWidth: Math.max(1.5, strokeWidth * 0.55),
      shadow: "0 1px 3px rgba(18,17,15,0.45)",
      contrastStatus: "recolored",
      minRatio: paperRatio,
    };
  }

  // Last resort: high-contrast pair with thick outline.
  const pick = avgLum > 0.45 ? FALLBACK_DARK : FALLBACK_LIGHT;
  const pickRatio = minContrastAlong(parseColor(pick)!, backgrounds);
  return {
    strokeColor: pick,
    outlineColor: avgLum > 0.45 ? OUTLINE_LIGHT : OUTLINE_DARK,
    outlineWidth: Math.max(2.5, strokeWidth),
    shadow: avgLum > 0.45 ? "0 0 6px rgba(18,17,15,0.5)" : "0 0 6px rgba(246,241,232,0.4)",
    contrastStatus: pickRatio >= 2.0 ? "recolored" : "failed",
    minRatio: pickRatio,
  };
}

/** Convenience: SVG path string "M x y L x y …" → points for analysis. */
export function pathFromSvgCommands(d: string): PathPoint[] {
  const nums = d.match(/-?\d*\.?\d+/g)?.map(Number) || [];
  const pts: PathPoint[] = [];
  for (let i = 0; i + 1 < nums.length; i += 2) {
    pts.push({ x: nums[i], y: nums[i + 1] });
  }
  return pts.length >= 2 ? pts : [{ x: 0, y: 0 }, { x: 100, y: 0 }];
}

/** Infer scene theme from a plate treatment / background plate id. */
export function sceneThemeFromPlate(plate?: string | null): SceneTheme {
  const p = String(plate || "").toLowerCase();
  if (
    p.includes("paper") ||
    p.includes("beige") ||
    p.includes("cream") ||
    p.includes("screenshot") ||
    p.includes("sand") ||
    p.includes("warm_slate") ||
    p.includes("mist")
  ) {
    return "paper";
  }
  if (p.includes("navy") || p.includes("grid") || p.includes("teal") || p.includes("midnight")) return "navy";
  if (p.includes("gold") || p.includes("amber")) return "gold_veil";
  if (p.includes("photo") || p.includes("broll") || p.includes("image")) return "photo";
  if (p.includes("ink") || p.includes("vignette") || p.includes("graphite") || p.includes("olive") || p.includes("dark")) {
    return "ink";
  }
  return "auto";
}
