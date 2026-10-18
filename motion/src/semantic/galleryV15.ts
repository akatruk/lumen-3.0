import type { LayoutVariant } from "./layouts";
import { GALLERY_LAYOUTS, SHOT_FRAMES, type GalleryLocale } from "./galleryScript";
import { COMPONENT_IDS, type SemanticMotionPayload, type VisualIntent } from "./types";

const COPY = {
  "en-US": {
    cells: [
      { label: "Low risk", row: 0, col: 0, highlight: false },
      { label: "High risk", row: 0, col: 1, highlight: true },
    ],
    axisX: "Impact",
    segments: [
      { label: "Operations", value: 40, unit: "%" },
      { label: "Property", value: 35, unit: "%" },
      { label: "Reserves", value: 25, unit: "%" },
    ],
    total: "Total capital",
    nodes: [
      { id: "parent", label: "Parent company", role: "parent" },
      { id: "sub", label: "Subsidiary", role: "subsidiary" },
      { id: "investor", label: "Investor", role: "investor" },
    ],
    docs: ["Application", "Review", "Approval"],
    metrics: [{ label: "Revenue", value: 120000, unit: "USD", format: "currency" as const }],
    root: "Company structure",
    branches: ["Option A", "Option B"],
    places: ["Thailand", "Singapore"],
    milestones: ["Company created", "Investment received", "Operations launched"],
    parties: [
      { id: "investor", label: "Investor", kind: "entity" as const },
      { id: "contract", label: "Contract", kind: "document" as const },
      { id: "company", label: "Company", kind: "entity" as const },
    ],
    before: "Before investment",
    after: "After investment",
  },
  "ru-RU": {
    cells: [
      { label: "Низкий риск", row: 0, col: 0, highlight: false },
      { label: "Высокий риск", row: 0, col: 1, highlight: true },
    ],
    axisX: "Влияние",
    segments: [
      { label: "Операционная деятельность компании", value: 40, unit: "%" },
      { label: "Недвижимость", value: 35, unit: "%" },
      { label: "Резервы", value: 25, unit: "%" },
    ],
    total: "Весь капитал",
    nodes: [
      { id: "parent", label: "Материнская компания", role: "parent" },
      { id: "sub", label: "Дочерняя компания", role: "subsidiary" },
      { id: "investor", label: "Инвестор", role: "investor" },
    ],
    docs: ["Заявление", "Проверка", "Одобрение"],
    metrics: [{ label: "Выручка", value: 120000, unit: "USD", format: "currency" as const }],
    root: "Структура компании",
    branches: ["Вариант А", "Вариант Б"],
    places: ["Таиланд", "Сингапур"],
    milestones: ["Компания создана", "Инвестиция получена", "Операции запущены"],
    parties: [
      { id: "investor", label: "Инвестор", kind: "entity" as const },
      { id: "contract", label: "Договор", kind: "document" as const },
      { id: "company", label: "Компания", kind: "entity" as const },
    ],
    before: "До инвестиции",
    after: "После инвестиции",
  },
  "zh-CN": {
    cells: [
      { label: "低风险", row: 0, col: 0, highlight: false },
      { label: "高风险", row: 0, col: 1, highlight: true },
    ],
    axisX: "影响",
    segments: [
      { label: "运营", value: 40, unit: "%" },
      { label: "物业", value: 35, unit: "%" },
      { label: "储备", value: 25, unit: "%" },
    ],
    total: "总资本",
    nodes: [
      { id: "parent", label: "母公司", role: "parent" },
      { id: "sub", label: "子公司", role: "subsidiary" },
      { id: "investor", label: "投资人", role: "investor" },
    ],
    docs: ["申请、审核", "批准"],
    metrics: [{ label: "营收", value: 120000, unit: "USD", format: "currency" as const }],
    root: "公司结构",
    branches: ["方案甲", "方案乙"],
    places: ["泰国", "新加坡"],
    milestones: ["公司成立", "收到投资", "开始运营"],
    parties: [
      { id: "investor", label: "投资人", kind: "entity" as const },
      { id: "contract", label: "协议", kind: "document" as const },
      { id: "company", label: "公司", kind: "entity" as const },
    ],
    before: "投资之前",
    after: "投资之后",
  },
} as const;

export const V15_INTENTS: VisualIntent[] = [
  "risk_matrix",
  "capital_allocation",
  "company_ecosystem",
  "document_workflow",
  "financial_metrics",
  "business_decision",
  "geographic_expansion",
  "investment_milestones",
  "contract_relationship",
  "before_after",
];

export function galleryShotV15(intent: VisualIntent, layout: LayoutVariant, locale: GalleryLocale): SemanticMotionPayload {
  const copy = COPY[locale];
  const base = {
    layout,
    locale,
    version: "v15.0",
    preview: true,
    sceneTheme: layout === "full_frame" ? ("navy" as const) : ("paper" as const),
    connectorBackground: layout === "full_frame" ? "#0F1720" : "#C4B6A2",
    mediaSide: "left" as const,
    evidence: { factClass: "source_stated" as const, sourceQuote: "preview fixture", segmentId: "preview" },
  };
  const id = COMPONENT_IDS[intent as keyof typeof COMPONENT_IDS];
  if (intent === "risk_matrix") {
    return { ...base, componentId: id, visualIntent: intent, cells: copy.cells.map((cell) => ({ ...cell })), axisX: copy.axisX };
  }
  if (intent === "capital_allocation") {
    return { ...base, componentId: id, visualIntent: intent, totalLabel: copy.total, segments: copy.segments.map((segment) => ({ ...segment })) };
  }
  if (intent === "company_ecosystem") {
    return {
      ...base,
      componentId: id,
      visualIntent: intent,
      nodes: copy.nodes.map((node) => ({ ...node })),
      connections: [
        { from: "parent", to: "sub" },
        { from: "investor", to: "parent" },
      ],
    };
  }
  if (intent === "document_workflow") {
    return { ...base, componentId: id, visualIntent: intent, steps: copy.docs.map((label) => ({ label })) };
  }
  if (intent === "financial_metrics") {
    return { ...base, componentId: id, visualIntent: intent, metrics: copy.metrics.map((metric) => ({ ...metric })) };
  }
  if (intent === "business_decision") {
    return { ...base, componentId: id, visualIntent: intent, root: copy.root, branches: [...copy.branches] };
  }
  if (intent === "geographic_expansion") {
    return { ...base, componentId: id, visualIntent: intent, places: [...copy.places], directed: true };
  }
  if (intent === "investment_milestones") {
    return { ...base, componentId: id, visualIntent: intent, milestones: [...copy.milestones] };
  }
  if (intent === "contract_relationship") {
    return { ...base, componentId: id, visualIntent: intent, parties: copy.parties.map((party) => ({ ...party })) };
  }
  return { ...base, componentId: COMPONENT_IDS.before_after, visualIntent: "before_after", before: copy.before, after: copy.after };
}

export function galleryShotsV15(locale: GalleryLocale): SemanticMotionPayload[] {
  const shots: SemanticMotionPayload[] = [];
  for (const intent of V15_INTENTS) {
    for (const layout of GALLERY_LAYOUTS) shots.push(galleryShotV15(intent, layout, locale));
  }
  return shots;
}

export const V15_GALLERY_FRAMES = V15_INTENTS.length * GALLERY_LAYOUTS.length * SHOT_FRAMES;
