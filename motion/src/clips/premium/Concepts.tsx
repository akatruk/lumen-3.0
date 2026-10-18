import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import { blue, check, gold, line, paper } from "./tokens";

export function ShieldPulse() {
  const frame = useCurrentFrame();
  const breath = 0.96 + Math.sin((frame / 120) * Math.PI * 2) * 0.04;
  const draw = interpolate(frame, [0, 36], [0, 1], {
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  const opacity = interpolate(frame, [0, 8], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ backgroundColor: "transparent", opacity }}>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
        <svg width="560" height="640" viewBox="0 0 120 140" style={{ transform: `scale(${breath})` }}>
          <path
            d="M60 18 L96 34 V70 C96 98 78 116 60 124 C42 116 24 98 24 70 V34 Z"
            fill="none"
            stroke={gold}
            strokeWidth="3"
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeDasharray="260"
            strokeDashoffset={260 * (1 - draw)}
          />
          <path
            d="M44 72 l12 12 22-28"
            fill="none"
            stroke={check}
            strokeWidth="4"
            strokeLinecap="round"
            strokeLinejoin="round"
            opacity={interpolate(frame, [40, 70], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })}
          />
        </svg>
      </AbsoluteFill>
    </AbsoluteFill>
  );
}

export function FolderReveal() {
  const frame = useCurrentFrame();
  const open = interpolate(frame, [12, 70], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  const opacity = interpolate(frame, [0, 8], [0, 1], { extrapolateRight: "clamp" });
  const flap = interpolate(open, [0, 1], [0, -28]);

  return (
    <AbsoluteFill style={{ backgroundColor: "transparent", opacity }}>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
        <svg width="640" height="520" viewBox="0 0 200 160">
          <rect x="30" y="48" width="140" height="90" rx="8" fill={paper} />
          <rect x="30" y="48" width="140" height="90" rx="8" fill="none" stroke={gold} strokeWidth="2.4" />
          <g transform={`translate(0 ${flap})`}>
            <path d="M30 48 H88 L100 34 H170 V48 Z" fill={paper} stroke={gold} strokeWidth="2.4" strokeLinejoin="round" />
          </g>
          <rect
            x="48"
            y={70 - open * 10}
            width="104"
            height="18"
            rx="4"
            fill={line}
            opacity={0.55 * open}
          />
          <rect
            x="48"
            y={96 - open * 8}
            width="80"
            height="12"
            rx="4"
            fill={blue}
            opacity={0.35 * open}
          />
        </svg>
      </AbsoluteFill>
    </AbsoluteFill>
  );
}

export function PathDraw() {
  const frame = useCurrentFrame();
  const draw = interpolate(frame, [8, 95], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.inOut(Easing.cubic),
  });
  const opacity = interpolate(frame, [0, 8], [0, 1], { extrapolateRight: "clamp" });
  const len = 280;

  return (
    <AbsoluteFill style={{ backgroundColor: "transparent", opacity }}>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
        <svg width="720" height="520" viewBox="0 0 240 160">
          <path
            d="M28 120 C 70 120, 70 40, 120 40 S 170 120, 212 50"
            fill="none"
            stroke={gold}
            strokeWidth="3"
            strokeLinecap="round"
            strokeDasharray={len}
            strokeDashoffset={len * (1 - draw)}
          />
          {[
            [28, 120, 0.05],
            [120, 40, 0.45],
            [212, 50, 0.92],
          ].map(([cx, cy, at], i) => (
            <circle key={i} cx={cx} cy={cy} r="6" fill={gold} opacity={draw > at ? 1 : 0} />
          ))}
        </svg>
      </AbsoluteFill>
    </AbsoluteFill>
  );
}

export function CheckStamp() {
  const frame = useCurrentFrame();
  const pop = interpolate(frame, [20, 55], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.back(1.4)),
  });
  const draw = interpolate(frame, [48, 90], [22, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const opacity = interpolate(frame, [0, 8], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ backgroundColor: "transparent", opacity }}>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
        <svg width="520" height="520" viewBox="0 0 160 160">
          <rect x="28" y="36" width="104" height="88" rx="10" fill={paper} opacity={0.95} />
          <path d="M44 58h72M44 74h72M44 90h48" stroke={line} strokeWidth="3" strokeLinecap="round" />
          <g transform={`translate(80 80) scale(${0.6 + pop * 0.4}) translate(-80 -80)`} opacity={pop}>
            <circle cx="112" cy="104" r="28" fill="none" stroke={check} strokeWidth="4" />
            <path
              d="M98 104 l10 10 18-22"
              fill="none"
              stroke={check}
              strokeWidth="5"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeDasharray="22"
              strokeDashoffset={draw}
            />
          </g>
        </svg>
      </AbsoluteFill>
    </AbsoluteFill>
  );
}
