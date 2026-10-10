import { LocalizationError, t } from "./index";
import type { SupportedLocale } from "./language-config";

const SYMBOLS: Record<string, string> = { THB: "THB", USD: "$" };

function grouped(value: number, locale: SupportedLocale, digits = 0): string {
  return new Intl.NumberFormat(locale, {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  }).format(value);
}

export function formatNumber(value: number, locale: SupportedLocale, digits = 0): string {
  if (!Number.isFinite(value)) throw new LocalizationError("invalid number");
  return grouped(value, locale, digits);
}

export function formatCurrency(value: number, currency: string, locale: SupportedLocale): string {
  if (!Number.isFinite(value)) throw new LocalizationError("invalid number");
  if (!/^[A-Z]{3}$/.test(currency)) throw new LocalizationError(`invalid currency ${currency}`);
  const symbol = SYMBOLS[currency];
  const amount = grouped(value, locale, 0);
  if (!symbol) {
    return new Intl.NumberFormat(locale, { style: "currency", currency, maximumFractionDigits: 0 }).format(value);
  }
  if (symbol.length > 1) return locale === "ru-RU" ? `${amount} ${symbol}` : `${symbol} ${amount}`;
  return locale === "ru-RU" ? `${amount} ${symbol}` : `${symbol}${amount}`;
}

/** Compact display. The currency code stays the one on the property. */
export function formatCompactCurrency(value: number, currency: string, locale: SupportedLocale): string {
  if (!Number.isFinite(value)) throw new LocalizationError("invalid number");
  if (!/^[A-Z]{3}$/.test(currency)) throw new LocalizationError(`invalid currency ${currency}`);
  const symbol = SYMBOLS[currency] ?? currency;
  const glue = symbol.length > 1 ? " " : "";
  if (locale === "zh-CN" && Math.abs(value) >= 10000) {
    const wan = value / 10000;
    const digits = Number.isInteger(wan) ? 0 : 1;
    return `${symbol}${glue}${grouped(wan, locale, digits)}万`;
  }
  if (Math.abs(value) >= 1_000_000) {
    const millions = value / 1_000_000;
    const digits = Number.isInteger(millions) ? 0 : 1;
    const amount = grouped(millions, locale, digits);
    if (locale === "ru-RU") return `${amount} млн ${symbol}`;
    return symbol.length > 1 ? `${symbol} ${amount}M` : `${symbol}${amount}M`;
  }
  return formatCurrency(value, currency, locale);
}

export function formatPercent(value: number, locale: SupportedLocale): string {
  if (!Number.isFinite(value)) throw new LocalizationError("invalid number");
  const digits = Number.isInteger(value) ? 0 : 1;
  return `${grouped(value, locale, digits)}%`;
}

export function formatDate(date: Date, locale: SupportedLocale): string {
  if (Number.isNaN(date.getTime())) throw new LocalizationError("invalid date");
  return new Intl.DateTimeFormat(locale, { day: "numeric", month: "long", year: "numeric" }).format(date);
}

export function formatArea(sqm: number, locale: SupportedLocale): string {
  return `${grouped(sqm, locale, 0)} ${t(locale, "units.sqm")}`;
}

const BEDROOMS: Record<SupportedLocale, { one?: string; few?: string; many?: string; other: string }> = {
  "en-US": { one: "bedroom", other: "bedrooms" },
  "ru-RU": { one: "спальня", few: "спальни", many: "спален", other: "спальни" },
  "zh-CN": { other: "间卧室" },
};

const BATHROOMS: Record<SupportedLocale, { one?: string; few?: string; many?: string; other: string }> = {
  "en-US": { one: "bathroom", other: "bathrooms" },
  "ru-RU": { one: "ванная", few: "ванные", many: "ванных", other: "ванные" },
  "zh-CN": { other: "间卫生间" },
};

function countPhrase(count: number, locale: SupportedLocale, forms: (typeof BEDROOMS)["en-US"]): string {
  const rule = new Intl.PluralRules(locale).select(count);
  const word = (forms as Record<string, string | undefined>)[rule] ?? forms.other;
  if (!word) throw new LocalizationError(`missing plural for ${locale} ${rule}`);
  return locale === "zh-CN" ? `${count}${word}` : `${grouped(count, locale, 0)} ${word}`;
}

export function formatBedrooms(count: number, locale: SupportedLocale): string {
  return countPhrase(count, locale, BEDROOMS[locale]);
}

export function formatBathrooms(count: number, locale: SupportedLocale): string {
  return countPhrase(count, locale, BATHROOMS[locale]);
}
