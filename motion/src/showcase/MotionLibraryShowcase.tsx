import { AbsoluteFill, Sequence } from "remotion";
import { theme } from "../themes/tokens";
import { renderScene } from "../registry/motionRegistry";
import { SHOWCASE_SCENES } from "./script";

export function MotionLibraryShowcase() {
  const placed: { from: number; scene: (typeof SHOWCASE_SCENES)[number] }[] = [];
  let from = 0;
  for (const scene of SHOWCASE_SCENES) {
    placed.push({ from, scene });
    from += scene.durationInFrames;
  }
  return (
    <AbsoluteFill style={{ background: theme.color.bg, fontFamily: theme.font.sans }}>
      {placed.map(({ scene, from: start }) => (
        <Sequence key={scene.id} from={start} durationInFrames={scene.durationInFrames} name={scene.id}>
          {renderScene(scene)}
        </Sequence>
      ))}
    </AbsoluteFill>
  );
}
