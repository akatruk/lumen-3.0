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
export type TimelineStep = {
  label: string;
  evidence?: string;
  /** Seconds after the evidence window starts. The row stays hidden before this. */
  at?: number;
  /** Seconds after the evidence window starts. The row stops being the current thought here. */
  until?: number;
};
export type MatrixCell = { label: string; row: number; col: number; highlight?: boolean };
export type AllocSegment = { label: string; value: number; unit?: string };
export type GraphNode = { id: string; label: string; role?: string };
export type MetricItem = {
  label: string;
  value: number;
  unit?: string;
  format?: "currency" | "percent" | "number";
};
export type PartyNode = { id: string; label: string; kind?: "entity" | "document" };
/** Spoken endpoints. Strings stay as recognized — no complement, no unit rewrite. */
export type NumericRangeValue = {
  lowText: string;
  highText: string;
  unit?: string;
  kind?: "salary" | "day_rate" | "money";
};

export type VisualIntent =
  | "capital_flow"
  | "shareholder_network"
  | "business_comparison"
  | "ownership_split"
  | "process_timeline"
  | "risk_matrix"
  | "capital_allocation"
  | "company_ecosystem"
  | "document_workflow"
  | "financial_metrics"
  | "business_decision"
  | "geographic_expansion"
  | "investment_milestones"
  | "contract_relationship"
  | "before_after"
  | "numeric_range";

export type SemanticMotionPayload = {
  componentId: string;
  version?: string;
  visualIntent: VisualIntent;
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
  cells?: MatrixCell[];
  axisX?: string;
  axisY?: string;
  segments?: AllocSegment[];
  totalLabel?: string;
  nodes?: GraphNode[];
  metrics?: MetricItem[];
  root?: string;
  branches?: string[];
  places?: string[];
  directed?: boolean;
  milestones?: string[];
  parties?: PartyNode[];
  before?: string;
  after?: string;
  range?: NumericRangeValue;
  evidence?: EvidenceRef;
  /** V16 composer. Absent on the V14/V15 path. */
  speakerMode?: "fullscreen" | "split";
  motionRect?: { left: number; top: number; width: number; height: number };
  speakerRect?: { left: number; top: number; width: number; height: number };
  faceRect?: { left: number; top: number; width: number; height: number };
  captionRect?: { left: number; top: number; width: number; height: number };
  columnScrim?: boolean;
  enterFrame?: number;
  /** Frames the graphic stays mounted inside this scene. Absent means the rest of the scene. */
  holdFrames?: number;
  eventId?: string;
  outputTime?: [number, number];
  /** step.at is seconds after sourceOrigin. Renderer subtracts sceneStart once. */
  timebase?: { sourceOrigin: number; sceneStart: number; stepClock: "sourceOrigin_plus_step_at" };
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
  risk_matrix: "motion.risk_matrix.v1",
  capital_allocation: "motion.capital_allocation.v1",
  company_ecosystem: "motion.company_ecosystem.v1",
  document_workflow: "motion.document_workflow.v1",
  financial_metrics: "motion.financial_metrics.v1",
  business_decision: "motion.business_decision.v1",
  geographic_expansion: "motion.geographic_expansion.v1",
  investment_milestones: "motion.investment_milestones.v1",
  contract_relationship: "motion.contract_relationship.v1",
  before_after: "motion.before_after.v1",
  numeric_range: "motion.numeric_range.v1",
} as const;
