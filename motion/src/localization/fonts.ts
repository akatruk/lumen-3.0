import type { SupportedLocale, TypographyProfileId } from "./language-config";
import { LANGUAGE_CONFIG } from "./language-config";

export type TypographyProfile = {
  id: TypographyProfileId;
  fontFamily: string;
  fontFiles: readonly string[];
};

export const TYPOGRAPHY_PROFILES: Record<TypographyProfileId, TypographyProfile> = {
  latin: {
    id: "latin",
    fontFamily: 'Arial, "Helvetica Neue", Helvetica, sans-serif',
    fontFiles: ["/System/Library/Fonts/Supplemental/Arial.ttf", "/Library/Fonts/Arial.ttf"],
  },
  cyrillic: {
    id: "cyrillic",
    fontFamily: 'Arial, "Helvetica Neue", Helvetica, sans-serif',
    fontFiles: ["/System/Library/Fonts/Supplemental/Arial.ttf", "/Library/Fonts/Arial.ttf"],
  },
  cjk: {
    id: "cjk",
    fontFamily: '"PingFang SC", "Noto Sans SC", "Hiragino Sans GB", "Source Han Sans SC", sans-serif',
    fontFiles: [
      "/System/Library/Fonts/Hiragino Sans GB.ttc",
      "/System/Library/Fonts/STHeiti Medium.ttc",
      "/System/Library/Fonts/Supplemental/Songti.ttc",
      "/System/Library/Fonts/PingFang.ttc",
    ],
  },
};

export function fontFamilyFor(locale: SupportedLocale): string {
  return TYPOGRAPHY_PROFILES[LANGUAGE_CONFIG[locale].typographyProfile].fontFamily;
}

export const GLYPH_SAMPLES: Record<SupportedLocale, string> = {
  "en-US": "Planning to buy property?",
  "ru-RU": "Планируете купить недвижимость?",
  "zh-CN": "打算购买房产吗？",
};
