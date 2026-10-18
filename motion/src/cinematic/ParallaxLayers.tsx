import type { ReactNode } from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";

const clamp = { extrapolateLeft: "clamp" as const, extrapolateRight: "clamp" as const };

export type ParallaxLayer = {
  depth: number;
  children: ReactNode;
};

/** Deterministic multi-layer parallax. Depth 0 is camera-locked; higher drifts more. */
export function ParallaxLayers({
  frames,
  intensity = 1,
  layers,
}: {
  frames: number;
  intensity?: number;
  layers: ParallaxLayer[];
}) {
  const frame = useCurrentFrame();
  const span = Math.max(1, frames - 1);
  return (
    <AbsoluteFill>
      {layers.map((layer, index) => {
        const drift = 18 * layer.depth * intensity;
        const y = interpolate(frame, [0, span], [drift, -drift], clamp);
        const scale = 1 + layer.depth * 0.04 * intensity;
        return (
          <AbsoluteFill
            key={index}
            style={{
              transform: `translateY(${y}px) scale(${scale})`,
              willChange: "transform",
            }}
          >
            {layer.children}
          </AbsoluteFill>
        );
      })}
    </AbsoluteFill>
  );
}
