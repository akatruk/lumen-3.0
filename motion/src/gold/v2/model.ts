import type { SupportedLocale } from "../../localization/language-config";
import { CAPTIONS, GOLD_DURATION, GOLD_FPS, LAYER_AT, captionAt } from "../threeLayersModel";

export { CAPTIONS, GOLD_DURATION, GOLD_FPS, LAYER_AT, captionAt };

export const V2_CAPTION = { left: 48, top: 1660, width: 984, height: 168 };

/** Hero union must clear this. Measured principle: reference objects are 42%+ of frame width. */
export const HERO_MIN = { width: 454, height: 538 };

export type Rect = { left: number; top: number; width: number; height: number };

export const SPEAKER_FULL: Rect = { left: 0, top: 0, width: 1080, height: 1920 };
export const SPEAKER_SCENE: Rect = { left: 36, top: 168, width: 400, height: 640 };
export const SPEAKER_FAMILY: Rect = { left: 668, top: 120, width: 360, height: 500 };
export const SPEAKER_COST: Rect = { left: 48, top: 128, width: 300, height: 420 };

const clamp01 = (value: number) => Math.min(1, Math.max(0, value));
export const easeOut = (value: number) => {
  const t = clamp01(value);
  return 1 - (1 - t) ** 3;
};

export function enterFrame(at: number): number {
  return Math.round(at * GOLD_FPS);
}

export type Dimension = 0 | 1 | 2 | 3;

export function dimensionAt(frame: number): Dimension {
  if (frame < enterFrame(LAYER_AT[0])) return 0;
  if (frame < enterFrame(LAYER_AT[1])) return 1;
  if (frame < enterFrame(LAYER_AT[2])) return 2;
  return 3;
}

/** Which scene object is the hero. Changes on spoken sub-phrases, not once per dimension. */
export type HeroId = "none" | "house" | "work" | "school" | "stay" | "family" | "cost";

const HERO_AT: { at: number; id: HeroId }[] = [
  { at: 5.44, id: "house" },
  { at: 7.88, id: "work" },
  { at: 9.76, id: "school" },
  { at: 11.04, id: "stay" },
  { at: 16.52, id: "family" },
  { at: 30.44, id: "cost" },
];

export function heroAt(frame: number): HeroId {
  let id: HeroId = "none";
  for (const row of HERO_AT) {
    if (frame >= enterFrame(row.at)) id = row.id;
  }
  return id;
}

export function heroEnter(frame: number): number {
  let at = 0;
  for (const row of HERO_AT) {
    if (frame >= enterFrame(row.at)) at = enterFrame(row.at);
  }
  return easeOut((frame - at) / 12);
}

export type FamilyFocus = "assemble" | "household" | "parents";

export function familyFocus(frame: number): FamilyFocus {
  if (frame >= enterFrame(28.56)) return "parents";
  if (frame >= enterFrame(24.92)) return "household";
  return "assemble";
}

/** Parents and the extra adult appear when the line about them starts. */
export function familyExtended(frame: number): boolean {
  return frame >= enterFrame(20.68);
}

export function costFan(frame: number): number {
  return easeOut((frame - enterFrame(32.2)) / 12);
}

export function plateOpacity(frame: number): number {
  return easeOut((frame - enterFrame(2.4)) / 14);
}

export function exitMix(frame: number): number {
  return easeOut((frame - enterFrame(33.0)) / 6);
}

function lerpRect(a: Rect, b: Rect, t: number): Rect {
  const m = easeOut(t);
  return {
    left: a.left + (b.left - a.left) * m,
    top: a.top + (b.top - a.top) * m,
    width: a.width + (b.width - a.width) * m,
    height: a.height + (b.height - a.height) * m,
  };
}

export function speakerRect(frame: number): Rect {
  const sceneIn = (frame - enterFrame(2.4)) / 16;
  const familyIn = (frame - enterFrame(16.52)) / 16;
  const costIn = (frame - enterFrame(30.44)) / 14;
  if (frame < enterFrame(2.4)) return SPEAKER_FULL;
  if (frame < enterFrame(16.52)) return lerpRect(SPEAKER_FULL, SPEAKER_SCENE, sceneIn);
  if (frame < enterFrame(30.44)) return lerpRect(SPEAKER_SCENE, SPEAKER_FAMILY, familyIn);
  return lerpRect(SPEAKER_FAMILY, SPEAKER_COST, costIn);
}

export function rectsOverlap(a: Rect, b: Rect): boolean {
  return a.left < b.left + b.width && a.left + a.width > b.left && a.top < b.top + b.height && a.top + a.height > b.top;
}

export const HERO_BOX: Rect = { left: 448, top: 200, width: 588, height: 1120 };
export const FAMILY_BOX: Rect = { left: 36, top: 200, width: 620, height: 1180 };
export const COST_BOX: Rect = { left: 360, top: 280, width: 680, height: 1200 };

type Copy = { kicker: string; title: string; house: string; work: string; school: string; few: string; long: string; spouse: string; household: string; parents: string; fee: string };

export const V2_COPY: Record<SupportedLocale, Copy> = {
  "zh-CN": {
    kicker: "三个筛选",
    title: "使用场景",
    house: "在当地住",
    work: "工作、开公司",
    school: "送孩子上学",
    few: "一年只去几天",
    long: "长期居住",
    spouse: "配偶与子女",
    household: "三口之家",
    parents: "照顾父母",
    fee: "申请费",
  },
  "en-US": {
    kicker: "Three filters",
    title: "Where you live",
    house: "Living there",
    work: "Work, a company",
    school: "A child in school",
    few: "A few days a year",
    long: "Long-term residence",
    spouse: "Spouse and children",
    household: "A household of three",
    parents: "Caring for parents",
    fee: "Application fee",
  },
  "ru-RU": {
    kicker: "Три фильтра",
    title: "Где жить",
    house: "Жизнь на месте",
    work: "Работа, компания",
    school: "Ребёнок в школе",
    few: "Несколько дней в году",
    long: "Долгое проживание",
    spouse: "Супруг и дети",
    household: "Семья из трёх",
    parents: "Забота о родителях",
    fee: "Сбор за заявление",
  },
};

export const DIMENSION_TITLE: Record<SupportedLocale, readonly [string, string, string]> = {
  "zh-CN": ["使用场景", "家庭结构", "代价"],
  "en-US": ["Where you live", "Who applies", "What it costs"],
  "ru-RU": ["Где жить", "Кто едет", "Какова цена"],
};

export function heroLabel(locale: SupportedLocale, hero: HeroId, focus: FamilyFocus): string {
  const copy = V2_COPY[locale];
  if (hero === "house") return copy.house;
  if (hero === "work") return copy.work;
  if (hero === "school") return copy.school;
  if (hero === "stay") return copy.few;
  if (hero === "family") return focus === "parents" ? copy.parents : focus === "household" ? copy.household : copy.spouse;
  if (hero === "cost") return copy.fee;
  return "";
}
