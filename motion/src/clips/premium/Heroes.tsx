import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import { blue, gold, line, mint, paper } from "./tokens";

export function GrowthArrow() {
  const frame = useCurrentFrame();
  const rise = interpolate(frame, [8, 90], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  const opacity = interpolate(frame, [0, 10], [0, 1], { extrapolateRight: "clamp" });
  const y = interpolate(rise, [0, 1], [160, 0]);
  const trail = interpolate(frame, [40, 100], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ backgroundColor: "transparent", opacity }}>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
        <svg width="640" height="720" viewBox="0 0 200 240">
          <path
            d={`M40 ${200 - trail * 120} L100 ${40 + (1 - rise) * 160} L160 ${200 - trail * 80}`}
            fill="none"
            stroke={mint}
            strokeWidth="2"
            opacity={0.35}
            strokeLinecap="round"
          />
          <g transform={`translate(0 ${y})`}>
            <line x1="100" y1="180" x2="100" y2="56" stroke={gold} strokeWidth="4" strokeLinecap="round" />
            <path d="M100 40 l-18 28 h36 z" fill={gold} />
          </g>
        </svg>
      </AbsoluteFill>
    </AbsoluteFill>
  );
}

export function RiskFall() {
  const frame = useCurrentFrame();
  const fall = interpolate(frame, [8, 90], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.in(Easing.cubic),
  });
  const opacity = interpolate(frame, [0, 10], [0, 1], { extrapolateRight: "clamp" });
  const y = interpolate(fall, [0, 1], [0, 140]);

  return (
    <AbsoluteFill style={{ backgroundColor: "transparent", opacity }}>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
        <svg width="640" height="720" viewBox="0 0 200 240">
          <path
            d={`M40 60 L100 ${60 + fall * 140} L160 ${80 + fall * 100}`}
            fill="none"
            stroke={blue}
            strokeWidth="2"
            opacity={0.35}
            strokeLinecap="round"
          />
          <g transform={`translate(0 ${y})`}>
            <line x1="100" y1="56" x2="100" y2="180" stroke={gold} strokeWidth="4" strokeLinecap="round" />
            <path d="M100 198 l-18 -28 h36 z" fill={gold} />
          </g>
        </svg>
      </AbsoluteFill>
    </AbsoluteFill>
  );
}

export function DeadlineScale() {
  const frame = useCurrentFrame();
  const draw = interpolate(frame, [6, 50], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  const mark = interpolate(frame, [48, 88], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  const opacity = interpolate(frame, [0, 8], [0, 1], { extrapolateRight: "clamp" });
  const x = 36 + draw * 128;

  return (
    <AbsoluteFill style={{ backgroundColor: "transparent", opacity }}>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
        <svg width="760" height="320" viewBox="0 0 240 100">
          <line x1="20" y1="55" x2={20 + draw * 200} y2="55" stroke={line} strokeWidth="3" strokeLinecap="round" />
          {[0, 0.25, 0.5, 0.75, 1].map((t, i) => (
            <line
              key={i}
              x1={20 + t * 200}
              y1="46"
              x2={20 + t * 200}
              y2="64"
              stroke={line}
              strokeWidth="2"
              opacity={draw > t ? 1 : 0}
            />
          ))}
          <g opacity={mark}>
            <circle cx={x} cy="55" r={6 + mark * 4} fill={gold} />
            <line x1={x} y1="28" x2={x} y2="44" stroke={gold} strokeWidth="3" strokeLinecap="round" />
          </g>
        </svg>
      </AbsoluteFill>
    </AbsoluteFill>
  );
}

export function StepCascade() {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 8], [0, 1], { extrapolateRight: "clamp" });
  const steps = [0, 1, 2, 3, 4].map((index) => {
    const start = 8 + index * 14;
    const t = interpolate(frame, [start, start + 16], [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: Easing.out(Easing.cubic),
    });
    return { index, t, y: interpolate(t, [0, 1], [24, 0]) };
  });

  return (
    <AbsoluteFill style={{ backgroundColor: "transparent", opacity }}>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
        <svg width="520" height="720" viewBox="0 0 160 240">
          {steps.map((step) => (
            <g key={step.index} opacity={step.t} transform={`translate(0 ${step.index * 40 + step.y})`}>
              <circle cx="28" cy="28" r="10" fill="none" stroke={gold} strokeWidth="2.4" />
              <circle cx="28" cy="28" r="4" fill={step.t > 0.85 ? gold : "none"} stroke={gold} strokeWidth="2" />
              <rect x="52" y="20" width={70 + step.index * 6} height="16" rx="8" fill={paper} opacity={0.92} />
              <rect x="52" y="20" width={(70 + step.index * 6) * step.t} height="16" rx="8" fill={mint} opacity={0.35} />
            </g>
          ))}
        </svg>
      </AbsoluteFill>
    </AbsoluteFill>
  );
}

export function CompareColumns() {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 8], [0, 1], { extrapolateRight: "clamp" });
  const left = interpolate(frame, [10, 48], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  const right = interpolate(frame, [28, 66], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });

  const column = (x: number, t: number, accent: string) => (
    <g opacity={t} transform={`translate(${x} ${interpolate(t, [0, 1], [30, 0])})`}>
      <rect x="0" y="0" width="70" height="140" rx="10" fill={paper} opacity={0.95} />
      <rect x="12" y="18" width="46" height="10" rx="5" fill={accent} opacity={0.55} />
      <rect x="12" y="42" width="46" height="8" rx="4" fill={line} />
      <rect x="12" y="60" width="36" height="8" rx="4" fill={line} />
      <rect x="12" y="78" width="42" height="8" rx="4" fill={line} />
      <circle cx="35" cy="118" r="12" fill="none" stroke={accent} strokeWidth="2.4" />
    </g>
  );

  return (
    <AbsoluteFill style={{ backgroundColor: "transparent", opacity }}>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
        <svg width="640" height="640" viewBox="0 0 200 180">
          {column(18, left, gold)}
          {column(112, right, blue)}
        </svg>
      </AbsoluteFill>
    </AbsoluteFill>
  );
}
