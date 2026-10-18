/**
 * Isolated editorial proof. Not a Director scene recipe.
 * Clock is the original3 gold excerpt: source time = excerpt + GOLD_OFFSET.
 */
import { GOLD_OFFSET } from "../threeLayersModel";

export const STORY_FPS = 30;
export const STORY_START_FRAME = 392;
export const STORY_START = STORY_START_FRAME / STORY_FPS;
export const STORY_END = 33.2;
export const STORY_FRAMES = Math.round((STORY_END - STORY_START) * STORY_FPS);

export const PAPER = "#f3eee6";
export const INK = "#1c1612";
export const ACCENT = "#9c3b2e";
export const GROUND = "#14110f";

export const CAPTION_BAND = { left: 64, top: 1704, width: 952, height: 148 };

export type Rect = { left: number; top: number; width: number; height: number };

export const SPEAKER_A: Rect = { left: 0, top: 0, width: 1080, height: 1920 };
export const SPEAKER_B: Rect = { left: 736, top: 64, width: 292, height: 448 };
export const SPEAKER_C: Rect = { left: 28, top: 48, width: 320, height: 480 };
export const SPEAKER_D: Rect = { left: 0, top: 0, width: 500, height: 1920 };

export const PLATES = {
  adultA: { file: "adult-a.png", w: 329, h: 1082, height: 780 },
  adultB: { file: "adult-b.png", w: 308, h: 1102, height: 760 },
  child: { file: "child.png", w: 397, h: 1018, height: 540 },
  youth: { file: "youth.png", w: 306, h: 1070, height: 560 },
  elderA: { file: "elder-a.png", w: 328, h: 1094, height: 720 },
  elderB: { file: "elder-b.png", w: 345, h: 1122, height: 740 },
} as const;

export type PlateId = keyof typeof PLATES;

export const FEET = 1520;
export const V1_PROOF_SHA = "c0f92a027ec41c5dbab26b10136900bc112d087053d4223ce9923df48dcfbc02";

export function plateWidth(id: PlateId): number {
  const plate = PLATES[id];
  return (plate.height * plate.w) / plate.h;
}

export function easeOut(t: number): number {
  const x = Math.min(1, Math.max(0, t));
  return 1 - (1 - x) ** 3;
}

export function rise(excerpt: number, at: number, span: number): number {
  if (excerpt <= at) return 0;
  return easeOut((excerpt - at) / span);
}

export function storyExcerpt(frame: number): number {
  return STORY_START + frame / STORY_FPS;
}

export function sourceTime(excerpt: number): number {
  return excerpt + GOLD_OFFSET;
}

export type SceneId = "A" | "B" | "C" | "D";

export function sceneAt(excerpt: number): SceneId {
  if (excerpt < 18.76) return "A";
  if (excerpt < 20.68) return "B";
  if (excerpt < 24.92) return "C";
  return "D";
}

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

function lerpRect(a: Rect, b: Rect, t: number): Rect {
  return {
    left: lerp(a.left, b.left, t),
    top: lerp(a.top, b.top, t),
    width: lerp(a.width, b.width, t),
    height: lerp(a.height, b.height, t),
  };
}

export function speakerBox(excerpt: number): Rect {
  const ab = rise(excerpt, 18.76, 0.28);
  const bc = rise(excerpt, 20.52, 0.24);
  const cd = rise(excerpt, 24.78, 0.2);
  if (ab <= 0) return SPEAKER_A;
  if (bc <= 0) return lerpRect(SPEAKER_A, SPEAKER_B, ab);
  if (cd <= 0) return lerpRect(SPEAKER_B, SPEAKER_C, bc);
  return lerpRect(SPEAKER_C, SPEAKER_D, cd);
}

export function photoOpacity(excerpt: number): number {
  return rise(excerpt, 18.76, 0.18) * (1 - rise(excerpt, 20.36, 0.22));
}

export function familyOpacity(excerpt: number): number {
  return rise(excerpt, 20.52, 0.2) * (1 - rise(excerpt, 24.7, 0.18));
}

export function documentOpacity(excerpt: number): number {
  return rise(excerpt, 24.78, 0.16);
}

export type PersonPose = {
  id: PlateId;
  left: number;
  top: number;
  width: number;
  height: number;
  opacity: number;
};

export function familyPoses(excerpt: number): PersonPose[] {
  const spread = rise(excerpt, 21.0, 0.36);
  const adults = rise(excerpt, 20.52, 0.16);
  const childIn = rise(excerpt, 20.62, 0.16);
  const kin = rise(excerpt, 21.05, 0.32);
  const aw = plateWidth("adultA");
  const bw = plateWidth("adultB");
  const cw = plateWidth("child");
  const yw = plateWidth("youth");
  const eaw = plateWidth("elderA");
  const ebw = plateWidth("elderB");
  const coreW = aw + 36 + bw;
  const extW = eaw + 24 + ebw;
  const coreLeft = lerp((1080 - coreW) / 2, 24, spread);
  const extLeft = lerp(1120, coreLeft + coreW + 48, spread);
  const pose = (id: PlateId, left: number, opacity: number): PersonPose => {
    const height = PLATES[id].height;
    const width = plateWidth(id);
    return { id, left, top: FEET - height, width, height, opacity };
  };
  return [
    pose("adultA", coreLeft, adults),
    pose("adultB", coreLeft + aw + 36, adults),
    pose("elderA", extLeft, kin),
    pose("elderB", extLeft + eaw + 24, kin),
    pose("child", coreLeft + (coreW - cw) / 2, childIn),
    pose("youth", extLeft + (extW - yw) / 2, kin),
  ];
}

export function clusterLabel(excerpt: number, ids: PlateId[]): Rect {
  const people = familyPoses(excerpt).filter((person) => ids.includes(person.id) && person.id !== "child" && person.id !== "youth");
  const left = Math.min(...people.map((person) => person.left));
  const right = Math.max(...people.map((person) => person.left + person.width));
  return { left, top: FEET + 16, width: right - left, height: 72 };
}

export function graphicLabel(excerpt: number): string {
  if (excerpt < 16.52) return "";
  if (excerpt < 18.76) return "家庭结构";
  if (excerpt < 24.92) return "";
  if (excerpt < 28.56) return "三口之家";
  if (excerpt < 30.44) return "照顾父母";
  if (excerpt < 32.2) return "代价";
  return "申请费";
}

export function documentBox(_excerpt: number): Rect {
  return { left: 500, top: 0, width: 580, height: 1648 };
}

export function rectsOverlap(a: Rect, b: Rect): boolean {
  return a.left < b.left + b.width && a.left + a.width > b.left && a.top < b.top + b.height && a.top + a.height > b.top;
}
