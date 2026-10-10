import type { ConceptPreset, ConceptTriggerRule } from "./schema";

export const CONCEPT_PRESETS: readonly ConceptPreset[] = [
  {
    id: "growth_arrow",
    layout: "arrow_up",
    label: "Growth",
    description: "Profit or growth as an arrow moving up",
    intensityDefault: "medium",
  },
  {
    id: "risk_arrow",
    layout: "arrow_down",
    label: "Risk",
    description: "Risk or a fall as an arrow moving down",
    intensityDefault: "medium",
  },
  {
    id: "big_figure",
    layout: "figure",
    label: "Figure",
    description: "A spoken number as a large figure",
    intensityDefault: "high",
  },
  {
    id: "steps_reveal",
    layout: "steps",
    label: "Steps",
    description: "Named stages appear one by one",
    intensityDefault: "medium",
  },
  {
    id: "comparison_columns",
    layout: "columns",
    label: "Compare",
    description: "A comparison as two columns",
    intensityDefault: "medium",
  },
  {
    id: "deadline_scale",
    layout: "scale",
    label: "Deadline",
    description: "A deadline as a mark on a scale",
    intensityDefault: "medium",
  },
  {
    id: "route_link",
    layout: "route",
    label: "Route",
    description: "Cards linked by a route between places",
    intensityDefault: "medium",
  },
  {
    id: "document_stamp",
    layout: "stamp",
    label: "Approval",
    description: "Document approval stamp motion",
    intensityDefault: "low",
  },
  {
    id: "family_cluster",
    layout: "cluster",
    label: "Family",
    description: "Family / goals cluster cards",
    intensityDefault: "low",
  },
  {
    id: "budget_scale",
    layout: "budget",
    label: "Budget",
    description: "Budget as a balanced scale",
    intensityDefault: "medium",
  },
] as const;

export function presetById(id: string): ConceptPreset | undefined {
  return CONCEPT_PRESETS.find((preset) => preset.id === id);
}

/** Longer phrases first so a short stem does not eat a specific query. */
export const CONCEPT_TRIGGER_RULES: readonly ConceptTriggerRule[] = [
  {
    conceptId: "speech.growth",
    presetId: "growth_arrow",
    phrases: [
      { phrase: "рост", locale: "ru" },
      { phrase: "прибыль", locale: "ru" },
      { phrase: "growth", locale: "en" },
      { phrase: "profit", locale: "en" },
      { phrase: "增长", locale: "zh" },
      { phrase: "利润", locale: "zh" },
    ],
  },
  {
    conceptId: "speech.risk",
    presetId: "risk_arrow",
    phrases: [
      { phrase: "риск", locale: "ru" },
      { phrase: "падение", locale: "ru" },
      { phrase: "risk", locale: "en" },
      { phrase: "fall", locale: "en" },
      { phrase: "风险", locale: "zh" },
      { phrase: "下降", locale: "zh" },
    ],
  },
  {
    conceptId: "speech.steps",
    presetId: "steps_reveal",
    phrases: [
      { phrase: "с чего начать", locale: "ru" },
      { phrase: "весь процесс", locale: "ru" },
      { phrase: "консультация и программа", locale: "ru" },
      { phrase: "процесс", locale: "ru" },
      { phrase: "шаг", locale: "ru" },
      { phrase: "where to start", locale: "en" },
      { phrase: "process", locale: "en" },
      { phrase: "steps", locale: "en" },
      { phrase: "从何开始", locale: "zh" },
      { phrase: "流程", locale: "zh" },
    ],
  },
  {
    conceptId: "speech.comparison",
    presetId: "comparison_columns",
    phrases: [
      { phrase: "сравнен", locale: "ru" },
      { phrase: "подходящую программу", locale: "ru" },
      { phrase: "программу", locale: "ru" },
      { phrase: "comparison", locale: "en" },
      { phrase: "versus", locale: "en" },
      { phrase: "program", locale: "en" },
      { phrase: "比较", locale: "zh" },
      { phrase: "方案", locale: "zh" },
    ],
  },
  {
    conceptId: "speech.deadline",
    presetId: "deadline_scale",
    phrases: [
      { phrase: "срок", locale: "ru" },
      { phrase: "дедлайн", locale: "ru" },
      { phrase: "deadline", locale: "en" },
      { phrase: "timeline", locale: "en" },
      { phrase: "期限", locale: "zh" },
    ],
  },
  {
    conceptId: "speech.residency",
    presetId: "document_stamp",
    phrases: [
      { phrase: "второй вид на жительство", locale: "ru" },
      { phrase: "вид на жительство", locale: "ru" },
      { phrase: "жительство", locale: "ru" },
      { phrase: "residence", locale: "en" },
      { phrase: "residency", locale: "en" },
      { phrase: "居留", locale: "zh" },
    ],
  },
  {
    conceptId: "speech.relocation",
    presetId: "route_link",
    phrases: [
      { phrase: "планируете переезд", locale: "ru" },
      { phrase: "переезд", locale: "ru" },
      { phrase: "relocation", locale: "en" },
      { phrase: "moving abroad", locale: "en" },
      { phrase: "搬迁", locale: "zh" },
      { phrase: "移居", locale: "zh" },
    ],
  },
  {
    conceptId: "speech.family_budget",
    presetId: "family_cluster",
    phrases: [
      { phrase: "семьи и бюджета", locale: "ru" },
      { phrase: "с учетом целей", locale: "ru" },
      { phrase: "семьи", locale: "ru" },
      { phrase: "целей", locale: "ru" },
      { phrase: "family", locale: "en" },
      { phrase: "goals", locale: "en" },
      { phrase: "家庭", locale: "zh" },
      { phrase: "目标", locale: "zh" },
    ],
  },
  {
    conceptId: "speech.budget",
    presetId: "budget_scale",
    phrases: [
      { phrase: "бюджета", locale: "ru" },
      { phrase: "бюджет", locale: "ru" },
      { phrase: "budget", locale: "en" },
      { phrase: "预算", locale: "zh" },
    ],
  },
  {
    conceptId: "speech.number",
    presetId: "big_figure",
    valueKey: "spoken_number",
    phrases: [
      { phrase: "второй", locale: "ru" },
      { phrase: "second", locale: "en" },
      { phrase: "第二", locale: "zh" },
    ],
  },
] as const;
