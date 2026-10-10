export const CANVAS = {
  width: 1080,
  height: 1920,
  fps: 30,
} as const;

/** TikTok / Reels UI chrome. Text stays inside these insets. */
export const SAFE_INSET = {
  top: 180,
  right: 120,
  bottom: 320,
  left: 72,
} as const;

export type TypeRole = {
  min: number;
  max: number;
  weight: number;
  lineHeight: number;
  tracking: number;
};

export const theme = {
  color: {
    bg: "#12110F",
    bgElevated: "#1C1A17",
    ink: "#F6F1E8",
    inkSoft: "rgba(246,241,232,0.22)",
    inkFaint: "rgba(246,241,232,0.12)",
    muted: "#A79B8C",
    accent: "#E0B15A",
    accentInk: "#1A1408",
    paper: "#F4EFE6",
    paperInk: "#1A1714",
    line: "rgba(246,241,232,0.16)",
    lineStrong: "rgba(246,241,232,0.4)",
    scrim: "rgba(18,17,15,0.55)",
  },
  gradient: {
    speaker: "linear-gradient(165deg, #3A332C 0%, #16130F 72%)",
    broll: "linear-gradient(180deg, #314047 0%, #141A1E 100%)",
    background: "linear-gradient(180deg, #243036 0%, #101418 100%)",
    image: "linear-gradient(180deg, #4A4036 0%, #1A1612 100%)",
    screenshot: "linear-gradient(180deg, #E8E2D8 0%, #CFC6BA 100%)",
    scrimBottom:
      "linear-gradient(to top, rgba(18,17,15,0.92) 0%, rgba(18,17,15,0.45) 42%, rgba(18,17,15,0) 100%)",
    scrimCenter:
      "linear-gradient(180deg, rgba(18,17,15,0.35) 0%, rgba(18,17,15,0.62) 48%, rgba(18,17,15,0.78) 100%)",
    vignette:
      "radial-gradient(ellipse at center, rgba(18,17,15,0) 40%, rgba(18,17,15,0.45) 100%)",
  },
  font: {
    sans: 'Arial, "Helvetica Neue", Helvetica, sans-serif',
    numeric: "tabular-nums",
    smoothing: "antialiased",
  },
  type: {
    hook: { min: 54, max: 128, weight: 600, lineHeight: 1.02, tracking: -0.03 },
    number: { min: 120, max: 420, weight: 600, lineHeight: 0.9, tracking: -0.045 },
    title: { min: 40, max: 84, weight: 600, lineHeight: 1.05, tracking: -0.03 },
    caption: { min: 36, max: 64, weight: 600, lineHeight: 1.16, tracking: -0.02 },
    captionQuiet: { min: 28, max: 40, weight: 500, lineHeight: 1.25, tracking: 0 },
    support: { min: 28, max: 48, weight: 500, lineHeight: 1.2, tracking: -0.01 },
    step: { min: 24, max: 40, weight: 600, lineHeight: 1.15, tracking: -0.02 },
    label: { min: 18, max: 28, weight: 500, lineHeight: 1.25, tracking: 0.04 },
  } satisfies Record<string, TypeRole>,
  space: {
    xs: 8,
    sm: 16,
    md: 24,
    lg: 40,
    xl: 64,
    xxl: 96,
  },
  radius: {
    sm: 10,
    md: 18,
    lg: 28,
    pill: 999,
  },
  shadow: {
    soft: "0 24px 60px rgba(0,0,0,0.35)",
    ring: "0 0 0 1px rgba(246,241,232,0.22)",
    paper: "0 30px 70px rgba(0,0,0,0.28)",
  },
  border: {
    hairline: "1px solid rgba(246,241,232,0.16)",
    strong: "2px solid rgba(224,177,90,0.9)",
    paper: "1px solid rgba(26,23,20,0.08)",
  },
} as const;

export type Theme = typeof theme;
