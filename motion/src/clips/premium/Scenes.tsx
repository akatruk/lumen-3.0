import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import { blue, check, gold, line, paper } from "./tokens";

export function ApprovalDesk() {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 8], [0, 1], { extrapolateRight: "clamp" });
  const cards = [0, 1, 2].map((index) => {
    const start = 6 + index * 12;
    const t = interpolate(frame, [start, start + 18], [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: Easing.out(Easing.cubic),
    });
    return { index, t, x: interpolate(t, [0, 1], [60, index * 12]) };
  });
  const stamp = interpolate(frame, [70, 100], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });

  return (
    <AbsoluteFill style={{ backgroundColor: "transparent", opacity }}>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
        <svg width="820" height="640" viewBox="0 0 260 200">
          <rect x="20" y="150" width="220" height="18" rx="6" fill={line} opacity={0.25} />
          {cards.map((card) => (
            <g key={card.index} opacity={card.t} transform={`translate(${card.x} ${20 + card.index * 10})`}>
              <rect x="40" y="30" width="150" height="100" rx="8" fill={paper} />
              <path d="M56 55h110M56 72h110M56 89h70" stroke={line} strokeWidth="3" strokeLinecap="round" />
            </g>
          ))}
          <g opacity={stamp} transform={`translate(170 110) scale(${0.7 + stamp * 0.3}) translate(-170 -110)`}>
            <circle cx="170" cy="110" r="26" fill="none" stroke={check} strokeWidth="4" />
            <path
              d="M156 110 l10 10 18-22"
              fill="none"
              stroke={check}
              strokeWidth="5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </g>
        </svg>
      </AbsoluteFill>
    </AbsoluteFill>
  );
}

export function MobilityPins() {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 8], [0, 1], { extrapolateRight: "clamp" });
  const draw = interpolate(frame, [12, 85], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.inOut(Easing.cubic),
  });
  const pins = [
    [48, 130, 18],
    [110, 56, 42],
    [168, 100, 72],
  ] as const;

  return (
    <AbsoluteFill style={{ backgroundColor: "transparent", opacity }}>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
        <svg width="720" height="720" viewBox="0 0 220 200">
          <circle cx="110" cy="100" r="78" fill="none" stroke={blue} strokeWidth="1.6" opacity={0.45} />
          <ellipse cx="110" cy="100" rx="34" ry="78" fill="none" stroke={blue} strokeWidth="1.2" opacity={0.35} />
          <path
            d="M48 130 C 78 70, 130 40, 168 100"
            fill="none"
            stroke={gold}
            strokeWidth="2.6"
            strokeLinecap="round"
            strokeDasharray="220"
            strokeDashoffset={220 * (1 - draw)}
          />
          {pins.map(([cx, cy, at], i) => {
            const on = frame > at;
            const drop = interpolate(frame, [at, at + 14], [-18, 0], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
              easing: Easing.out(Easing.cubic),
            });
            return (
              <g key={i} opacity={on ? 1 : 0} transform={`translate(0 ${drop})`}>
                <path d={`M${cx} ${cy - 16} c8 0 14 6 14 14 0 12 -14 22 -14 22 s-14 -10 -14 -22 c0 -8 6 -14 14 -14z`} fill={gold} />
                <circle cx={cx} cy={cy - 4} r="4" fill={paper} />
              </g>
            );
          })}
        </svg>
      </AbsoluteFill>
    </AbsoluteFill>
  );
}

export function ChoiceFork() {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 8], [0, 1], { extrapolateRight: "clamp" });
  const stem = interpolate(frame, [6, 40], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  const left = interpolate(frame, [36, 85], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  const right = interpolate(frame, [48, 95], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });

  return (
    <AbsoluteFill style={{ backgroundColor: "transparent", opacity }}>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
        <svg width="720" height="720" viewBox="0 0 200 200">
          <path
            d="M100 170 V110"
            fill="none"
            stroke={gold}
            strokeWidth="3"
            strokeLinecap="round"
            strokeDasharray="60"
            strokeDashoffset={60 * (1 - stem)}
          />
          <path
            d="M100 110 C 100 80, 70 70, 48 42"
            fill="none"
            stroke={gold}
            strokeWidth="3"
            strokeLinecap="round"
            strokeDasharray="120"
            strokeDashoffset={120 * (1 - left)}
          />
          <path
            d="M100 110 C 100 80, 130 70, 152 42"
            fill="none"
            stroke={blue}
            strokeWidth="3"
            strokeLinecap="round"
            strokeDasharray="120"
            strokeDashoffset={120 * (1 - right)}
          />
          <circle cx="48" cy="42" r="7" fill={gold} opacity={left} />
          <circle cx="152" cy="42" r="7" fill={blue} opacity={right} />
          <circle cx="100" cy="170" r="6" fill={gold} opacity={stem} />
        </svg>
      </AbsoluteFill>
    </AbsoluteFill>
  );
}
