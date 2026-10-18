import { AbsoluteFill, useCurrentFrame } from "remotion";
import { blue, gold, mint, navy } from "./tokens";

export function NavyBreathe() {
  const frame = useCurrentFrame();
  const turn = (frame / 120) * Math.PI * 2;
  const glow = 0.12 + Math.sin(turn) * 0.04;

  return (
    <AbsoluteFill style={{ backgroundColor: navy }}>
      <svg width="1080" height="1920" viewBox="0 0 1080 1920">
        <circle cx={540 + Math.sin(turn) * 40} cy={720} r={420} fill={blue} opacity={glow} />
        <circle cx={480 + Math.cos(turn) * 50} cy={1280} r={380} fill={gold} opacity={glow * 0.55} />
      </svg>
    </AbsoluteFill>
  );
}

export function SoftGrid() {
  const frame = useCurrentFrame();
  const drift = (frame / 120) * 40;
  const lines = Array.from({ length: 14 }, (_, i) => i);

  return (
    <AbsoluteFill style={{ backgroundColor: navy }}>
      <svg width="1080" height="1920" viewBox="0 0 1080 1920">
        {lines.map((i) => (
          <line
            key={`v${i}`}
            x1={40 + i * 80 + (drift % 80)}
            y1="0"
            x2={40 + i * 80 + (drift % 80)}
            y2="1920"
            stroke={blue}
            strokeWidth="1"
            opacity={0.12}
          />
        ))}
        {lines.map((i) => (
          <line
            key={`h${i}`}
            x1="0"
            y1={40 + i * 140 - (drift % 140)}
            x2="1080"
            y2={40 + i * 140 - (drift % 140)}
            stroke={mint}
            strokeWidth="1"
            opacity={0.1}
          />
        ))}
      </svg>
    </AbsoluteFill>
  );
}

export function GoldDust() {
  const frame = useCurrentFrame();
  const seeds = Array.from({ length: 28 }, (_, i) => {
    const x = (i * 97 + 41) % 1080;
    const base = (i * 173 + 29) % 1920;
    const y = (base + frame * (1.2 + (i % 5) * 0.35)) % 1920;
    const r = 2 + (i % 4);
    return { x, y, r, o: 0.15 + (i % 5) * 0.05 };
  });

  return (
    <AbsoluteFill style={{ backgroundColor: navy }}>
      <svg width="1080" height="1920" viewBox="0 0 1080 1920">
        {seeds.map((p, i) => (
          <circle key={i} cx={p.x} cy={p.y} r={p.r} fill={i % 3 === 0 ? gold : blue} opacity={p.o} />
        ))}
      </svg>
    </AbsoluteFill>
  );
}
