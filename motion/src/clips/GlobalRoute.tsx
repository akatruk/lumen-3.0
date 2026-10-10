import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";

const blue = "#7EB6C9";
const gold = "#E0B15A";

export function GlobalRoute() {
  const frame = useCurrentFrame();
  const draw = interpolate(frame, [10, 80], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.inOut(Easing.cubic) });
  const spin = interpolate(frame, [0, 119], [-6, 6]);
  const dash = 180 * (1 - draw);

  return (
    <AbsoluteFill style={{ backgroundColor: "transparent" }}>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
        <svg width="720" height="720" viewBox="0 0 200 200" style={{ transform: `rotate(${spin}deg)` }}>
          <g fill="none" stroke={blue} strokeWidth="1.6">
            <circle cx="100" cy="100" r="72" />
            <ellipse cx="100" cy="100" rx="32" ry="72" />
            <ellipse cx="100" cy="100" rx="72" ry="28" />
            <path d="M40 70h120M40 130h120" />
          </g>
          <path
            d="M48 118 C 80 60, 130 50, 158 96"
            fill="none"
            stroke={gold}
            strokeWidth="2.4"
            strokeLinecap="round"
            strokeDasharray="180"
            strokeDashoffset={dash}
          />
          {[
            [48, 118, 18],
            [104, 62, 42],
            [158, 96, 70],
          ].map(([cx, cy, at], index) => (
            <circle key={index} cx={cx} cy={cy} r="4" fill={gold} opacity={frame > at ? 1 : 0} />
          ))}
        </svg>
      </AbsoluteFill>
    </AbsoluteFill>
  );
}
