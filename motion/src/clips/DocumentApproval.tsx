import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";

const paper = "#F4EFE6";
const line = "#C8C0B4";
const check = "#3E8F62";

export function DocumentApproval() {
  const frame = useCurrentFrame();
  const cards = [0, 1, 2].map((index) => {
    const start = 6 + index * 12;
    const x = interpolate(frame, [start, start + 16], [80, index * 14], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: Easing.out(Easing.cubic),
    });
    const opacity = interpolate(frame, [start, start + 8], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
    return { x, opacity, index };
  });
  const draw = interpolate(frame, [62, 92], [28, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ backgroundColor: "transparent" }}>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
        <svg width="760" height="560" viewBox="0 0 240 180">
          {cards.map((card) => (
            <g key={card.index} opacity={card.opacity} transform={`translate(${card.x} ${card.index * 8})`}>
              <rect x="20" y="24" width="150" height="100" rx="6" fill={paper} />
              <path d="M36 52h90M36 68h90M36 84h60" stroke={line} strokeWidth="3" strokeLinecap="round" />
            </g>
          ))}
          <path
            d="M150 78 l14 14 28-32"
            fill="none"
            stroke={check}
            strokeWidth="6"
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeDasharray="28"
            strokeDashoffset={draw}
          />
        </svg>
      </AbsoluteFill>
    </AbsoluteFill>
  );
}
