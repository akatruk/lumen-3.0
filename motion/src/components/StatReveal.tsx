import { theme } from "../themes/tokens";
import type { StatRevealScene } from "../types/scene";
import { AutoFitText } from "../typography/AutoFitText";
import { CountUp } from "../primitives/marks";
import { ScaleIn } from "../primitives/entrances";
import { SafeArea, useSafeBox } from "../layouts/SafeArea";
import { SceneStage } from "./SceneStage";

export function StatReveal({ scene }: { scene: StatRevealScene }) {
  const box = useSafeBox();
  const figure = scene.variant === "counter" || scene.variant === "impact" ? <CountUp value={scene.value} /> : scene.value;
  const scale = scene.variant === "scale" || scene.variant === "impact";
  const number = (
    <div style={{ color: theme.color.accent, fontFamily: theme.font.sans, fontWeight: 600, fontSize: scene.variant === "comparison" ? 160 : 220, lineHeight: 0.9, letterSpacing: "-0.04em" }}>
      {figure}
    </div>
  );
  return (
    <SceneStage transition={scene.transition}>
      <SafeArea style={{ display: "flex", flexDirection: "column", justifyContent: "center", gap: theme.space.lg }}>
        {scale ? <ScaleIn>{number}</ScaleIn> : number}
        <div style={{ width: 160, height: 4, background: theme.color.accent }} />
        <AutoFitText text={scene.headline} maxWidth={box.width} maxHeight={140} role={theme.type.title} align="left" vertical="start" />
        {scene.context ? (
          <AutoFitText text={scene.context} maxWidth={box.width} maxHeight={80} role={theme.type.support} color={theme.color.muted} align="left" vertical="start" />
        ) : null}
      </SafeArea>
    </SceneStage>
  );
}
