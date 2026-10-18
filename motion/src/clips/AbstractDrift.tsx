import { AbsoluteFill, useCurrentFrame } from "remotion";

const gold = "#E0B15A";
const blue = "#7EB6C9";
const mint = "#8FCBB4";

/** A slow drift that returns to the same place at frame 120, so it can loop. */
export function AbstractDrift() {
  const frame = useCurrentFrame();
  const turn = (frame / 120) * Math.PI * 2;
  const blobs = [
    { color: gold, x: 540 + Math.sin(turn) * 80, y: 700 + Math.cos(turn) * 60, r: 280 },
    { color: blue, x: 640 + Math.cos(turn) * 90, y: 1100 + Math.sin(turn) * 70, r: 320 },
    { color: mint, x: 420 + Math.sin(turn + 1) * 50, y: 900 + Math.cos(turn + 1) * 40, r: 220 },
  ];
  return (
    <AbsoluteFill style={{ backgroundColor: "transparent" }}>
      <svg width="1080" height="1920" viewBox="0 0 1080 1920">
        {blobs.map((blob) => (
          <circle key={blob.color} cx={blob.x} cy={blob.y} r={blob.r} fill={blob.color} opacity="0.22" />
        ))}
      </svg>
    </AbsoluteFill>
  );
}
