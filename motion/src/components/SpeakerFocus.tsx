import type { ReactNode } from "react";
import { AbsoluteFill } from "remotion";
import { theme } from "../themes/tokens";
import type { SpeakerFocusScene } from "../types/scene";
import { MediaPlate } from "../media/plates";
import { SpringEntrance } from "../primitives/entrances";
import { AnimatedCaption } from "../typography/AnimatedCaption";
import { SafeArea, useSafeBox } from "../layouts/SafeArea";
import { SceneStage } from "./SceneStage";

export function SpeakerFocus({ scene }: { scene: SpeakerFocusScene }) {
  const box = useSafeBox();
  const caption = scene.caption ? (
    <AnimatedCaption
      text={scene.caption}
      words={scene.words}
      variant={scene.captionVariant ?? "clean"}
      maxWidth={scene.variant === "portrait" || scene.variant === "side" ? box.width * 0.42 : box.width}
      maxHeight={260}
      align={scene.variant === "side" || scene.variant === "portrait" ? "left" : "center"}
      vertical={scene.variant === "fullscreen" ? "end" : "center"}
      durationInFrames={scene.durationInFrames}
      tone={scene.variant === "side" ? "dark" : "light"}
    />
  ) : null;

  return (
    <SceneStage transition={scene.transition}>
      {scene.variant === "fullscreen" ? (
        <AbsoluteFill>
          <MediaPlate media={scene.media} motion="pan" frames={scene.durationInFrames} />
          <AbsoluteFill style={{ background: theme.gradient.scrimBottom, pointerEvents: "none" }} />
          <div style={{ position: "absolute", left: box.x, width: box.width, top: box.y + box.height - 280, height: 280 }}>
            {caption}
          </div>
        </AbsoluteFill>
      ) : null}
      {scene.variant === "circle" ? <Circle scene={scene} caption={caption} /> : null}
      {scene.variant === "portrait" ? <Portrait scene={scene} caption={caption} /> : null}
      {scene.variant === "side" ? <Side scene={scene} caption={caption} /> : null}
    </SceneStage>
  );
}

function Circle({ scene, caption }: { scene: SpeakerFocusScene; caption: ReactNode }) {
  const box = useSafeBox();
  const diameter = Math.min(box.width * 0.78, box.height * 0.46);
  return (
    <SafeArea>
      <div style={{ height: "100%", display: "flex", flexDirection: "column", alignItems: "center" }}>
        <div style={{ position: "relative", width: diameter, height: diameter, marginTop: box.height * 0.06 }}>
          <MediaPlate media={scene.media} mask="circle" frames={scene.durationInFrames} objectPosition="center 30%" />
        </div>
        <div style={{ width: box.width, height: 240, marginTop: theme.space.xl }}>{caption}</div>
      </div>
    </SafeArea>
  );
}

function Portrait({ scene, caption }: { scene: SpeakerFocusScene; caption: ReactNode }) {
  const box = useSafeBox();
  const cardWidth = box.width * 0.48;
  const cardHeight = box.height * 0.72;
  return (
    <SafeArea>
      <div style={{ height: "100%", display: "flex", alignItems: "center", gap: theme.space.lg }}>
        <SpringEntrance>
          <div style={{ position: "relative", width: cardWidth, height: cardHeight }}>
            <MediaPlate media={scene.media} mask="rounded" frames={scene.durationInFrames} />
          </div>
        </SpringEntrance>
        <div style={{ width: box.width - cardWidth - theme.space.lg, height: 320 }}>{caption}</div>
      </div>
    </SafeArea>
  );
}

function Side({ scene, caption }: { scene: SpeakerFocusScene; caption: ReactNode }) {
  const box = useSafeBox();
  return (
    <AbsoluteFill>
      <div style={{ position: "absolute", top: 0, bottom: 0, left: "46%", right: 0 }}>
        <MediaPlate media={scene.media} frames={scene.durationInFrames} />
      </div>
      <div
        style={{
          position: "absolute",
          top: 0,
          bottom: 0,
          left: 0,
          width: "50%",
          background: theme.color.paper,
        }}
      />
      <div style={{ position: "absolute", left: box.x, top: box.y, width: box.width * 0.4, height: box.height, display: "flex", alignItems: "center" }}>
        <div style={{ width: "100%", height: 320 }}>{caption}</div>
      </div>
    </AbsoluteFill>
  );
}
