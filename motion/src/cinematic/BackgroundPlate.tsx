import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { theme } from "../themes/tokens";

const clamp = { extrapolateLeft: "clamp" as const, extrapolateRight: "clamp" as const };

/** First-batch cinematic plates — Remotion/CSS remix; no generative video required. */
export type BackgroundPlateTreatment =
  | "ink_lift"
  | "paper_grain"
  | "navy_grid"
  | "gold_veil"
  | "soft_vignette"
  | "mist_paper"
  | "teal_depth"
  | "warm_slate"
  | "amber_haze"
  | "graphite_drift"
  | "olive_haze"
  | "midnight_ridge"
  | "sand_lift";

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
  const driftX = interpolate(frame, [0, span], [0, 16 * intensity], clamp);

  if (treatment === "paper_grain" || treatment === "mist_paper") {
    return (
      <AbsoluteFill
        style={{
          background:
            treatment === "mist_paper"
              ? `linear-gradient(155deg, #F7F2E9 0%, #E9E0D4 48%, #D9D0C4 100%)`
              : `linear-gradient(165deg, ${theme.color.paper} 0%, #E7DFD2 55%, #D8CFC2 100%)`,
          transform: `translateY(${-drift * 0.35}px) scale(${1.04})`,
        }}
      >
        <AbsoluteFill
          style={{
            opacity: 0.08,
            backgroundImage:
              "radial-gradient(circle at 20% 30%, rgba(28,26,23,0.35) 0 1px, transparent 1px), radial-gradient(circle at 70% 60%, rgba(28,26,23,0.25) 0 1px, transparent 1px)",
            backgroundSize: "6px 6px, 9px 9px",
          }}
        />
      </AbsoluteFill>
    );
  }
  if (treatment === "navy_grid" || treatment === "teal_depth") {
    const base = treatment === "teal_depth" ? "#0C1C1F" : "#0F1720";
    const line = treatment === "teal_depth" ? "rgba(94,184,176,0.1)" : "rgba(224,177,90,0.08)";
    return (
      <AbsoluteFill style={{ background: base, transform: `scale(${1.06}) translateY(${-drift * 0.25}px)` }}>
        <AbsoluteFill
          style={{
            backgroundImage: `linear-gradient(${line} 1px, transparent 1px), linear-gradient(90deg, ${line} 1px, transparent 1px)`,
            backgroundSize: "48px 48px",
            opacity: 0.7 * pulse,
          }}
        />
      </AbsoluteFill>
    );
  }
  if (treatment === "gold_veil" || treatment === "amber_haze") {
    const c = treatment === "amber_haze" ? "224,140,70" : "224,177,90";
    return (
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse at 40% 30%, rgba(${c},${0.28 * pulse}) 0%, rgba(18,17,15,0.95) 62%)`,
          transform: `translate(${drift * 0.2}px, ${-drift * 0.15}px)`,
        }}
      />
    );
  }
  if (treatment === "soft_vignette" || treatment === "graphite_drift") {
    return (
      <AbsoluteFill
        style={{
          background:
            treatment === "graphite_drift"
              ? `linear-gradient(180deg, #2A2E33 0%, #12151A 70%)`
              : theme.color.bg,
          transform: `translateX(${driftX * 0.2}px)`,
        }}
      >
        <AbsoluteFill style={{ background: theme.gradient.vignette, opacity: 0.85 }} />
      </AbsoluteFill>
    );
  }
  if (treatment === "warm_slate") {
    return (
      <AbsoluteFill
        style={{
          background: `linear-gradient(160deg, #C9BEB0 0%, #A89A8A 45%, #6E655C 100%)`,
          transform: `translateY(${-drift * 0.3}px) scale(1.05)`,
        }}
      />
    );
  }
  if (treatment === "olive_haze") {
    return (
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse at 60% 40%, rgba(120,130,90,${0.35 * pulse}) 0%, #1A1C14 65%)`,
          transform: `translate(${-driftX * 0.15}px, ${-drift * 0.2}px)`,
        }}
      />
    );
  }
  if (treatment === "midnight_ridge") {
    return (
      <AbsoluteFill style={{ background: "#0A1018" }}>
        <AbsoluteFill
          style={{
            background: `linear-gradient(115deg, transparent 40%, rgba(90,120,160,${0.18 * pulse}) 52%, transparent 64%)`,
            transform: `translateX(${driftX}px)`,
          }}
        />
      </AbsoluteFill>
    );
  }
  if (treatment === "sand_lift") {
    return (
      <AbsoluteFill
        style={{
          background: `linear-gradient(180deg, #D8C9B0 0%, #B8A48A 55%, #3A3228 100%)`,
          transform: `scale(${1.04 * pulse}) translateY(${-drift * 0.25}px)`,
        }}
      />
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
