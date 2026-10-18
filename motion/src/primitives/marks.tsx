import type { ReactNode } from "react";
import { Easing, interpolate, useCurrentFrame } from "remotion";
import { theme } from "../themes/tokens";
import { lockedText } from "../typography/lock";

const clamp = { extrapolateLeft: "clamp" as const, extrapolateRight: "clamp" as const };

export function formatCount(value: number, progress: number): string {
  const current = value * progress;
  if (Number.isInteger(value)) return String(Math.round(current));
  return current.toFixed(1);
}

export function CountUp({
  value,
  prefix = "",
  suffix = "",
  delay = 0,
  duration = 36,
}: {
  value: number;
  prefix?: string;
  suffix?: string;
  delay?: number;
  duration?: number;
}) {
  const frame = useCurrentFrame();
  const progress = interpolate(frame, [delay, delay + duration], [0, 1], {
    ...clamp,
    easing: Easing.out(Easing.cubic),
  });
  return (
    <span style={lockedText}>
      {prefix}
      {formatCount(value, progress)}
      {suffix}
    </span>
  );
}

export function ProgressFill({
  delay = 4,
  duration = 60,
  height = 8,
}: {
  delay?: number;
  duration?: number;
  height?: number;
}) {
  const frame = useCurrentFrame();
  const progress = interpolate(frame, [delay, delay + duration], [0, 1], {
    ...clamp,
    easing: Easing.out(Easing.cubic),
  });
  return (
    <div
      style={{
        width: "100%",
        height,
        borderRadius: theme.radius.pill,
        background: theme.color.line,
        overflow: "hidden",
      }}
    >
      <div
        style={{
          width: `${progress * 100}%`,
          height: "100%",
          borderRadius: theme.radius.pill,
          background: theme.color.accent,
        }}
      />
    </div>
  );
}

export function DrawLine({
  direction = "horizontal",
  length,
  thickness = 2,
  color = theme.color.accent,
  delay = 0,
  duration = 18,
}: {
  direction?: "horizontal" | "vertical";
  length: number;
  thickness?: number;
  color?: string;
  delay?: number;
  duration?: number;
}) {
  const frame = useCurrentFrame();
  const progress = interpolate(frame - delay, [0, duration], [0, 1], {
    ...clamp,
    easing: Easing.out(Easing.cubic),
  });
  const horizontal = direction === "horizontal";
  const width = horizontal ? length : thickness;
  const height = horizontal ? thickness : length;
  const dash = length;
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} style={{ display: "block", overflow: "visible" }}>
      <line
        x1={horizontal ? 0 : thickness / 2}
        y1={horizontal ? thickness / 2 : 0}
        x2={horizontal ? length : thickness / 2}
        y2={horizontal ? thickness / 2 : length}
        stroke={color}
        strokeWidth={thickness}
        strokeLinecap="round"
        strokeDasharray={dash}
        strokeDashoffset={dash * (1 - progress)}
      />
    </svg>
  );
}

export function AnimatedArrow({
  direction = "down",
  length = 72,
  delay = 8,
}: {
  direction?: "down" | "right";
  length?: number;
  delay?: number;
}) {
  const frame = useCurrentFrame();
  const progress = interpolate(frame - delay, [0, 16], [0, 1], {
    ...clamp,
    easing: Easing.out(Easing.cubic),
  });
  const vertical = direction === "down";
  const width = vertical ? 16 : length;
  const height = vertical ? length : 16;
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} style={{ display: "block", opacity: progress }}>
      <line
        x1={vertical ? 8 : 0}
        y1={vertical ? 0 : 8}
        x2={vertical ? 8 : length - 8}
        y2={vertical ? length - 8 : 8}
        stroke={theme.color.accent}
        strokeWidth={2}
        strokeLinecap="round"
        strokeDasharray={length}
        strokeDashoffset={length * (1 - progress)}
      />
      {vertical ? (
        <polyline
          points={`3,${length - 12} 8,${length - 4} 13,${length - 12}`}
          fill="none"
          stroke={theme.color.accent}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      ) : (
        <polyline
          points={`${length - 12},3 ${length - 4},8 ${length - 12},13`}
          fill="none"
          stroke={theme.color.accent}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      )}
    </svg>
  );
}

export function Highlight({ children, delay = 0 }: { children: ReactNode; delay?: number }) {
  const frame = useCurrentFrame();
  const progress = interpolate(frame - delay, [0, 10], [0, 1], clamp);
  return (
    <span style={{ position: "relative", display: "inline-block", whiteSpace: "nowrap" }}>
      <span
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          bottom: "0.08em",
          height: "0.28em",
          background: theme.color.accent,
          opacity: 0.85,
          transform: `scaleX(${progress})`,
          transformOrigin: "left center",
          borderRadius: theme.radius.sm,
        }}
      />
      <span style={{ position: "relative", whiteSpace: "nowrap" }}>{children}</span>
    </span>
  );
}

export function Pulse({ children }: { children: ReactNode }) {
  const frame = useCurrentFrame();
  const scale = interpolate(frame % 50, [0, 25, 50], [1, 1.06, 1], clamp);
  return <span style={{ display: "inline-flex", transform: `scale(${scale})` }}>{children}</span>;
}
