import type { SemanticMotionPayload } from "./types";
import type { LayoutVariant } from "./layouts";
import { COMPONENT_IDS } from "./types";

export const GALLERY_LAYOUTS: LayoutVariant[] = ["full_frame", "speaker_visual", "overlay"];

const COPY = {
  "en-US": {
    flow: [
      { id: "investor", label: "Investor" },
      { id: "capital", label: "Capital" },
      { id: "company", label: "Company" },
    ],
    company: "Company",
    node: "Shareholder",
    group: "Shareholders",
    left: "Thai process",
    right: "Chinese process",
    foreign: "Foreign capital",
    steps: ["Consultation", "Documents", "Registration"],
  },
  "ru-RU": {
    flow: [
      { id: "investor", label: "Инвестор" },
      { id: "capital", label: "Капитал" },
      { id: "company", label: "Компания" },
    ],
    company: "Компания",
    node: "Акционер",
    group: "Акционеры",
    left: "Тайский процесс",
    right: "Китайский процесс",
    foreign: "Иностранный капитал",
    steps: ["Консультация", "Документы", "Регистрация"],
  },
  "zh-CN": {
    flow: [
      { id: "investor", label: "投资人" },
      { id: "capital", label: "资本" },
      { id: "company", label: "公司" },
    ],
    company: "公司",
    node: "股东",
    group: "股东",
    left: "泰国流程",
    right: "中国流程",
    foreign: "外资",
    steps: ["咨询", "文件", "注册"],
  },
} as const;

export type GalleryLocale = keyof typeof COPY;

export function galleryShot(intent: SemanticMotionPayload["visualIntent"], layout: LayoutVariant, locale: GalleryLocale): SemanticMotionPayload {
  const copy = COPY[locale];
  const base = {
    layout,
    locale,
    version: "v14.1",
    preview: true,
    sceneTheme: layout === "full_frame" ? ("navy" as const) : ("paper" as const),
    connectorBackground: layout === "full_frame" ? "#0F1720" : "#C4B6A2",
    mediaSide: "left" as const,
    evidence: { factClass: "source_stated" as const, sourceQuote: "preview", segmentId: "preview" },
  };
  if (intent === "capital_flow") {
    return {
      ...base,
      componentId: COMPONENT_IDS.capital_flow,
      visualIntent: intent,
      entities: copy.flow.map((e) => ({ ...e })),
      connections: [
        { from: "investor", to: "capital" },
        { from: "capital", to: "company" },
      ],
    };
  }
  if (intent === "shareholder_network") {
    return {
      ...base,
      componentId: COMPONENT_IDS.shareholder_network,
      visualIntent: intent,
      company: copy.company,
      showCount: true,
      nodeCount: 3,
      countPrefix: "≥",
      labels: { node: copy.node, company: copy.company },
    };
  }
  if (intent === "business_comparison") {
    return {
      ...base,
      componentId: COMPONENT_IDS.business_comparison,
      visualIntent: intent,
      left: copy.left,
      right: copy.right,
      operator: "≠",
    };
  }
  if (intent === "ownership_split") {
    return {
      ...base,
      componentId: COMPONENT_IDS.ownership_split,
      visualIntent: intent,
      values: [{ value: 49, label: copy.foreign, unit: "%", qualifier: "at_most" }],
      labels: { remainder: "" },
    };
  }
  return {
    ...base,
    componentId: COMPONENT_IDS.process_timeline,
    visualIntent: "process_timeline",
    steps: copy.steps.map((label) => ({ label })),
  };
}

export const GALLERY_INTENTS: SemanticMotionPayload["visualIntent"][] = [
  "capital_flow",
  "shareholder_network",
  "business_comparison",
  "ownership_split",
  "process_timeline",
];

export const SHOT_FRAMES = 75;

export function galleryShots(locale: GalleryLocale): SemanticMotionPayload[] {
  const shots: SemanticMotionPayload[] = [];
  for (const intent of GALLERY_INTENTS) {
    for (const layout of GALLERY_LAYOUTS) shots.push(galleryShot(intent, layout, locale));
  }
  return shots;
}
