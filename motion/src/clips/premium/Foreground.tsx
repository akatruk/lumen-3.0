import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import { blue, gold, mint } from "./tokens";

export function WipeArc() {
  const frame = useCurrentFrame();
  const sweep = interpolate(frame, [0, 100], [0, 1], {
    extrapolateRight: "clamp",
    easing: Easing.inOut(Easing.cubic),
  });
  const opacity = interpolate(frame, [0, 6, 100, 119], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const end = -90 + sweep * 220;

  return (
    <AbsoluteFill style={{ backgroundColor: "transparent", opacity }}>
      <svg width="1080" height="1920" viewBox="0 0 1080 1920">
        <path
          d={`M540 960 L540 220 A740 740 0 ${sweep > 0.5 ? 1 : 0} 1 ${540 + Math.cos((end * Math.PI) / 180) * 740} ${960 + Math.sin((end * Math.PI) / 180) * 740} Z`}
          fill={gold}
          opacity={0.18}
        />
        <path
          d="M540 220 A740 740 0 0 1 1040 1200"
          fill="none"
          stroke={gold}
          strokeWidth="4"
          strokeLinecap="round"
          strokeDasharray="1200"
          strokeDashoffset={1200 * (1 - sweep)}
        />
      </svg>
    </AbsoluteFill>
  );
}

export function RingReveal() {
  const frame = useCurrentFrame();
  const scale = interpolate(frame, [0, 70], [0.35, 1], {
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  const fade = interpolate(frame, [70, 110], [1, 0.35], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const opacity = interpolate(frame, [0, 8], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ backgroundColor: "transparent", opacity: opacity * fade }}>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
        <svg width="720" height="720" viewBox="0 0 200 200" style={{ transform: `scale(${scale})` }}>
          <circle cx="100" cy="100" r="78" fill="none" stroke={gold} strokeWidth="2.4" />
          <circle cx="100" cy="100" r="58" fill="none" stroke={blue} strokeWidth="1.6" opacity={0.7} />
          <circle cx="100" cy="100" r="18" fill="none" stroke={mint} strokeWidth="2" />
        </svg>
      </AbsoluteFill>
    </AbsoluteFill>
  );
}

export function DiagonalMask() {
  const frame = useCurrentFrame();
  const sweep = interpolate(frame, [0, 95], [-0.2, 1.2], {
    extrapolateRight: "clamp",
    easing: Easing.inOut(Easing.cubic),
  });
  const opacity = interpolate(frame, [0, 8, 100, 119], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const x = sweep * 1400 - 200;

  return (
    <AbsoluteFill style={{ backgroundColor: "transparent", opacity }}>
      <svg width="1080" height="1920" viewBox="0 0 1080 1920">
        <defs>
          <linearGradient id="pmDiag" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor={gold} stopOpacity="0" />
            <stop offset="45%" stopColor={gold} stopOpacity="0.28" />
            <stop offset="55%" stopColor={blue} stopOpacity="0.22" />
            <stop offset="100%" stopColor={blue} stopOpacity="0" />
          </linearGradient>
        </defs>
        <polygon points={`${x},0 ${x + 280},0 ${x - 120},1920 ${x - 400},1920`} fill="url(#pmDiag)" />
        <line
          x1={x + 80}
          y1="0"
          x2={x - 220}
          y2="1920"
          stroke={gold}
          strokeWidth="3"
          opacity={0.55}
        />
      </svg>
    </AbsoluteFill>
  );
}
