import { SUPPORTED_LOCALES, type SupportedLocale } from "../localization/language-config";
import type { SceneId } from "../types/scene";
import { SCENE_IDS, VARIANTS } from "../types/scene";

export type CatalogEntry = {
  id: SceneId;
  implemented: boolean;
  phase: 1 | 2;
  variants: readonly string[];
  defaultDurationSeconds: number;
  description: string;
  supportedLocales: readonly SupportedLocale[];
};

const META: Record<
  SceneId,
  { implemented: boolean; phase: 1 | 2; defaultDurationSeconds: number; description: string }
> = {
  kinetic_hook: {
    implemented: true,
    phase: 1,
    defaultDurationSeconds: 3,
    description: "Opening phrase revealed as whole words",
  },
  big_number: {
    implemented: true,
    phase: 1,
    defaultDurationSeconds: 3,
    description: "One spoken figure with a short label",
  },
  progress_steps: {
    implemented: true,
    phase: 1,
    defaultDurationSeconds: 4,
    description: "A short sequence of steps",
  },
  speaker_focus: {
    implemented: true,
    phase: 1,
    defaultDurationSeconds: 4,
    description: "Host framing chosen by the scene variant",
  },
  broll_caption: {
    implemented: true,
    phase: 1,
    defaultDurationSeconds: 4,
    description: "Footage with a phrase-level caption",
  },
  timeline: {
    implemented: true,
    phase: 2,
    defaultDurationSeconds: 4,
    description: "Ordered events",
  },
  comparison: {
    implemented: true,
    phase: 2,
    defaultDurationSeconds: 4,
    description: "Two sides of a comparison",
  },
  split_screen: {
    implemented: true,
    phase: 2,
    defaultDurationSeconds: 4,
    description: "Two panels",
  },
  animated_diagram: {
    implemented: true,
    phase: 2,
    defaultDurationSeconds: 4,
    description: "Spoken-concept diagram (growth, risk, steps, comparison, deadline)",
  },
  checklist: {
    implemented: true,
    phase: 2,
    defaultDurationSeconds: 4,
    description: "A checklist",
  },
  quote: {
    implemented: false,
    phase: 2,
    defaultDurationSeconds: 4,
    description: "A quoted line",
  },
  stat_reveal: {
    implemented: true,
    phase: 2,
    defaultDurationSeconds: 3,
    description: "A statistic reveal",
  },
  process_flow: {
    implemented: false,
    phase: 2,
    defaultDurationSeconds: 4,
    description: "A process",
  },
  image_focus: {
    implemented: false,
    phase: 2,
    defaultDurationSeconds: 4,
    description: "A still image",
  },
  final_cta: {
    implemented: false,
    phase: 2,
    defaultDurationSeconds: 3,
    description: "A closing line",
  },
};

export const CATALOG: readonly CatalogEntry[] = SCENE_IDS.map((id) => ({
  id,
  variants: VARIANTS[id],
  supportedLocales: SUPPORTED_LOCALES,
  ...META[id],
}));

export function lookupScene(id: string): CatalogEntry | undefined {
  return CATALOG.find((entry) => entry.id === id);
}
