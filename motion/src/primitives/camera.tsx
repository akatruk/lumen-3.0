import type { ReactNode } from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";

const clamp = { extrapolateLeft: "clamp" as const, extrapolateRight: "clamp" as const };

export function Zoom({
  children,
  to = 1.03,
  frames,
}: {
  children: ReactNode;
  to?: number;
  frames?: number;
}) {
  const frame = useCurrentFrame();
  const config = useVideoConfig();
  const duration = Math.max(1, frames ?? config.durationInFrames);
  const scale = interpolate(frame, [0, duration - 1], [1, to], clamp);
  return <AbsoluteFill style={{ transform: `scale(${scale})` }}>{children}</AbsoluteFill>;
}

export function Pan({
  children,
  amount = 20,
  frames,
}: {
  children: ReactNode;
  amount?: number;
  frames?: number;
}) {
  const frame = useCurrentFrame();
  const config = useVideoConfig();
  const duration = Math.max(1, frames ?? config.durationInFrames);
  const x = interpolate(frame, [0, duration - 1], [0, -amount], clamp);
  return <AbsoluteFill style={{ transform: `translateX(${x}px) scale(1.06)` }}>{children}</AbsoluteFill>;
}
