import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { theme } from "../themes/tokens";
import type { SplitScreenScene } from "../types/scene";
import { AutoFitText } from "../typography/AutoFitText";
import { SpeakerVideo } from "../media/plates";
import { Zoom } from "../primitives/camera";
import { SafeArea } from "../layouts/SafeArea";
import { SceneStage } from "./SceneStage";

const clamp = { extrapolateLeft: "clamp" as const, extrapolateRight: "clamp" as const };

export function SplitScreen({ scene }: { scene: SplitScreenScene }) {
  const frame = useCurrentFrame();
  const { height } = useVideoConfig();
  const mediaShare = scene.variant === "30_70" ? 0.32 : scene.variant === "top_bottom" ? 0.5 : 0.5;
  const textFirst = scene.variant === "top_bottom";
  const grow = scene.variant === "dynamic" ? interpolate(frame, [0, scene.durationInFrames], [0.46, 0.62], clamp) : mediaShare;
  const mediaHeight = Math.round(height * grow);
  const media = (
    <div style={{ position: "relative", height: mediaHeight, overflow: "hidden" }}>
      {scene.variant === "dynamic" ? (
        <Zoom>
          <SpeakerVideo media={scene.media} mask="none" />
        </Zoom>
      ) : (
        <SpeakerVideo media={scene.media} mask="none" />
      )}
    </div>
  );
  const copy = (
    <SafeArea>
      <AutoFitText text={scene.text} maxWidth={880} maxHeight={280} role={theme.type.hook} align="left" vertical="center" animate="slide" />
    </SafeArea>
  );
  return (
    <SceneStage transition={scene.transition}>
      {textFirst ? copy : media}
      {textFirst ? media : copy}
    </SceneStage>
  );
}
