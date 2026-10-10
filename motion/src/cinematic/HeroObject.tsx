import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import { theme } from "../themes/tokens";

const clamp = { extrapolateLeft: "clamp" as const, extrapolateRight: "clamp" as const };

export type HeroObjectKind = "passport" | "key" | "globe" | "house";

/** SVG hero objects — preferred over random video gen for product icons. */
export function HeroObject({
  kind = "passport",
  frames,
}: {
  kind?: HeroObjectKind;
  frames: number;
}) {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 10], [0, 1], clamp);
  const y = interpolate(frame, [0, Math.min(20, frames)], [36, 0], {
    ...clamp,
    easing: Easing.out(Easing.cubic),
  });
  const float = interpolate(frame % 90, [0, 45, 90], [0, -8, 0], clamp);

  return (
    <AbsoluteFill style={{ opacity, transform: `translateY(${y + float}px)`, alignItems: "center", justifyContent: "center" }}>
      {kind === "passport" ? <PassportMark /> : null}
      {kind === "key" ? <KeyMark /> : null}
      {kind === "globe" ? <GlobeMark /> : null}
      {kind === "house" ? <HouseMark /> : null}
    </AbsoluteFill>
  );
}

function PassportMark() {
  return (
    <svg width="360" height="460" viewBox="0 0 180 230">
      <rect x="20" y="16" width="140" height="198" rx="16" fill={theme.color.paper} stroke={theme.color.accent} strokeWidth="4" />
      <rect x="40" y="48" width="100" height="12" rx="4" fill={theme.color.lineStrong} />
      <circle cx="90" cy="120" r="34" fill="none" stroke={theme.color.accent} strokeWidth="5" />
      <rect x="40" y="170" width="100" height="8" rx="4" fill={theme.color.line} />
    </svg>
  );
}

function KeyMark() {
  return (
    <svg width="420" height="220" viewBox="0 0 210 110">
      <circle cx="48" cy="55" r="30" fill="none" stroke={theme.color.accent} strokeWidth="8" />
      <circle cx="48" cy="55" r="10" fill={theme.color.bg} />
      <line x1="78" y1="55" x2="190" y2="55" stroke={theme.color.accent} strokeWidth="8" strokeLinecap="round" />
      <line x1="160" y1="55" x2="160" y2="78" stroke={theme.color.accent} strokeWidth="8" strokeLinecap="round" />
      <line x1="180" y1="55" x2="180" y2="72" stroke={theme.color.accent} strokeWidth="8" strokeLinecap="round" />
    </svg>
  );
}

function GlobeMark() {
  return (
    <svg width="420" height="420" viewBox="0 0 200 200">
      <circle cx="100" cy="100" r="72" fill="none" stroke={theme.color.accent} strokeWidth="5" />
      <ellipse cx="100" cy="100" rx="36" ry="72" fill="none" stroke={theme.color.lineStrong} strokeWidth="4" />
      <line x1="28" y1="100" x2="172" y2="100" stroke={theme.color.lineStrong} strokeWidth="4" />
      <path d="M40 60 C80 48, 120 48, 160 60" fill="none" stroke={theme.color.line} strokeWidth="3" />
      <path d="M40 140 C80 152, 120 152, 160 140" fill="none" stroke={theme.color.line} strokeWidth="3" />
    </svg>
  );
}

function HouseMark() {
  return (
    <svg width="420" height="360" viewBox="0 0 200 170">
      <path d="M20 80 L100 20 L180 80" fill="none" stroke={theme.color.accent} strokeWidth="7" strokeLinejoin="round" />
      <rect x="40" y="80" width="120" height="70" fill={theme.color.bgElevated} stroke={theme.color.lineStrong} strokeWidth="5" />
      <rect x="85" y="105" width="30" height="45" fill={theme.color.bg} stroke={theme.color.accent} strokeWidth="4" />
    </svg>
  );
}
