export const SUPPORTED_LOCALES = ["en-US", "ru-RU", "zh-CN"] as const;

export type SupportedLocale = (typeof SUPPORTED_LOCALES)[number];

export type TypographyProfileId = "latin" | "cyrillic" | "cjk";

export type LanguageConfig = {
  label: string;
  script: "latin" | "cyrillic" | "han";
  direction: "ltr";
  typographyProfile: TypographyProfileId;
};

export const LANGUAGE_CONFIG: Record<SupportedLocale, LanguageConfig> = {
  "en-US": { label: "English", script: "latin", direction: "ltr", typographyProfile: "latin" },
  "ru-RU": { label: "Русский", script: "cyrillic", direction: "ltr", typographyProfile: "cyrillic" },
  "zh-CN": { label: "中文", script: "han", direction: "ltr", typographyProfile: "cjk" },
};

export function isSupportedLocale(value: string): value is SupportedLocale {
  return (SUPPORTED_LOCALES as readonly string[]).includes(value);
}
