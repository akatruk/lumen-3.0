import { AbsoluteFill } from "remotion";
import { theme } from "../themes/tokens";
import type { AnimatedDiagramScene } from "../types/scene";
import { AutoFitText } from "../typography/AutoFitText";
import { ConceptViz } from "../concepts/ConceptViz";
import type { ConceptPresetId } from "../concepts/schema";
import { SceneStage } from "./SceneStage";
import { SafeArea } from "../layouts/SafeArea";

const VARIANT_PRESET: Record<AnimatedDiagramScene["variant"], ConceptPresetId> = {
  nodes: "family_cluster",
  flow: "route_link",
  growth: "growth_arrow",
  risk: "risk_arrow",
  steps: "steps_reveal",
  comparison: "comparison_columns",
  deadline: "deadline_scale",
};

export function AnimatedDiagram({ scene }: { scene: AnimatedDiagramScene }) {
  const presetId = VARIANT_PRESET[scene.variant];
  const labels = scene.labels?.length ? scene.labels : scene.nodes?.map((n) => n.label);
  return (
    <SceneStage transition={scene.transition} background={theme.color.bg}>
      <SafeArea>
        {scene.title ? (
          <AbsoluteFill style={{ paddingTop: 40, height: 160, pointerEvents: "none" }}>
            <AutoFitText
              text={scene.title}
              maxWidth={900}
              maxHeight={120}
              role={theme.type.caption}
              align="center"
              vertical="start"
              locale="ru-RU"
            />
          </AbsoluteFill>
        ) : null}
        <ConceptViz
          frames={scene.durationInFrames}
          hit={{
            conceptId: `diagram.${scene.variant}`,
            presetId,
            phrase: scene.title || scene.variant,
            score: 1,
            ...(scene.value != null ? { value: scene.value } : {}),
            ...(labels ? { labels } : {}),
          }}
        />
      </SafeArea>
    </SceneStage>
  );
}
