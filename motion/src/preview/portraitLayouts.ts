/**
 * Shared portrait (1080×1920) layout geometry for Director V3.
 * Layouts must fill the canvas — never landscape shrink into a black void.
 * Face band stays clear of overlays through entrance / hold / exit.
 */
import { CANVAS, SAFE_INSET } from "../themes/tokens";

export const PORTRAIT = {
  width: CANVAS.width,
  height: CANVAS.height,
  /** Upper-center face band when speaker is full-bleed (fraction of height). */
  faceBand: { top: 0.1, bottom: 0.46 },
  /** Caption plate clearance from bottom. */
  captionClearance: SAFE_INSET.bottom,
  pad: 28,
  gutter: 20,
  radius: 28,
  /** Speaker column in split layouts — tall, face-safe, fills height above captions. */
  splitSpeaker: {
    width: 500,
    top: SAFE_INSET.top - 40,
    bottomClearance: SAFE_INSET.bottom + 36,
  },
  /** Side PIP during concept overlays — rounded card, not a tiny circle. */
  conceptPip: {
    width: 300,
    height: 400,
    right: 40,
    bottom: SAFE_INSET.bottom + 48,
  },
} as const;

export type CriteriaCard = {
  title: string;
  explanation: string;
};

/** Goals / family / budget as relationships the viewer can act on. */
export const CRITERIA_CARDS_RU: readonly CriteriaCard[] = [
  { title: "Цели", explanation: "куда и зачем вы переезжаете" },
  { title: "Семья", explanation: "кто едет с вами и какие сроки" },
  { title: "Бюджет", explanation: "что реально потянуть по программе" },
];

export const CRITERIA_CARDS_EN: readonly CriteriaCard[] = [
  { title: "Goals", explanation: "where you are moving and why" },
  { title: "Family", explanation: "who travels with you and when" },
  { title: "Budget", explanation: "what the program can realistically cost" },
];

export const CRITERIA_CARDS_ZH: readonly CriteriaCard[] = [
  { title: "目标", explanation: "迁往哪里以及为何出发" },
  { title: "家庭", explanation: "同行家人与时间安排" },
  { title: "预算", explanation: "项目费用是否可承受" },
];

export function criteriaCardsFor(locale: string): readonly CriteriaCard[] {
  if (locale.startsWith("zh")) return CRITERIA_CARDS_ZH;
  if (locale.startsWith("en")) return CRITERIA_CARDS_EN;
  return CRITERIA_CARDS_RU;
}

/** Full-height speaker panel rect (px) for split layouts. */
export function splitSpeakerRect(side: "left" | "right") {
  const { width, top, bottomClearance } = PORTRAIT.splitSpeaker;
  const height = PORTRAIT.height - top - bottomClearance;
  const left = side === "left" ? PORTRAIT.pad : PORTRAIT.width - PORTRAIT.pad - width;
  return { left, top, width, height };
}

/** Remaining column for supporting media / cards. */
export function splitMediaRect(side: "left" | "right") {
  const speaker = splitSpeakerRect(side === "left" ? "right" : "left");
  const left = side === "left" ? PORTRAIT.pad : speaker.left + speaker.width + PORTRAIT.gutter;
  const width =
    side === "left"
      ? speaker.left - PORTRAIT.gutter - PORTRAIT.pad
      : PORTRAIT.width - PORTRAIT.pad - left;
  return {
    left,
    top: PORTRAIT.splitSpeaker.top,
    width,
    height: speaker.height,
  };
}

/** True when a point in normalized frame coords sits in the face band. */
export function overlapsFaceBand(normY: number, normHeight: number) {
  const top = normY;
  const bottom = normY + normHeight;
  return top < PORTRAIT.faceBand.bottom && bottom > PORTRAIT.faceBand.top;
}
