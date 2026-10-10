import { lookupCard } from "../cards/registry";
import { TYPOGRAPHY_PROFILES } from "./fonts";
import { formatCurrency } from "./formatter";
import { LANGUAGE_CONFIG, isSupportedLocale, type SupportedLocale } from "./language-config";
import { LocalizationError, t } from "./index";

export function validateLocalizedCard(cardId: string, locale: string, data?: { currency?: string }): void {
  const card = lookupCard(cardId);
  if (!card) throw new LocalizationError(`unknown card ${cardId}`);
  if (!isSupportedLocale(locale) || !card.supportedLocales.includes(locale)) {
    throw new LocalizationError(`unsupported locale ${locale} for ${cardId}`);
  }
  const profile = LANGUAGE_CONFIG[locale].typographyProfile;
  if (!TYPOGRAPHY_PROFILES[profile]) throw new LocalizationError(`unsupported typography profile ${profile}`);
  for (const key of card.requiredKeys) t(locale as SupportedLocale, key);
  if (data?.currency !== undefined) formatCurrency(0, data.currency, locale);
}
