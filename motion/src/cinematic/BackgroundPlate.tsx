import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { theme } from "../themes/tokens";

const clamp = { extrapolateLeft: "clamp" as const, extrapolateRight: "clamp" as const };

export type BackgroundPlateTreatment =
  | "ink_lift"
  | "paper_grain"
  | "navy_grid"
  | "gold_veil"
  | "soft_vignette";

/** Deterministic full-bleed plates — no generative footage required. */
export function BackgroundPlate({
  treatment = "ink_lift",
  frames,
  intensity = 1,
}: {
  treatment?: BackgroundPlateTreatment;
  frames: number;
  intensity?: number;
}) {
  const frame = useCurrentFrame();
  const span = Math.max(1, frames - 1);
  const drift = interpolate(frame, [0, span], [0, 24 * intensity], clamp);
  const pulse = interpolate(frame % 120, [0, 60, 120], [0.92, 1, 0.92], clamp);

  if (treatment === "paper_grain") {
    return (
      <AbsoluteFill
        style={{
          background: `linear-gradient(165deg, ${theme.color.paper} 0%, #E7DFD2 55%, #D8CFC2 100%)`,
          transform: `translateY(${-drift * 0.35}px) scale(${1.04})`,
        }}
      />
    );
  }
  if (treatment === "navy_grid") {
    return (
      <AbsoluteFill style={{ background: "#0F1720", transform: `scale(${1.06}) translateY(${-drift * 0.25}px)` }}>
        <AbsoluteFill
          style={{
            backgroundImage:
              "linear-gradient(rgba(224,177,90,0.08) 1px, transparent 1px), linear-gradient(90deg, rgba(224,177,90,0.08) 1px, transparent 1px)",
            backgroundSize: "48px 48px",
            opacity: 0.7 * pulse,
          }}
        />
      </AbsoluteFill>
    );
  }
  if (treatment === "gold_veil") {
    return (
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse at 40% 30%, rgba(224,177,90,${0.28 * pulse}) 0%, rgba(18,17,15,0.95) 62%)`,
          transform: `translate(${drift * 0.2}px, ${-drift * 0.15}px)`,
        }}
      />
    );
  }
  if (treatment === "soft_vignette") {
    return (
      <AbsoluteFill style={{ background: theme.color.bg }}>
        <AbsoluteFill style={{ background: theme.gradient.vignette, opacity: 0.85 }} />
      </AbsoluteFill>
    );
  }
  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(180deg, #2A2520 0%, ${theme.color.bg} 70%)`,
        transform: `scale(${1.05 * pulse}) translateY(${-drift * 0.2}px)`,
      }}
    />
  );
}
