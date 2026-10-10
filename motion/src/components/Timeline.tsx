import { interpolate, useCurrentFrame } from "remotion";
import { theme } from "../themes/tokens";
import type { TimelineScene } from "../types/scene";
import { AutoFitText } from "../typography/AutoFitText";
import { DrawLine } from "../primitives/marks";
import { SlideIn } from "../primitives/entrances";
import { SafeArea, useSafeBox } from "../layouts/SafeArea";
import { SceneStage } from "./SceneStage";

export function Timeline({ scene }: { scene: TimelineScene }) {
  const frame = useCurrentFrame();
  const box = useSafeBox();
  const shift = scene.variant === "scroll" ? interpolate(frame, [0, scene.durationInFrames], [40, -40], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) : 0;
  const row = scene.variant === "horizontal";
  return (
    <SceneStage transition={scene.transition}>
      <SafeArea style={{ display: "flex", alignItems: "center", justifyContent: row ? "center" : "flex-start" }}>
        <div style={{ display: "flex", flexDirection: row ? "row" : "column", gap: theme.space.lg, transform: `translateY(${shift}px)`, width: "100%" }}>
          {scene.variant === "vertical" || scene.variant === "center_line" ? (
            <DrawLine direction="vertical" length={Math.min(box.height * 0.7, scene.events.length * 140)} duration={scene.durationInFrames - 16} />
          ) : null}
          <div style={{ display: "flex", flexDirection: row ? "row" : "column", gap: row ? theme.space.md : theme.space.xl, alignItems: row ? "flex-end" : "flex-start" }}>
            {scene.events.map((event, index) => {
              const shown = frame >= 6 + index * (scene.variant === "scroll" ? 8 : 12);
              return (
                <SlideIn key={`${event.label}-${index}`} delay={index * 8}>
                  <div style={{ opacity: shown ? 1 : 0.2, maxWidth: row ? box.width / scene.events.length - 16 : box.width - 48 }}>
                    {event.date ? (
                      <AutoFitText text={event.date} maxWidth={row ? 180 : box.width - 80} maxHeight={36} role={theme.type.label} color={theme.color.accent} align="left" vertical="start" />
                    ) : null}
                    <AutoFitText text={event.label} maxWidth={row ? 220 : box.width - 80} maxHeight={100} role={theme.type.title} align="left" vertical="start" />
                  </div>
                </SlideIn>
              );
            })}
          </div>
        </div>
      </SafeArea>
    </SceneStage>
  );
}
