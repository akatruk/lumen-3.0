import type { SupportedLocale } from "./language-config";

export type LayoutHint = {
  headlineMaxLines: number;
  headlineScale: number;
};

export const CARD_LAYOUT_HINTS: Record<string, Record<SupportedLocale, LayoutHint>> = {
  kinetic_hook: {
    "en-US": { headlineMaxLines: 3, headlineScale: 1 },
    "ru-RU": { headlineMaxLines: 4, headlineScale: 0.92 },
    "zh-CN": { headlineMaxLines: 3, headlineScale: 1.05 },
  },
  key_takeaway: {
    "en-US": { headlineMaxLines: 4, headlineScale: 1 },
    "ru-RU": { headlineMaxLines: 5, headlineScale: 0.88 },
    "zh-CN": { headlineMaxLines: 3, headlineScale: 1.05 },
  },
  caption_card: {
    "en-US": { headlineMaxLines: 4, headlineScale: 1 },
    "ru-RU": { headlineMaxLines: 5, headlineScale: 0.9 },
    "zh-CN": { headlineMaxLines: 3, headlineScale: 1 },
  },
};

export function hintFor(cardId: string, locale: SupportedLocale): LayoutHint {
  return CARD_LAYOUT_HINTS[cardId]?.[locale] ?? { headlineMaxLines: 4, headlineScale: 1 };
}
