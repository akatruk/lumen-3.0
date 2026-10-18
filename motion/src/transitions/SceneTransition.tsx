import type { ReactNode } from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import type { SceneTransitionSpec } from "../types/scene";

const clamp = { extrapolateLeft: "clamp" as const, extrapolateRight: "clamp" as const };

export function SceneTransition({
  transition,
  children,
}: {
  transition?: SceneTransitionSpec;
  children: ReactNode;
}) {
  const frame = useCurrentFrame();
  if (!transition || transition.type === "cut" || transition.durationInFrames <= 0) {
    return <AbsoluteFill>{children}</AbsoluteFill>;
  }
  const duration = transition.durationInFrames;
  if (transition.type === "fade") {
    const opacity = interpolate(frame, [0, duration], [0, 1], { ...clamp, easing: Easing.out(Easing.cubic) });
    return <AbsoluteFill style={{ opacity }}>{children}</AbsoluteFill>;
  }
  if (transition.type === "slide") {
    const y = interpolate(frame, [0, duration], [28, 0], { ...clamp, easing: Easing.out(Easing.cubic) });
    const opacity = interpolate(frame, [0, duration], [0, 1], clamp);
    return <AbsoluteFill style={{ opacity, transform: `translateY(${y}px)` }}>{children}</AbsoluteFill>;
  }
  if (transition.type === "wipe") {
    const inset = interpolate(frame, [0, duration], [100, 0], { ...clamp, easing: Easing.out(Easing.cubic) });
    return <AbsoluteFill style={{ clipPath: `inset(0 0 ${inset}% 0)` }}>{children}</AbsoluteFill>;
  }
  if (transition.type === "soft_pull") {
    const opacity = interpolate(frame, [0, duration], [0, 1], clamp);
    const scale = interpolate(frame, [0, duration], [1.06, 1], { ...clamp, easing: Easing.out(Easing.cubic) });
    return <AbsoluteFill style={{ opacity, transform: `scale(${scale})` }}>{children}</AbsoluteFill>;
  }
  if (transition.type === "cross_blur") {
    const opacity = interpolate(frame, [0, duration], [0, 1], { ...clamp, easing: Easing.inOut(Easing.cubic) });
    const blur = interpolate(frame, [0, duration / 2, duration], [6, 2, 0], clamp);
    return (
      <AbsoluteFill style={{ opacity, filter: `blur(${blur}px)`, transform: "scale(1.02)" }}>{children}</AbsoluteFill>
    );
  }
  if (transition.type === "iris_soft") {
    const r = interpolate(frame, [0, duration], [8, 120], { ...clamp, easing: Easing.out(Easing.cubic) });
    return (
      <AbsoluteFill style={{ clipPath: `circle(${r}% at 50% 42%)` }}>{children}</AbsoluteFill>
    );
  }
  // Premium cinematic: soft pull + fade for any extended transition token.
  const opacity = interpolate(frame, [0, duration], [0, 1], clamp);
  const scale = interpolate(frame, [0, duration], [1.04, 1], { ...clamp, easing: Easing.out(Easing.cubic) });
  return <AbsoluteFill style={{ opacity, transform: `scale(${scale})` }}>{children}</AbsoluteFill>;
}
