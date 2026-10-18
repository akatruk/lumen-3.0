import type { ReactNode } from "react";
import { AnimatedDiagram } from "../components/AnimatedDiagram";
import { BigNumber } from "../components/BigNumber";
import { BrollCaption } from "../components/BrollCaption";
import { Checklist } from "../components/Checklist";
import { Comparison } from "../components/Comparison";
import { KineticHook } from "../components/KineticHook";
import { ProgressSteps } from "../components/ProgressSteps";
import { SpeakerFocus } from "../components/SpeakerFocus";
import { SplitScreen } from "../components/SplitScreen";
import { StatReveal } from "../components/StatReveal";
import { Timeline } from "../components/Timeline";
import type { Scene } from "../types/scene";
import { CATALOG, lookupScene } from "./catalog";

export function renderScene(scene: Scene): ReactNode {
  switch (scene.type) {
    case "kinetic_hook":
      return <KineticHook scene={scene} />;
    case "big_number":
      return <BigNumber scene={scene} />;
    case "progress_steps":
      return <ProgressSteps scene={scene} />;
    case "speaker_focus":
      return <SpeakerFocus scene={scene} />;
    case "broll_caption":
      return <BrollCaption scene={scene} />;
    case "timeline":
      return <Timeline scene={scene} />;
    case "comparison":
      return <Comparison scene={scene} />;
    case "split_screen":
      return <SplitScreen scene={scene} />;
    case "checklist":
      return <Checklist scene={scene} />;
    case "stat_reveal":
      return <StatReveal scene={scene} />;
    case "animated_diagram":
      return <AnimatedDiagram scene={scene} />;
    default: {
      const unreachable: never = scene;
      return unreachable;
    }
  }
}

export const motionRegistry = {
  catalog: CATALOG,
  lookup: lookupScene,
  render: renderScene,
};
