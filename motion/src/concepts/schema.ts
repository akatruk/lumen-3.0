/** Spoken-concept → deterministic Remotion viz. Director picks preset id + data only. */

export const CONCEPT_PRESET_IDS = [
  "growth_arrow",
  "risk_arrow",
  "big_figure",
  "steps_reveal",
  "comparison_columns",
  "deadline_scale",
  "route_link",
  "document_stamp",
  "family_cluster",
  "budget_scale",
] as const;

export type ConceptPresetId = (typeof CONCEPT_PRESET_IDS)[number];

export type ConceptLayout =
  | "arrow_up"
  | "arrow_down"
  | "figure"
  | "steps"
  | "columns"
  | "scale"
  | "route"
  | "stamp"
  | "cluster"
  | "budget";

export type ConceptPreset = {
  id: ConceptPresetId;
  layout: ConceptLayout;
  /** English catalog label; never invent a spoken statistic. */
  label: string;
  description: string;
  intensityDefault: "low" | "medium" | "high";
};

export type ConceptTriggerPhrase = {
  /** Case-folded match needle (ru / en / zh). Longer first. */
  phrase: string;
  locale: "ru" | "en" | "zh" | "any";
};

export type ConceptTriggerRule = {
  conceptId: string;
  presetId: ConceptPresetId;
  phrases: ConceptTriggerPhrase[];
  /** Optional figure when the spoken line names a number the source states. */
  valueKey?: "none" | "spoken_number";
};

export type ConceptTriggerHit = {
  conceptId: string;
  presetId: ConceptPresetId;
  phrase: string;
  /** 0–1 confidence from phrase length / specificity. */
  score: number;
  value?: number;
  labels?: string[];
};

export type SyncedConceptTrigger = ConceptTriggerHit & {
  fromFrame: number;
  durationInFrames: number;
  captionText: string;
};
