import { messages as en } from "./locales/en-US";
import { messages as ru } from "./locales/ru-RU";
import { messages as zh } from "./locales/zh-CN";
import { isSupportedLocale, LANGUAGE_CONFIG, SUPPORTED_LOCALES, type SupportedLocale } from "./language-config";

export class LocalizationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "LocalizationError";
  }
}

export function flattenMessages(tree: object, prefix = ""): Record<string, string> {
  const out: Record<string, string> = {};
  for (const [key, value] of Object.entries(tree)) {
    const path = prefix ? `${prefix}.${key}` : key;
    if (typeof value === "string") out[path] = value;
    else if (value && typeof value === "object") Object.assign(out, flattenMessages(value, path));
  }
  return out;
}

const FLAT: Record<SupportedLocale, Record<string, string>> = {
  "en-US": flattenMessages(en),
  "ru-RU": flattenMessages(ru),
  "zh-CN": flattenMessages(zh),
};

export function messageKeys(): string[] {
  return Object.keys(FLAT["en-US"]).sort();
}

/** Resolve one string. A missing translation throws. English is never substituted. */
export function t(locale: SupportedLocale, key: string): string {
  if (!isSupportedLocale(locale)) {
    throw new LocalizationError(`unsupported locale ${String(locale)}`);
  }
  const value = FLAT[locale][key];
  if (!value) throw new LocalizationError(`missing ${locale} translation for ${key}`);
  return value;
}

export function sameKeysAcrossLocales(): void {
  const expected = messageKeys();
  for (const locale of SUPPORTED_LOCALES) {
    const keys = Object.keys(FLAT[locale]).sort();
    if (keys.join("\n") !== expected.join("\n")) {
      throw new LocalizationError(`${locale} message keys do not match en-US`);
    }
  }
}

export { LANGUAGE_CONFIG, SUPPORTED_LOCALES, isSupportedLocale };
export type { SupportedLocale };
