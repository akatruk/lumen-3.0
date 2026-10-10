import { AbsoluteFill } from "remotion";
import { theme } from "../themes/tokens";
import type { BrollCaptionScene } from "../types/scene";
import { MediaPlate } from "../media/plates";
import { AnimatedCaption } from "../typography/AnimatedCaption";
import { useSafeBox } from "../layouts/SafeArea";
import { SceneStage } from "./SceneStage";

export function BrollCaption({ scene }: { scene: BrollCaptionScene }) {
  const box = useSafeBox();
  const captionWidth = scene.variant === "cinematic" ? 420 : box.width;
  const caption = (
    <AnimatedCaption
      text={scene.text}
      words={scene.words}
      variant={scene.captionVariant}
      maxWidth={captionWidth}
      maxHeight={scene.variant === "cinematic" ? 120 : scene.variant === "minimal" ? 140 : scene.captionVariant === "impact" ? 360 : 240}
      align={scene.variant === "minimal" || scene.variant === "cinematic" ? "left" : "center"}
      vertical={scene.variant === "cinematic" ? "start" : scene.variant === "center_statement" || scene.captionVariant === "impact" ? "center" : "end"}
      durationInFrames={scene.durationInFrames}
    />
  );

  if (scene.variant === "minimal") {
    const cardWidth = box.width * 0.78;
    const cardHeight = Math.min(box.height * 0.58, cardWidth * 1.15);
    return (
      <SceneStage transition={scene.transition}>
        <div
          style={{
            position: "absolute",
            left: box.x + (box.width - cardWidth) / 2,
            top: box.y,
            width: cardWidth,
            height: cardHeight,
          }}
        >
          <MediaPlate media={scene.media} mask="rounded" frames={scene.durationInFrames} />
        </div>
        <div style={{ position: "absolute", left: box.x, width: box.width, top: box.y + box.height - 180, height: 160 }}>
          {caption}
        </div>
      </SceneStage>
    );
  }

  if (scene.variant === "cinematic") {
    const bar = 150;
    return (
      <SceneStage transition={scene.transition}>
        <MediaPlate media={scene.media} motion="zoom" frames={scene.durationInFrames} />
        <div style={{ position: "absolute", top: 0, left: 0, right: 0, height: bar, background: theme.color.bg }} />
        <div style={{ position: "absolute", bottom: 0, left: 0, right: 0, height: bar, background: theme.color.bg }} />
        <div
          style={{
            position: "absolute",
            left: box.x,
            top: box.y,
            width: captionWidth,
            padding: theme.space.md,
            background: theme.color.scrim,
            borderRadius: theme.radius.lg,
          }}
        >
          {caption}
        </div>
      </SceneStage>
    );
  }

  return (
    <SceneStage transition={scene.transition}>
      <MediaPlate
        media={scene.media}
        motion={scene.variant === "bottom_caption" ? "pan" : "none"}
        frames={scene.durationInFrames}
      />
      <AbsoluteFill
        style={{
          background: scene.variant === "center_statement" ? theme.gradient.scrimCenter : theme.gradient.scrimBottom,
        }}
      />
      {scene.variant === "center_statement" ? (
        <div
          style={{
            position: "absolute",
            left: box.x,
            width: box.width,
            top: box.y + box.height * 0.28,
            height: box.height * 0.4,
          }}
        >
          {caption}
        </div>
      ) : (
        <div style={{ position: "absolute", left: box.x, width: box.width, top: box.y + box.height - 300, height: 280 }}>
          {caption}
        </div>
      )}
    </SceneStage>
  );
}
