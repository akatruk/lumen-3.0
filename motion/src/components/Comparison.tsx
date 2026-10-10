import { interpolate, useCurrentFrame } from "remotion";
import { theme } from "../themes/tokens";
import type { ComparisonScene, ComparisonSide } from "../types/scene";
import { AutoFitText } from "../typography/AutoFitText";
import { SlideIn } from "../primitives/entrances";
import { SafeArea, useSafeBox } from "../layouts/SafeArea";
import { SceneStage } from "./SceneStage";

const clamp = { extrapolateLeft: "clamp" as const, extrapolateRight: "clamp" as const };

function Side({ side, width, height }: { side: ComparisonSide; width: number; height: number }) {
  return (
    <div style={{ width, minHeight: height, display: "flex", flexDirection: "column", justifyContent: "center", gap: theme.space.sm }}>
      <AutoFitText text={side.label} maxWidth={width} maxHeight={120} role={theme.type.title} align="left" vertical="start" />
      {side.detail ? (
        <AutoFitText text={side.detail} maxWidth={width} maxHeight={80} role={theme.type.support} color={theme.color.muted} align="left" vertical="start" />
      ) : null}
    </div>
  );
}

export function Comparison({ scene }: { scene: ComparisonScene }) {
  const frame = useCurrentFrame();
  const box = useSafeBox();
  const swipe = scene.variant === "swipe" ? interpolate(frame, [10, scene.durationInFrames - 10], [0, 1], clamp) : 1;
  const stacked = scene.variant === "before_after";
  const columnWidth = stacked ? box.width : Math.floor(box.width * 0.42);
  return (
    <SceneStage transition={scene.transition}>
      <SafeArea style={{ display: "flex", flexDirection: stacked ? "column" : "row", alignItems: "center", justifyContent: "space-between", gap: theme.space.md }}>
        <div style={{ opacity: scene.variant === "swipe" ? swipe : 1, clipPath: scene.variant === "swipe" ? `inset(0 ${(1 - swipe) * 100}% 0 0)` : undefined }}>
          <SlideIn>
            <Side side={scene.left} width={columnWidth} height={stacked ? box.height * 0.35 : box.height * 0.4} />
          </SlideIn>
        </div>
        <div style={{ color: theme.color.accent, fontFamily: theme.font.sans, fontWeight: 600, fontSize: scene.variant === "versus" ? 72 : 28, letterSpacing: 0 }}>
          {scene.variant === "versus" ? "vs" : ""}
        </div>
        <SlideIn delay={10}>
          <Side side={scene.right} width={columnWidth} height={stacked ? box.height * 0.35 : box.height * 0.4} />
        </SlideIn>
      </SafeArea>
    </SceneStage>
  );
}
