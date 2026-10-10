import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";

const gold = "#E0B15A";
const blue = "#7EB6C9";

const pins = [
  { x: 70, y: 92, at: 8 },
  { x: 118, y: 70, at: 28 },
  { x: 150, y: 108, at: 48 },
  { x: 96, y: 128, at: 68 },
];

export function LocationPins() {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{ backgroundColor: "transparent" }}>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
        <svg width="720" height="720" viewBox="0 0 220 200">
          <path d="M50 140 C 90 40, 150 40, 180 120" fill="none" stroke={blue} strokeWidth="1.4" strokeDasharray="3 4" opacity="0.8" />
          {pins.map((pin) => {
            const drop = interpolate(frame, [pin.at, pin.at + 14], [-24, 0], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
              easing: Easing.out(Easing.cubic),
            });
            const opacity = interpolate(frame, [pin.at, pin.at + 6], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
            return (
              <g key={pin.at} transform={`translate(0 ${drop})`} opacity={opacity}>
                <path d={`M${pin.x} ${pin.y + 16} s10-9 10-16 a10 10 0 1 0-20 0 c0 7 10 16 10 16z`} fill="none" stroke={gold} strokeWidth="2.2" />
                <circle cx={pin.x} cy={pin.y} r="2.4" fill={gold} />
              </g>
            );
          })}
        </svg>
      </AbsoluteFill>
    </AbsoluteFill>
  );
}
