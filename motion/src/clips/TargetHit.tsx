import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";

const gold = "#E0B15A";

export function TargetHit() {
  const frame = useCurrentFrame();
  const ring = interpolate(frame, [0, 18], [0.72, 1], { extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) });
  const travel = interpolate(frame, [12, 68], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.inOut(Easing.cubic) });
  const x = interpolate(travel, [0, 1], [220, 0]);
  const y = interpolate(travel, [0, 1], [-220, 0]);
  const impact = interpolate(frame, [68, 84], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const opacity = interpolate(frame, [0, 8], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ backgroundColor: "transparent", opacity }}>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
        <svg width="640" height="640" viewBox="0 0 200 200" style={{ transform: `scale(${ring})` }}>
          <g fill="none" stroke={gold} strokeWidth="3" strokeLinecap="round">
            <circle cx="100" cy="100" r="78" />
            <circle cx="100" cy="100" r="48" />
            <circle cx="100" cy="100" r="18" />
          </g>
          <g transform={`translate(${x} ${y})`}>
            <line x1="150" y1="40" x2="104" y2="96" stroke={gold} strokeWidth="3" strokeLinecap="round" />
            <path d="M150 40 l-16 2 10 12 z" fill={gold} stroke="none" />
          </g>
          <circle cx="100" cy="100" r={18 + impact * 28} fill="none" stroke={gold} strokeWidth="2" opacity={1 - impact} />
        </svg>
      </AbsoluteFill>
    </AbsoluteFill>
  );
}
