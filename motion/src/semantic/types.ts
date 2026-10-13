import type { BackgroundProbe, SceneTheme } from "../utils/adaptiveLineStyle";
import type { LayoutVariant, MediaSide } from "./layouts";

export type FactClass = "source_stated" | "derived" | "external_verification";

export type EvidenceRef = {
  segmentId?: string;
  sourceTimestamp?: [number, number];
  sourceQuote?: string;
  factClass?: FactClass;
};

export type FlowEntity = { id: string; label: string; amount?: string };
export type FlowConnection = { from: string; to: string };
export type SplitValue = {
  value: number;
  label: string;
  unit?: string;
  /** at_most | at_least | exact — never invent the complement. */
  qualifier?: "at_most" | "at_least" | "exact";
};
export type TimelineStep = { label: string; evidence?: string };

export type SemanticMotionPayload = {
  componentId: string;
  version?: string;
  visualIntent:
    | "capital_flow"
    | "shareholder_network"
    | "business_comparison"
    | "ownership_split"
    | "process_timeline";
  layout?: LayoutVariant;
  mediaSide?: MediaSide;
  locale?: string;
  labels?: Record<string, string>;
  entities?: FlowEntity[];
  connections?: FlowConnection[];
  shareholders?: string[];
  company?: string;
  /** Spoken count only. Absent → group node, not a fake headcount. */
  nodeCount?: number;
  showCount?: boolean;
  countPrefix?: string;
  left?: string;
  right?: string;
  operator?: "≠" | "=" | "→";
  values?: SplitValue[];
  steps?: TimelineStep[] | string[];
  evidence?: EvidenceRef;
  sceneTheme?: SceneTheme;
  connectorBackground?: BackgroundProbe;
  preview?: boolean;
};

export const COMPONENT_IDS = {
  capital_flow: "motion.capital_flow.v1",
  shareholder_network: "motion.shareholder_network.v1",
  business_comparison: "motion.business_comparison.v1",
  ownership_split: "motion.ownership_split.v1",
  process_timeline: "motion.process_timeline.v1",
} as const;
