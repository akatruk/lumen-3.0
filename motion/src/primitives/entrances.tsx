import type { CSSProperties, ReactNode } from "react";
import { Easing, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

const clamp = { extrapolateLeft: "clamp" as const, extrapolateRight: "clamp" as const };

function shell(inline: boolean | undefined, style: CSSProperties): CSSProperties {
  return inline ? { display: "inline-block", whiteSpace: "nowrap", verticalAlign: "baseline", ...style } : style;
}

export function FadeIn({
  children,
  delay = 0,
  duration = 14,
  inline = false,
}: {
  children: ReactNode;
  delay?: number;
  duration?: number;
  inline?: boolean;
}) {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame - delay, [0, duration], [0, 1], {
    ...clamp,
    easing: Easing.out(Easing.cubic),
  });
  const Tag = inline ? "span" : "div";
  return <Tag style={shell(inline, { opacity })}>{children}</Tag>;
}

export function SlideIn({
  children,
  direction = "up",
  delay = 0,
  duration = 16,
  distance = 22,
  inline = false,
}: {
  children: ReactNode;
  direction?: "up" | "down" | "left" | "right";
  delay?: number;
  duration?: number;
  distance?: number;
  inline?: boolean;
}) {
  const frame = useCurrentFrame();
  const progress = interpolate(frame - delay, [0, duration], [0, 1], {
    ...clamp,
    easing: Easing.out(Easing.cubic),
  });
  const horizontal = direction === "left" || direction === "right";
  const fromPositive = direction === "up" || direction === "left";
  const offset = (1 - progress) * distance * (fromPositive ? 1 : -1);
  const opacity = interpolate(frame - delay, [0, Math.min(8, duration)], [0, 1], clamp);
  const Tag = inline ? "span" : "div";
  return (
    <Tag
      style={shell(inline, {
        opacity,
        transform: horizontal ? `translateX(${offset}px)` : `translateY(${offset}px)`,
      })}
    >
      {children}
    </Tag>
  );
}

export function ScaleIn({
  children,
  delay = 0,
  duration = 18,
  from = 0.96,
  inline = false,
}: {
  children: ReactNode;
  delay?: number;
  duration?: number;
  from?: number;
  inline?: boolean;
}) {
  const frame = useCurrentFrame();
  const progress = interpolate(frame - delay, [0, duration], [0, 1], {
    ...clamp,
    easing: Easing.out(Easing.cubic),
  });
  const Tag = inline ? "span" : "div";
  return (
    <Tag style={shell(inline, { opacity: progress, transform: `scale(${from + (1 - from) * progress})` })}>
      {children}
    </Tag>
  );
}

export function PopIn({
  children,
  delay = 0,
  inline = false,
}: {
  children: ReactNode;
  delay?: number;
  inline?: boolean;
}) {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const progress = Math.min(1, spring({ frame: frame - delay, fps, config: { damping: 200, stiffness: 180, mass: 0.8 } }));
  const Tag = inline ? "span" : "div";
  return (
    <Tag style={shell(inline, { opacity: progress, transform: `scale(${0.94 + progress * 0.06})` })}>{children}</Tag>
  );
}

export function SpringEntrance({
  children,
  delay = 0,
}: {
  children: ReactNode;
  delay?: number;
}) {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const progress = Math.min(1, spring({ frame: frame - delay, fps, config: { damping: 200, stiffness: 140, mass: 0.9 } }));
  return (
    <div style={{ opacity: progress, transform: `translateY(${(1 - progress) * 16}px) scale(${0.98 + progress * 0.02})` }}>
      {children}
    </div>
  );
}

export function MaskReveal({
  children,
  delay = 0,
  duration = 12,
  inline = false,
}: {
  children: ReactNode;
  delay?: number;
  duration?: number;
  inline?: boolean;
}) {
  const frame = useCurrentFrame();
  const progress = interpolate(frame - delay, [0, duration], [0, 1], {
    ...clamp,
    easing: Easing.out(Easing.cubic),
  });
  const Tag = inline ? "span" : "div";
  return (
    <Tag style={shell(inline, { overflow: "hidden" })}>
      <Tag style={shell(inline, { transform: `translateY(${(1 - progress) * 110}%)` })}>{children}</Tag>
    </Tag>
  );
}
