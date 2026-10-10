import { flattenMessages, t } from "./index";
import { SUPPORTED_LOCALES, type SupportedLocale } from "./language-config";
import { messages as en } from "./locales/en-US";

/** Semantic ids. Display text lives in the locale packs, not in filenames or asset tags. */
export const GLOSSARY_IDS = Object.keys(flattenMessages(en.realEstate, "realEstate")).sort();

export function glossaryEntry(id: string): Record<SupportedLocale, string> {
  const row = {} as Record<SupportedLocale, string>;
  for (const locale of SUPPORTED_LOCALES) row[locale] = t(locale, id);
  return row;
}
