import { interpolate, useCurrentFrame } from "remotion";
import { theme } from "../themes/tokens";
import type { ChecklistScene } from "../types/scene";
import { AutoFitText } from "../typography/AutoFitText";
import { ProgressFill } from "../primitives/marks";
import { SlideIn } from "../primitives/entrances";
import { SafeArea, useSafeBox } from "../layouts/SafeArea";
import { SceneStage } from "./SceneStage";

const clamp = { extrapolateLeft: "clamp" as const, extrapolateRight: "clamp" as const };

export function Checklist({ scene }: { scene: ChecklistScene }) {
  const frame = useCurrentFrame();
  const box = useSafeBox();
  const step = scene.variant === "rapid" ? 5 : 12;
  const done = interpolate(frame, [8, scene.durationInFrames - 8], [0, scene.items.length], clamp);
  return (
    <SceneStage transition={scene.transition}>
      <SafeArea style={{ display: "flex", flexDirection: "column", justifyContent: "center", gap: scene.variant === "minimal" ? theme.space.lg : theme.space.xl }}>
        {scene.items.map((item, index) => {
          const checked = done > index + 0.65;
          return (
            <SlideIn key={`${item.label}-${index}`} delay={index * step}>
              <div style={{ display: "flex", alignItems: "center", gap: theme.space.md }}>
                <div
                  style={{
                    width: scene.variant === "minimal" ? 18 : 36,
                    height: scene.variant === "minimal" ? 18 : 36,
                    borderRadius: theme.radius.pill,
                    background: checked ? theme.color.accent : "transparent",
                    border: checked ? "none" : theme.border.strong,
                    flex: "0 0 auto",
                  }}
                />
                <AutoFitText
                  text={item.label}
                  maxWidth={box.width - 80}
                  maxHeight={90}
                  role={theme.type.title}
                  color={checked ? theme.color.ink : theme.color.muted}
                  align="left"
                  vertical="center"
                />
              </div>
            </SlideIn>
          );
        })}
        {scene.variant === "progressive" ? <ProgressFill duration={scene.durationInFrames - 16} /> : null}
      </SafeArea>
    </SceneStage>
  );
}
