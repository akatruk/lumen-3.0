import type { SupportedLocale } from "../localization/language-config";

export const GOLD_FPS = 30;
export const GOLD_OFFSET = 42.8;
export const GOLD_DURATION = 33.2;

/** Spoken moments inside the excerpt, taken from the saved transcript. */
export const LAYER_AT = [2.4, 16.52, 30.44] as const;

export const GOLD_FACE = { left: 220, top: 520, width: 620, height: 700 };
export const GOLD_GRAPHIC = { left: 548, top: 28, width: 496, height: 456 };
export const GOLD_CAPTION = { left: 64, top: 1596, width: 952, height: 176 };

export type Rect = { left: number; top: number; width: number; height: number };

export const LAYER_COPY: Record<SupportedLocale, readonly [string, string, string]> = {
  "zh-CN": ["使用场景", "家庭结构", "代价"],
  "en-US": ["Where you live", "Who applies", "What it costs"],
  "ru-RU": ["Где жить", "Кто едет", "Какова цена"],
};

export const LAYER_INDEX: Record<SupportedLocale, readonly [string, string, string]> = {
  "zh-CN": ["第一层", "第二层", "第三层"],
  "en-US": ["Layer 1", "Layer 2", "Layer 3"],
  "ru-RU": ["Слой 1", "Слой 2", "Слой 3"],
};

export const CAPTIONS: { start: number; end: number; text: string }[] = [
  { start: 0, end: 2.4, text: "我建议先做三个筛选" },
  { start: 2.4, end: 4.6, text: "第一层叫使用场景" },
  { start: 4.6, end: 5.44, text: "未来五年" },
  { start: 5.44, end: 7.88, text: "你每年愿意在当地住多久" },
  { start: 7.88, end: 8.96, text: "会不会工作" },
  { start: 8.96, end: 9.76, text: "开公司" },
  { start: 9.76, end: 11.04, text: "送孩子上学" },
  { start: 11.04, end: 13.04, text: "如果一年只能去几天" },
  { start: 13.04, end: 14.8, text: "就不要研究依赖长期" },
  { start: 14.8, end: 16.4, text: "真实居住的路线" },
  { start: 16.52, end: 18.76, text: "第二层叫家庭结构" },
  { start: 18.76, end: 20.68, text: "配偶未成年子女" },
  { start: 20.68, end: 23.6, text: "成年子女和父母能否一起申请" },
  { start: 23.6, end: 24.92, text: "各国定义不同" },
  { start: 24.92, end: 27.32, text: "今天适合三口之家的方案" },
  { start: 27.32, end: 28.56, text: "可能完全不适合" },
  { start: 28.56, end: 30.44, text: "需要照顾父母的家庭" },
  { start: 30.44, end: 32.2, text: "第三层叫代价" },
  { start: 32.2, end: 33.2, text: "这里不只是申请费" },
];

export function rectsOverlap(a: Rect, b: Rect): boolean {
  return a.left < b.left + b.width && a.left + a.width > b.left && a.top < b.top + b.height && a.top + a.height > b.top;
}

export function enterFrame(at: number): number {
  return Math.round(at * GOLD_FPS);
}

export type LayerMotion = {
  visible: boolean;
  opacity: number;
  rise: number;
  scale: number;
  draw: number;
  reduced: boolean;
};

const clamp01 = (value: number) => Math.min(1, Math.max(0, value));

/** Cubic ease-out. Frame in, frame out. Same input always returns the same motion. */
export function layerMotion(frame: number, index: number, exitStart = 985): LayerMotion {
  const enter = enterFrame(LAYER_AT[index]);
  const next = index < 2 ? enterFrame(LAYER_AT[index + 1]) : exitStart;
  const local = frame - enter;
  if (local < 0) return { visible: false, opacity: 0, rise: 28, scale: 1, draw: 0, reduced: false };
  const arrive = clamp01(local / 16);
  const eased = 1 - (1 - arrive) ** 3;
  const reduced = frame >= next && index < 2;
  const reduce = reduced ? clamp01((frame - next) / 12) : 0;
  const exit = frame >= exitStart ? clamp01((frame - exitStart) / 10) : 0;
  const exitEased = exit * exit;
  return {
    visible: exit < 1,
    opacity: eased * (1 - exitEased) * (reduced ? 0.72 + 0.28 * (1 - reduce) : 1),
    rise: (1 - eased) * 28 - exitEased * 48,
    scale: 1 - reduce * 0.06,
    draw: clamp01((local - 4) / 14),
    reduced,
  };
}

export function visibleLayerCount(frame: number): number {
  return LAYER_AT.filter((at) => frame >= enterFrame(at)).length;
}

export function captionAt(seconds: number): string {
  const row = CAPTIONS.find((item) => seconds >= item.start && seconds < item.end);
  return row?.text ?? "";
}
